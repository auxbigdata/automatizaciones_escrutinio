from playwright.sync_api import sync_playwright
import subprocess
import time

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