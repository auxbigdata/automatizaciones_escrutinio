from src.settings.entorno import env
from src.settings.config import parametrizar_logs_y_ruta_archivos
from src.services.servicios_email import enviar_email
from src.services.escrutinio_consultas_bd import buscar_loterias_hora_actual
from src.services.escrutinio_orquestador_scraping import procesar_loterias


robot = "Scraping"
log,ruta_descarga = parametrizar_logs_y_ruta_archivos(robot)

if env.ENV == "dev":
    prefijo = "PRUEBAS"
else:
    prefijo = ""


# enviar correo 
destinatarios =[
    "auxanalista@consuerte.com.co"
]


asunto = f"{prefijo} EJECUCION PROCESO SCRAPING"
titulo_mensaje = f"{prefijo} ROBOT SCRAPING"
mensaje = f"se notifica la ejecucion del proceso automatico de scraping:<br><br>"

def main():
    log.info("Inicia proceso de scraping")
    loterias, mensaje_error = buscar_loterias_hora_actual(log)

    if loterias is None:
        log.error(mensaje_error)
        enviar_email(
            destinatario=destinatarios,
            asunto=f"ERROR {asunto}",
            mensaje=f"{mensaje}{mensaje_error}",
            titulo_mensaje=titulo_mensaje,
            prioridad=1
        )
        return
    
    log.info(f"Loterías encontradas para procesar: {len(loterias)}")

    log.info("Inicia proceso de scraping")

    resultados, error_scraping = procesar_loterias(loterias, log)

    if resultados is None:
        log.error(error_scraping)
        # enviar_email(
        #     destinatario=destinatarios,
        #     asunto=f"ERROR {asunto}",
        #     mensaje=f"{mensaje}{error_scraping}",
        #     titulo_mensaje=titulo_mensaje,
        #     prioridad=1
        # )
        # return

    cuerpo_resultados =""
    for r in resultados:
        # construimos la linea del resultado si hay quinta mostramos con guion, si no solo el numero
        if r["quinta"]:
            resultado_texto=f"{r['numero']}-{r['quinta']}"
        else:
            resultado_texto=f"{r['numero']}"

        log.info(f"RESULTADO FINAL: {r['nombre_loteria']} → {resultado_texto} ({r['total_coincidencias']} fuentes)")
        # Agregamos al cuerpo del correo

        cuerpo_resultados += (
            f"<b>Lotería:</b> {r['nombre_loteria']}<br>"
            f"<b>Resultado:</b> {resultado_texto}<br>"
            f"<b>Fuentes coincidentes:</b> {r['total_coincidencias']}<br>"
            f"<br>"
        )

    # Enviamos el correo con todos los resultados del ciclo
    log.info("Enviando correo con resultados del scraping")
    enviar_email(
        destinatario=destinatarios,
        asunto=asunto,
        mensaje=f"{mensaje}{cuerpo_resultados}",
        titulo_mensaje=titulo_mensaje
    )
        



if __name__ == "__main__":
    main()