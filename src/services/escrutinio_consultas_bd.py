import os
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

# El scraping solo busca sorteos que ya quedaron programados en las dos plataformas:
# estado_programacion (BNET) = 3 y programacion_superx (Superflex) = 3
ESTADO_PROGRAMACION_FINALIZADA = 3


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
              AND estado_programacion = %s
              AND programacion_superx = %s
              AND (
                    estado_scraping = %s
                 OR (estado_scraping = %s
                     AND fecha_actualizacion < now() - interval %s)
              )
        """

        interval_param = f"{TIMEOUT_LOCK_MINUTOS} minutes"
        loterias = ejecutar_query(sql, (fecha_hoy, hora_actual, ESTADO_PROGRAMACION_FINALIZADA, ESTADO_PROGRAMACION_FINALIZADA, ESTADO_PENDIENTE, ESTADO_CORRIENDO_SCRAPING, interval_param))
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


def insertar_resultado_scraping(id_horario: int,numero:str,quinta:str,signo:str,serie:str,log: object, ids_scraping: list = None):
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
        # la columna ids_scraping es texto: la lista [4, 5, 9] se guarda como "4,5,9"
        ids_scraping = ",".join(str(id_origen) for id_origen in ids_scraping) if ids_scraping else None

        queries =[
            (
                """
                INSERT INTO es_resultados_loterias (id_horario, numero_ganador, fecha_sys, ids_scraping)
                VALUES (%s, %s, %s, %s)
                """,
                (id_horario, numero_ganador, fecha_hoy, ids_scraping)
            ),
            (
                f"UPDATE es_config_horarios SET estado_scraping = {ESTADO_SCRAPING_EJECUTADO} WHERE id_horario = %s",
                (id_horario,)

            ),
        ]

        ejecutar_transaccion(queries)

        log.info(f"Resultado insertado correctamente | id_horario={id_horario} | numero_ganador={numero_ganador} | ids_scraping={ids_scraping}")
        return True, None

    except Exception as e:
        mensaje_error = f"Error al insertar resultado en es_resultados_loterias: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def consultar_loterias_por_programar(ruta_archivos, log=object):
    try:
        # estado_programacion = estado en BNET, programacion_superx = estado en Superflex
        log.info("consultando loterias por programar (estado_programacion = 0 o programacion_superx = 0)")
        sql = """
            SELECT id_horario, nombre_loteria, cod_proceso, hora_programada, hora_cierre, fecha_sorteo, estado_programacion, programacion_superx
            FROM es_config_horarios
            WHERE estado_programacion = 0 OR programacion_superx = 0
            ORDER BY hora_programada
        """
        filas = ejecutar_query(sql)

        if not filas:
            mensaje = "no hay loterias con estado_programacion = 0 ni programacion_superx = 0"
            log.info(mensaje)
            return [], mensaje

        loterias = []
        loterias_json = []
        for id_horario, nombre_loteria, cod_proceso, hora_programada, hora_cierre, fecha_sorteo, estado_programacion, programacion_superx in filas:
            datos = {
                "nombre_loteria": nombre_loteria,
                "cod_proceso": cod_proceso,
                "hora_programada": hora_programada.strftime("%H:%M:%S"),
                # hora_cierre puede venir NULL en la tabla; en ese caso va None y en BNET no se toca
                "hora_cierre": hora_cierre.strftime("%H:%M:%S") if hora_cierre else None,
                "fecha_sorteo": fecha_sorteo.strftime("%d/%m/%Y"),
                "estado_programacion": estado_programacion,
                "programacion_superx": programacion_superx,
            }
            loterias_json.append(datos)
            # en memoria si necesitamos el id_horario para el UPDATE; en el json no va
            loterias.append({"id_horario": id_horario, **datos})

        ruta_json = os.path.join(ruta_archivos, "loterias_por_programar.json")
        with open(ruta_json, "w", encoding="utf-8") as archivo:
            json.dump(loterias_json, archivo, ensure_ascii=False, indent=4)

        log.info(f"{len(loterias)} loterias guardadas en {ruta_json}")
        return loterias, None

    except Exception as e:
        mensaje = f"Ocurrio un error al consultar las loterias por programar: {e}"
        log.error(mensaje)
        return None, mensaje





