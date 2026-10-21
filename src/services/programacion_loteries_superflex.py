from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
import traceback
from src.services.db import ejecutar_query
from src.services.browser import tomar_captura

def navegacion_menu_programacion_loterias(page, ruta_archivos, log=object):
    try:
        log.info("navegando al menu de programacion de loterias/sorteos")
        page_buscador = page.wait_for_selector('a:has(span.layout-menuitem-text:has-text("PRODUCTO-SERVICIO"))', state='visible', timeout=(10000))
        page_buscador.click()

        menu_apuesta_azar = page.wait_for_selector('li.active-menuitem ul[role="menu"] a:has(span:has-text("APUESTAS AZAR"))', state= 'visible')
        menu_apuesta_azar.click()

        config_general_apuesta = page.wait_for_selector('a:has(span.layout-menuitem-text:has-text("1-CONFIGURACIÓN GENERAL DE APUESTAS"))',state='visible',timeout=10000)
        config_general_apuesta.click()

        sorteos_loterias = page.wait_for_selector('a:has(span.layout-menuitem-text:has-text("2-Solicitud de sorteos y loterías"))', state='visible', timeout=10000)
        sorteos_loterias.click()
        page.wait_for_timeout(10000)
        log.info("Navegación de menú exitosa en Superflex")
        return True, "Navegación de menú exitosa en Superflex"

    except PlaywrightTimeoutError:
        tomar_captura(page, "menu_superflex", ruta_archivos, log)
        if not page.locator('a:has(span.layout-menuitem-text:has-text("PRODUCTO-SERVICIO"))').count():
            mensaje = "Error: la página de Superflex no cargó (no aparece el menú)"
        else:
            mensaje = "Error: Timeout al desplegar el menú de navegación en Superflex (APUESTAS AZAR / CONFIGURACIÓN GENERAL DE APUESTAS / Solicitud de sorteos y loterías  )"
        log.error(mensaje)
        return False, mensaje

    except Exception as e:
        tomar_captura(page, "menu_superflex", ruta_archivos, log)
        mensaje = f"Ocurrio un error al navegar el menú en superflex: {e}"
        log.error(mensaje)
        log.error(traceback.format_exc())
        return False, mensaje

def llenar_hora_superflex(page, campo, hora):
    # el campo de hora abre un selector con dos casillas (hora y minutos); escribir en el input principal no queda
    horas, minutos = hora.split(":")
    selector = f'[formcontrolname="{campo}"]'
    page.locator(f'{selector} #timeonly').focus()
    page.locator(f'{selector} .p-hour-picker input').fill(horas)
    page.locator(f'{selector} .p-minute-picker input').fill(minutos)
    page.locator(f'{selector} .p-minute-picker input').press("Tab")
    page.keyboard.press("Escape")

def programacion_sorteos_superflex(page, loteria, ruta_archivos, log=object):
    try:
        fecha = loteria["fecha_sorteo"]
        # superflex maneja la hora sin segundos (HH:MM), la consulta la trae como HH:MM:SS
        hora_sorteo = loteria["hora_programada"][:5]
        hora_cierre = loteria["hora_cierre"][:5] if loteria["hora_cierre"] else None
        nombre_loteria = loteria["nombre_loteria"]
        # el cod_proceso es el mismo en BNET y en Superflex
        codigo = str(loteria["cod_proceso"])
        log.info(f"Iniciando proceso de programación de sorteos en Superflex: {nombre_loteria} | codigo={codigo} | fecha={fecha} | hora_sorteo={hora_sorteo} | hora_cierre={hora_cierre}")
        solicitar_sorteo =page.wait_for_selector('Button:has-text("Solicitar Sorteo")', state='visible', timeout=10000)
        solicitar_sorteo.click()

        log.info("seleccionando el sorteo a programar")
        # dentro de tipoSolicitud porque la lista de sorteos tambien tiene un dropdown
        page.locator('[formcontrolname="tipoSolicitud"] span.p-dropdown-label').click()
        page.locator('li[aria-label="CREACIÓN"]').click()
        log.info("sorteo seleccionado correctamente")


        loteria= page.get_by_placeholder("Buscar Loteria (*)")
        loteria.fill(codigo)
        loteria.press("Enter")

        page.wait_for_timeout(10000)

        # si superflex encuentra la loteria el campo cambia al nombre; si se queda con el codigo es que no existe
        if loteria.input_value() == codigo:
            tomar_captura(page, f"superflex_{nombre_loteria}", ruta_archivos, log)
            page.locator('button:has-text("Cancelar")').click()
            page.wait_for_timeout(3000)
            mensaje = f"Superflex no encontro la loteria {nombre_loteria} con el codigo {codigo}"
            log.error(mensaje)
            return False, mensaje
        log.info(f"Loteria seleccionada correctamente: {loteria.input_value()}")

        # fecha inicial y fecha final: las dos van con la fecha del sorteo.
        # el calendario no toma el fill(), hay que teclear la fecha y dar Enter
        fecha_inicial = page.locator('p-calendar[formcontrolname="fechaInicial"] input')
        fecha_inicial.wait_for(state='visible', timeout=10000)
        fecha_inicial.focus()
        fecha_inicial.press_sequentially(fecha, delay=60)
        fecha_inicial.press("Enter")
        page.keyboard.press("Escape")

        fecha_final = page.locator('p-calendar[formcontrolname="fechaFinal"] input')
        fecha_final.wait_for(state='visible', timeout=10000)
        fecha_final.focus()
        fecha_final.press_sequentially(fecha, delay=60)
        fecha_final.press("Enter")
        page.keyboard.press("Escape")
        log.info(f"fecha inicial y fecha final: {fecha}")

        # hora cierre venta: si superflex ya tiene la misma hora_cierre se deja, si es distinta se cambia
        hora_cierre_superflex = page.locator('[formcontrolname="horaCierreVenta"] #timeonly').input_value()
        if hora_cierre is None:
            log.info(f"hora_cierre vacia en BD, se deja la hora cierre venta de Superflex: {hora_cierre_superflex}")
        elif hora_cierre_superflex == hora_cierre:
            log.info(f"hora cierre venta igual a hora_cierre ({hora_cierre}), se deja")
        else:
            llenar_hora_superflex(page, "horaCierreVenta", hora_cierre)
            log.info(f"hora cierre venta cambiada de {hora_cierre_superflex} a {hora_cierre}")

        # hora sorteo = hora_programada
        llenar_hora_superflex(page, "horaSorteoVenta", hora_sorteo)
        log.info(f"hora sorteo: {hora_sorteo}")

        page.wait_for_timeout(5000)

        # superflex solo habilita Guardar cuando acepta todos los campos (ej. no deja fechas pasadas)
        if not page.locator('button:has-text("Guardar")').is_enabled():
            tomar_captura(page, f"superflex_{nombre_loteria}", ruta_archivos, log)
            page.locator('button:has-text("Cancelar")').click()
            page.wait_for_timeout(3000)
            mensaje = f"Superflex no acepto los datos de {nombre_loteria} (fecha={fecha}, hora_cierre={hora_cierre}, hora_sorteo={hora_sorteo}), el boton Guardar no se habilito"
            log.error(mensaje)
            return False, mensaje

        page.locator('button:has-text("Guardar")').click()

        # superflex pide confirmacion: "¿Está seguro que desea guardar en un nuevo registro...?"
        confirmacion = page.locator('.p-confirm-dialog:visible')
        confirmacion.wait_for(state='visible', timeout=10000)
        confirmacion.locator('button:has-text("Aceptar")').click()

        # se espera el PRIMER mensaje que muestre superflex despues de Aceptar (exito o error), menos el aviso
        # de festivos que sale siempre al guardar y no es un error. Asi se actua apenas aparece el mensaje y la
        # captura sale con el mensaje en pantalla (duran 6 segundos), no cuando ya desaparecio
        respuesta_superflex = page.locator('.p-toast-message').filter(has_not_text="festivos").first
        try:
            respuesta_superflex.wait_for(state='visible', timeout=15000)
            texto_respuesta = " ".join(respuesta_superflex.inner_text().split())
        except PlaywrightTimeoutError:
            texto_respuesta = ""

        if "con éxito" not in texto_respuesta:
            tomar_captura(page, f"superflex_{nombre_loteria}", ruta_archivos, log)
            mensaje = f"Superflex no confirmo el guardado de {nombre_loteria}"
            if texto_respuesta:
                mensaje += f", mensaje en pantalla: {texto_respuesta}"
            log.error(mensaje)
            # se cierra el formulario para que la siguiente loteria pueda volver a Solicitar Sorteo
            # :visible porque el Cancelar del dialogo de confirmacion sigue en la pagina aunque oculto
            cancelar_formulario = page.locator('button:has-text("Cancelar"):visible').first
            if cancelar_formulario.count():
                cancelar_formulario.click()
                page.wait_for_timeout(3000)
            return False, mensaje

        page.wait_for_selector('Button:has-text("Solicitar Sorteo")', state='visible', timeout=15000)
        log.info(f"Sorteo guardado en Superflex: {nombre_loteria}")
        return True, ""

    except PlaywrightTimeoutError as e:
        tomar_captura(page, "superflex_programacion", ruta_archivos, log)
        mensaje = f"Error: timeout al solicitar el sorteo en Superflex: {e}"
        log.error(mensaje)
        return False, mensaje

    except Exception as e:
        tomar_captura(page, "superflex_programacion", ruta_archivos, log)
        mensaje = f"Ocurrio un error al programar el sorteo en superflex: {e}"
        log.error(mensaje)
        log.error(traceback.format_exc())
        return False, mensaje

    

        

