import re
from datetime import datetime
from urllib.parse import urlparse
from playwright.sync_api import Page
from src.services.utils_scraping import (
    construir_resultado,
    separar_numero_y_extra,
    clasificar_extra,
    normalizar_fecha,
    limpiar_texto,
    fecha_hoy_iso,
    homologar_nombre_sorteo,
)


def parsear_chancescolombia(page: Page, url: str, log=None) -> list[dict]:

    resultados = []

    hoy = fecha_hoy_iso()

    try:
        # 1. Asegurar la carga e hidratación del SPA de Nuxt
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(4000)

        # 2. Localizar las cabeceras de texto de las fechas
        cabeceras_fecha = page.locator("div.uppercase.secondary-caption")
        total_fechas = cabeceras_fecha.count()

        # 3. Iterar por cada fecha
        for idx in range(total_fechas):
            cabecera = cabeceras_fecha.nth(idx)
            fecha_texto = cabecera.inner_text()
            fecha_iso = normalizar_fecha(fecha_texto)

            if fecha_iso != hoy:
                continue

            # Tarjetas del bloque usando el eje del DOM hermano
            tarjetas_bloque = cabecera.locator("xpath=./following-sibling::div[1]//div[@data-pc-name='card']")
            total_tarjetas = tarjetas_bloque.count()

            # 4. Procesar las tarjetas
            for t_idx in range(total_tarjetas):
                tarjeta = tarjetas_bloque.nth(t_idx)

                try:
                    # Validar enlace interno de resultados
                    enlace = tarjeta.locator("a[href*='/resultados/']")
                    if enlace.count() == 0:
                        continue

                    href = enlace.first.get_attribute("href") or ""
                    if not href:
                        continue

                    # Extraer el nombre del sorteo
                    slug = href.rstrip("/").split("/")[-1]
                    nombre_sorteo = slug.replace("-", " ").replace("_", " ").title()
                    # Usar nombre homologado
                    nombre_sorteo = homologar_nombre_sorteo(nombre_sorteo)

                    # Extraer dígitos de las balotas
                    balotas = tarjeta.locator("div.score-shape-circle span")
                    total_balotas = balotas.count()

                    digitos = []
                    for b_idx in range(total_balotas):
                        texto_balota = balotas.nth(b_idx).inner_text()
                        texto_limpio = limpiar_texto(texto_balota)
                        if texto_limpio.isdigit():
                            digitos.append(texto_limpio)

                    if not digitos:
                        continue

                    # Parametrización de las balotas
                    quinta_balota = None
                    if len(digitos) >= 5:
                        numero_ganador = "".join(digitos[:4])  # Primeros 4 dígitos
                        quinta_balota = digitos[4]             # El 5to dígito es la Quinta
                    else:
                        numero_ganador = "".join(digitos)     # Comportamiento normal (4 dígitos o menos)

                    # Extraer campos adicionales (Signos, Series, etc.)
                    locator_extra = tarjeta.locator("div.flex.items-center.gap-2")
                    extra_texto = None
                    if locator_extra.count() > 0:
                        extra_texto = limpiar_texto(locator_extra.first.inner_text())

                    clasificacion = clasificar_extra(extra_texto)

                    # Prioridad: quinta detectada visualmente sobre la de clasificar_extra
                    quinta_final = quinta_balota if quinta_balota is not None else clasificacion.pop('quinta', None)

                    # Asegurar que 'quinta' no quede en kwargs
                    if 'quinta' in clasificacion:
                        clasificacion.pop('quinta')

                    resultado = construir_resultado(
                        nombre_sorteo=nombre_sorteo,
                        numero=numero_ganador,
                        fecha_iso=fecha_iso,
                        fuente=url,
                        quinta=quinta_final,
                        **clasificacion
                    )
                    resultados.append(resultado)

                except Exception as card_error:
                    if log:
                        log.warning(f"      Error en tarjeta #{t_idx} del bloque {fecha_iso}: {card_error}")
                    continue

    except Exception as e:
        if log:
            log.error(f"Error crítico general en chancescolombia: {e}")

    return resultados


def parsear_loteriasdecolombia(page: Page, url: str, log=None) -> list[dict]:

    resultados = []
    hoy = fecha_hoy_iso()
    anio_actual = str(datetime.now().year)

    MESES_MAPA = {
        "JAN": "ENERO", "FEB": "FEBRERO", "MAR": "MARZO", "APR": "ABRIL",
        "MAY": "MAYO", "JUN": "JUNIO", "JUL": "JULIO", "AUG": "AGOSTO",
        "SEP": "SEPTIEMBRE", "OCT": "OCTUBRE", "NOV": "NOVIEMBRE", "DEC": "DICIEMBRE",
        "ENE": "ENERO", "ABR": "ABRIL", "AGO": "AGOSTO"
    }

    try:
        # 1. Esperar hidratación completa del SPA
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(4000)

        # 2. Localizar las tarjetas p-card
        tarjetas = page.locator("div.p-card")
        total_tarjetas = tarjetas.count()

        # 3. Iteración sobre cada tarjeta de sorteo
        for idx in range(total_tarjetas):
            tarjeta = tarjetas.nth(idx)

            try:
                # Extraer Nombre del Sorteo
                locator_nombre = tarjeta.locator(".text-xl.font-bold, div.font-bold").first
                if locator_nombre.count() == 0:
                    continue
                nombre_sorteo = limpiar_texto(locator_nombre.inner_text())
                # Usar nombre homologado
                nombre_sorteo = homologar_nombre_sorteo(nombre_sorteo)
                nombre_sorteo_upper = nombre_sorteo.upper()

                # Extraer y normalizar la Fecha
                locator_fecha = tarjeta.locator("div.text-sm").first
                if locator_fecha.count() == 0:
                    continue
                fecha_original = limpiar_texto(locator_fecha.inner_text()).upper()

                partes_fecha = fecha_original.split()
                if len(partes_fecha) >= 2:
                    dia = partes_fecha[0]
                    mes_corto = partes_fecha[1]
                    mes_completo = MESES_MAPA.get(mes_corto, mes_corto)
                    fecha_preparada = f"{dia} {mes_completo} {anio_actual}"
                else:
                    fecha_preparada = f"{fecha_original} {anio_actual}"

                fecha_iso = normalizar_fecha(fecha_preparada)
                # Validar resultados de hoy
                if fecha_iso != hoy:
                    continue

                # Extraer balotas numéricas
                loc_balotas_num = tarjeta.locator("div.score-shape-circle span, .past-score-ball:not(.score-shape-square) span")
                total_balotas = loc_balotas_num.count()

                digitos_lista = []
                for b_idx in range(total_balotas):
                    digito = limpiar_texto(loc_balotas_num.nth(b_idx).inner_text())
                    if digito.isdigit():
                        digitos_lista.append(digito)

                if not digitos_lista:
                    continue

                # Inicializar variables de control
                numero_final = "".join(digitos_lista)
                quinta_final = None
                signo_final = None

                # MANEJO DE JUEGOS MULTIBALOTA (BALOTO / MILOTO)
                if "MILOTO" in nombre_sorteo_upper or "BALOTO" in nombre_sorteo_upper:
                    numero_final = "-".join(digitos_lista)

                # EXTRACCIÓN DE LA QUINTA CIFRA EN CHANCES TRADICIONALES
                elif len(numero_final) == 5 and "ASTRO" not in nombre_sorteo_upper:
                    quinta_final = numero_final[-1]   # Último dígito
                    numero_final = numero_final[:-1]  # Primeros 4 dígitos

                # EXTRACCIÓN DEL SIGNO ZODIACAL (PARA LOS ASTROS)
                loc_signo = tarjeta.locator("div.score-shape-square span div, div.score-shape-square span")
                if loc_signo.count() > 0:
                    texto_signo = limpiar_texto(loc_signo.first.inner_text()).upper()
                    if texto_signo and not texto_signo.isdigit() and len(texto_signo) > 3:
                        signo_final = texto_signo

                resultado = construir_resultado(
                    nombre_sorteo=nombre_sorteo,
                    numero=numero_final,
                    fecha_iso=fecha_iso,
                    quinta=quinta_final,
                    signo=signo_final,
                    fuente=url
                )
                resultados.append(resultado)

            except Exception as e_tarjeta:
                if log:
                    log.warning(f"   Error procesando tarjeta en el índice #{idx}: {e_tarjeta}")
                continue

    except Exception as e:
        if log:
            log.error(f"Error crítico general en el parser del ID 13: {e}")

    return resultados


def parsear_boletin_gana(page: Page, url: str, log=None) -> list[dict]:
    """boletin.gana.com.co: SPA vacío en el HTML inicial; se espera a que cargue el JS antes de leer."""

    resultados = []
    hoy = fecha_hoy_iso()

    # Normaliza abreviaturas de mes
    MESES_MAPA = {
        "ENE": "ENERO", "FEB": "FEBRERO", "MAR": "MARZO", "ABR": "ABRIL",
        "MAY": "MAYO", "JUN": "JUNIO", "JUL": "JULIO", "AGO": "AGOSTO",
        "SEP": "SEPTIEMBRE", "OCT": "OCTUBRE", "NOV": "NOVIEMBRE", "DIC": "DICIEMBRE"
    }
    anio_actual = str(datetime.now().year)

    try:
        # 1. Esperar hidratación completa del SPA de Gana
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(4000)

        # =========================================================================
        # PARTE A: RESULTADOS RECIENTES (CHANCES - COLUMNA IZQUIERDA)
        # =========================================================================

        locator_fecha_izq = page.locator("div.lg\\:col-span-3 h3:has-text('Resultados Recientes') + p")
        txt_izq = limpiar_texto(locator_fecha_izq.first.inner_text()).upper().replace(",", " ").replace("DE", "")
        fecha_izq_iso = normalizar_fecha(txt_izq)

        # Filas del tbody izquierdo
        filas_chances = page.locator("#main-results-body tr")
        total_chances = filas_chances.count()

        for i in range(total_chances):
            fila = filas_chances.nth(i)
            try:
                # Celda 1: Nombre del Sorteo (Ej: ANTIOQ1, DORDIA)
                celda_nombre = fila.locator("td").nth(0)
                if celda_nombre.count() == 0:
                    continue
                nombre_sorteo = limpiar_texto(celda_nombre.inner_text())
                # Usar nombre homologado
                nombre_sorteo = homologar_nombre_sorteo(nombre_sorteo)

                # Celda 2: Contenedor de Resultado y Quinta
                celda_resultado = fila.locator("td").nth(1)
                if celda_resultado.count() == 0:
                    continue

                # Número principal: span con clase text-3xl
                loc_num = celda_resultado.locator("span.text-3xl")
                if loc_num.count() == 0:
                    continue
                numero_ganador = limpiar_texto(loc_num.first.inner_text())

                if not numero_ganador:
                    continue

                # Fecha de la sección izquierda
                locator_fecha_izq = page.locator("div.lg\\:col-span-3 h3:has-text('Resultados Recientes') + p")
                txt_izq = limpiar_texto(locator_fecha_izq.first.inner_text()).upper().replace(",", " ").replace("DE", "")
                fecha_izq_iso = normalizar_fecha(txt_izq)

                # Solo resultados del día de hoy
                if fecha_izq_iso != hoy:
                    continue

                # AJUSTE DE QUINTA CIFRA:
                quinta_final = None
                loc_badge_quinta = celda_resultado.locator("span.bg-gray-100")

                if loc_badge_quinta.count() > 0:
                    txt_q = loc_badge_quinta.first.inner_text().upper()
                    if "QUINTA" in txt_q:
                        quinta_final = "".join([c for c in txt_q if c.isdigit()])

                # Construir resultado estandarizado para Chance
                resultado_chance = construir_resultado(
                    nombre_sorteo=nombre_sorteo,
                    numero=numero_ganador,
                    fecha_iso=fecha_izq_iso,
                    quinta=quinta_final,
                    fuente=url
                )
                resultados.append(resultado_chance)

            except Exception as e_chance:
                if log:
                    log.warning(f"      Error parseando fila #{i} de chances: {e_chance}")
                continue

        # =========================================================================
        # PARTE B: RESULTADOS DE LOTERÍAS (COLUMNA DERECHA)
        # =========================================================================

        cabeceras_fecha = page.locator("div.lg\\:col-span-2 h4.uppercase")
        total_cabeceras = cabeceras_fecha.count()

        for idx in range(total_cabeceras):
            cabecera = cabeceras_fecha.nth(idx)
            fecha_texto = limpiar_texto(cabecera.inner_text()).upper()

            # Filtrar textos que no corresponden a un bloque de fecha
            if "PLACA" in fecha_texto or "BALOTO" in fecha_texto or "MILOTO" in fecha_texto:
                continue

            # Expandir fecha abreviada a formato completo
            fecha_preparada = fecha_texto.replace(",", " ")
            palabras = fecha_preparada.split()
            palabras_expandidas = [MESES_MAPA.get(p, p) for p in palabras]
            fecha_preparada = " ".join(palabras_expandidas)

            if anio_actual not in fecha_preparada:
                fecha_preparada = f"{fecha_preparada} {anio_actual}"

            fecha_iso_loteria = normalizar_fecha(fecha_preparada)

            # Formato no procesable, saltar
            if not fecha_iso_loteria:
                continue

            # Solo resultados de hoy
            if fecha_iso_loteria != hoy:
                continue

            # Tarjetas del bloque (hermano div.space-y-3)
            tarjetas_bloque = cabecera.locator("xpath=./following-sibling::div[1]/div")
            total_tarjetas = tarjetas_bloque.count()

            for t_idx in range(total_tarjetas):
                tarjeta = tarjetas_bloque.nth(t_idx)
                try:
                    # Nombre de la Lotería (div font-bold text-gray-800)
                    loc_nom_lot = tarjeta.locator("div.font-bold")
                    if loc_nom_lot.count() == 0:
                        continue
                    nombre_loteria = limpiar_texto(loc_nom_lot.first.inner_text())
                    # Usar nombre homologado
                    nombre_loteria = homologar_nombre_sorteo(nombre_loteria)

                    # Número Ganador (div text-3xl font-mono text-gana-green)
                    loc_num_lot = tarjeta.locator("div.text-gana-green, div.font-mono")
                    if loc_num_lot.count() == 0:
                        continue
                    numero_loteria = limpiar_texto(loc_num_lot.first.inner_text())

                    # Serie (span bg-gray-100)
                    loc_badge_lot = tarjeta.locator("span.bg-gray-100")
                    serie_final = None
                    if loc_badge_lot.count() > 0:
                        txt_badge = limpiar_texto(loc_badge_lot.first.inner_text()).upper()
                        if "SERIE" in txt_badge:
                            serie_final = "".join([c for c in txt_badge if c.isdigit()])

                    # Construir resultado estandarizado para Lotería
                    resultado_loteria = construir_resultado(
                        nombre_sorteo=nombre_loteria,
                        numero=numero_loteria,
                        fecha_iso=fecha_iso_loteria,
                        serie=serie_final,
                        fuente=url
                    )
                    resultados.append(resultado_loteria)

                except Exception as e_lot:
                    if log:
                        log.warning(f"      Error parseando tarjeta de lotería #{t_idx}: {e_lot}")
                    continue

            # Solo procesar el primer bloque (más reciente)
            break

    except Exception as e:
        if log:
            log.error(f"Error crítico general en el parser unificado del ID 12: {e}")

    return resultados


def parsear_pagatodo(page: Page, url: str, log=None) -> list[dict]:

    resultados = []

    try:
        if log:
            log.info("   [PagaTodo] Esperando la inyección dinámica del DOM de Elementor...")

        # 1. Intentar esperar el contenedor principal o el formulario de consultas
        try:
            page.wait_for_selector("div.contenedor-resultado, form#frmConsultaResultados", timeout=12000)
        except Exception:
            if log:
                log.warning("   [PagaTodo] Timeout esperando contenedores principales. Intentando lectura directa del DOM...")

        # 2. Localizar los bloques utilizando selectores nativos de Playwright
        loc_bloques = page.locator("div.contenedor-resultado")
        total_bloques = loc_bloques.count()

        # Fallback: reemplaza find_parent inválido
        if total_bloques == 0:
            loc_bloques = page.locator("form#frmConsultaResultados div.datos-resultado")
            total_bloques = loc_bloques.count()
            usando_fallback_datos = True
        else:
            usando_fallback_datos = False

        if log:
            log.info(f"parsear_pagatodo: Detectados {total_bloques} bloques en vivo.")

        if total_bloques == 0:
            try:
                page.screenshot(path="pagatodo_error_render.png")
                if log:
                    log.error("   [PagaTodo] El DOM está vacío. Evidencia guardada en 'pagatodo_error_render.png'")
            except Exception:
                pass
            return resultados

        # 3. Extracción iterativa de los datos de los sorteos
        for idx in range(total_bloques):
            if usando_fallback_datos:
                bloque = loc_bloques.nth(idx).locator("..")  # ".." sube al padre en selectores XPath/Playwright
            else:
                bloque = loc_bloques.nth(idx)

            try:
                # Extraer Nombre del Sorteo (Desde el alt de la imagen)
                loc_img = bloque.locator("img")
                if loc_img.count() == 0:
                    continue

                nombre_raw = loc_img.first.get_attribute("alt") or ""
                nombre_sorteo = limpiar_texto(nombre_raw.replace("Lotera", "Lotería").replace("Lotería de", "").strip())

                if not nombre_sorteo:
                    continue

                # Extraer Fecha (Input de tipo date)
                loc_input = bloque.locator("input[type='date']")
                fecha_iso = None
                if loc_input.count() > 0:
                    fecha_iso = loc_input.first.get_attribute("value")

                if not fecha_iso:
                    fecha_iso = datetime.now().strftime("%Y-%m-%d")

                # Extraer Número Ganador
                loc_numero = bloque.locator("p.numero-ganador strong")
                if loc_numero.count() == 0:
                    loc_numero = bloque.locator("strong[id^='r-']")

                if loc_numero.count() == 0:
                    continue

                numero_txt = limpiar_texto(loc_numero.first.inner_text())
                numero, _ = separar_numero_y_extra(numero_txt)

                if not numero:
                    continue

                # Extraer Serie
                loc_serie = bloque.locator("p.numero-serie strong")
                if loc_serie.count() == 0:
                    loc_serie = bloque.locator("strong[id^='s-']")

                serie_final = None
                if loc_serie.count() > 0:
                    serie_txt = limpiar_texto(loc_serie.first.inner_text())
                    posible_serie = re.sub(r"\D", "", serie_txt)
                    if posible_serie:
                        serie_final = posible_serie

                # Formatear y añadir el resultado
                resultado = construir_resultado(
                    nombre_sorteo=nombre_sorteo,
                    numero=numero,
                    fecha_iso=fecha_iso,
                    serie=serie_final,
                    fuente=url
                )
                resultados.append(resultado)

                if log:
                    log.info(f"   [OK ID 15 - PagaTodo] {nombre_sorteo} -> Nro: {numero} | Serie: {serie_final} | Fecha: {fecha_iso}")

            except Exception as e_card:
                if log:
                    log.warning(f"   Error analizando el bloque index #{idx} en PagaTodo: {e_card}")
                continue

    except Exception as e:
        if log:
            log.error(f"Error crítico en el motor del parser de PagaTodo (ID 15): {e}")

    return resultados


PARSERS_SPA_POR_DOMINIO = {
    "chancescolombia.com": parsear_chancescolombia,
    "loteriasdecolombia.co": parsear_loteriasdecolombia,
    "boletin.gana.com.co": parsear_boletin_gana,
    "pagatodo.com.co": parsear_pagatodo,
}


def obtener_parser_spa(url: str):
    """Devuelve el parser SPA (Playwright `page`) para esta URL, o None. Compara por hostname real (evita colisiones entre dominios similares)."""
    hostname = (urlparse(url).hostname or "").lower()
    for dominio, parser in PARSERS_SPA_POR_DOMINIO.items():
        dominio = dominio.lower()
        if hostname == dominio or hostname.endswith("." + dominio):
            return parser
    return None
