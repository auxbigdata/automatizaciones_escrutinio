from playwright.sync_api import sync_playwright

def abrir_navegador(url: str, log: object, espera: str = "domcontentloaded"):
    """
    Abre el navegador Chromium en modo headless, navega a la URL
    y retorna el HTML completamente renderizado (con JavaScript ejecutado).

    Parámetros:
    - url    : URL a visitar
    - log    : objeto de logs
    - espera : condición de espera
               'networkidle' = espera a que no haya más peticiones de red
               'domcontentloaded' = más rápido, solo espera el HTML básico

    Retorna:
    - (str, None) → HTML renderizado si funcionó
    - (None, str) → None, mensaje de error si falló
    """
    try:
        log.info(f"Abriendo navegador para: {url}")

        with sync_playwright() as p:
            # Lanzamos Chromium en modo headless
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ]
            )

            # Abrimos una nueva pestaña
            page = browser.new_page()

            # Simulamos un navegador real
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "es-CO,es;q=0.9"
            })

            # Navegamos y esperamos que cargue el JavaScript
            page.goto(url, timeout=60000, wait_until=espera)
            page.wait_for_timeout(3000)  # Esperamos un poco más para que cargue todo el contenido dinámico

            # Obtenemos el HTML ya renderizado
            html = page.content()

            # Cerramos el navegador
            browser.close()

        log.info(f"HTML obtenido correctamente | Tamaño: {len(html)} chars")
        return html, None

    except Exception as e:
        mensaje_error = f"Error al obtener HTML con Playwright de {url}: {e}"
        log.error(mensaje_error)
        return None, mensaje_error