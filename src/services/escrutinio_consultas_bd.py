import pytz
import json
import requests
from datetime import datetime
from src.services.db import ejecutar_query, ejecutar_transaccion
from src.services.servicios_email import fecha_actual_colombia

def buscar_loterias_hora_actual(log: object):
    try:
        log.info("obteniendo hora actual")
        zona_colombia = pytz.timezone("America/Bogota")
        hora_actual = datetime.now(zona_colombia).strftime("%H:%M")
        log.info(f"hora actual: {hora_actual}")

        sql = """SELECT id_horario, nombre_loteria, hora_programada FROM es_config_horarios WHERE hora_programada <= %s AND estado = 0"""

        loterias = ejecutar_query(sql, (hora_actual,))
        # log.info(f"loterias encontradas: {loterias}")
        
        if not loterias:
            log.info("No hay loterías programadas para la hora actual")
            return None, f"no hay loterías programadas para la hora actual: {hora_actual}"
        
        log.info(f"loterías encontradas: {loterias}")
        for loteria in loterias:
            log.info(f"ID: {loteria[0]} | Nombre: {loteria[1]} | Hora: {loteria[2]}")
        return loterias, None
        
    except Exception as e:
        mensaje_error = f"Error al buscar loterías para la hora actual: {e}"
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
                "UPDATE es_config_horarios SET estado = 1 WHERE id_horario = %s",
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






# def clasificar_urls(log: object):
#     try:
#         log.info("Iniciando clasificación de URLs")

#         # Obtenemos todas las URLs de la tabla
#         sql = """SELECT id, url FROM es_origenes_scraping"""
#         urls = ejecutar_query(sql)

#         if not urls:
#             log.info("No hay URLs para clasificar")
#             return None, "No hay URLs para clasificar"

#         log.info(f"URLs encontradas: {len(urls)}")

#         headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
#             "Accept": "text/html,application/json,*/*"
#         }

#         for url_data in urls:
#             id_url = url_data[0]
#             url = url_data[1]
#             tipo = None

#             try:
#                 log.info(f"Revisando URL: {url}")
#                 response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
#                 content_type = response.headers.get("Content-Type", "")

#                 if "application/json" in content_type:
#                     tipo = "API"
#                 elif "text/html" in content_type:
#                     tipo = "HTML"
#                 else:
#                     tipo = "OTRO"

#                 log.info(f"ID: {id_url} | URL: {url} | Tipo: {tipo} | Status: {response.status_code}")

#             except requests.exceptions.Timeout:
#                 log.error(f"Timeout en URL: {url}")
#                 tipo = "OTRO"
#             except requests.exceptions.ConnectionError:
#                 log.error(f"Error de conexión en URL: {url}")
#                 tipo = "OTRO"
#             except Exception as e:
#                 log.error(f"Error inesperado en URL {url}: {e}")
#                 tipo = "OTRO"

#             # Actualizamos el tipo en la tabla
#             sql_update = """UPDATE es_origenes_scraping SET tipo = %s WHERE id = %s"""
#             ejecutar_query(sql_update, (tipo, id_url))
#             log.info(f"Tipo actualizado en tabla: ID {id_url} -> {tipo}")

#         log.info("Clasificación de URLs finalizada")
#         return True, None

#     except Exception as e:
#         mensaje_error = f"Error al clasificar URLs: {e}"
#         log.error(mensaje_error)
#         return None, mensaje_error

