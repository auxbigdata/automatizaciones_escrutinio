from playwright.sync_api import sync_playwright
import subprocess
import time
import os
from datetime import datetime


# rutas de las capturas tomadas en esta ejecucion, para adjuntarlas al correo de error
CAPTURAS = []
def tomar_captura(page, nombre, ruta_archivos, log):
    """Toma una captura de lo visible en la pagina en el momento del error y la guarda en la carpeta del dia."""
    try:
        carpeta = os.path.join(ruta_archivos, datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"{datetime.now().strftime('%H-%M-%S')}_{nombre.replace(' ', '_')}.png")
        page.screenshot(path=ruta)
        CAPTURAS.append(ruta)
        log.info(f"captura del error guardada en: {ruta}")
    except Exception as e:
        log.error(f"no se pudo tomar la captura {nombre}: {e}")

def open_browser(headless=True, workspace=None, log=None):
    """
    :param workspace: si se indica (0 = primer espacio de trabajo, 1 = segundo, etc.),
        se intenta mover la ventana de Firefox a ese espacio de trabajo apenas se abre,
        para que no aparezca encima de lo que el usuario esté usando en su escritorio
        actual. Solo aplica con headless=False y requiere un gestor de ventanas real
        (no aplica en xvfb). Si falla, no interrumpe el proceso.
    """
    p = sync_playwright().start()
    browser = p.firefox.launch(headless=headless)
    page = browser.new_page()

    # if not headless and workspace is not None:
    #     _mover_ventana_a_workspace(workspace, log=log)
    return page