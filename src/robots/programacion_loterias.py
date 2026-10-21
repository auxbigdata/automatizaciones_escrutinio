import traceback
from src.settings.entorno import env
from src.services.browser import open_browser, CAPTURAS
from src.services.sesion_bnet_superflex import iniciar_bnet, iniciar_superflex
from src.services.programacion_loteries import menu_programacion_loterias,programacion_loterias
from src.services.programacion_loteries_superflex import navegacion_menu_programacion_loterias
from src.settings.config import parametrizar_logs_y_ruta_archivos
from src.services.servicios_email import enviar_email
from src.services.servicios_discord import enviar_discord

URL_BNET= env.URL_BNET
URL_HOMEBNET=env.URL_HOMEBNET
USER_BNET=env.USER_BNET
PASS_BNET=env.PASS_BNET
URL_SUPERFLEX=env.URL_SUPERFLEX
URL_SUPERFLEX_HOME=env.URL_SUPERFLEX_HOME
USER_SUPERFLEX=env.USER_SUPERFLEX
PASS_SUPERFLEX=env.PASS_SUPERFLEX



robot = "programacion_loterias"
log,ruta_descarga = parametrizar_logs_y_ruta_archivos(robot)

if env.ENV == "dev":
    prefijo = "PRUEBAS"
else:
    prefijo = ""


destinatarios =[
    "auxanalista@consuerte.com.co"
]

asunto = f"{prefijo} EJECUCION PROCESO PROGRAMACION LOTERIAS"
titulo_mensaje = f"{prefijo} ROBOT PROGRAMACION LOTERIAS"
mensaje=f"se notifica la ejecucion del proceso automatico de la programacion de los sorteos"

def procesar(page):
    login_ok, mensaje= iniciar_bnet(page,URL_BNET,URL_HOMEBNET,USER_BNET,PASS_BNET, ruta_descarga, log=log)
    if not login_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                adjuntos=CAPTURAS or None,
                )
            return

    menu_ok, mensaje= menu_programacion_loterias(page, ruta_descarga, log=log)
    if not menu_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                adjuntos=CAPTURAS or None,
                )
            return

    # superflex en otra pestaña del mismo navegador, cada loteria se programa en BNET y en Superflex
    page_superflex = page.context.browser.new_page()

    login_superflex_ok, mensaje= iniciar_superflex(page_superflex,URL_SUPERFLEX,URL_SUPERFLEX_HOME,USER_SUPERFLEX,PASS_SUPERFLEX, ruta_descarga, log=log)
    if not login_superflex_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                adjuntos=CAPTURAS or None,
                )
            return

    menu_superflex_ok, mensaje= navegacion_menu_programacion_loterias(page_superflex, ruta_descarga, log=log)
    if not menu_superflex_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                adjuntos=CAPTURAS or None,
                )
            return

    # el correo con el resumen se envia siempre: normal si todo quedo en las dos plataformas, como error si no
    programacion_ok, mensaje= programacion_loterias(page, page_superflex, ruta_descarga, log=log)

    # None = no habia loterias por programar: se avisa por Discord y no por correo
    if programacion_ok is None:
        enviar_discord(
            mensaje=mensaje,
            titulo=f"{prefijo} SIN LOTERÍAS POR PROGRAMAR",
            log=log,
            color=15105570  # naranja: aviso, no es un error
        )
        return

    if not programacion_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                adjuntos=CAPTURAS or None,
                )
            return

    enviar_email(
        destinatario=destinatarios,
        mensaje=f"{mensaje}",
        asunto=asunto,
        titulo_mensaje=titulo_mensaje,
        )
    log.info("correo con el resumen de la programacion enviado")

def main():
    log.info("inicia proceso programacion loterias")
    page = None
    try:
        page = open_browser(headless=False, log=log)
        procesar(page)
    except Exception as e:
        # error no controlado (ej. no abre el navegador o falla el correo): se avisa por Discord porque el correo pudo ser lo que fallo
        log.error(f"error no controlado en el robot: {e}")
        log.error(traceback.format_exc())
        enviar_discord(
            mensaje=f"error no controlado: {e}",
            titulo=f"{prefijo} ERROR ROBOT PROGRAMACION LOTERIAS",
            log=log,
            color=15158332  # rojo: error
        )
    finally:
        if page is not None:
            # si Firefox ya se habia caido, close() falla: se anota y el robot termina normal
            try:
                page.context.browser.close()
            except Exception as e:
                log.error(f"no se pudo cerrar el navegador: {e}")
        log.info("fin proceso programacion loterias")

if __name__ == "__main__":
    main()