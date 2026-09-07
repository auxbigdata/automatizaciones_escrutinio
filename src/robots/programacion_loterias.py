from src.settings.entorno import env
from src.services.browser import open_browser
from src.services.programacion_loteries import iniciar_bnet, menu_programacion_loterias,programacion_loterias
from src.settings.config import parametrizar_logs_y_ruta_archivos
from src.services.servicios_email import enviar_email

URL_BNET= env.URL_BNET
URL_HOMEBNET=env.URL_HOMEBNET
USER_BNET=env.USER_BNET
PASS_BNET=env.PASS_BNET



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
mensaje=f"se notifica la ejecucion del proceso automatico de la programacion de las loterias\chances"

def main():
    log.info("inicia proceso programacion loterias")
    
    page = open_browser(headless=False, log=log)

    login_ok, mensaje= iniciar_bnet(page,URL_BNET,URL_HOMEBNET,USER_BNET,PASS_BNET, log=log)
    if not login_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                # adjuntos=[ruta_captura_login] if ruta_captura_login else None
                )
            return

    menu_ok, mensaje= menu_programacion_loterias(page, log=log)
    if not menu_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                # adjuntos=[ruta_captura_login] if ruta_captura_login else None
                )
            return

    programacion_ok, mensaje= programacion_loterias(page, ruta_descarga, log=log)
    if not programacion_ok:
            enviar_email(
                destinatario=destinatarios,
                mensaje=f"{mensaje}",
                asunto=f"ERORR {asunto}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1,
                # adjuntos=[ruta_captura_login] if ruta_captura_login else None
                )
            return
if __name__ == "__main__":
    main()