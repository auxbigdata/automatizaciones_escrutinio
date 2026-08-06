import time
from src.services.db import ejecutar_query
from src.services.escrutinio_consultas_bd import (
    insertar_resultado_scraping,
    actualizar_estado_horario,
    ESTADO_PENDIENTE,
    ESTADO_ERROR,
)
from src.services.escrutinio_api import scraping_gane_norte_valle
from src.services.escrutinio_respaldo_scraping import (
    recolectar_pool_secundario,
    filtrar_pool_por_loteria,
)
from src.services.utils_scraping import MIN_FUENTES_COINCIDENTES, validar_coincidencias
from src.services.escrutinio_html import (
    scraping_supergiros,
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

        elif nombre_fuente == "supergiros":
            resultado, error = scraping_supergiros(nombre_loteria, url, log)

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


def procesar_loterias(loterias: list, log: object):
    """Orquesta scraping y validación completa para cada lotería en `loterias`.

    Una lotería sin coincidencias suficientes se omite (queda pendiente para el próximo cron),
    NO es un error del robot. Por eso el retorno exitoso siempre es (list, None) -aunque la
    lista quede vacía-. Una excepción no controlada en UNA lotería puntual queda aislada
    (se marca ESTADO_ERROR solo para esa lotería) y no aborta el resto del lote.
    (None, mensaje) queda reservado para fallas técnicas que afectan a TODO el ciclo
    (ej. sin URLs activas), que es lo único que debe disparar el Caso 3."""
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

            # Cada lotería queda aislada: si algo inesperado revienta procesándola (falla técnica
            # real, no "sin consenso de fuentes"), se marca ESTADO_ERROR solo para esa lotería y
            # se sigue con las demás del lote, en vez de tumbar el ciclo completo.
            try:
                _procesar_una_loteria(id_horario, nombre_loteria, urls, log, resultados_finales)
            except Exception as e:
                log.error(f"{nombre_loteria}: falla técnica procesando la lotería, se marca estado={ESTADO_ERROR}: {e}")
                actualizar_estado_horario(id_horario, ESTADO_ERROR, log)

        if not resultados_finales:
            log.info("No se validó ningún resultado con suficientes coincidencias en este ciclo (no es una falla, se reintentará en el próximo cron)")

        return resultados_finales, None

    except Exception as e:
        mensaje_error = f"Error en el orquestador: {e}"
        log.error(mensaje_error)
        return None, mensaje_error


def _procesar_una_loteria(id_horario: int, nombre_loteria: str, urls: list, log: object, resultados_finales: list):
    """Cuerpo del PASO 2 para una sola lotería, aislado en su propia función para que
    procesar_loterias pueda envolver cada lotería en su propio try/except (ver arriba)."""
    log.info(f"Iniciando scraping para: {nombre_loteria}")

    # PASO 3+4/CASO 1: intenta resultado validado (principal+respaldo); si no alcanza el mínimo, reintenta hasta MAX_REINTENTOS_SIN_COINCIDENCIAS veces
    resultado_validado = None

    # Este set vive fuera del for de reintentos: así, si el scraping
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

        # CASO 1: si el principal no validó (número o quinta/signo sin llegar al mínimo),
        # se dispara el scraping de respaldo para esta lotería y sus fuentes se SUMAN
        # a las del principal -no se le exige al respaldo llegar solo al mínimo-, y se
        # vuelve a validar el total combinado con la misma validar_coincidencias().
        if resultado_validado is None:
            log.info(f"{nombre_loteria}: {error_validacion}. Intentando scraping de respaldo...")

            pool_respaldo    = recolectar_pool_secundario(log, urls_excluir=urls_ya_usadas_para_esta_loteria)
            fuentes_respaldo = filtrar_pool_por_loteria(pool_respaldo, nombre_loteria)

            if fuentes_respaldo:
                log.info(
                    f"{nombre_loteria}: el scraping de respaldo aportó {len(fuentes_respaldo)} "
                    f"fuente(s) más, se suman a las {len(resultados_acumulados)} del principal"
                )
                resultados_acumulados.extend(fuentes_respaldo)

                # Marcamos también esas URLs como usadas, por si el CASO 2 necesita respaldo de nuevo
                for r in fuentes_respaldo:
                    if r.get("fuente"):
                        urls_ya_usadas_para_esta_loteria.add(r["fuente"])

                # Revalidamos número/quinta/signo con el total combinado (principal + respaldo)
                resultado_validado, error_validacion = validar_coincidencias(
                    resultados_acumulados,
                    log
                )

                if resultado_validado is None:
                    log.info(f"{nombre_loteria}: {error_validacion} (ya sumando el respaldo)")
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
        # No es una falla técnica: vuelve a ESTADO_PENDIENTE para que el próximo cron la reintente sola.
        actualizar_estado_horario(id_horario, ESTADO_PENDIENTE, log)
        return

    # CASO 2: la quinta y/o el signo no alcanzaron el mínimo de fuentes (0, 1, o 2 sin
    # llegar a las MIN_FUENTES_COINCIDENTES habituales) -> buscamos más fuentes de
    # respaldo para esta lotería y revalidamos con el total combinado. Si ni así se
    # alcanzan las 3, validar_coincidencias ya acepta el mejor valor con 2 fuentes de
    # acuerdo (MIN_FUENTES_QUINTA_SIGNO); si ni eso, queda vacía pero el número se reporta igual.
    if resultado_validado.get("quinta_pendiente") or resultado_validado.get("signo_pendiente"):
        log.info(f"{nombre_loteria}: quinta/signo sin alcanzar {MIN_FUENTES_COINCIDENTES} fuentes, buscando respaldo para completar...")

        pool_respaldo    = recolectar_pool_secundario(log, urls_excluir=urls_ya_usadas_para_esta_loteria)
        fuentes_respaldo = filtrar_pool_por_loteria(pool_respaldo, nombre_loteria)

        if fuentes_respaldo:
            log.info(f"{nombre_loteria}: el scraping de respaldo aportó {len(fuentes_respaldo)} fuente(s) más para completar quinta/signo")
            resultados_acumulados.extend(fuentes_respaldo)

            resultado_revalidado, error_revalidacion = validar_coincidencias(resultados_acumulados, log)
            if resultado_revalidado is not None:
                resultado_validado = resultado_revalidado
            else:
                log.info(f"{nombre_loteria}: {error_revalidacion} al revalidar con el respaldo de quinta/signo, se mantiene el resultado previo")
        else:
            log.info(f"{nombre_loteria}: tampoco se encontró en el scraping de respaldo para completar quinta/signo")

    # PASO 5: inserta el resultado final (con o sin parche de respaldo) en la BD
    # (deja estado=ESTADO_SCRAPING_EJECUTADO en es_config_horarios en la misma transacción)
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