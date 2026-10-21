import traceback
import html
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.services.db import ejecutar_query
from src.services.escrutinio_consultas_bd import consultar_loterias_por_programar
from src.services.programacion_loteries_superflex import programacion_sorteos_superflex
from src.services.browser import tomar_captura

def menu_programacion_loterias(page, ruta_archivos, log=object):
    try:
        log.info("abriendo el menu de programacion de loterias en BNET")
        menu_procesos = page.wait_for_selector('a.ui-menuitem-link:has(span.ui-menuitem-text:has-text("Procesos escrutinio"))',state='visible',timeout=10000)
        menu_procesos.click()

        resultado_loterias= page.wait_for_selector('a.ui-menuitem-link:has(span.ui-menuitem-text:has-text("Resultados de loterías"))', state='visible', timeout=15000)
        resultado_loterias.click()
        page.wait_for_timeout(10000) 

        log.info("menu 'Resultados de loterías' abierto correctamente en BNET")
        return True, ""

    except PlaywrightTimeoutError:
        # se revisa cual menu no aparecio, para que el correo diga exactamente donde fallo
        if not page.locator('a.ui-menuitem-link:has(span.ui-menuitem-text:has-text("Procesos escrutinio"))').count():
            mensaje = "Error: no aparecio el menu 'Procesos escrutinio' en BNET"
        else:
            mensaje = "Error: no aparecio el menu 'Resultados de loterías' en BNET"
        log.error(mensaje)
        tomar_captura(page, "menu_bnet", ruta_archivos, log)
        return False, mensaje
    
    except Exception as e:
        mensaje = f"Ocurrio un error durante la programación de loterías: {e}"
        log.error(mensaje)
        log.error(traceback.format_exc())
        tomar_captura(page, "menu_bnet", ruta_archivos, log)
        return False, mensaje

def programacion_loterias(page, page_superflex, ruta_archivos, log=object):
    try:
        log.info("iniciando proceso de programacion de loterias")

        loterias, error = consultar_loterias_por_programar(ruta_archivos, log)
        # None = fallo la consulta (error real), lista vacia = no hay loterias por programar (no es error)
        if loterias is None:
            return False, error
        if not loterias:
            return None, error

        # resultado de cada loteria en cada plataforma, para el resumen del correo
        resultados = []

        for loteria in loterias:
            id_horario = loteria["id_horario"]
            codigo = str(loteria["cod_proceso"])
            fecha = loteria["fecha_sorteo"]
            hora = loteria["hora_programada"]
            hora_cierre = loteria["hora_cierre"]
            # cada plataforma solo se programa si SU columna esta en 0
            bnet_pendiente = loteria["estado_programacion"] == 0
            superflex_pendiente = loteria["programacion_superx"] == 0
            log.info(f"programando loteria: {loteria['nombre_loteria']} | codigo={codigo} | fecha={fecha} | hora={hora} | hora_cierre={hora_cierre} | bnet_pendiente={bnet_pendiente} | superflex_pendiente={superflex_pendiente}")

            # ---------- BNET (columna estado_programacion) ----------
            # None = no tocaba (ya estaba programada), True = se programo, False = fallo
            bnet_ok, error_bnet = None, ""
            if bnet_pendiente:
                # 1 = Corriendo Programacion: marcamos ESTA loteria apenas la tomamos
                ejecutar_query(
                    "UPDATE es_config_horarios SET estado_programacion = 1 WHERE id_horario = %s",
                    (id_horario,)
                )
                log.info(f"estado_programacion = 1 para id_horario: {id_horario}")
                bnet_ok = True
                try:
                    page.bring_to_front()
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

                    # hora final venta online: si BNET ya tiene la misma hora_cierre se deja, si es distinta se cambia
                    input_hora_final = page.locator('input[name="tbwLoterias:frmLoteria:txtmHoraFinalVentaOnline"]')
                    input_hora_final.wait_for(state="visible", timeout=15000)
                    hora_final_bnet = input_hora_final.input_value()
                    if hora_cierre is None:
                        log.info(f"hora_cierre vacia en BD, se deja la hora final venta online de BNET: {hora_final_bnet}")
                    elif hora_final_bnet == hora_cierre:
                        log.info(f"hora final venta online igual a hora_cierre ({hora_cierre}), se deja")
                    else:
                        input_hora_final.fill(hora_cierre)
                        log.info(f"hora final venta online cambiada de {hora_final_bnet} a {hora_cierre}")
                        page.wait_for_timeout(4000)

                    boton_guardar = page.locator('button[name="tbwLoterias:frmLoteria:btnGuardarloteria"]')
                    boton_guardar.wait_for(state="visible", timeout=15000)
                    # BNET deja sus mensajes en pantalla (no se borran solos): se limpian los viejos
                    # para leer solo la respuesta de ESTE guardado
                    page.evaluate("() => { const c = document.getElementById('growle_container'); if (c) c.innerHTML = ''; }")
                    boton_guardar.click()

                    # respuesta de BNET: "Información" = guardo bien; "Advertencia" o "Error" = no guardo
                    respuesta_bnet = page.locator('#growle_container .ui-growl-item-container').first
                    respuesta_bnet.wait_for(state="visible", timeout=15000)
                    texto_respuesta = " ".join(respuesta_bnet.inner_text().split())
                    if "ui-growl-image-info" not in respuesta_bnet.locator('.ui-growl-image').get_attribute("class"):
                        raise Exception(f"BNET no guardo la loteria: {texto_respuesta}")
                    log.info(f"loteria guardada en BNET: {loteria['nombre_loteria']} ({texto_respuesta})")

                    boton_limpiar = page.locator('button[name="tbwLoterias:frmLoteria:j_idt182"]')
                    boton_limpiar.wait_for(state="visible", timeout=15000)
                    boton_limpiar.click()

                except PlaywrightTimeoutError as e:
                    tomar_captura(page, f"bnet_{loteria['nombre_loteria']}", ruta_archivos, log)
                    bnet_ok, error_bnet = False, f"BNET no respondio a tiempo (timeout): {e}"
                    log.error(f"no se pudo programar id_horario={id_horario} ({loteria['nombre_loteria']}) en BNET por timeout: {e}")

                except Exception as e:
                    tomar_captura(page, f"bnet_{loteria['nombre_loteria']}", ruta_archivos, log)
                    bnet_ok, error_bnet = False, str(e)
                    log.error(f"no se pudo programar id_horario={id_horario} ({loteria['nombre_loteria']}) en BNET: {e}")
                    log.error(traceback.format_exc())

                if bnet_ok:
                    # 3 = Finalizada Programacion: BNET mostro el mensaje de exito, se marca de una vez
                    # para que si el robot se cae con la siguiente loteria esta no quede a medias
                    ejecutar_query(
                        "UPDATE es_config_horarios SET estado_programacion = 3 WHERE id_horario = %s",
                        (id_horario,)
                    )
                    log.info(f"estado_programacion = 3 para id_horario: {id_horario}")
                else:
                    # 4 = error en BNET, queda para revision manual
                    ejecutar_query(
                        "UPDATE es_config_horarios SET estado_programacion = 4 WHERE id_horario = %s",
                        (id_horario,)
                    )
                    log.info(f"estado_programacion = 4 para id_horario: {id_horario}")

            # ---------- SUPERFLEX (columna programacion_superx, se intenta aunque BNET haya fallado) ----------
            superflex_ok, error_superflex = None, ""
            if superflex_pendiente:
                ejecutar_query(
                    "UPDATE es_config_horarios SET programacion_superx = 1 WHERE id_horario = %s",
                    (id_horario,)
                )
                log.info(f"programacion_superx = 1 para id_horario: {id_horario}")
                try:
                    page_superflex.bring_to_front()
                    superflex_ok, error_superflex = programacion_sorteos_superflex(page_superflex, loteria, ruta_archivos, log=log)
                except Exception as e:
                    superflex_ok, error_superflex = False, str(e)

                if superflex_ok:
                    # 3 = Finalizada Programacion: Superflex mostro el mensaje "con éxito", se marca de una vez
                    ejecutar_query(
                        "UPDATE es_config_horarios SET programacion_superx = 3 WHERE id_horario = %s",
                        (id_horario,)
                    )
                    log.info(f"programacion_superx = 3 para id_horario: {id_horario}")
                else:
                    log.error(f"no se pudo programar id_horario={id_horario} ({loteria['nombre_loteria']}) en SUPERFLEX: {error_superflex}")
                    ejecutar_query(
                        "UPDATE es_config_horarios SET programacion_superx = 4 WHERE id_horario = %s",
                        (id_horario,)
                    )
                    log.info(f"programacion_superx = 4 para id_horario: {id_horario}")

            resultados.append({
                "loteria": loteria,
                "bnet_ok": bnet_ok,
                "superflex_ok": superflex_ok,
                "error_bnet": error_bnet,
                "error_superflex": error_superflex,
            })

        # el correo siempre lleva el resumen; si alguna fallo en cualquier plataforma se devuelve False para que vaya como error
        todas_ok = not any(r["bnet_ok"] is False or r["superflex_ok"] is False for r in resultados)
        return todas_ok, armar_resumen_programacion(resultados)

    except PlaywrightTimeoutError:
        mensaje = "Error: Timeout durante la programación de loterías"
        log.error(mensaje)
        return False, mensaje

    except Exception as e:
        mensaje = f"Ocurrio un error durante la programación de loterías: {e}"
        log.error(mensaje)
        log.error(traceback.format_exc())
        return False, mensaje

def _motivo_corto(error):
    # los errores de playwright traen varias lineas de detalle; al correo solo va la primera
    return html.escape(error.strip().splitlines()[0][:200]) if error else ""

def armar_resumen_programacion(resultados):
    """Arma el cuerpo HTML del correo: una tabla con cada loteria y, debajo, los grupos por plataforma.
    En cada plataforma: True = se programo, False = fallo, None = no tocaba (ya estaba programada)."""
    si = '<span style="color:#1e7e34;font-weight:bold;">Sí</span>'
    no = '<span style="color:#c82333;font-weight:bold;">No</span>'
    ya_estaba = '<span style="color:#6c757d;">Ya estaba</span>'
    celda = 'style="border:1px solid #cccccc;padding:4px 8px;"'

    def texto_estado(ok):
        return ya_estaba if ok is None else (si if ok else no)

    filas = ""
    for r in resultados:
        loteria = r["loteria"]
        filas += (
            f"<tr><td {celda}>{html.escape(loteria['nombre_loteria'])}</td>"
            f"<td {celda}>{loteria['fecha_sorteo']}</td>"
            f"<td {celda}>{loteria['hora_programada'][:5]}</td>"
            f"<td {celda} align='center'>{texto_estado(r['bnet_ok'])}</td>"
            f"<td {celda} align='center'>{texto_estado(r['superflex_ok'])}</td></tr>"
        )

    tabla = (
        '<table style="border-collapse:collapse;font-size:13px;margin:10px 0;">'
        f"<tr style='background-color:#f0f0f0;'><th {celda}>Lotería</th><th {celda}>Fecha</th>"
        f"<th {celda}>Hora</th><th {celda}>BNET</th><th {celda}>Superflex</th></tr>"
        f"{filas}</table>"
    )

    def nombre(r):
        return html.escape(r["loteria"]["nombre_loteria"])

    def motivos(r):
        partes = []
        if r["bnet_ok"] is False:
            partes.append(f"BNET: {_motivo_corto(r['error_bnet'])}")
        if r["superflex_ok"] is False:
            partes.append(f"Superflex: {_motivo_corto(r['error_superflex'])}")
        return " | ".join(partes)

    # (titulo del grupo, estado BNET, estado Superflex)
    grupos_definidos = [
        ("Se programaron en BNET y en Superflex", True, True),
        ("Se programaron solo en BNET (en Superflex ya estaba)", True, None),
        ("Se programaron solo en Superflex (en BNET ya estaba)", None, True),
        ("Se programaron en BNET pero NO en Superflex", True, False),
        ("Se programaron en Superflex pero NO en BNET", False, True),
        ("No se programaron en ninguna plataforma", False, False),
        ("NO se programaron en BNET (en Superflex ya estaba)", False, None),
        ("NO se programaron en Superflex (en BNET ya estaba)", None, False),
    ]

    grupos = ""
    for titulo, estado_bnet, estado_superflex in grupos_definidos:
        del_grupo = [r for r in resultados if r["bnet_ok"] is estado_bnet and r["superflex_ok"] is estado_superflex]
        if not del_grupo:
            continue
        if estado_bnet is False or estado_superflex is False:
            grupos += f"<b>{titulo}:</b><br>" + "<br>".join(f"- {nombre(r)} ({motivos(r)})" for r in del_grupo) + "<br><br>"
        else:
            grupos += f"<b>{titulo}:</b> {', '.join(nombre(r) for r in del_grupo)}<br><br>"

    return f"Resumen de la programación de sorteos ({len(resultados)} loterías):<br>{tabla}<br>{grupos}"
