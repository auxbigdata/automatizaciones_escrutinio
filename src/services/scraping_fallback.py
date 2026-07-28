"""
Fallback genérico: se usa cuando no hay parser específico para el dominio
(parsers_html.py/json.py/spa.py) o cuando este devolvió una lista vacía.
Separa número/extra, filtra patrones que no son resultados (años, horas,
montos) y arma el dict con construir_resultado(). No inventa fechas: si
no hay fecha explícita, el campo queda None.
"""
import re
from bs4 import BeautifulSoup
from src.services.utils_scraping import (
    construir_resultado,
    separar_numero_y_extra,
    clasificar_extra,
    normalizar_fecha,
    extraer_fecha_de_texto_libre,
    limpiar_texto,
)

PATRON_HORA = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")
PATRON_SORTEO_PREFIJO = re.compile(r"sorteo\s*\d+", re.IGNORECASE)
PATRON_MONTO = re.compile(r"[$]\s*[\d.,]+")
PATRON_ANIO = re.compile(r"\b202[0-9]\b")
PATRON_NUMERO_EN_CUALQUIER_POSICION = re.compile(r"\b(\d{3,4})\b")


def _buscar_numero_en_cualquier_posicion(texto: str):
    """
    Busca el primer número de 3-4 dígitos en cualquier posición (a diferencia
    de separar_numero_y_extra, que exige que esté al inicio), excluyendo años.
    """
    t = PATRON_ANIO.sub("", texto)
    m = PATRON_NUMERO_EN_CUALQUIER_POSICION.search(t)
    return m.group(1) if m else None


def _texto_parece_resultado_valido(texto: str) -> bool:
    """Filtra textos que casi seguro NO son resultados (horas, montos, años sueltos)."""
    t = texto.strip()
    if PATRON_HORA.match(t):
        return False
    if PATRON_MONTO.search(t):
        return False
    return True


def scraping_fallback_json(data, url: str, log=None) -> list[dict]:
    """
    Fallback para APIs JSON sin parser específico. Busca recursivamente
    diccionarios con un número de 3-4 cifras y otro campo de texto, y
    construye el dict estandarizado.
    """
    resultados = []

    def buscar(obj):
        if isinstance(obj, dict):
            valores_str = [str(v) for v in obj.values() if isinstance(v, (str, int, float)) and v]
            texto_unido = " ".join(valores_str)

            numero = _buscar_numero_en_cualquier_posicion(texto_unido)
            if numero and len(valores_str) > 1:
                # Extra: lo que quede del valor que contenía el número, después de él
                extra = None
                for v in valores_str:
                    if numero in v and v != numero:
                        idx = v.find(numero) + len(numero)
                        resto = v[idx:].strip(" -()")
                        extra = resto if resto else None
                        break
                clasif = clasificar_extra(extra)
                # Nombre = primer valor de texto que no sea numérico ni fecha ISO
                nombre = "Desconocido"
                fecha_iso = None
                for v in valores_str:
                    if normalizar_fecha(v):
                        fecha_iso = normalizar_fecha(v)
                    elif numero not in v and not v.replace(".", "").replace(":", "").isdigit():
                        nombre = v
                resultados.append(construir_resultado(
                    nombre_sorteo=nombre,
                    numero=numero,
                    fecha_iso=fecha_iso,
                    fuente=url,
                    **clasif,
                ))
            else:
                for v in obj.values():
                    buscar(v)
        elif isinstance(obj, list):
            for item in obj:
                buscar(item)

    buscar(data)
    if log:
        log.info(f"Fallback JSON: se extrajeron {len(resultados)} posibles resultados de {url}")
    return resultados


def scraping_fallback_html(soup: BeautifulSoup, url: str, log=None) -> list[dict]:
    """
    Fallback para HTML sin parser específico. Combina estrategia A (filas de
    <table>) y B (divs/cards con clases sugerentes). A diferencia de los
    parsers específicos, no asume que el número esté al inicio: busca
    celda por celda.
    """
    resultados = []
    textos_vistos = set()

    # --- Estrategia A: tablas ---
    for tabla in soup.find_all("table"):
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all(["td", "th"])
            if len(celdas) < 2:
                continue
            textos = [limpiar_texto(c.get_text()) for c in celdas]
            # No limpiar años/prefijos en celdas que ya son fecha completa (evita romper "2026-06-19")
            textos_limpios = []
            for t in textos:
                if normalizar_fecha(t):
                    textos_limpios.append(t)
                else:
                    textos_limpios.append(PATRON_SORTEO_PREFIJO.sub("", PATRON_ANIO.sub("", t)))
            textos = textos_limpios

            # Primera celda con número válido, excluyendo las que son fecha
            numero = None
            extra = None
            celda_numero_idx = None
            for idx, t in enumerate(textos):
                if normalizar_fecha(t):
                    continue  # esta celda es una fecha, no un resultado
                if not _texto_parece_resultado_valido(t):
                    continue
                n, e = separar_numero_y_extra(t)
                if n:
                    numero, extra, celda_numero_idx = n, e, idx
                    break

            if not numero:
                continue

            # Nombre = primera celda no vacía distinta de la celda del número
            nombre = next(
                (t for idx, t in enumerate(textos) if t and idx != celda_numero_idx),
                "Desconocido",
            )
            # Fecha = primera celda que parezca fecha
            fecha_iso = None
            for t in textos:
                f = normalizar_fecha(t)
                if f:
                    fecha_iso = f
                    break

            clasif = clasificar_extra(extra)
            texto_unido = " ".join(textos)
            if texto_unido in textos_vistos:
                continue
            resultados.append(construir_resultado(
                nombre_sorteo=nombre,
                numero=numero,
                fecha_iso=fecha_iso,
                fuente=url,
                **clasif,
            ))
            textos_vistos.add(texto_unido)

    # --- Estrategia B: divs/cards con clases sugerentes ---
    patron_clases = re.compile(r"result|card|sorteo|balota|score|ganador|premio|chance", re.I)
    elementos = soup.find_all(attrs={"class": patron_clases})

    for el in elementos:
        if len(el.find_all()) > 50:
            continue

        texto = limpiar_texto(el.get_text())
        if not texto or len(texto) < 5 or texto in textos_vistos:
            continue

        texto_sin_anios_para_filtro = PATRON_ANIO.sub("", texto)
        texto_sin_sorteo = PATRON_SORTEO_PREFIJO.sub("", texto_sin_anios_para_filtro)

        if not _texto_parece_resultado_valido(texto_sin_sorteo):
            continue

        # En cards el texto viene todo junto ("Nombre Fecha Número[-extra]"), por eso se busca en cualquier posición
        numero = _buscar_numero_en_cualquier_posicion(texto_sin_sorteo)
        if not numero:
            continue
        idx = texto_sin_sorteo.find(numero)
        resto_despues = texto_sin_sorteo[idx + len(numero):].strip(" -()")
        # Extra = solo la primera palabra después del número (evita arrastrar el resto de la frase)
        extra = resto_despues.split(" ")[0] if resto_despues else None

        clasif = clasificar_extra(extra)
        fecha_iso = extraer_fecha_de_texto_libre(texto)

        # Nombre = texto antes de la fecha (o del número), si tiene un largo razonable
        nombre = "Desconocido"
        corte = None
        if fecha_iso and fecha_iso in texto:
            corte = texto.find(fecha_iso)
        else:
            corte = texto.find(numero)
        if corte and corte > 0:
            candidato = limpiar_texto(texto[:corte])
            if 2 <= len(candidato) <= 40:
                nombre = candidato

        resultados.append(construir_resultado(
            nombre_sorteo=nombre,
            numero=numero,
            fecha_iso=fecha_iso,
            fuente=url,
            **clasif,
        ))
        textos_vistos.add(texto)

    if log:
        log.info(f"Fallback HTML: se extrajeron {len(resultados)} posibles resultados de {url}")
    return resultados
