import time
from src.services.db import ejecutar_query
from src.services.escrutinio_consultas_bd import insertar_resultado_scraping
from src.services.escrutinio_api import scraping_gane_norte_valle
from src.services.escrutinio_respaldo_scraping import buscar_respaldo_secundario
from src.services.utils_scraping import normalizar_texto, MAPEO_SIGNOS
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

# Reintentos del ciclo completo (principal + respaldo) antes de omitir la lotería y esperar al próximo cron
MAX_REINTENTOS_SIN_COINCIDENCIAS = 3


def obtener_urls_scraping(log: object):
    """Retorna las URLs activas (estado=1) de es_origenes_scraping. (list, None) o (None, mensaje) si falla."""
    try:
        log.info("Obteniendo URLs activas de es_origenes_scraping")

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
    """Llama la función de scraping según nombre_fuente (para una nueva fuente, agregar su elif aquí). Retorna (dict, None) o (None, mensaje)."""
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
            # Fuente sin función implementada
            log.info(f"Fuente '{nombre_fuente}' aún no tiene función implementada")
            return None, f"Fuente '{nombre_fuente}' no implementada"

        if resultado:
            log.info(f"Fuente '{nombre_fuente}' → numero={resultado.get('numero')} | quinta='{resultado.get('quinta', '')}' | signo='{resultado.get('signo', '')}'")

        return resultado, error

    except Exception as e:
        mensaje_error = f"Error inesperado al ejecutar scraping en {nombre_fuente}: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def validar_coincidencias(resultados: list, log: object):
    """Valida en 3 niveles: número (mínimo MIN_FUENTES_COINCIDENTES), quinta y signo (solo entre fuentes que los trajeron). Retorna (dict, None) o (None, mensaje)."""
    try:
        if not resultados:
            return None, "No hay resultados para comparar"

        # NIVEL 1: Validar el número
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

            # Solo si la fuente trajo quinta: normalizamos y resolvemos sinónimos (ej. Escorpión=Escorpio)
            if r.get('quinta'):
                quinta_normalizada = normalizar_texto(r['quinta'])
                quinta_final = MAPEO_SIGNOS.get(quinta_normalizada, quinta_normalizada)
                conteo_numero[num]["quintas"].append(quinta_final)

            # Solo acumulamos signo si la fuente lo trajo
            if r.get('signo'):
                signo_normalizado = normalizar_texto(r['signo'])
                signo_final = MAPEO_SIGNOS.get(signo_normalizado, signo_normalizado)
                conteo_numero[num]["signos"].append(signo_final)

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

        # NIVEL 2: Validar la quinta (solo si alguna fuente la trajo)
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

        # NIVEL 3: Validar el signo (solo si alguna fuente lo trajo)
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
    """Orquesta scraping y validación completa para cada lotería en `loterias`. Retorna (list, None) o (None, mensaje)."""
    try:
        # PASO 1: obtenemos todas las URLs activas de la BD
        urls, error_urls = obtener_urls_scraping(log)

        if urls is None:
            return None, error_urls

        resultados_finales = []

        # PASO 2: procesamos cada lotería encontrada
        for loteria in loterias:

            id_horario     = loteria[0]
            nombre_loteria = loteria[1]

            log.info(f"Iniciando scraping para: {nombre_loteria}")

            # PASO 3+4/CASO 1: intenta resultado validado (principal+respaldo); si no alcanza el mínimo, reintenta hasta MAX_REINTENTOS_SIN_COINCIDENCIAS veces
            resultado_validado = None

            #Este set vive fuera del for de reintentos: así, si el scraping
            # principal validó algo pero el CASO 2 necesita volver a llamar
            # al respaldo (para completar quinta/signo), sabemos qué URLs
            # ya no repetir.
            urls_ya_usadas_para_esta_loteria = set()

            for intento in range(MAX_REINTENTOS_SIN_COINCIDENCIAS + 1):
                if intento > 0:
                    log.info(
                        f"{nombre_loteria}: reintento {intento}/{MAX_REINTENTOS_SIN_COINCIDENCIAS} "
                        f"(scraping principal + respaldo)"
                    )

                resultados_acumulados = []

                for url_data in urls:
                    nombre_fuente = url_data[1]
                    url           = url_data[2]

                    resultado, error = ejecutar_scraping_por_url(
                        nombre_loteria,
                        nombre_fuente,
                        url,
                        log
                    )

                    # Si trajo resultado, lo acumulamos con numero/quinta/signo/fuente
                    if resultado:
                        resultados_acumulados.append({
                            "numero": resultado["numero"],
                            "quinta": resultado.get("quinta", ""),
                            "signo" : resultado.get("signo", ""),
                            "fuente": nombre_fuente
                        })
                        log.info(f"Fuentes acumuladas hasta ahora: {len(resultados_acumulados)}")

                urls_ya_usadas_para_esta_loteria = set()

                for r in resultados_acumulados:
                    # buscamos dentro de las urls activas cuál fuente trajo este resultado
                    for url_data in urls:
                        if url_data[1] == r["fuente"]:
                            urls_ya_usadas_para_esta_loteria.add(url_data[2])
                            break

                # Validamos número, quinta y signo
                resultado_validado, error_validacion = validar_coincidencias(
                    resultados_acumulados,
                    log
                )

                # CASO 1: si el principal no validó ningún número, se dispara el scraping de respaldo para esta lotería
                if resultado_validado is None:
                    log.info(f"{nombre_loteria}: {error_validacion}. Intentando scraping de respaldo...")

                    respaldo = buscar_respaldo_secundario(nombre_loteria, log, urls_excluir=urls_ya_usadas_para_esta_loteria)

                    # El respaldo exige el mismo mínimo de fuentes que el principal
                    if respaldo and respaldo["total_coincidencias"] >= MIN_FUENTES_COINCIDENTES:
                        resultado_validado = {
                            "numero"             : respaldo["numero"],
                            "quinta"             : respaldo.get("quinta") or "",
                            "signo"              : respaldo.get("signo") or "",
                            "fuentes"            : respaldo["fuentes"],
                            "total_coincidencias": respaldo["total_coincidencias"],
                        }
                        log.info(
                            f"{nombre_loteria}: resultado obtenido por scraping de respaldo -> "
                            f"numero={resultado_validado['numero']} "
                            f"({resultado_validado['total_coincidencias']} fuente(s) secundaria(s))"
                        )
                    elif respaldo:
                        log.info(
                            f"{nombre_loteria}: el scraping de respaldo solo tuvo "
                            f"{respaldo['total_coincidencias']} fuente(s) coincidente(s) "
                            f"(mínimo {MIN_FUENTES_COINCIDENTES})"
                        )
                    else:
                        log.info(f"{nombre_loteria}: tampoco se encontró en el scraping de respaldo")

                # Ya hay resultado validado (principal o respaldo), no hace falta reintentar
                if resultado_validado is not None:
                    break

            if resultado_validado is None:
                log.info(
                    f"{nombre_loteria}: se agotaron los {MAX_REINTENTOS_SIN_COINCIDENCIAS} reintentos "
                    f"sin alcanzar {MIN_FUENTES_COINCIDENTES} fuentes coincidentes, se omite en este ciclo"
                )
                continue

            # CASO 2: falta quinta Y signo -> completar con respaldo si coincide el número
            # (escrutinio_html.py nunca separa "signo" de "quinta", por eso se exige que falten ambos)
            if not resultado_validado.get("quinta") and not resultado_validado.get("signo"):
                respaldo = buscar_respaldo_secundario(nombre_loteria, log, urls_excluir=urls_ya_usadas_para_esta_loteria)

                if respaldo and respaldo.get("numero") == resultado_validado["numero"]:
                    if not resultado_validado.get("quinta") and respaldo.get("quinta"):
                        resultado_validado["quinta"] = respaldo["quinta"]
                        log.info(f"{nombre_loteria}: quinta completada por scraping de respaldo ({respaldo['quinta']})")
                    if not resultado_validado.get("signo") and respaldo.get("signo"):
                        resultado_validado["signo"] = respaldo["signo"]
                        log.info(f"{nombre_loteria}: signo completado por scraping de respaldo ({respaldo['signo']})")
                elif respaldo:
                    log.info(
                        f"{nombre_loteria}: el scraping de respaldo trajo un número distinto "
                        f"({respaldo.get('numero')} vs {resultado_validado['numero']}), se descarta su quinta/signo"
                    )

            # PASO 5: inserta el resultado final (con o sin parche de respaldo) en la BD
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

            # PASO 6: agregamos el resultado a la lista final
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