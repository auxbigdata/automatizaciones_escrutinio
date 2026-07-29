"""
Scraping de respaldo (segundo scraping).

Se dispara desde el orquestador si una lotería queda sin resultado
validado o le falta quinta/signo, y desde src/robots/scraping.py como
respaldo total si el scraping principal falla por completo.

A diferencia del principal (busca UNA lotería por fuente), este motor
lee cada página completa y devuelve TODOS los sorteos del día, por eso
se consolida por nombre de lotería.
"""
from collections import Counter
from playwright.sync_api import sync_playwright
from src.services.escru_scraping import scraping_generico, obtener_paginas_db


def recolectar_pool_secundario(log, urls_excluir: set = None) -> list[dict]:
    """Recorre TODAS las páginas activas con el motor de respaldo y devuelve el pool combinado de resultados de hoy."""
    paginas = obtener_paginas_db()
    if not paginas:
        log.warning("Scraping de respaldo: no hay páginas activas en es_origenes_scraping")
        return []

    urls_excluir = urls_excluir or set()

    pool: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CO,es;q=0.9"
        })

        for pagina in paginas:
            url = pagina[2]

            if url in urls_excluir:
                log.info(f"Scraping de respaldo: se omite{url}")
                log.info(f"Ya aporto resultado en el scraping principal")
                continue
            try:
                pool.extend(scraping_generico(page, url, log))
            except Exception as e:
                log.warning(f"Scraping de respaldo: error navegando {url}: {e}")
                continue

        browser.close()

    log.info(f"Scraping de respaldo: {len(pool)} resultado(s) recolectados de {len(paginas)} página(s)")
    return pool


def filtrar_pool_por_loteria(pool: list[dict], nombre_loteria: str) -> list[dict]:
    """Filtra el pool crudo (sin consolidar) para una lotería puntual, en el mismo formato
    que usa el orquestador para las fuentes del principal (numero/quinta/signo/fuente).
    Se usa para SUMAR las fuentes del respaldo a las del principal antes de validar,
    en vez de exigirle al respaldo alcanzar el mínimo de fuentes por su cuenta."""
    return [
        {
            "numero": r["numero"],
            "quinta": r.get("quinta") or "",
            "signo" : r.get("signo") or "",
            "fuente": r.get("fuente"),
        }
        for r in pool
        if r.get("nombre_sorteo") == nombre_loteria and r.get("numero")
    ]


def consolidar_resultados_secundarios(pool: list[dict]) -> dict:
    """Agrupa el pool por lotería y saca el número mayoritario, junto con quinta/signo/serie mayoritarios entre las fuentes que reportaron ese número.

    Retorna {nombre_loteria: {"numero", "quinta", "signo", "serie", "fuentes", "total_coincidencias"}}.
    """
    por_loteria: dict[str, list[dict]] = {}
    for r in pool:
        nombre = r.get("nombre_sorteo")
        if not nombre:
            continue
        por_loteria.setdefault(nombre, []).append(r)

    consolidado = {}
    for nombre, candidatos in por_loteria.items():
        conteo_numero = Counter(c["numero"] for c in candidatos if c.get("numero"))
        if not conteo_numero:
            continue
        numero_mayoritario, total_coincidencias = conteo_numero.most_common(1)[0]

        candidatos_del_numero = [c for c in candidatos if c.get("numero") == numero_mayoritario]

        quinta = None
        conteo_quinta = Counter(c["quinta"] for c in candidatos_del_numero if c.get("quinta"))
        if conteo_quinta:
            quinta = conteo_quinta.most_common(1)[0][0]

        signo = None
        conteo_signo = Counter(c["signo"] for c in candidatos_del_numero if c.get("signo"))
        if conteo_signo:
            signo = conteo_signo.most_common(1)[0][0]

        serie = None
        conteo_serie = Counter(c["serie"] for c in candidatos_del_numero if c.get("serie"))
        if conteo_serie:
            serie = conteo_serie.most_common(1)[0][0]

        fuentes = [c.get("fuente") for c in candidatos_del_numero if c.get("fuente")]

        consolidado[nombre] = {
            "numero": numero_mayoritario,
            "quinta": quinta,
            "signo": signo,
            "serie": serie,
            "fuentes": fuentes,
            "total_coincidencias": total_coincidencias,
        }

    return consolidado


def buscar_respaldo_secundario(nombre_loteria: str, log, urls_excluir: set = None):
    """Casos 1 y 2: dispara el scraping de respaldo completo y devuelve lo encontrado para `nombre_loteria`, o None."""
    log.info(f"Scraping de respaldo: buscando '{nombre_loteria}' en todas las fuentes secundarias")

    # Le pasamos las URLS que ya aportaron resultado en el scraping principal, para que no las vuelva a consultar
    pool = recolectar_pool_secundario(log, urls_excluir=urls_excluir)
    if not pool:
        return None

    consolidado = consolidar_resultados_secundarios(pool)
    resultado = consolidado.get(nombre_loteria)

    if resultado:
        log.info(
            f"Scraping de respaldo: '{nombre_loteria}' -> numero={resultado['numero']} "
            f"| quinta={resultado['quinta']} | signo={resultado['signo']} "
            f"| coincidencias={resultado['total_coincidencias']}"
        )
    else:
        log.info(f"Scraping de respaldo: no se encontró '{nombre_loteria}' en ninguna fuente secundaria")

    return resultado


def respaldo_total_scraping(log) -> list[dict]:
    """Caso 3: el scraping principal falló por completo. Corre el respaldo sobre TODAS las páginas y devuelve el mejor resultado por lotería, en el formato que espera el correo de src/robots/scraping.py."""
    pool = recolectar_pool_secundario(log)
    if not pool:
        return []

    consolidado = consolidar_resultados_secundarios(pool)

    resultados = []
    for nombre_loteria, datos in consolidado.items():
        resultados.append({
            "nombre_loteria"     : nombre_loteria,
            "numero"             : datos["numero"],
            "quinta"             : datos.get("quinta") or "",
            "signo"              : datos.get("signo") or "",
            "fuentes"            : datos["fuentes"],
            "total_coincidencias": datos["total_coincidencias"],
        })

    log.info(f"Scraping de respaldo (total): {len(resultados)} lotería(s) consolidada(s)")
    return resultados
