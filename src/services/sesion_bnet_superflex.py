from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.services.browser import tomar_captura


def iniciar_superflex(page,URL_SUPERFLEX,URL_SUPERFLEX_HOME,USER_SUPERFLEX,PASS_SUPERFLEX, ruta_archivos, log= object):
    log.info("Iniciando sesión en Superflex")
    try:
        page.goto(f"{URL_SUPERFLEX}")
        page.wait_for_timeout(10000)  # Esperar 10 segundos para que la página se cargue completamente

        # USUARIO
        input_usuario = page.wait_for_selector('input[formcontrolname="usuario"]',state='visible', timeout=(10000))
        input_usuario.fill(str(USER_SUPERFLEX))

        # CONTRASEÑA
        input_pass = page.wait_for_selector('input[formcontrolname="contrasena"]',state='visible',timeout= (10000))
        input_pass.fill(str(PASS_SUPERFLEX))

        page.locator("button:has-text('ingresar')").click()

        page.wait_for_timeout(10000)
        page.wait_for_url(URL_SUPERFLEX_HOME, timeout=25000)
        log.info("Login exitoso en Superflex")
        return True, "Login exitoso en Superflex"

    except PlaywrightTimeoutError:
        mensaje = "Error: Timeout al cargar la página de inicio de sesión de Superflex"
        log.error(mensaje)
        tomar_captura(page, "login_superflex", ruta_archivos, log)
        return False, mensaje

    except Exception as e:
        mensaje = f"Ocurrio un error al iniciar sesión en superflex: {e}"
        log.error(mensaje)
        tomar_captura(page, "login_superflex", ruta_archivos, log)
        return False, mensaje

def iniciar_bnet(page,URL_BNET,URL_HOMEBNET,USER_BNET,PASS_BNET, ruta_archivos, log=object):
    try:
        log.info("iniciando sesion en bnet")
        page.goto(f"{URL_BNET}")
        page.wait_for_load_state("domcontentloaded")

        input_usuario = page.wait_for_selector('input[name="idFormLogin:user"]', state='visible', timeout=(15000))
        input_usuario.fill(str(USER_BNET))

        input_password=page.wait_for_selector('input[name="idFormLogin:password"]', state='visible', timeout=(15000))
        input_password.fill(str(PASS_BNET))

        page.locator('button[name="idFormLogin:ingresar"]').click()
        page.wait_for_url(f"{URL_HOMEBNET}", timeout=15000)
        log.info("Login exitoso en BNET")

        input_apuesta = page.wait_for_selector('span.modulo-titulo:has-text("Módulo de Apuestas")',state='visible',timeout=15000)
        input_apuesta.scroll_into_view_if_needed()
        input_apuesta.click()
        page.wait_for_load_state("domcontentloaded")
        log.info("Modulo de apuestas cargado correctamente")
        return True,""

    except PlaywrightTimeoutError:
        mensaje = "Error: Timeout al cargar la página de inicio de sesión de BNET"
        log.error(mensaje)
        tomar_captura(page, "login_bnet", ruta_archivos, log)
        return False, mensaje

    except Exception as e:
        mensaje = f"Ocurrio un error al iniciar sesión en BNET: {e}"
        log.error(mensaje)
        tomar_captura(page, "login_bnet", ruta_archivos, log)
        return False, mensaje