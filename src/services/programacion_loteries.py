import os
import json
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.services.db import ejecutar_query

def iniciar_bnet(page,URL_BNET,URL_HOMEBNET,USER_BNET,PASS_BNET,log=object):
    try:
        log.info("iniciando sesion en bnet")
        page.goto(f"{URL_BNET}")
        page.wait_for_load_state("domcontentloaded")

        input_usuario = page.wait_for_selector('input[name="idFormLogin:user"]', state='visible', timeout=(15000))
        input_usuario.fill(str(USER_BNET))

        input_password=page.wait_for_selector('input[name="idFormLogin:password"]', state='visible', timeout=(15000))
        input_password.fill(str(PASS_BNET))

        page.locator('button[name="idFormLogin:ingresar"]').click()
        page.wait_for_url(f"{URL_HOMEBNET}", timeout=15000)
        log.info("Login exitoso en Superflex")

        input_apuesta = page.wait_for_selector('span.modulo-titulo:has-text("Módulo de Apuestas")',state='visible',timeout=15000)
        input_apuesta.scroll_into_view_if_needed()
        input_apuesta.click()
        page.wait_for_load_state("domcontentloaded")
        log.info("Modulo de apuestas cargado correctamente")
        return True,""

    except PlaywrightTimeoutError:
        mensaje = "Error: Timeout al cargar la página de inicio de sesión de BNET"
        log.error(mensaje)
        return False, mensaje

    except Exception as e:
        mensaje = f"Ocurrio un error al iniciar sesión en BNET: {e}"
        log.error(mensaje)
        return False, mensaje

def menu_programacion_loterias(page, log=object):
    try:
        log.info("iniciando proceso de programacion de loterias")
        menu_procesos = page.wait_for_selector('a.ui-menuitem-link:has(span.ui-menuitem-text:has-text("Procesos escrutinio"))',state='visible',timeout=10000)
        menu_procesos.click()

        resultado_loterias= page.wait_for_selector('a.ui-menuitem-link:has(span.ui-menuitem-text:has-text("Resultados de loterías"))', state='visible', timeout=15000)
        resultado_loterias.click()
        page.wait_for_timeout(10000) 


        log.info("Proceso de programación de loterías completado exitosamente")
        return True, ""

    except PlaywrightTimeoutError:
        mensaje = "Error: Timeout durante la programación de loterías"
        log.error(mensaje)
        return False, mensaje
    
    except Exception as e:
        mensaje = f"Ocurrio un error durante la programación de loterías: {e}"
        log.error(mensaje)
        return False, mensaje


def consultar_loterias_por_programar(ruta_archivos, log=object):
    try:
        log.info("consultando loterias por programar (estado_programacion = 0)")
        sql = """
            SELECT id_horario, nombre_loteria, cod_proceso, hora_programada, fecha_sorteo, estado_programacion
            FROM es_config_horarios
            WHERE estado_programacion = 0
            ORDER BY hora_programada
        """
        filas = ejecutar_query(sql)

        if not filas:
            mensaje = "no hay loterias con estado_programacion = 0"
            log.info(mensaje)
            return None, mensaje

        loterias = []
        loterias_json = []
        for id_horario, nombre_loteria, cod_proceso, hora_programada, fecha_sorteo, estado_programacion in filas:
            datos = {
                "nombre_loteria": nombre_loteria,
                "cod_proceso": cod_proceso,
                "hora_programada": hora_programada.strftime("%H:%M:%S"),
                "fecha_sorteo": fecha_sorteo.strftime("%d/%m/%Y"),
                "estado_programacion": estado_programacion,
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


def programacion_loterias(page, ruta_archivos, log=object):
    try:
        log.info("iniciando proceso de programacion de loterias")

        loterias, error = consultar_loterias_por_programar(ruta_archivos, log)
        if error:
            return False, error

        # ids de las loterias que SI se programaron (para el update final a 3)
        ids_programadas = []

        for loteria in loterias:
            id_horario = loteria["id_horario"]
            codigo = str(loteria["cod_proceso"])
            fecha = loteria["fecha_sorteo"]
            hora = loteria["hora_programada"]
            log.info(f"programando loteria: {loteria['nombre_loteria']} | codigo={codigo} | fecha={fecha} | hora={hora}")

            try:
                # 1 = Corriendo Programacion: marcamos ESTA loteria apenas la tomamos
                ejecutar_query(
                    "UPDATE es_config_horarios SET estado_programacion = 1 WHERE id_horario = %s",
                    (id_horario,)
                )
                log.info(f"estado_programacion = 1 para id_horario: {id_horario}")

                input_codigo_loteria = page.locator('input[name="tbwLoterias:frmLoteria:txtCodigo"]')
                input_codigo_loteria.wait_for(state="visible", timeout=15000)
                input_codigo_loteria.fill(codigo)
                input_codigo_loteria.press("Enter")
                page.wait_for_timeout(4000)

                input_fecha = page.locator('input[name="tbwLoterias:frmLoteria:txtmFechaSorteo_input"]')
                input_fecha.wait_for(state="visible", timeout=15000)
                input_fecha.fill(fecha)
                input_fecha.press("Enter")

                input_hora = page.locator('input[name="tbwLoterias:frmLoteria:txtmHoraRealSorteoOnline"]')
                input_hora.wait_for(state="visible", timeout=15000)
                input_hora.fill(hora)
                page.wait_for_timeout(4000)

                boton_guardar = page.locator('button[name="tbwLoterias:frmLoteria:btnGuardarloteria"]')
                boton_guardar.wait_for(state="visible", timeout=15000)
                boton_guardar.click()
                page.wait_for_timeout(5000)

                # 2 = Programacion Ejecutado: ESTA loteria ya se guardo en BNET
                ejecutar_query(
                    "UPDATE es_config_horarios SET estado_programacion = 2 WHERE id_horario = %s",
                    (id_horario,)
                )
                log.info(f"estado_programacion = 2 para id_horario: {id_horario}")

                boton_limpiar = page.locator('button[name="tbwLoterias:frmLoteria:j_idt182"]')
                boton_limpiar.wait_for(state="visible", timeout=15000)
                boton_limpiar.click()

                ids_programadas.append(id_horario)

            except Exception as e:
                # una loteria que falla no detiene el lote: se marca en 4 y se sigue con la siguiente
                log.error(f"no se pudo programar id_horario={id_horario} ({loteria['nombre_loteria']}): {e}")
                ejecutar_query(
                    "UPDATE es_config_horarios SET estado_programacion = 4 WHERE id_horario = %s",
                    (id_horario,)
                )
                log.info(f"estado_programacion = 4 para id_horario: {id_horario}")
                continue

        # 3 = Finalizada Programacion: solo las que realmente se programaron,
        # no toda la tabla ni las que se trajeron pero no se alcanzaron a hacer.
        if ids_programadas:
            ejecutar_query(
                "UPDATE es_config_horarios SET estado_programacion = 3 WHERE id_horario = ANY(%s)",
                (ids_programadas,)
            )
        log.info(f"estado_programacion = 3 para id_horario: {ids_programadas}")

        return True, ""

    except PlaywrightTimeoutError:
        mensaje = "Error: Timeout durante la programación de loterías"
        log.error(mensaje)
        return False, mensaje

    except Exception as e:
        mensaje = f"Ocurrio un error durante la programación de loterías: {e}"
        log.error(mensaje)
        return False, mensaje