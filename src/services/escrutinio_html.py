import re
import requests
from datetime import datetime
import pytz
from bs4 import BeautifulSoup
from src.services.servicios_email import fecha_actual_colombia
from src.services.utils_scraping import MAPEO_GENERICO, normalizar_texto,SLUGS_GANAR_CHANCE,CODIGOS_LOTI
from src.services.playwright import abrir_navegador


# centraliza la peticion para no repetir el headers en cada funcion
def realizar_peticion(url: str, log: object):
    try:
        headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*"
        }
        response = requests.get(url,headers=headers,timeout=15)
        return response, None
    except requests.exceptions.Timeout:
        mensaje_error = f"Timeout al realizar la petición a {url}"
        log.error(mensaje_error)
        return None, mensaje_error
    except requests.exceptions.ConnectionError:
        mensaje_error = f"Error de conexión al realizar la petición a {url}"
        log.error(mensaje_error)
        return None, mensaje_error
    except Exception as e:
        mensaje_error = f"Error al consultar la URl: {url}: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_supergiros(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde SuperGiros Norte del Valle (resultados/).

    Es un WordPress cuya tabla de resultados se llena en el navegador vía JS
    (consume la misma API que "Gane Norte del Valle"), por eso necesita
    Playwright (abrir_navegador) en vez de una petición simple. Cada resultado
    es un '.newcard.result' con: nombre en 'h2.newcard__name', número + extra
    juntos en 'span.newcard__number' (el extra viene en un '<i class="newcard__sign">'
    interno, con formato "serie: 000" para chances o el nombre del signo para
    astros) y fecha completa "YYYY-MM-DD HH:MM:SS" en 'span.newcard__date'.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando SuperGiros para: {nombre_loteria}")

        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        cards = soup.select('#results .newcard.result')

        if not cards:
            mensaje_error = "No se encontraron cards de resultados en SuperGiros"
            log.error(mensaje_error)
            return None, mensaje_error

        for card in cards:
            div_nombre = card.find('h2', class_='newcard__name')
            if not div_nombre:
                continue

            nombre_en_pagina = ' '.join(div_nombre.get_text().split())
            nombre_normalizado = normalizar_texto(nombre_en_pagina)
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            if nombre_mapeado != nombre_loteria:
                continue

            # Fecha completa "2026-07-29 10:00:00": solo nos importa la parte de fecha
            span_fecha = card.find('span', class_='newcard__date')
            fecha_texto = span_fecha.get_text().strip() if span_fecha else ""
            fecha_resultado = fecha_texto.split(" ")[0] if fecha_texto else ""

            if fecha_resultado != fecha_hoy:
                log.info(f"Resultado de {nombre_loteria} en SuperGiros es de {fecha_resultado}, no de hoy ({fecha_hoy})")
                return None, f"Resultado de {nombre_loteria} en SuperGiros no es de la fecha actual"

            span_numero = card.find('span', class_='newcard__number')
            if not span_numero:
                continue

            # El "extra" (quinta/signo) viene en un <i> dentro del mismo span,
            # pegado al número: hay que separarlos antes de limpiar el número.
            i_extra = span_numero.find('i', class_='newcard__sign')
            extra_texto = i_extra.get_text().strip() if i_extra else ""

            numero = span_numero.get_text().strip()
            if extra_texto and numero.endswith(extra_texto):
                numero = numero[:-len(extra_texto)].strip()

            if not numero:
                continue

            # "serie: 000" -> quinta = "0" (quitamos ceros a la izquierda para que
            # coincida con el formato de las demás fuentes); si no dice "serie:"
            # es un signo zodiacal (Astros)
            quinta = ""
            if "serie:" in extra_texto.lower():
                quinta = extra_texto.split(":", 1)[1].strip()
                if quinta.isdigit():
                    quinta = str(int(quinta))
            elif extra_texto:
                quinta = extra_texto.strip()

            log.info(f"Resultado encontrado en SuperGiros | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' con fecha de hoy en SuperGiros"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en SuperGiros: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_perla_todo(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Perla Todo.

    Tabla con filas <td>NOMBRE</td>|<td>dígitos en divs</td>|<td>FECHA</td>.
    Dígitos en divs 'balotera-home' (uno por dígito); quinta/serie en un
    <div> sin clase después de los dígitos.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando Perla Todo para: {nombre_loteria}")

        response, error = realizar_peticion(url, log)
        if error:
            return None, error

        if response.status_code != 200:
            mensaje_error = f"Perla Todo respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        soup = BeautifulSoup(response.text, 'html.parser')
        fecha_hoy = fecha_actual_colombia()

        filas = soup.find_all('tr')

        for fila in filas:
            celdas = fila.find_all('td')

            # Fila válida: mínimo 3 celdas [nombre|dígitos|fecha]
            if len(celdas) < 3:
                continue

            nombre_en_pagina = normalizar_texto(celdas[0].get_text())
            nombre_mapeado = MAPEO_GENERICO.get(nombre_en_pagina)

            if nombre_mapeado != nombre_loteria:
                continue

            fecha_resultado = celdas[2].get_text().strip()
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Perla Todo es de {fecha_resultado}, no de hoy ({fecha_hoy})"
                log.info(mensaje_error)
                return None, mensaje_error

            # Cada div 'balotera-home' trae un dígito, se concatenan para el número
            digitos = celdas[1].find_all('div', class_='balotera-home')
            numero = ''.join([d.get_text().strip() for d in digitos])

            div_quinta = celdas[1].find('div', class_='balotera-home-dem')
            quinta = div_quinta.get_text().strip() if div_quinta else ""

            # Para el Astro la quinta viene en un div sin clase (signo zodiacal)
            if not quinta:
                divs_sin_clase = celdas[1].find_all('div', class_=False)
                for div in divs_sin_clase:
                    texto_div = div.get_text().strip()
                    if texto_div:
                        if "serie:" in texto_div.lower():
                            quinta = texto_div.split(":")[1].strip()
                        else:
                            quinta = texto_div
                        break

            log.info(f"Resultado encontrado en Perla Todo | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en la tabla de Perla Todo"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Perla Todo: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_ganagana(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde GanaGana.

    Tabla de 3 columnas: [0] Sorteo (texto o title del img) | [1] Fecha (<strong>)
    | [2] Resultado (dígitos en <span class="balota">, quinta en "balota1").
    Algunas filas solo tienen imagen, el nombre va en el atributo 'title'.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando GanaGana para: {nombre_loteria}")

        # Cabeceras que simulan ser un navegador real
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*"
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            mensaje_error = f"GanaGana respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        soup = BeautifulSoup(response.text, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        tabla = soup.find('table')

        if not tabla:
            mensaje_error = "No se encontró la tabla de resultados en GanaGana"
            log.error(mensaje_error)
            return None, mensaje_error

        filas = tabla.find_all('tr')

        for fila in filas:
            celdas = fila.find_all('td')

            # Fila válida: 3 celdas [sorteo|fecha|resultado]
            if len(celdas) < 3:
                continue

            # Algunas filas no tienen texto visible, solo imagen con 'title'
            texto_celda = ' '.join(celdas[0].get_text().split())
            img = celdas[0].find('img')
            titulo_img = img.get('title', '').strip() if img else ""
            nombre_en_pagina = texto_celda if texto_celda else titulo_img

            nombre_normalizado = normalizar_texto(nombre_en_pagina)
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            if nombre_mapeado != nombre_loteria:
                continue

            fecha_resultado = celdas[1].get_text().strip()

            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en GanaGana es de {fecha_resultado}, no de hoy ({fecha_hoy})"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros spans 'balota' forman el número, 'balota1' es la quinta
            spans_numero = celdas[2].find_all('span', class_='balota')
            spans_quinta = celdas[2].find_all('span', class_='balota1')

            numero = ''.join([s.get_text().strip() for s in spans_numero])
            quinta = spans_quinta[0].get_text().strip() if spans_quinta else ""

            if not numero:
                mensaje_error = f"Se encontró '{nombre_en_pagina}' en GanaGana pero no se pudieron extraer los dígitos"
                log.info(mensaje_error)
                return None, mensaje_error

            log.info(f"Resultado encontrado en GanaGana | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en la tabla de GanaGana"
        log.info(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.Timeout:
        mensaje_error = f"Timeout al consultar GanaGana: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.ConnectionError:
        mensaje_error = f"Error de conexión al consultar GanaGana: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en GanaGana: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_jer(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde JER.

    3 tablas '.tablaresultados': (1) tradicionales nombre|dígitos|quinta|serie|fecha,
    (2) chances ídem sin serie, (3) Astro con signo zodiacal en <td> en vez de quinta.
    Dígitos en divs 'balotera-home', quinta en div 'balotera-quinta'.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando JER para: {nombre_loteria}")

        # Cabeceras que simulan ser un navegador real
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*"
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            mensaje_error = f"JER respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        soup = BeautifulSoup(response.text, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # JER tiene varias tablas con clase 'tablaresultados', se recorren todas
        tablas = soup.find_all('table', class_='tablaresultados')

        if not tablas:
            mensaje_error = "No se encontraron tablas de resultados en JER"
            log.error(mensaje_error)
            return None, mensaje_error

        for tabla in tablas:
            filas = tabla.find_all('tr')

            for fila in filas:
                celdas = fila.find_all('td')

                # Fila válida: mínimo 4 celdas
                if len(celdas) < 4:
                    continue

                nombre_en_pagina = ' '.join(celdas[0].get_text().split())
                nombre_normalizado = normalizar_texto(nombre_en_pagina)
                nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

                if nombre_mapeado != nombre_loteria:
                    continue

                digitos = celdas[1].find_all('div', class_='balotera-home')
                numero = ''.join([d.get_text().strip() for d in digitos])

                if not numero:
                    mensaje_error = f"Se encontró '{nombre_en_pagina}' en JER pero no se pudieron extraer los dígitos"
                    log.info(mensaje_error)
                    return None, mensaje_error

                # La quinta va en div 'balotera-quinta' (tablas 1-2) o como texto en el <td> (Astro)
                quinta = ""
                div_quinta = celdas[2].find('div', class_='balotera-quinta')
                if div_quinta:
                    quinta = div_quinta.get_text().strip()
                else:
                    texto_quinta = celdas[2].get_text().strip()
                    if texto_quinta and texto_quinta.upper() != "QUINTA" and texto_quinta.upper() != "SIGNO":
                        quinta = texto_quinta

                # La fecha va en la última celda antes del enlace VER MAS (formato YYYY-MM-DD)
                fecha_resultado = ""
                for celda in reversed(celdas):
                    texto = celda.get_text().strip()
                    if re.match(r'\d{4}-\d{2}-\d{2}', texto):
                        fecha_resultado = texto
                        break

                if fecha_resultado != fecha_hoy:
                    mensaje_error = f"Resultado de {nombre_loteria} en JER es de {fecha_resultado}, no de hoy ({fecha_hoy})"
                    log.info(mensaje_error)
                    return None, mensaje_error

                log.info(f"Resultado encontrado en JER | {nombre_loteria}: número={numero} | quinta={quinta}")
                return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en las tablas de JER"
        log.info(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.Timeout:
        mensaje_error = f"Timeout al consultar JER: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.ConnectionError:
        mensaje_error = f"Error de conexión al consultar JER: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en JER: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

# ============================funciones de scraping playwright============================

def _extraer_signo_zodiacal_card(card, div_nombre, div_fecha):
    """
    Busca el signo zodiacal (Astro Sol/Luna) en una card de Chances Colombia
    o loteriasdecolombia: no viene en un círculo 'score-shape-circle' sino
    como texto suelto en algún div/span, por eso se busca aparte.

    Retorna el texto encontrado o "" si no hay nada aprovechable.
    """
    for elemento in card.find_all(['div', 'span']):
        # Solo nodos "hoja", para no capturar contenedores con todo el texto junto
        if elemento.find(['div', 'span']):
            continue
        if elemento in (div_nombre, div_fecha):
            continue
        texto = elemento.get_text().strip()
        if texto and not texto.isdigit():
            return texto
    return ""


def scraping_chances_colombia(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Chances Colombia.

    SPA Vue/PrimeVue (necesita JS). Cards '.p-card-content': nombre en
    div 'text-xl font-bold', fecha en 'text-sm' ('02 Jul 03:26 PM'), dígitos
    en divs 'score-shape-circle' (los primeros 4 son el número, el 5to la quinta).

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando Chances Colombia para: {nombre_loteria}")
        # Chances Colombia necesita JS para mostrar los resultados
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Cada card ('p-card-content') representa una lotería con su resultado
        cards = soup.find_all('div', class_='p-card-content')

        if not cards:
            mensaje_error = "No se encontraron cards de resultados en Chances Colombia"
            log.error(mensaje_error)
            return None, mensaje_error

        for card in cards:

            # Ejemplo: <div class="text-xl font-bold"><div>Dorado Tarde</div></div>
            div_nombre = card.find('div', class_='text-xl')
            if not div_nombre:
                continue

            nombre_en_pagina = ' '.join(div_nombre.get_text().split())
            nombre_normalizado = normalizar_texto(nombre_en_pagina)
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            if nombre_mapeado != nombre_loteria:
                continue

            # Fecha en div 'text-sm', formato '02 Jul 03:26 PM'
            div_fecha = card.find('div', class_='text-sm')
            if not div_fecha:
                continue

            fecha_texto = div_fecha.get_text().strip()

            # Convertimos '02 Jul' a YYYY-MM-DD tomando el año del sistema
            try:
                fecha_resultado = datetime.strptime(
                    fecha_texto.split()[0] + ' ' + fecha_texto.split()[1],
                    "%d %b"
                ).replace(year=datetime.now().year).strftime("%Y-%m-%d")
            except Exception:
                fecha_resultado = ""

            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Chances Colombia es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Cada círculo 'score-shape-circle' trae un dígito dentro de un <span>
            circulos = card.find_all('div', class_=re.compile('score-shape-circle'))
            digitos = [c.find('span').get_text().strip() for c in circulos if c.find('span')]

            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en Chances Colombia para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 dígitos forman el número; el 5to (si existe) es la quinta
            numero = ''.join(digitos[:4])
            quinta = digitos[4] if len(digitos) > 4 else ""

            # Para Astro Sol/Luna el signo no viene en un círculo, sino como texto suelto
            if not quinta:
                quinta = _extraer_signo_zodiacal_card(card, div_nombre, div_fecha)

            log.info(f"Resultado encontrado en Chances Colombia | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en Chances Colombia"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Chances Colombia: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_loterias_colombia(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde loteriasdecolombia.co

    Misma estructura y lógica que Chances Colombia (mismo framework Vue/PrimeVue):
    cards '.p-card-content', dígitos en 'score-shape-circle'.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando loteriasdecolombia para: {nombre_loteria}")

        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        cards = soup.find_all('div', class_='p-card-content')

        if not cards:
            mensaje_error = "No se encontraron cards de resultados en loteriasdecolombia"
            log.error(mensaje_error)
            return None, mensaje_error

        for card in cards:

            div_nombre = card.find('div', class_='text-xl')
            if not div_nombre:
                continue

            nombre_en_pagina = ' '.join(div_nombre.get_text().split())
            nombre_normalizado = normalizar_texto(nombre_en_pagina)
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            if nombre_mapeado != nombre_loteria:
                continue

            div_fecha = card.find('div', class_='text-sm')
            if not div_fecha:
                continue

            fecha_texto = div_fecha.get_text().strip()

            try:
                fecha_resultado = datetime.strptime(
                    fecha_texto.split()[0] + ' ' + fecha_texto.split()[1],
                    "%d %b"
                ).replace(year=datetime.now().year).strftime("%Y-%m-%d")
            except Exception:
                fecha_resultado = ""

            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en loteriasdecolombia es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            circulos = card.find_all('div', class_=re.compile('score-shape-circle'))
            digitos = [c.find('span').get_text().strip() for c in circulos if c.find('span')]

            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en loteriasdecolombia para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 forman el número, el 5to es la quinta si existe
            numero = ''.join(digitos[:4])
            quinta = digitos[4] if len(digitos) > 4 else ""

            # Para Astro Sol/Luna el signo no viene en un círculo, sino como texto suelto
            if not quinta:
                quinta = _extraer_signo_zodiacal_card(card, div_nombre, div_fecha)

            log.info(f"Resultado encontrado en loteriasdecolombia | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en loteriasdecolombia"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en loteriasdecolombia: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_loterias_de_hoy2(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Loterias de Hoy2.

    SPA Next.js (necesita JS). Divs '.resultado-chance': nombre en <h3>,
    fecha en <h4> ('02 julio 2026'), dígitos en <i class='num'>.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando Loterias de Hoy2 para: {nombre_loteria}")

        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        resultados = soup.find_all('div', class_='resultado-chance')

        if not resultados:
            mensaje_error = "No se encontraron resultados en Loterias de Hoy2"
            log.error(mensaje_error)
            return None, mensaje_error

        for resultado in resultados:

            h3 = resultado.find('h3')
            if not h3:
                continue

            nombre_en_pagina = ' '.join(h3.get_text().split())
            nombre_normalizado = normalizar_texto(nombre_en_pagina)
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            if nombre_mapeado != nombre_loteria:
                continue

            # Fecha en <h4>, formato '02 julio 2026'
            h4 = resultado.find('h4')
            if not h4:
                continue

            fecha_texto = h4.get_text().strip()

            try:
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                partes_fecha = fecha_texto.lower().split()
                dia  = partes_fecha[0].zfill(2)
                mes  = meses.get(partes_fecha[1], '00')
                anio = partes_fecha[2]
                fecha_resultado = f"{anio}-{mes}-{dia}"
            except Exception:
                fecha_resultado = ""

            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Loterias de Hoy2 es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Cada <i class='num'> contiene un dígito del número
            digitos_elementos = resultado.find_all('i', class_='num')
            digitos = [d.get_text().strip() for d in digitos_elementos if d.get_text().strip() != '-']

            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en Loterias de Hoy2 para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 dígitos forman el número; el 5to (si existe) es la quinta
            numero = ''.join(digitos[:4])
            quinta = digitos[4] if len(digitos) > 4 else ""

            log.info(f"Resultado encontrado en Loterias de Hoy2 | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en Loterias de Hoy2"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Loterias de Hoy2: {e}"
        log.error(mensaje_error)
        return None, mensaje_error
    
def scraping_ganar_chance(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde GANAR CHANCE.

    La home no asocia nombres con números; cada lotería tiene su propia
    sub-URL /resultado/{slug}. Tabla Fecha|Número|Quinta, la primera fila
    (tras el encabezado) es el resultado más reciente. `url` no se usa,
    se arma la sub-URL con el slug.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando GANAR CHANCE para: {nombre_loteria}")

        # El slug identifica la lotería en la URL, ej: "Dorado Mañana" → "dorado-manana"
        slug = SLUGS_GANAR_CHANCE.get(nombre_loteria)

        if not slug:
            mensaje_error = f"No hay slug definido para '{nombre_loteria}' en GANAR CHANCE"
            log.info(mensaje_error)
            return None, mensaje_error

        url_loteria = f"https://www.ganarchance.com/resultado/{slug}"
        log.info(f"Consultando sub-URL: {url_loteria}")

        html, error = abrir_navegador(url_loteria, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        tabla = soup.find('table')

        if not tabla:
            mensaje_error = f"No se encontró la tabla de resultados en GANAR CHANCE para {nombre_loteria}"
            log.info(mensaje_error)
            return None, mensaje_error

        # Se salta el encabezado (primera fila)
        filas = tabla.find_all('tr')
        for fila in filas[1:]:
            celdas = fila.find_all('td')

            if len(celdas) < 2:
                continue

            # Formato: "Sábado 04 de julio de 2026"
            fecha_texto = celdas[0].get_text().strip()

            try:
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                # partes = ['sábado', '04', 'de', 'julio', 'de', '2026']
                partes = fecha_texto.lower().split()
                dia  = partes[1].zfill(2)
                mes  = meses.get(partes[3], '00')
                anio = partes[5]
                fecha_resultado = f"{anio}-{mes}-{dia}"
            except Exception:
                fecha_resultado = ""

            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en GANAR CHANCE es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            numero = celdas[1].get_text().strip()
            quinta = celdas[2].get_text().strip() if len(celdas) > 2 else ""

            if not re.match(r'^\d{4}$', numero):
                mensaje_error = f"El número encontrado en GANAR CHANCE no es válido: {numero}"
                log.info(mensaje_error)
                return None, mensaje_error

            log.info(f"Resultado encontrado en GANAR CHANCE | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró resultado de hoy para '{nombre_loteria}' en GANAR CHANCE"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en GANAR CHANCE: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_gana(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Gana (boletin.gana.com.co).

    SPA React (necesita JS). Filas: nombre en 1ra <td>, resultado en
    <td class="winner-number"> formato "NUMERO-QUINTA" (ej "0150-6"). No hay
    fecha por fila, la 2da columna siempre es la más reciente.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando Gana para: {nombre_loteria}")

        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Gana tiene varias tablas, se recorren todas buscando la lotería
        tablas = soup.find_all('table')

        if not tablas:
            mensaje_error = "No se encontraron tablas de resultados en Gana"
            log.error(mensaje_error)
            return None, mensaje_error

        for tabla in tablas:
            filas = tabla.find_all('tr')

            # El th con fecha "3 jul" más reciente está en el encabezado
            fecha_resultado = ""
            encabezado = filas[0] if filas else None
            if encabezado:
                ths = encabezado.find_all('th')
                for th in ths:
                    texto_th = th.get_text(separator=' ').strip()
                    match_fecha = re.search(r'(\d{1,2})\s+(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)',
                                           texto_th, re.IGNORECASE)
                    if match_fecha:
                        meses_abr = {
                            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
                            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                            'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
                        }
                        dia = match_fecha.group(1).zfill(2)
                        mes = meses_abr.get(match_fecha.group(2).lower(), '00')
                        anio = datetime.now(pytz.timezone("America/Bogota")).year
                        fecha_resultado = f"{anio}-{mes}-{dia}"
                        break

            if fecha_resultado and fecha_resultado != fecha_hoy:
                log.info(f"Tabla de Gana tiene fecha {fecha_resultado}, no de hoy ({fecha_hoy})")
                continue

            # Se saltan las 2 filas de encabezado
            for fila in filas[2:]:
                celdas = fila.find_all('td')

                if len(celdas) < 2:
                    continue

                nombre_en_pagina = ' '.join(celdas[0].get_text().split())
                nombre_normalizado = normalizar_texto(nombre_en_pagina)
                nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

                if nombre_mapeado != nombre_loteria:
                    continue

                # Formato: "0150-6" (número-quinta)
                td_winner = celdas[1].find('td', class_='winner-number') or celdas[1]
                resultado_crudo = td_winner.find('span')
                if not resultado_crudo:
                    resultado_crudo = celdas[1].find('span')

                if not resultado_crudo:
                    mensaje_error = f"No se encontró el resultado en Gana para {nombre_loteria}"
                    log.info(mensaje_error)
                    return None, mensaje_error

                resultado_texto = resultado_crudo.get_text().strip()
                partes = resultado_texto.split('-')
                numero = partes[0].strip()
                quinta = partes[1].strip() if len(partes) > 1 else ""

                if not re.match(r'^\d{4}$', numero):
                    mensaje_error = f"Número inválido en Gana para {nombre_loteria}: {numero}"
                    log.info(mensaje_error)
                    return None, mensaje_error

                log.info(f"Resultado encontrado en Gana | {nombre_loteria}: número={numero} | quinta={quinta}")
                return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en Gana"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Gana: {e}"
        log.error(mensaje_error)
        return None, mensaje_error
    
def scraping_loterias_de_hoy(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Loterias de Hoy (loteriasdehoy.co).

    Necesita JS (SSL ignorado en Playwright). Divs '.chances_hoy': nombre en
    <h3><a title=...>, fecha en div.fecha_resultado ('4 Julio 2026'), dígitos
    en span.chance1, quinta en span.premio5.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando Loterias de Hoy para: {nombre_loteria}")

        # Esta página tiene SSL inválido, se ignora con --ignore-certificate-errors
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        resultados = soup.find_all('div', class_='chances_hoy')

        if not resultados:
            mensaje_error = "No se encontraron resultados en Loterias de Hoy"
            log.error(mensaje_error)
            return None, mensaje_error

        for resultado in resultados:

            # Ejemplo: <h3><a href="/dorado-manana" title="Dorado Mañana">
            h3 = resultado.find('h3')
            if not h3:
                continue

            enlace = h3.find('a')
            if not enlace:
                continue

            nombre_en_pagina = enlace.get('title', '').strip()
            if not nombre_en_pagina:
                nombre_en_pagina = enlace.get_text().strip()

            nombre_normalizado = normalizar_texto(nombre_en_pagina)
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            if nombre_mapeado != nombre_loteria:
                continue

            div_fecha = resultado.find('div', class_='fecha_resultado')
            if not div_fecha:
                continue

            fecha_texto = div_fecha.get_text().strip()

            try:
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                partes = fecha_texto.lower().split()
                dia  = partes[0].zfill(2)
                mes  = meses.get(partes[1], '00')
                anio = partes[2]
                fecha_resultado = f"{anio}-{mes}-{dia}"
            except Exception:
                fecha_resultado = ""

            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Loterias de Hoy es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            spans_numero = resultado.find_all('span', class_='chance1')
            digitos = [s.get_text().strip() for s in spans_numero]

            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en Loterias de Hoy para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            numero = ''.join(digitos[:4])

            span_quinta = resultado.find('span', class_='premio5')
            quinta = span_quinta.get_text().strip() if span_quinta else ""

            log.info(f"Resultado encontrado en Loterias de Hoy | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en Loterias de Hoy"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Loterias de Hoy: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_loti(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde loti.com.co

    Necesita JS. Divs '.result-single-page'; el nombre se identifica por el
    código en la URL de la imagen (ej: 1ANT.png → Antioqueñita Uno). Dígitos
    separados "4 0 5 6 - 6" (4 primeros = número, último = quinta), fecha DD/MM/YYYY.

    Retorna (dict, None) con numero/quinta si encontró, o (None, str) con el error.
    """
    try:
        log.info(f"Consultando loti para: {nombre_loteria}")

        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        paginas = soup.find_all('div', class_='result-single-page')

        if not paginas:
            mensaje_error = "No se encontraron resultados en loti"
            log.error(mensaje_error)
            return None, mensaje_error

        for pagina in paginas:

            # El nombre se identifica por el código en la URL de la imagen
            img = pagina.find('img', class_='d-block')
            if not img:
                continue

            src = img.get('src', '')
            codigo = src.split('/')[-1].replace('.png', '')
            nombre_en_loti = CODIGOS_LOTI.get(codigo)

            if nombre_en_loti != nombre_loteria:
                continue

            texto_pagina = pagina.get_text(separator=' ')

            # Normalizamos para quitar tildes (NÚMERO → NUMERO)
            texto_normalizado = normalizar_texto(texto_pagina)

            match_fecha = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto_pagina)
            if match_fecha:
                fecha_resultado = f"{match_fecha.group(3)}-{match_fecha.group(2)}-{match_fecha.group(1)}"
            else:
                fecha_resultado = ""

            if fecha_resultado and fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en loti es de {fecha_resultado}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Dígitos separados por espacios entre NUMERO y SERIE, ej: "4 0 5 6 - 6"
            match_bloque = re.search(
                r'NUMERO\s+([\d\s\-]+?)\s+SERIE',
                texto_normalizado,
                re.IGNORECASE
            )

            if not match_bloque:
                # Chances sin SERIE: se busca entre NUMERO y FECHA
                match_bloque = re.search(
                    r'NUMERO\s+([\d\s\-]+?)\s+FECHA',
                    texto_normalizado,
                    re.IGNORECASE
                )

            if not match_bloque:
                mensaje_error = f"No se pudo extraer el número en loti para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            bloque = match_bloque.group(1).strip()
            partes = bloque.split('-')
            numero = partes[0].replace(' ', '').strip()
            quinta = partes[1].replace(' ', '').strip() if len(partes) > 1 else ""

            if not re.match(r'^\d{4}$', numero):
                mensaje_error = f"Número inválido en loti para {nombre_loteria}: {numero}"
                log.info(mensaje_error)
                return None, mensaje_error

            log.info(f"Resultado encontrado en loti | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        mensaje_error = f"No se encontró '{nombre_loteria}' en loti"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en loti: {e}"
        log.error(mensaje_error)
        return None, mensaje_error