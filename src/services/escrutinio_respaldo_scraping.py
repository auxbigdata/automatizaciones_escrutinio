"""
Scraping de respaldo (segundo scraping).

Se dispara desde el orquestador si una lotería queda sin resultado
validado o le falta quinta/signo, y desde src/robots/scraping.py como
respaldo total si el scraping principal falla por completo.

A diferencia del principal (busca UNA lotería por fuente), este motor
lee cada página completa y devuelve TODOS los sorteos del día, por eso
se consolida por nombre de lotería.
"""
from playwright.sync_api import sync_playwright
from src.services.escru_scraping import scraping_generico, obtener_paginas_db
from src.services.utils_scraping import validar_coincidencias


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


def consolidar_resultados_secundarios(pool: list[dict], log) -> dict:
    """Agrupa el pool por lotería y valida cada una con validar_coincidencias(), el mismo
    criterio (mínimo MIN_FUENTES_COINCIDENTES fuentes) que usa el scraping principal.
    Las loterías que no alcancen el mínimo quedan fuera del resultado.

    Retorna {nombre_loteria: {"numero", "quinta", "signo", "fuentes", "total_coincidencias"}}.
    """
    por_loteria: dict[str, list[dict]] = {}
    for r in pool:
        nombre = r.get("nombre_sorteo")
        if not nombre:
            continue
        por_loteria.setdefault(nombre, []).append(r)

    consolidado = {}
    for nombre, candidatos in por_loteria.items():
        resultado_validado, error = validar_coincidencias(candidatos, log)
        if resultado_validado is None:
            log.info(f"Scraping de respaldo: '{nombre}' descartado ({error})")
            continue
        consolidado[nombre] = resultado_validado

    return consolidado


def respaldo_total_scraping(log) -> list[dict]:
    """Caso 3: el scraping principal falló por completo. Corre el respaldo sobre TODAS las páginas y devuelve, por lotería, solo los resultados que alcanzaron el mínimo de fuentes coincidentes (mismo criterio que el scraping principal), en el formato que espera el correo de src/robots/scraping.py."""
    pool = recolectar_pool_secundario(log)
    if not pool:
        return []

    consolidado = consolidar_resultados_secundarios(pool, log)

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
