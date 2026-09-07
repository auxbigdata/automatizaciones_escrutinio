import pytz
import json
import requests
from datetime import datetime
from src.services.db import ejecutar_query, ejecutar_transaccion
from src.services.servicios_email import fecha_actual_colombia

# 0=Pendiente, 1=Corriendo Scraping, 2=Scraping Ejecutado, 3=Finalizado Total, 4=Error
ESTADO_PENDIENTE          = 0
ESTADO_CORRIENDO_SCRAPING = 1
ESTADO_SCRAPING_EJECUTADO = 2
ESTADO_ERROR              = 4

# Si una lotería lleva más de este tiempo en ESTADO_CORRIENDO_SCRAPING, se asume que el
# proceso que la tomó murió sin liberarla (kill -9, caída del servidor, etc.) y se vuelve
# a ofrecer al siguiente cron en vez de quedar bloqueada para siempre.
TIMEOUT_LOCK_MINUTOS = 15


def buscar_loterias_hora_actual(log: object):
    try:
        log.info("obteniendo hora actual")
        zona_colombia = pytz.timezone("America/Bogota")
        hora_actual = datetime.now(zona_colombia).strftime("%H:%M")
        fecha_hoy = fecha_actual_colombia()
        log.info(f"hora actual: {hora_actual} | fecha: {fecha_hoy}")

        sql = """
            SELECT id_horario, nombre_loteria, hora_programada
            FROM es_config_horarios
            WHERE fecha_sorteo = %s
              AND hora_programada <= %s
              AND (
                    estado_scraping = %s
                 OR (estado_scraping = %s
                     AND fecha_actualizacion < now() - interval %s)
              )
        """

        interval_param = f"{TIMEOUT_LOCK_MINUTOS} minutes"
        loterias = ejecutar_query(sql, (fecha_hoy, hora_actual, ESTADO_PENDIENTE, ESTADO_CORRIENDO_SCRAPING, interval_param))
        # log.info(f"loterias encontradas: {loterias}")

        if not loterias:
            log.info("No hay loterías programadas para la hora actual")
            return None, f"no hay loterías programadas para la hora actual: {hora_actual}"

        log.info(f"loterías encontradas: {loterias}")
        for loteria in loterias:
            log.info(f"ID: {loteria[0]} | Nombre: {loteria[1]} | Hora: {loteria[2]}")

        # Marcamos de una vez TODO el lote como "Corriendo Scraping" para que, si el ciclo se
        # demora, el próximo cron (a los 5 min) no vuelva a tomar ninguna de estas loterías
        # -ni la que ya está corriendo ni las que todavía están en cola dentro de este mismo ciclo.
        ids_horario = [loteria[0] for loteria in loterias]
        ejecutar_query(
            "UPDATE es_config_horarios SET estado_scraping = %s WHERE id_horario = ANY(%s)",
            (ESTADO_CORRIENDO_SCRAPING, ids_horario)
        )
        log.info(f"Loterías marcadas como Corriendo Scraping (estado_scraping={ESTADO_CORRIENDO_SCRAPING}): {ids_horario}")

        return loterias, None

    except Exception as e:
        mensaje_error = f"Error al buscar loterías para la hora actual: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def actualizar_estado_horario(id_horario: int, estado: int, log: object):
    """Actualiza es_config_horarios.estado_scraping para una lotería puntual. Retorna (True, None) o (None, mensaje)."""
    try:
        ejecutar_query(
            "UPDATE es_config_horarios SET estado_scraping = %s WHERE id_horario = %s",
            (estado, id_horario)
        )
        log.info(f"id_horario={id_horario} actualizado a estado_scraping={estado}")
        return True, None
    except Exception as e:
        mensaje_error = f"Error al actualizar estado_scraping de id_horario={id_horario} a estado={estado}: {e}"
        log.error(mensaje_error)
        return None, mensaje_error
    




def insertar_resultado_scraping(id_horario: int,numero:str,quinta:str,signo:str,serie:str,log: object):
    try:
        log.info(f"Insertando resultado en es_resultados_loterias para id_horario: {id_horario}")

        # construimos el JSON
        numero_ganador = json.dumps({
            "numero": numero,
            "quinta": quinta,
            "signo": signo, 
            "serie": serie
        }, ensure_ascii=False)

        fecha_hoy = fecha_actual_colombia()

        queries =[
            (
                """
                INSERT INTO es_resultados_loterias (id_horario, numero_ganador, fecha_sys)
                VALUES (%s, %s, %s)
                """,
                (id_horario, numero_ganador, fecha_hoy)
            ),
            (
                f"UPDATE es_config_horarios SET estado_scraping = {ESTADO_SCRAPING_EJECUTADO} WHERE id_horario = %s",
                (id_horario,)

            ),
        ]

        ejecutar_transaccion(queries)

        log.info(f"Resultado insertado correctamente | id_horario={id_horario} | numero_ganador={numero_ganador}")
        return True, None

    except Exception as e:
        mensaje_error = f"Error al insertar resultado en es_resultados_loterias: {e}"
        log.error(mensaje_error)
        return None, mensaje_error





