"""
Parsers HTML por sitio. Reciben un BeautifulSoup con el HTML ya renderizado
(tras JS, si aplica) y devuelven una lista de dicts estandarizados. Nunca
lanzan excepción por "no encontré nada": devuelven [] y el llamador cae al
fallback genérico.
"""
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.services.utils_scraping import (
    construir_resultado,
    separar_numero_y_extra,
    clasificar_extra,
    normalizar_fecha,
    limpiar_texto,
    fecha_hoy_iso,
    es_signo_zodiacal,
    homologar_nombre_sorteo,
)


def _texto_tabla_por_columnas(tabla, log=None) -> list[list[str]]:
    """Extrae todas las filas de una tabla como listas de textos de celda."""
    filas_out = []
    for fila in tabla.find_all("tr"):
        celdas = fila.find_all(["td", "th"])
        if not celdas:
            continue

        fila_texto = []
        for c in celdas:
            texto = limpiar_texto(c.get_text())
            # Sin texto visible: buscar en title/alt de una imagen
            if not texto:
                img = c.find("img")
                if img:
                    texto = limpiar_texto(img.get("title") or img.get("alt") or "")
            fila_texto.append(texto)

        filas_out.append(fila_texto)
    return filas_out


def parsear_acertemos(soup: BeautifulSoup, url: str, log=None) -> list[dict]:

    resultados = []

    hoy = fecha_hoy_iso()  # Formato YYYY-MM-DD

    tablas = soup.find_all("table")

    for tabla in tablas:
        filas = _texto_tabla_por_columnas(tabla)
        for fila in filas:
            if len(fila) < 3:
                continue
            fecha_extraida, nombre, resultado_crudo = fila[0], fila[1], fila[2]

            # Normalizar fecha (dd/mm/yyyy → YYYY-MM-DD)
            fecha_iso = normalizar_fecha(fecha_extraida)

            # Solo resultados de hoy
            if fecha_iso != hoy:
                continue

            numero, extra = separar_numero_y_extra(resultado_crudo)
            if not numero:
                continue

            # Usar nombre homologado
            nombre = homologar_nombre_sorteo(nombre)

            clasif = clasificar_extra(extra)
            resultados.append(construir_resultado(
                nombre_sorteo=nombre,
                numero=numero,
                fecha_iso=fecha_iso,
                fuente=url,
                **clasif,
            ))

    return resultados


# Timeout en segundos para la petición POST a perlatodo
_TIMEOUT_POST = 15

# Headers mínimos para que el servidor no rechace la petición
_HEADERS_POST = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://perlatodo.com/perla/resultados/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def parsear_perlatodo(soup: BeautifulSoup, url: str, log=None) -> list[dict]:

    resultados = []
    hoy = fecha_hoy_iso()

    # --- Intentar POST con fecha de hoy ---
    html_completo = None
    try:
        resp = requests.post(
            url,
            data={"fecha": hoy},
            headers=_HEADERS_POST,
            timeout=_TIMEOUT_POST,
        )
        resp.raise_for_status()
        html_completo = resp.text
        if log:
            log.info(
                f"perlatodo: POST con fecha={hoy} exitoso "
                f"({len(html_completo)} bytes)"
            )
    except Exception as e:
        if log:
            log.warning(
                f"perlatodo: no se pudo hacer POST con fecha={hoy} ({e}). "
                f"Se usa el HTML inicial como fallback parcial."
            )

    # Parsear el HTML completo (del POST) o el inicial (fallback)
    soup_a_parsear = (
        BeautifulSoup(html_completo, "html.parser")
        if html_completo
        else soup
    )

    tablas = soup_a_parsear.find_all("table")

    # Evitar duplicados por (nombre, fecha)
    sorteos_procesados = set()

    for tabla in tablas:
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all(["td", "th"])
            if len(celdas) < 3:
                continue
            textos = [limpiar_texto(c.get_text()) for c in celdas]
            nombre, numero_crudo, fecha_txt = textos[0], textos[1], textos[2]

            if not nombre or nombre.lower() in ("nombre", "sorteo"):
                continue  # saltar cabecera si viene como <td>

            fecha_iso = normalizar_fecha(fecha_txt)

            # Solo resultados de hoy
            if fecha_iso != hoy:
                continue

            numero, extra = separar_numero_y_extra(numero_crudo)
            if not numero:
                continue

            # Usar nombre homologado
            nombre = homologar_nombre_sorteo(nombre)

            identificador_unico = (nombre, fecha_iso)
            if identificador_unico in sorteos_procesados:
                continue

            sorteos_procesados.add(identificador_unico)

            clasif = clasificar_extra(extra)
            resultados.append(construir_resultado(
                nombre_sorteo=nombre,
                numero=numero,
                fecha_iso=fecha_iso,
                fuente=url,
                **clasif,
            ))

    return resultados


def parsear_jer(soup: BeautifulSoup, url: str, log=None) -> list[dict]:

    resultados = []
    hoy = fecha_hoy_iso()
    tablas = soup.find_all("table")

    for tabla in tablas:
        filas = tabla.find_all("tr")
        if not filas:
            continue

        # Detectar encabezado (puede no tener <th>, se identifica por palabras clave)
        encabezado = [limpiar_texto(c.get_text()).lower() for c in filas[0].find_all(["td", "th"])]
        tiene_quinta = "quinta" in encabezado
        tiene_serie = "serie" in encabezado
        tiene_signo = "signo" in encabezado
        idx_fecha = encabezado.index("fecha") if "fecha" in encabezado else None

        for fila in filas[1:]:
            celdas = fila.find_all(["td", "th"])
            if len(celdas) < 3:
                continue
            textos = [limpiar_texto(c.get_text()) for c in celdas]

            nombre = textos[0]
            # Usar nombre homologado
            nombre = homologar_nombre_sorteo(nombre)

            numero_crudo = textos[1] if len(textos) > 1 else ""
            numero, _ = separar_numero_y_extra(numero_crudo)
            if not numero:
                continue

            quinta = None
            serie = None
            signo = None
            fecha_txt = None

            col = 2
            if tiene_quinta and col < len(textos):
                quinta = textos[col] or None
                col += 1
            if tiene_serie and col < len(textos):
                serie = textos[col] or None
                col += 1
            if tiene_signo and col < len(textos):
                signo = textos[col] or None
                col += 1
            if idx_fecha is not None and idx_fecha < len(textos):
                fecha_txt = textos[idx_fecha]
            elif col < len(textos):
                fecha_txt = textos[col]

            fecha_iso = normalizar_fecha(fecha_txt) if fecha_txt else None

            # Validar fecha de hoy
            if fecha_iso != hoy:
                continue

            resultados.append(construir_resultado(
                nombre_sorteo=nombre,
                numero=numero,
                fecha_iso=fecha_iso,
                serie=serie,
                quinta=quinta,
                signo=signo,
                fuente=url,
            ))

    return resultados


def parsear_ganagana(soup: BeautifulSoup, url: str, log=None) -> list[dict]:
    """ganagana.com.co: tabla con columnas Sorteo | Fecha (YYYY-MM-DD) | Resultado."""
    resultados = []
    hoy = fecha_hoy_iso()
    tablas = soup.find_all("table")

    for tabla in tablas:
        filas = _texto_tabla_por_columnas(tabla)

        for fila in filas:
            if len(fila) < 3:
                continue

            nombre, fecha_txt, resultado_crudo = fila[0], fila[1], fila[2]
            # Usar nombre homologado
            nombre = homologar_nombre_sorteo(nombre)

            if not nombre:
                continue

            fecha_iso = normalizar_fecha(fecha_txt)

            # Validar fecha de hoy
            if fecha_iso != hoy:
                continue

            numero, extra = separar_numero_y_extra(resultado_crudo)
            if not numero:
                continue
            clasif = clasificar_extra(extra)
            resultados.append(construir_resultado(
                nombre_sorteo=nombre,
                numero=numero,
                fecha_iso=fecha_iso,
                fuente=url,
                **clasif,
            ))

    return resultados


def parsear_loteriasdehoy_co(soup: BeautifulSoup, url: str, log=None) -> list[dict]:
    resultados = []

    hoy = fecha_hoy_iso()

    # Divs de sorteo individual: clase termina en "_hoy"
    contenedores = soup.find_all(
        "div", class_=re.compile(r"(chances_hoy|loterias_hoy)$")
    )

    for cont in contenedores:
        # --- Nombre del sorteo ---
        titulo_div = cont.find(attrs={"class": re.compile(r"titulo_")})
        nombre = limpiar_texto(titulo_div.get_text()) if titulo_div else None
        # Usar nombre homologado
        nombre = homologar_nombre_sorteo(nombre)

        if not nombre:
            continue

        # --- Fecha ---
        fecha_div = cont.find(attrs={"class": re.compile(r"fecha_resultado")})
        fecha_iso = normalizar_fecha(limpiar_texto(fecha_div.get_text())) if fecha_div else None

        # Validar Fecha de hoy
        if fecha_iso != hoy:
            continue

        # --- Dígitos / extra ---
        resultado_div = cont.find(attrs={"class": re.compile(r"resultado_")})
        if not resultado_div:
            continue

        spans = resultado_div.find_all("span")
        if not spans:
            continue

        digitos_numero = []
        extra_valor = None
        tipo_extra = None  # "premio" (quinta), "serie", o "signo"

        for sp in spans:
            clases = " ".join(sp.get("class", []))
            valor = limpiar_texto(sp.get_text())
            if not valor:
                continue

            if re.search(r"premio", clases, re.IGNORECASE):
                extra_valor = valor
                tipo_extra = "premio"
            elif re.search(r"serie", clases, re.IGNORECASE):
                extra_valor = valor
                tipo_extra = "serie"
            elif re.search(r"signo", clases, re.IGNORECASE):
                extra_valor = valor
                tipo_extra = "signo"
            else:
                # Dígito del número principal
                digitos_numero.append(valor)

        if not digitos_numero:
            continue

        numero = "".join(digitos_numero)
        if not re.fullmatch(r"\d{3,4}", numero):
            # Descartar si no son 3-4 cifras limpias
            continue

        quinta = extra_valor if tipo_extra == "premio" else None
        serie = extra_valor if tipo_extra == "serie" else None
        signo = extra_valor.title() if tipo_extra == "signo" else None

        resultados.append(construir_resultado(
            nombre_sorteo=nombre,
            numero=numero,
            fecha_iso=fecha_iso,
            serie=serie,
            quinta=quinta,
            signo=signo,
            fuente=url,
        ))

    return resultados


def parsear_loteriasdehoy_com(soup: BeautifulSoup, url: str, log=None) -> list[dict]:

    hoy = fecha_hoy_iso()
    resultados = []

    contenedores = soup.find_all("div", class_="resultado-chance")

    for cont in contenedores:
        h3 = cont.find("h3")
        h4 = cont.find("h4")
        div_chance = cont.find("div", class_="chance")

        if not h3 or not div_chance:
            continue

        nombre = limpiar_texto(h3.get_text())

        # Usar nombre homologado
        nombre = homologar_nombre_sorteo(nombre)

        fecha_iso = normalizar_fecha(limpiar_texto(h4.get_text())) if h4 else None

        # Validar resultados de hoy
        if fecha_iso != hoy:
            continue

        digitos = [limpiar_texto(i.get_text()) for i in div_chance.find_all("i", class_="num")]
        digitos = [d for d in digitos if d]
        if not digitos:
            continue

        if "-" in digitos:
            idx_sep = digitos.index("-")
            digitos_numero = digitos[:idx_sep]
            digitos_extra = digitos[idx_sep + 1:]
        else:
            digitos_numero = digitos
            digitos_extra = []

        numero = "".join(digitos_numero)
        if not re.fullmatch(r"\d{3,4}", numero):
            continue

        extra_valor = "".join(digitos_extra) if digitos_extra else None
        clasif = clasificar_extra(extra_valor)

        # Signo zodiacal está en div hermano "astro-front"
        astro_div = cont.find("div", class_="astro-front")
        if astro_div:
            signo_texto = limpiar_texto(astro_div.get_text())
            if signo_texto:
                clasif["signo"] = signo_texto.title()

        resultados.append(construir_resultado(
            nombre_sorteo=nombre,
            numero=numero,
            fecha_iso=fecha_iso,
            fuente=url,
            **clasif,
        ))

    return resultados


def parsear_ganarchance(soup: BeautifulSoup, url: str, log=None) -> list[dict]:

    resultados = []
    hoy = fecha_hoy_iso()

    texto_completo = soup.get_text("\n")
    lineas = [limpiar_texto(l) for l in texto_completo.split("\n")]
    lineas = [l for l in lineas if l]

    fecha_actual = None
    pendiente_nombre = None

    patron_encabezado_fecha = re.compile(
        r"resultados de (hoy|ayer)\s+\w+\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})", re.IGNORECASE
    )

    # Patrón alternativo: "Nombre: XXXX[-extra]" en una sola línea
    patron_inline = re.compile(
        r"^(.{2,40}?)\s*[:\-]\s*(\d{3,4}(?:[\s\-()]\S+)?)$"
    )

    for linea in lineas:
        coincidencia_fecha = patron_encabezado_fecha.search(linea)
        if coincidencia_fecha:
            fecha_actual = normalizar_fecha(coincidencia_fecha.group(2))
            pendiente_nombre = None
            continue

        # Validar fecha de hoy
        if fecha_actual != hoy:
            continue

        # ¿Línea inline nombre+número? Ej: "Dorado Tarde: 3485-4"
        coincidencia_inline = patron_inline.match(linea)

        if coincidencia_inline:
            nombre_inline = limpiar_texto(coincidencia_inline.group(1))
            resultado_inline = limpiar_texto(coincidencia_inline.group(2))
            numero, extra = separar_numero_y_extra(resultado_inline)
            # Usar nombre homologado
            nombre_inline = homologar_nombre_sorteo(nombre_inline)

            if numero and nombre_inline:
                clasif = clasificar_extra(extra)

                resultados.append(construir_resultado(
                    nombre_sorteo=nombre_inline,
                    numero=numero,
                    fecha_iso=fecha_actual,
                    fuente=url,
                    **clasif,
                ))
                pendiente_nombre = None
                continue

        # ¿Línea es número de resultado? (modo dos líneas)
        numero, extra = separar_numero_y_extra(linea)
        # Usar nombre homologado
        pendiente_nombre = homologar_nombre_sorteo(pendiente_nombre)

        if numero and pendiente_nombre:
            clasif = clasificar_extra(extra)
            resultados.append(construir_resultado(
                nombre_sorteo=pendiente_nombre,
                numero=numero,
                fecha_iso=fecha_actual,
                fuente=url,
                **clasif,
            ))
            pendiente_nombre = None
        elif not numero and resultados and ("la 5ta:" in linea.lower() or es_signo_zodiacal(linea) or (len(linea.split()) == 1 and len(linea) == 3 and linea.isdigit())):
            # Parece un extra (quinta/signo/serie): se asigna al último resultado
            clasif = clasificar_extra(linea)
            ultimo_res = resultados[-1]
            if clasif.get("quinta"): ultimo_res["quinta"] = clasif["quinta"]
            if clasif.get("signo"): ultimo_res["signo"] = clasif["signo"]
            if clasif.get("serie"): ultimo_res["serie"] = clasif["serie"]
        elif not numero and 2 <= len(linea) <= 40 and not linea.lower().startswith("resultado"):
            # Si no es número/extra, asumir nombre de sorteo
            pendiente_nombre = linea

    return resultados


def parsear_loti(soup: BeautifulSoup, url: str, log=None) -> list[dict]:

    resultados = []
    hoy = fecha_hoy_iso()
    bloques = soup.select("div.result-single-page")

    for bloque in bloques:
        try:
            # 1. Nombre del sorteo
            img_tag = bloque.select_one("img[src*='/loterias/']")
            if not img_tag:
                continue
            nombre_raw = img_tag['src'].split('/')[-1].replace('.png', '')
            nombre_sorteo = limpiar_texto(nombre_raw)
            # Usar nombre homologado
            nombre_sorteo = homologar_nombre_sorteo(nombre_sorteo)

            # 2. Extracción de Fecha del HTML
            fecha_tag = bloque.select_one("div.result-single-date")
            fecha_iso = None
            if fecha_tag:
                fecha_txt = fecha_tag.get_text(strip=True)
                from datetime import datetime
                try:
                    fecha_iso = datetime.strptime(fecha_txt, "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception:
                    fecha_iso = None

            # 3. Validar fecha de hoy
            if fecha_iso != hoy:
                continue

            # 4. Extracción de Número y Quinta (Aislado)
            numero = None
            quinta = None

            # Filas de parámetros
            filas_params = bloque.select("div.result-single-params div.row")
            for fila in filas_params:
                texto_fila = fila.get_text(strip=True).upper()
                # Fila que dice "NÚMERO"
                if "NUMERO" in texto_fila or "NÚMERO" in texto_fila:
                    # Spans solo de esta fila
                    spans_num = fila.select("span.mx-1.bolder")
                    texto_num_aislado = "".join([p.get_text(strip=True) for p in spans_num])

                    # Texto limpio, ej: "3134-0"
                    match = re.search(r"(\d+)\s*-\s*(\d+)", texto_num_aislado)
                    if match:
                        numero = match.group(1)
                        quinta = match.group(2)
                    break  # Fila encontrada, salir

            if not numero:
                continue

            # Construir resultado
            resultado = construir_resultado(
                nombre_sorteo=nombre_sorteo,
                numero=numero,
                quinta=quinta,
                fecha_iso=fecha_iso,
                fuente=url
            )
            resultados.append(resultado)

        except Exception as e:
            if log:
                log.warning(f"Error procesando bloque en Loti: {e}")
            continue

    return resultados


PARSERS_HTML_POR_DOMINIO = {
    "acertemos.com": parsear_acertemos,
    "perlatodo.com": parsear_perlatodo,
    "jer.com.co": parsear_jer,
    "ganagana.com.co": parsear_ganagana,
    "loteriasdehoy.co": parsear_loteriasdehoy_co,
    "loteriasdehoy.com": parsear_loteriasdehoy_com,
    "ganarchance.com": parsear_ganarchance,
    "loti.com.co": parsear_loti,
}


def obtener_parser_html(url: str):
    hostname = (urlparse(url).hostname or "").lower()
    for dominio, parser in PARSERS_HTML_POR_DOMINIO.items():
        dominio = dominio.lower()
        if hostname == dominio or hostname.endswith("." + dominio):
            return parser
    return None
