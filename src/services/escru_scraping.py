import json
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from playwright.sync_api import Page

from src.services.db import ejecutar_query

from src.services.parsers_json import obtener_parser_json
from src.services.parsers_html import obtener_parser_html
from src.services.parsers_spa import obtener_parser_spa
from src.services.scraping_fallback import scraping_fallback_json
from src.services.utils_scraping import fecha_hoy_iso

from bs4 import BeautifulSoup


def obtener_paginas_db():
    sql = """
        SELECT id, nombre_loteria, url
        FROM es_origenes_scraping
        WHERE estado = 1
        ORDER BY id ASC
    """
    return ejecutar_query(sql)


def _es_spa_conocido(url: str) -> bool:
    return obtener_parser_spa(url) is not None


def _verificar_robots(url: str, log) -> bool:
    import urllib.request
    import urllib.error

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        with urllib.request.urlopen(robots_url, timeout=10) as resp:
            contenido = resp.read().decode("utf-8", errors="ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        log.info(
            f"No se pudo descargar robots.txt de {parsed.netloc} ({e}); "
            f"se asume permitido para {url}."
        )
        return True

    try:
        rp = RobotFileParser()
        rp.parse(contenido.splitlines())
        permitido = rp.can_fetch("*", url)
    except Exception as e:
        log.info(f"robots.txt de {parsed.netloc} no se pudo interpretar ({e}); se asume permitido.")
        return True

    if not permitido:
        log.warning(
            f"robots.txt de {parsed.netloc} bloquea explícitamente el acceso a {url}. "
            f"Se omite este origen. Si tienes autorización del sitio para "
            f"acceder de todas formas, gestiona ese acceso vía su API "
            f"oficial o credenciales, no sobre la exclusión de robots.txt."
        )
    return permitido


def scraping_generico(page: Page, url: str, log) -> list[dict]:
    """Scraping de respaldo: navega a `url` y devuelve dicts estandarizados (nombre_sorteo, numero, fecha, serie, quinta, signo, fuente, fecha_aproximada)."""
    resultados: list[dict] = []
    hoy = fecha_hoy_iso()

    if not _verificar_robots(url, log):
        return resultados

    try:

        log.info(f"Navegando a {url}")
        response = page.goto(url, timeout=60000)

        # --- SPA conocido: requiere selectores Playwright ---
        if _es_spa_conocido(url):
            parser_spa = obtener_parser_spa(url)
            if parser_spa:
                log.info(f"Origen reconocido como SPA. Usando parser específico para {url}")
                resultados = parser_spa(page, url, log)

                if not resultados:
                    log.warning(f"No se encontraron resultados del día de hoy {hoy} en {url}")
                log.info(f"Parser SPA específico extrajo {len(resultados)} resultados de {url}")
                return resultados

        try:
            page.wait_for_load_state("networkidle", timeout=60000)
        except Exception:
            log.warning(f"Timeout esperando networkidle en {url} (puede que la red no haya quedado inactiva por anuncios/analytics). Continuando...")
        page.wait_for_timeout(3000)

        # --- Determinar si la respuesta es JSON (API) ---
        content_type = response.headers.get("content-type", "") if response else ""
        texto_crudo = ""
        if page.locator("pre").count() > 0:
            texto_crudo = page.locator("pre").first.inner_text().strip()
        else:
            texto_crudo = page.locator("body").inner_text().strip()

        es_json = False
        data = None
        if "application/json" in content_type or texto_crudo.startswith("{") or texto_crudo.startswith("["):
            try:
                data = json.loads(texto_crudo)
                es_json = True
            except json.JSONDecodeError:
                data = None

        if es_json:
            log.info("Se detectó que el origen es una API (JSON).")
            parser_json = obtener_parser_json(url)
            if parser_json:
                log.info(f"Usando parser JSON específico para {url}")
                resultados = parser_json(data, url)
                if not resultados:
                    log.warning(f"No se encontraron resultados del día de hoy {hoy} en {url}.")
                log.info(f"Total resultados (JSON) para {url}: {len(resultados)}")
                return resultados

            # Sin parser específico: usar fallback genérico.
            resultados = scraping_fallback_json(data, url, log)
            log.info(f"Total resultados (JSON) para {url}: {len(resultados)}")
            return resultados

        # --- HTML normal ---
        log.info("Procesando origen como sitio web (HTML).")
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        parser_html = obtener_parser_html(url)
        if parser_html:
            log.info(f"Usando parser HTML específico para {url}")
            resultados = parser_html(soup, url, log)

        if not resultados:
            if parser_html:
                log.warning(f"No se encontraron resultados del día de hoy {hoy} en {url}.")
            log.info(f"Total resultados (HTML) para {url}: {len(resultados)}")
            return resultados

        log.info(f"Total resultados (HTML) para {url}: {len(resultados)}")

    except Exception as e:
        log.error(f"Error en scraping para {url}: {e}")

    return resultados
