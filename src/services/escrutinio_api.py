import requests
from datetime import datetime
import pytz
from src.services.utils_scraping import MAPEO_GENERICO, normalizar_texto
from src.services.servicios_email import fecha_actual_colombia

# Consulta la API de Gane Norte del Valle y busca el resultado de la lotería indicada en nombre_loteria.
def scraping_gane_norte_valle(nombre_loteria:str, url:str, log:object):
    try:
        log.info(f"Consultando API Gane Norte del Valle para: {nombre_loteria}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=12)

        # Si la API no respondió bien no podemos continuar
        if response.status_code != 200:
            mensaje_error = f"Gane Norte del Valle respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        # Convertimos la respuesta JSON a un diccionario de Python
        data = response.json()

        # La API devuelve los resultados en una lista llamada "resultados"
        resultados = data.get("resultados", [])

        if not resultados:
            mensaje_error = "Gane Norte del Valle no devolvió resultados"
            log.error(mensaje_error)
            return None, mensaje_error

      # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Recorremos cada resultado que devolvió la API
        for item in resultados:

            # display_name es el nombre que usa esta fuente para la lotería
            # Lo normalizamos para compararlo con el mapeo genérico
            display_name = normalizar_texto(item.get("display_name", ""))

            # Buscamos en el mapeo genérico si ese display_name
            # corresponde a la lotería que estamos buscando
            nombre_mapeado = MAPEO_GENERICO.get(display_name)

            # Si no corresponde a la lotería que buscamos pasamos al siguiente
            if nombre_mapeado != nombre_loteria:
                continue

            # Verificamos que el resultado sea de la fecha de hoy
            played_at = item.get("played_at", "")
            fecha_resultado = played_at.split(" ")[0] if played_at else ""

            if fecha_resultado != fecha_hoy:
                log.info(f"Resultado de {nombre_loteria} encontrado pero es de {fecha_resultado}, no de hoy ({fecha_hoy})")
                return None, f"Resultado de {nombre_loteria} no es de la fecha actual"

            # Extraemos el número ganador
            numero = item.get("number", "")

            # La quinta/serie viene en zodiac_sign con formato "serie: 009"
            # Si dice "serie:" extraemos el número, si no (ej: "tauro") lo dejamos tal cual
            zodiac_sign = item.get("zodiac_sign", "") or ""
            quinta = ""
            if "serie:" in zodiac_sign.lower():
                quinta = zodiac_sign.split(":")[1].strip()
            elif zodiac_sign:
                # Para el Astro guardamos el signo zodiacal
                quinta = zodiac_sign.strip()

            log.info(f"Resultado encontrado en Gane Norte del Valle | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todos los resultados y no encontró la lotería
        mensaje_error = f"No se encontró {nombre_loteria} en Gane Norte del Valle"
        log.info(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.Timeout:
        mensaje_error = "Timeout al consultar Gane Norte del Valle"
        log.error(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.ConnectionError:
        mensaje_error = "Error de conexión con Gane Norte del Valle"
        log.error(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Gane Norte del Valle: {e}"
        log.error(mensaje_error)
        return None, mensaje_error
