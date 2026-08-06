from src.settings.entorno import env
from src.settings.config import parametrizar_logs_y_ruta_archivos
from src.services.servicios_email import enviar_email
from src.services.servicios_discord import enviar_discord
from src.services.escrutinio_consultas_bd import buscar_loterias_hora_actual
from src.services.escrutinio_orquestador_scraping import procesar_loterias
from src.services.escrutinio_respaldo_scraping import respaldo_total_scraping


robot = "Scraping"
log,ruta_descarga = parametrizar_logs_y_ruta_archivos(robot)

if env.ENV == "dev":
    prefijo = "PRUEBAS"
else:
    prefijo = ""


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
        enviar_discord(
            mensaje=mensaje_error,
            titulo=f"{prefijo} SIN LOTERÍAS POR PROCESAR",
            log=log,
            color=15105570  # naranja: aviso, no es un error crítico del robot
        )
        return
    
    log.info(f"Loterías encontradas para procesar: {len(loterias)}")

    log.info("Inicia proceso de scraping")

    resultados, error_scraping = procesar_loterias(loterias, log)

    # CASO 3: el scraping principal falló por completo (falla técnica real: sin URLs activas,
    # excepción no controlada, etc.) -> se corre el de respaldo como último recurso.
    # Si procesar_loterias corrió bien pero ninguna lotería alcanzó el mínimo de fuentes,
    # retorna [] (no None) y eso NO dispara el Caso 3: se omite este ciclo y se reintenta
    # en el próximo cron.
    if resultados is None:
        log.warning(f"procesar_loterias falló técnicamente: {error_scraping}. Ejecutando scraping de respaldo...")

        resultados = respaldo_total_scraping(log)

        if not resultados:
            log.error("El scraping de respaldo tampoco encontró resultados")
            enviar_email(
                destinatario=destinatarios,
                asunto=f"ERROR {asunto}",
                mensaje=f"{mensaje}Ni el scraping principal ni el de respaldo encontraron resultados. Detalle: {error_scraping}",
                titulo_mensaje=titulo_mensaje,
                prioridad=1
            )
            return

        log.info(f"Scraping de respaldo: {len(resultados)} resultado(s) obtenido(s)")

    elif not resultados:
        log.info("Ninguna lotería alcanzó el mínimo de fuentes coincidentes en este ciclo. Se omite, sin Caso 3, y se reintenta en el próximo cron.")
        enviar_discord(
            mensaje="No se alcanzaron fuentes coincidentes para las loterías pendientes de este ciclo.",
            titulo=f"{prefijo} SIN COINCIDENCIAS",
            log=log,
            color=15105570  # naranja: aviso, no es un error crítico del robot
        )
        return

    cuerpo_resultados =""
    cuerpo_resultados_discord =""
    for r in resultados:
        # con guion si hay quinta, entre paréntesis si hay signo, o solo el numero
        quinta = r.get("quinta") or ""
        signo = r.get("signo") or ""
        if quinta:
            resultado_texto=f"{r['numero']}-{quinta}"
        elif signo:
            resultado_texto=f"{r['numero']} ({signo})"
        else:
            resultado_texto=f"{r['numero']}"

        log.info(f"RESULTADO FINAL: {r['nombre_loteria']} → {resultado_texto} ({r['total_coincidencias']} fuentes)")

        cuerpo_resultados += (
            f"<b>Lotería:</b> {r['nombre_loteria']}<br>"
            f"<b>Resultado:</b> {resultado_texto}<br>"
            f"<b>Fuentes coincidentes:</b> {r['total_coincidencias']}<br>"
            f"<br>"
        )

        # formato markdown para Discord
        cuerpo_resultados_discord +=(
            f"**Lotería:**{r['nombre_loteria']}\n"
            f"**Resultado:**{resultado_texto}\n"
            f"**Fuentes coincidentes:**{r['total_coincidencias']}\n\n"
        )

    log.info("Enviando correo con resultados del scraping")
    enviar_email(
        destinatario=destinatarios,
        asunto=asunto,
        mensaje=f"{mensaje}{cuerpo_resultados}",
        titulo_mensaje=titulo_mensaje
    )

    # También se notifica por Discord cuando sí hubo loterías por procesar
    log.info("Enviando notificación de resultados a Discord")
    enviar_discord(
        mensaje=cuerpo_resultados_discord,
        titulo=f"{prefijo} RESULTADOS SCRAPING",
        log=log,
        color=3066993  # verde: proceso completado con resultados
    )



if __name__ == "__main__":
    main()