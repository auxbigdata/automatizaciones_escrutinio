import time
from src.services.db import ejecutar_query
from src.services.escrutinio_consultas_bd import insertar_resultado_scraping
from src.services.escrutinio_api import scraping_gane_norte_valle
from src.services.escrutinio_html import (
    scraping_acertemos,
    scraping_perla_todo,
    scraping_ganagana,
    scraping_jer,
    scraping_chances_colombia,
    scraping_loterias_colombia,
    scraping_loterias_de_hoy2,
    scraping_ganar_chance,
    scraping_gana,
    scraping_loterias_de_hoy,
    scraping_loti
)

# Mínimo de fuentes que deben coincidir para validar el resultado
MIN_FUENTES_COINCIDENTES = 3


def obtener_urls_scraping(log: object):
    """
    Consulta la tabla es_origenes_scraping y retorna
    todas las URLs activas (estado = 1).

    Retorna:
    - (list, None)  → lista de URLs si encontró
    - (None, str)   → None, mensaje si no encontró o falló
    """
    try:
        log.info("Obteniendo URLs activas de es_origenes_scraping")

        # Traemos solo las URLs activas (estado = 1)
        sql = """
            SELECT id, nombre_loteria, url, tipo
            FROM es_origenes_scraping
            WHERE estado = 1
        """

        urls = ejecutar_query(sql)

        if not urls:
            mensaje_error = "No hay URLs activas en es_origenes_scraping"
            log.info(mensaje_error)
            return None, mensaje_error

        log.info(f"URLs activas encontradas: {len(urls)}")
        return urls, None

    except Exception as e:
        mensaje_error = f"Error al obtener URLs de scraping: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def ejecutar_scraping_por_url(nombre_loteria: str, nombre_fuente: str, url: str, log: object):
    """
    Decide qué función de scraping llamar según el nombre de la fuente.
    Si se agrega una nueva URL al proyecto, solo se agrega su elif aquí.

    Parámetros:
    - nombre_loteria : lotería que estamos buscando
    - nombre_fuente  : nombre de la fuente en es_origenes_scraping
    - url            : URL a consultar
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → resultado si encontró
    - (None, str)   → None, mensaje si no encontró o falló
    """
    try:
        log.info(f"Ejecutando scraping en fuente: {nombre_fuente}")

        if nombre_fuente == "Gane Norte del Valle":
            # Pausa para no saturar la API
            time.sleep(10)
            resultado, error = scraping_gane_norte_valle(nombre_loteria, url, log)

        elif nombre_fuente == "Acertemos":
            resultado, error = scraping_acertemos(nombre_loteria, url, log)

        elif nombre_fuente == "Perla Todo":
            resultado, error = scraping_perla_todo(nombre_loteria, url, log)

        elif nombre_fuente == "GanaGana":
            resultado, error = scraping_ganagana(nombre_loteria, url, log)

        elif nombre_fuente == "JER":
            resultado, error = scraping_jer(nombre_loteria, url, log)

        elif nombre_fuente == "Chances Colombia":
            resultado, error = scraping_chances_colombia(nombre_loteria, url, log)

        elif nombre_fuente == "loteriasdecolombia":
            resultado, error = scraping_loterias_colombia(nombre_loteria, url, log)

        elif nombre_fuente == "Loterias de Hoy2":
            resultado, error = scraping_loterias_de_hoy2(nombre_loteria, url, log)

        elif nombre_fuente == "GANAR CHANCE":
            resultado, error = scraping_ganar_chance(nombre_loteria, url, log)

        elif nombre_fuente == "Gana":
            resultado, error = scraping_gana(nombre_loteria, url, log)

        elif nombre_fuente == "Loterias de Hoy":
            resultado, error = scraping_loterias_de_hoy(nombre_loteria, url, log)

        elif nombre_fuente == "loti":
            resultado, error = scraping_loti(nombre_loteria, url, log)

        else:
            # Fuentes que aún no tienen función implementada las ignoramos
            log.info(f"Fuente '{nombre_fuente}' aún no tiene función implementada")
            return None, f"Fuente '{nombre_fuente}' no implementada"

        # Log para ver qué trae cada fuente
        if resultado:
            log.info(f"Fuente '{nombre_fuente}' → numero={resultado.get('numero')} | quinta='{resultado.get('quinta', '')}' | signo='{resultado.get('signo', '')}'")

        return resultado, error

    except Exception as e:
        mensaje_error = f"Error inesperado al ejecutar scraping en {nombre_fuente}: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def validar_coincidencias(resultados: list, log: object):
    """
    Valida los resultados en 3 niveles:
    - Nivel 1: número (mínimo MIN_FUENTES_COINCIDENTES)
    - Nivel 2: quinta (solo entre fuentes que la trajeron)
    - Nivel 3: signo  (solo entre fuentes que lo trajeron)

    Parámetros:
    - resultados : lista de dicts con {"numero", "quinta", "signo", "fuente"}
    - log        : objeto de logs

    Retorna:
    - (dict, None)  → resultado validado si pasó los 3 niveles
    - (None, str)   → None, mensaje si no alcanzó las coincidencias
    """
    try:
        if not resultados:
            return None, "No hay resultados para comparar"

        # -----------------------------------------------
        # NIVEL 1: Validar el número
        # -----------------------------------------------
        conteo_numero = {}
        for r in resultados:
            num = r['numero']
            if num not in conteo_numero:
                conteo_numero[num] = {
                    "cantidad" : 0,
                    "fuentes"  : [],
                    "quintas"  : [],
                    "signos"   : []
                }
            conteo_numero[num]["cantidad"] += 1
            conteo_numero[num]["fuentes"].append(r["fuente"])

            # Solo acumulamos quinta si la fuente la trajo
            if r.get('quinta'):
                conteo_numero[num]["quintas"].append(r['quinta'].upper().strip())

            # Solo acumulamos signo si la fuente lo trajo
            if r.get('signo'):
                conteo_numero[num]["signos"].append(r['signo'].upper().strip())

        # Buscamos el número con suficientes coincidencias
        numero_validado = None
        datos_numero    = None
        for num, datos in conteo_numero.items():
            if datos["cantidad"] >= MIN_FUENTES_COINCIDENTES:
                numero_validado = num
                datos_numero    = datos
                log.info(f"Número validado: {num} con {datos['cantidad']} fuentes")
                break

        if numero_validado is None:
            mensaje_error = f"No se alcanzaron {MIN_FUENTES_COINCIDENTES} fuentes coincidentes para el número"
            log.info(mensaje_error)
            log.info(f"Resultados obtenidos: {resultados}")
            return None, mensaje_error

        # -----------------------------------------------
        # NIVEL 2: Validar la quinta
        # Solo si alguna fuente la trajo
        # -----------------------------------------------
        quinta_final = ""
        if datos_numero["quintas"]:
            conteo_quintas = {}
            for q in datos_numero["quintas"]:
                conteo_quintas[q] = conteo_quintas.get(q, 0) + 1

            for q, cantidad in conteo_quintas.items():
                if cantidad >= MIN_FUENTES_COINCIDENTES:
                    quinta_final = q
                    log.info(f"Quinta validada: {q} con {cantidad} fuentes")
                    break

            if not quinta_final:
                mensaje_error = f"Número {numero_validado} validado pero quinta no tiene {MIN_FUENTES_COINCIDENTES} fuentes coincidentes aún"
                log.info(mensaje_error)
                return None, mensaje_error

        # -----------------------------------------------
        # NIVEL 3: Validar el signo
        # Solo si alguna fuente lo trajo
        # -----------------------------------------------
        signo_final = ""
        if datos_numero["signos"]:
            conteo_signos = {}
            for s in datos_numero["signos"]:
                conteo_signos[s] = conteo_signos.get(s, 0) + 1

            for s, cantidad in conteo_signos.items():
                if cantidad >= MIN_FUENTES_COINCIDENTES:
                    signo_final = s
                    log.info(f"Signo validado: {s} con {cantidad} fuentes")
                    break

            if not signo_final:
                mensaje_error = f"Número {numero_validado} validado pero signo no tiene {MIN_FUENTES_COINCIDENTES} fuentes coincidentes aún"
                log.info(mensaje_error)
                return None, mensaje_error

        log.info(f"Resultado completamente validado")
        log.info(f"   Número : {numero_validado}")
        log.info(f"   Quinta : {quinta_final}")
        log.info(f"   Signo  : {signo_final}")
        log.info(f"   Fuentes: {', '.join(datos_numero['fuentes'])}")

        return {
            "numero"             : numero_validado,
            "quinta"             : quinta_final,
            "signo"              : signo_final,
            "fuentes"            : datos_numero["fuentes"],
            "total_coincidencias": datos_numero["cantidad"]
        }, None

    except Exception as e:
        mensaje_error = f"Error al validar coincidencias: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def procesar_loterias(loterias: list, log: object):
    """
    Función principal del orquestador.
    Recibe la lista de loterías a procesar y ejecuta
    el flujo completo de scraping y validación para cada una.

    Parámetros:
    - loterias : lista de loterías encontradas por buscar_loterias_hora_actual
    - log      : objeto de logs

    Retorna:
    - (list, None)  → lista de resultados validados si encontró
    - (None, str)   → None, mensaje si no encontró o falló
    """
    try:
        # PASO 1: obtenemos todas las URLs activas de la BD
        urls, error_urls = obtener_urls_scraping(log)

        if urls is None:
            return None, error_urls

        # Lista donde guardamos los resultados validados de todas las loterías
        resultados_finales = []

        # PASO 2: procesamos cada lotería encontrada
        for loteria in loterias:

            # Extraemos los datos de la lotería
            id_horario     = loteria[0]
            nombre_loteria = loteria[1]

            log.info(f"Iniciando scraping para: {nombre_loteria}")

            # Array donde acumulamos los resultados de cada URL
            resultados_acumulados = []

            # PASO 3: recorremos todas las URLs activas
            for url_data in urls:
                nombre_fuente = url_data[1]
                url           = url_data[2]

                # Ejecutamos el scraping en esta URL
                resultado, error = ejecutar_scraping_por_url(
                    nombre_loteria,
                    nombre_fuente,
                    url,
                    log
                )

                # Si esta URL tenía el resultado de hoy lo acumulamos
                # guardamos numero, quinta, signo y fuente
                if resultado:
                    resultados_acumulados.append({
                        "numero": resultado["numero"],
                        "quinta": resultado.get("quinta", ""),
                        "signo" : resultado.get("signo", ""),
                        "fuente": nombre_fuente
                    })
                    log.info(f"Fuentes acumuladas hasta ahora: {len(resultados_acumulados)}")

            # PASO 4: validamos número, quinta y signo
            resultado_validado, error_validacion = validar_coincidencias(
                resultados_acumulados,
                log
            )

            # Si no se alcanzaron las coincidencias mínimas pasamos a la siguiente lotería
            if resultado_validado is None:
                log.info(f"{nombre_loteria}: {error_validacion}")
                continue

            # PASO 5: insertamos el resultado validado en la BD
            insertado, error_insercion = insertar_resultado_scraping(
                id_horario = id_horario,
                numero     = resultado_validado["numero"],
                quinta     = resultado_validado["quinta"],
                signo      = resultado_validado.get("signo", ""),
                serie      = "",
                log        = log
            )

            # Si falló la inserción lo registramos pero seguimos con las demás loterías
            if insertado is None:
                log.error(f"Error al insertar resultado de {nombre_loteria}: {error_insercion}")

            # PASO 6: agregamos el resultado validado a la lista final
            resultados_finales.append({
                "id_horario"         : id_horario,
                "nombre_loteria"     : nombre_loteria,
                "numero"             : resultado_validado["numero"],
                "quinta"             : resultado_validado["quinta"],
                "signo"              : resultado_validado.get("signo", ""),
                "fuentes"            : resultado_validado["fuentes"],
                "total_coincidencias": resultado_validado["total_coincidencias"]
            })

        if not resultados_finales:
            return None, "No se validó ningún resultado con suficientes coincidencias"

        return resultados_finales, None

    except Exception as e:
        mensaje_error = f"Error en el orquestador: {e}"
        log.error(mensaje_error)
        return None, mensaje_error