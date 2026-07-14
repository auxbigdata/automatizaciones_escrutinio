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

def scraping_acertemos(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Acertemos.

    Cómo funciona esta página:
    - Los resultados vienen en tablas HTML con 3 columnas:
      [0] Fecha (formato dd/mm/yyyy)
      [1] Nombre del sorteo
      [2] Resultado (número + quinta entre paréntesis si aplica)
    - Nota: el meta description está desactualizado, los datos
      reales están en las tablas HTML de la página

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de Acertemos
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "1234", "quinta": "Géminis"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando Acertemos para: {nombre_loteria}")

        response, error = realizar_peticion(url, log)
        if error:
            return None, error

        if response.status_code != 200:
            mensaje_error = f"Acertemos respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Los resultados están en tablas HTML, no en el meta description
        tablas = soup.find_all('table')

        if not tablas:
            mensaje_error = "No se encontraron tablas de resultados en Acertemos"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada tabla
        for tabla in tablas:
            filas = tabla.find_all('tr')

            for fila in filas:
                celdas = fila.find_all('td')

                # Las filas válidas tienen al menos 3 columnas:
                # [0] Fecha | [1] Nombre | [2] Resultado
                if len(celdas) < 3:
                    continue

                # Extraemos la fecha de la primera celda
                # Acertemos usa formato dd/mm/yyyy
                fecha_str = celdas[0].get_text().strip()
                try:
                    # Convertimos dd/mm/yyyy → YYYY-MM-DD para comparar con fecha_hoy
                    fecha_resultado = datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    # Si no tiene formato de fecha válido ignoramos esta fila
                    continue

                # Verificamos que sea resultado de hoy
                if fecha_resultado != fecha_hoy:
                    continue

                # Extraemos el nombre del sorteo de la segunda celda
                nombre_en_pagina = ' '.join(celdas[1].get_text().split())
                nombre_normalizado = normalizar_texto(nombre_en_pagina)

                # Buscamos en el mapeo genérico si corresponde a la lotería buscada
                nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

                # Si no corresponde pasamos a la siguiente fila
                if nombre_mapeado != nombre_loteria:
                    continue

                # Extraemos el resultado de la tercera celda
                # Puede venir como "1234" o "1234 (Géminis)"
                resultado_crudo = celdas[2].get_text().strip()

                # Separamos por el guion
                partes = resultado_crudo.split('-')

                # Buscamos el número de 4 dígitos
                match_numero = re.search(r'\b\d{4}\b', partes[0])
                if not match_numero:
                    continue

                numero = match_numero.group()

                # Buscamos si hay quinta entre paréntesis
                # Ejemplo: "8463 (Géminis)"
                quinta = partes[1].strip() if len(partes) > 1 else ""

                log.info(f"Resultado encontrado en Acertemos | {nombre_loteria}: número={numero} | quinta={quinta}")
                return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todas las tablas y no encontró la lotería de hoy
        mensaje_error = f"No se encontró '{nombre_loteria}' con fecha de hoy en Acertemos"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en Acertemos: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_perla_todo(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Perla Todo.

    Cómo funciona esta página:
    - Los resultados vienen en una tabla HTML con filas <tr>
    - Cada fila tiene: <td>NOMBRE</td> | <td>dígitos en divs</td> | <td>FECHA</td>
    - Los dígitos vienen en divs con clase 'balotera-home', uno por dígito
    - La quinta/serie viene en un <div> sin clase después de los dígitos

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de Perla Todo
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "1193", "quinta": "cancer"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
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

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        fecha_hoy = fecha_actual_colombia()

        # Buscamos todas las filas de la tabla de resultados
        filas = soup.find_all('tr')

        for fila in filas:
            celdas = fila.find_all('td')

            # Las filas válidas tienen al menos 3 celdas:
            # [0] nombre | [1] dígitos | [2] fecha
            if len(celdas) < 3:
                continue

            # Normalizamos el nombre de la lotería en esta fila
            nombre_en_pagina = normalizar_texto(celdas[0].get_text())

            # Buscamos en el mapeo genérico si este nombre
            # corresponde a la lotería que buscamos
            nombre_mapeado = MAPEO_GENERICO.get(nombre_en_pagina)

            # Si no corresponde a la lotería que buscamos pasamos a la siguiente fila
            if nombre_mapeado != nombre_loteria:
                continue

            # Verificamos que el resultado sea de hoy
            fecha_resultado = celdas[2].get_text().strip()
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Perla Todo es de {fecha_resultado}, no de hoy ({fecha_hoy})"
                log.info(mensaje_error)
                return None, mensaje_error

            # Extraemos los dígitos del número desde los divs con clase 'balotera-home'
            # Cada div contiene UN dígito → los concatenamos para formar el número completo
            digitos = celdas[1].find_all('div', class_='balotera-home')
            numero = ''.join([d.get_text().strip() for d in digitos])

            # La quinta viene en el div con clase 'balotera-home-dem'
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

        # Si recorrió todas las filas y no encontró la lotería
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

    Cómo funciona esta página:
    - Los resultados vienen en una tabla HTML con 3 columnas:
      [0] Sorteo (nombre en texto o en atributo title del img)
      [1] Fecha (dentro de un <strong>)
      [2] Resultado (dígitos en <span class="balota"> y quinta en <span class="balota1">)
    - Algunas filas solo tienen imagen sin texto visible,
      en ese caso el nombre viene en el atributo 'title' del <img>
    - El último span con clase 'balota1' es la quinta/serie
    - Los demás spans con clase 'balota' forman el número principal

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de GanaGana
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "4268", "quinta": "6"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando GanaGana para: {nombre_loteria}")

        # Cabeceras que simulan ser un navegador real
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*"
        }

        # Hacemos la petición HTTP a la página
        response = requests.get(url, headers=headers, timeout=15)

        # Si la página no respondió bien no podemos continuar
        if response.status_code != 200:
            mensaje_error = f"GanaGana respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Buscamos la tabla de resultados
        tabla = soup.find('table')

        # Si no hay tabla no podemos extraer nada
        if not tabla:
            mensaje_error = "No se encontró la tabla de resultados en GanaGana"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos todas las filas de la tabla
        filas = tabla.find_all('tr')

        for fila in filas:
            celdas = fila.find_all('td')

            # Las filas válidas tienen 3 celdas: sorteo | fecha | resultado
            if len(celdas) < 3:
                continue

            # Extraemos el nombre del sorteo desde la primera celda
            # Algunas filas tienen el nombre en texto visible
            # Otras solo tienen imagen, en ese caso tomamos el atributo 'title' del img
            texto_celda = ' '.join(celdas[0].get_text().split())
            img = celdas[0].find('img')
            titulo_img = img.get('title', '').strip() if img else ""

            # Usamos el texto si existe, si no el título de la imagen
            nombre_en_pagina = texto_celda if texto_celda else titulo_img

            # Normalizamos para comparar sin tildes ni mayúsculas
            nombre_normalizado = normalizar_texto(nombre_en_pagina)

            # Buscamos en el mapeo genérico si corresponde a la lotería que buscamos
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            # Si no corresponde pasamos a la siguiente fila
            if nombre_mapeado != nombre_loteria:
                continue

            # Extraemos la fecha de la segunda celda
            fecha_resultado = celdas[1].get_text().strip()

            # Verificamos que sea resultado de hoy
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en GanaGana es de {fecha_resultado}, no de hoy ({fecha_hoy})"
                log.info(mensaje_error)
                return None, mensaje_error

            # Extraemos los dígitos del número desde los spans con clase 'balota'
            # Los primeros 4 forman el número principal
            spans_numero = celdas[2].find_all('span', class_='balota')

            # La quinta viene en el span con clase 'balota1'
            spans_quinta = celdas[2].find_all('span', class_='balota1')

            # Concatenamos los dígitos del número
            numero = ''.join([s.get_text().strip() for s in spans_numero])

            # Extraemos la quinta si existe
            quinta = spans_quinta[0].get_text().strip() if spans_quinta else ""

            if not numero:
                mensaje_error = f"Se encontró '{nombre_en_pagina}' en GanaGana pero no se pudieron extraer los dígitos"
                log.info(mensaje_error)
                return None, mensaje_error

            log.info(f"Resultado encontrado en GanaGana | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todas las filas y no encontró la lotería
        mensaje_error = f"No se encontró '{nombre_loteria}' en la tabla de GanaGana"
        log.info(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.Timeout:
        # La página tardó demasiado en responder
        mensaje_error = f"Timeout al consultar GanaGana: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.ConnectionError:
        # No se pudo establecer conexión con la página
        mensaje_error = f"Error de conexión al consultar GanaGana: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        # Cualquier otro error inesperado (parseo HTML, datos inesperados, etc.)
        mensaje_error = f"Error inesperado en GanaGana: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

def scraping_jer(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde JER.

    Cómo funciona esta página:
    - Tiene 3 tablas con clase 'tablaresultados':
      Tabla 1: Loterías tradicionales → nombre | dígitos | quinta (balotera-quinta) | serie | fecha
      Tabla 2: Chances → nombre | dígitos | quinta (balotera-quinta) | fecha
      Tabla 3: Astro Sol/Luna → nombre | dígitos | signo zodiacal en <td> | fecha
    - Los dígitos del número vienen en divs con clase 'balotera-home'
    - La quinta viene en un div con clase 'balotera-quinta'
    - Para el Astro el signo zodiacal viene directamente en un <td>

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de JER
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "4268", "quinta": "8"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando JER para: {nombre_loteria}")

        # Cabeceras que simulan ser un navegador real
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*"
        }

        # Hacemos la petición HTTP a la página
        response = requests.get(url, headers=headers, timeout=15)

        # Si la página no respondió bien no podemos continuar
        if response.status_code != 200:
            mensaje_error = f"JER respondió con status {response.status_code}"
            log.error(mensaje_error)
            return None, mensaje_error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # JER tiene varias tablas con clase 'tablaresultados'
        # Recorremos todas para buscar la lotería en cualquiera de ellas
        tablas = soup.find_all('table', class_='tablaresultados')

        if not tablas:
            mensaje_error = "No se encontraron tablas de resultados en JER"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada tabla
        for tabla in tablas:
            filas = tabla.find_all('tr')

            for fila in filas:
                celdas = fila.find_all('td')

                # Las filas válidas tienen al menos 4 celdas
                if len(celdas) < 4:
                    continue

                # El nombre de la lotería viene en la primera celda como texto
                nombre_en_pagina = ' '.join(celdas[0].get_text().split())

                # Normalizamos para comparar sin tildes ni mayúsculas
                nombre_normalizado = normalizar_texto(nombre_en_pagina)

                # Buscamos en el mapeo genérico si corresponde a la lotería buscada
                nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

                # Si no corresponde pasamos a la siguiente fila
                if nombre_mapeado != nombre_loteria:
                    continue

                # Extraemos los dígitos del número desde los divs con clase 'balotera-home'
                digitos = celdas[1].find_all('div', class_='balotera-home')
                numero = ''.join([d.get_text().strip() for d in digitos])

                if not numero:
                    mensaje_error = f"Se encontró '{nombre_en_pagina}' en JER pero no se pudieron extraer los dígitos"
                    log.info(mensaje_error)
                    return None, mensaje_error

                # La quinta puede venir de dos formas según la tabla:
                # Tabla 1 y 2 (loterías y chances): div con clase 'balotera-quinta'
                # Tabla 3 (Astro): texto directo en el <td>
                quinta = ""
                div_quinta = celdas[2].find('div', class_='balotera-quinta')
                if div_quinta:
                    # Para loterías y chances la quinta viene en balotera-quinta
                    quinta = div_quinta.get_text().strip()
                else:
                    # Para el Astro el signo viene como texto en el <td>
                    texto_quinta = celdas[2].get_text().strip()
                    if texto_quinta and texto_quinta.upper() != "QUINTA" and texto_quinta.upper() != "SIGNO":
                        quinta = texto_quinta

                # La fecha viene en la última celda antes del enlace VER MAS
                # En tabla 1 es índice 4, en tabla 2 y 3 es índice 3
                fecha_resultado = ""
                for celda in reversed(celdas):
                    texto = celda.get_text().strip()
                    # Buscamos el formato YYYY-MM-DD
                    if re.match(r'\d{4}-\d{2}-\d{2}', texto):
                        fecha_resultado = texto
                        break

                # Verificamos que sea resultado de hoy
                if fecha_resultado != fecha_hoy:
                    mensaje_error = f"Resultado de {nombre_loteria} en JER es de {fecha_resultado}, no de hoy ({fecha_hoy})"
                    log.info(mensaje_error)
                    return None, mensaje_error

                log.info(f"Resultado encontrado en JER | {nombre_loteria}: número={numero} | quinta={quinta}")
                return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todas las tablas y filas sin encontrar la lotería
        mensaje_error = f"No se encontró '{nombre_loteria}' en las tablas de JER"
        log.info(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.Timeout:
        # La página tardó demasiado en responder
        mensaje_error = f"Timeout al consultar JER: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except requests.exceptions.ConnectionError:
        # No se pudo establecer conexión con la página
        mensaje_error = f"Error de conexión al consultar JER: {url}"
        log.error(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        # Cualquier otro error inesperado
        mensaje_error = f"Error inesperado en JER: {e}"
        log.error(mensaje_error)
        return None, mensaje_error

# ============================funciones de scraping playwright============================

def scraping_chances_colombia(nombre_loteria: str, url: str, log: object):
    """
    Extrae el resultado de una lotería desde Chances Colombia.

    Cómo funciona esta página:
    - Es una SPA Vue/PrimeVue que necesita JavaScript para cargar
    - Los resultados vienen en cards con clase 'p-card-content'
    - Cada card tiene:
      [nombre]  en div class='text-xl font-bold'
      [fecha]   en div class='text-sm' formato '02 Jul 03:26 PM'
      [dígitos] en divs class='score-shape-circle', los primeros 4 son el número
      [quinta]  el 5to círculo si existe

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de Chances Colombia
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "8742", "quinta": "3"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando Chances Colombia para: {nombre_loteria}")
        # Abrimos el navegador y obtenemos el HTML completamente renderizado
        # Chances Colombia necesita JS para mostrar los resultados
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup para navegar su estructura
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Los resultados están dentro de divs con clase 'p-card-content'
        # Cada div es una card que representa una lotería con su resultado
        cards = soup.find_all('div', class_='p-card-content')

        # Si no hay cards la página no cargó bien o cambió su estructura
        if not cards:
            mensaje_error = "No se encontraron cards de resultados en Chances Colombia"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada card buscando la lotería que nos interesa
        for card in cards:

            # El nombre de la lotería viene en un div con clase 'text-xl font-bold'
            # Ejemplo: <div class="text-xl font-bold"><div>Dorado Tarde</div></div>
            div_nombre = card.find('div', class_='text-xl')
            if not div_nombre:
                # Esta card no tiene nombre, la ignoramos
                continue

            # Limpiamos el texto del nombre quitando espacios extra
            nombre_en_pagina = ' '.join(div_nombre.get_text().split())

            # Normalizamos para comparar sin tildes ni mayúsculas
            nombre_normalizado = normalizar_texto(nombre_en_pagina)

            # Buscamos en el mapeo genérico si corresponde a la lotería buscada
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            # Si no corresponde a la lotería que buscamos pasamos a la siguiente card
            if nombre_mapeado != nombre_loteria:
                continue

            # La fecha viene en un div con clase 'text-sm'
            # Formato: '02 Jul 03:26 PM'
            div_fecha = card.find('div', class_='text-sm')
            if not div_fecha:
                continue

            fecha_texto = div_fecha.get_text().strip()

            # Convertimos '02 Jul' al formato YYYY-MM-DD para comparar con fecha_hoy
            # Tomamos solo el día y mes, el año lo tomamos del sistema
            try:
                fecha_resultado = datetime.strptime(
                    fecha_texto.split()[0] + ' ' + fecha_texto.split()[1],
                    "%d %b"
                ).replace(year=datetime.now().year).strftime("%Y-%m-%d")
            except Exception:
                # Si no pudimos parsear la fecha ignoramos esta card
                fecha_resultado = ""

            # Verificamos que el resultado sea de hoy
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Chances Colombia es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los dígitos del número vienen en divs con clase 'score-shape-circle'
            # Cada div contiene un círculo con un dígito dentro de un <span>
            circulos = card.find_all('div', class_=re.compile('score-shape-circle'))

            # Extraemos el texto de cada círculo (cada dígito)
            digitos = [c.find('span').get_text().strip() for c in circulos if c.find('span')]

            # Necesitamos mínimo 4 dígitos para formar el número
            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en Chances Colombia para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 dígitos forman el número ganador
            numero = ''.join(digitos[:4])

            # El 5to dígito es la quinta si existe
            # Si solo hay 4 círculos, la lotería no maneja quinta
            quinta = digitos[4] if len(digitos) > 4 else ""

            log.info(f"Resultado encontrado en Chances Colombia | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todas las cards sin encontrar la lotería
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

    Cómo funciona esta página:
    - Misma estructura exacta que Chances Colombia (mismo framework Vue/PrimeVue)
    - Cards con clase 'p-card-content', dígitos en 'score-shape-circle'
    - La lógica de extracción es idéntica

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de loteriasdecolombia
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "8742", "quinta": "3"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando loteriasdecolombia para: {nombre_loteria}")

        # Abrimos el navegador y obtenemos el HTML completamente renderizado
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Misma estructura que Chances Colombia — cards con clase 'p-card-content'
        cards = soup.find_all('div', class_='p-card-content')

        if not cards:
            mensaje_error = "No se encontraron cards de resultados en loteriasdecolombia"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada card buscando la lotería que nos interesa
        for card in cards:

            # El nombre viene en div con clase 'text-xl font-bold'
            div_nombre = card.find('div', class_='text-xl')
            if not div_nombre:
                continue

            # Limpiamos y normalizamos el nombre
            nombre_en_pagina = ' '.join(div_nombre.get_text().split())
            nombre_normalizado = normalizar_texto(nombre_en_pagina)

            # Buscamos en el mapeo genérico si corresponde a la lotería buscada
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            # Si no corresponde pasamos a la siguiente card
            if nombre_mapeado != nombre_loteria:
                continue

            # Extraemos la fecha desde div class='text-sm'
            div_fecha = card.find('div', class_='text-sm')
            if not div_fecha:
                continue

            fecha_texto = div_fecha.get_text().strip()

            # Convertimos '02 Jul' al formato YYYY-MM-DD
            try:
                fecha_resultado = datetime.strptime(
                    fecha_texto.split()[0] + ' ' + fecha_texto.split()[1],
                    "%d %b"
                ).replace(year=datetime.now().year).strftime("%Y-%m-%d")
            except Exception:
                fecha_resultado = ""

            # Verificamos que sea resultado de hoy
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en loteriasdecolombia es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Extraemos los dígitos desde divs con clase 'score-shape-circle'
            circulos = card.find_all('div', class_=re.compile('score-shape-circle'))

            # Cada círculo tiene un dígito dentro de un <span>
            digitos = [c.find('span').get_text().strip() for c in circulos if c.find('span')]

            # Necesitamos mínimo 4 dígitos
            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en loteriasdecolombia para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 forman el número, el 5to es la quinta si existe
            numero = ''.join(digitos[:4])
            quinta = digitos[4] if len(digitos) > 4 else ""

            log.info(f"Resultado encontrado en loteriasdecolombia | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si no encontró la lotería en ninguna card
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

    Cómo funciona esta página:
    - Es una SPA Next.js que necesita JavaScript para cargar
    - Los resultados vienen en divs con clase 'resultado-chance'
    - Cada div tiene:
      [nombre] en <h3>
      [fecha]  en <h4> formato '02 julio 2026'
      [dígitos] en <span class='icon-circle--results num-chance'><i class='num'>

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de Loterias de Hoy2
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "8742", "quinta": "3"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando Loterias de Hoy2 para: {nombre_loteria}")

        # Abrimos el navegador y obtenemos el HTML completamente renderizado
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Los resultados están en divs con clase 'resultado-chance'
        # Cada div representa una lotería con su resultado
        resultados = soup.find_all('div', class_='resultado-chance')

        if not resultados:
            mensaje_error = "No se encontraron resultados en Loterias de Hoy2"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada div de resultado
        for resultado in resultados:

            # El nombre viene en el tag <h3>
            h3 = resultado.find('h3')
            if not h3:
                continue

            # Limpiamos y normalizamos el nombre
            nombre_en_pagina = ' '.join(h3.get_text().split())
            nombre_normalizado = normalizar_texto(nombre_en_pagina)

            # Buscamos en el mapeo genérico si corresponde a la lotería buscada
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            # Si no corresponde pasamos al siguiente div
            if nombre_mapeado != nombre_loteria:
                continue

            # La fecha viene en el tag <h4>
            # Formato: '02 julio 2026'
            h4 = resultado.find('h4')
            if not h4:
                continue

            fecha_texto = h4.get_text().strip()

            # Convertimos '02 julio 2026' al formato YYYY-MM-DD
            try:
                # Meses en español que usa la página
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                partes_fecha = fecha_texto.lower().split()
                # partes_fecha = ['02', 'julio', '2026']
                dia  = partes_fecha[0].zfill(2)
                mes  = meses.get(partes_fecha[1], '00')
                anio = partes_fecha[2]
                fecha_resultado = f"{anio}-{mes}-{dia}"
            except Exception:
                fecha_resultado = ""

            # Verificamos que sea resultado de hoy
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Loterias de Hoy2 es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los dígitos vienen en <i class='num'> dentro de spans
            # Cada <i> contiene un dígito del número
            digitos_elementos = resultado.find_all('i', class_='num')
            digitos = [d.get_text().strip() for d in digitos_elementos if d.get_text().strip() != '-']

            # Necesitamos mínimo 4 dígitos para formar el número
            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en Loterias de Hoy2 para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 dígitos forman el número ganador
            numero = ''.join(digitos[:4])

            # El 5to dígito es la quinta si existe
            quinta = digitos[4] if len(digitos) > 4 else ""

            log.info(f"Resultado encontrado en Loterias de Hoy2 | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todos los divs sin encontrar la lotería
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

    Cómo funciona esta página:
    - La página principal no tiene los nombres junto a los números
    - Cada lotería tiene su propia sub-URL: /resultado/{slug}
    - El resultado está en una tabla HTML con columnas: Fecha | Número | Quinta
    - La primera fila de la tabla (después del encabezado) es el resultado más reciente

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL base de GANAR CHANCE (no se usa, se construye la sub-URL)
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "1412", "quinta": "6"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando GANAR CHANCE para: {nombre_loteria}")

        # Buscamos el slug correspondiente a esta lotería en el diccionario
        # El slug es la parte de la URL que identifica cada lotería
        # Ejemplo: "Dorado Mañana" → "dorado-manana"
        slug = SLUGS_GANAR_CHANCE.get(nombre_loteria)

        # Si no está en el diccionario esta lotería no tiene página en GANAR CHANCE
        if not slug:
            mensaje_error = f"No hay slug definido para '{nombre_loteria}' en GANAR CHANCE"
            log.info(mensaje_error)
            return None, mensaje_error

        # Construimos la URL específica de esta lotería
        # Ejemplo: https://www.ganarchance.com/resultado/dorado-manana
        url_loteria = f"https://www.ganarchance.com/resultado/{slug}"
        log.info(f"Consultando sub-URL: {url_loteria}")

        # Abrimos el navegador y obtenemos el HTML completamente renderizado
        html, error = abrir_navegador(url_loteria, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # El resultado está en una tabla HTML
        # Columnas: Fecha | Número | Quinta
        # La primera fila (después del encabezado) es el resultado más reciente
        tabla = soup.find('table')

        if not tabla:
            mensaje_error = f"No se encontró la tabla de resultados en GANAR CHANCE para {nombre_loteria}"
            log.info(mensaje_error)
            return None, mensaje_error

        # Recorremos las filas saltando el encabezado (primera fila)
        filas = tabla.find_all('tr')
        for fila in filas[1:]:
            celdas = fila.find_all('td')

            # La fila válida tiene al menos 2 celdas: Fecha | Número
            if len(celdas) < 2:
                continue

            # Extraemos la fecha de la primera celda
            # Formato: "Sábado 04 de julio de 2026"
            fecha_texto = celdas[0].get_text().strip()

            # Convertimos "Sábado 04 de julio de 2026" a YYYY-MM-DD
            try:
                # Diccionario para convertir mes en español a número
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                # Dividimos el texto en partes: ['sábado', '04', 'de', 'julio', 'de', '2026']
                partes = fecha_texto.lower().split()
                dia  = partes[1].zfill(2)   # '04'
                mes  = meses.get(partes[3], '00')  # '07'
                anio = partes[5]             # '2026'
                fecha_resultado = f"{anio}-{mes}-{dia}"
            except Exception:
                # Si no pudimos parsear la fecha ignoramos esta fila
                fecha_resultado = ""

            # Verificamos que sea resultado de hoy
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en GANAR CHANCE es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Extraemos el número de la segunda celda
            numero = celdas[1].get_text().strip()

            # Extraemos la quinta de la tercera celda si existe
            quinta = celdas[2].get_text().strip() if len(celdas) > 2 else ""

            # Verificamos que el número tenga 4 dígitos
            if not re.match(r'^\d{4}$', numero):
                mensaje_error = f"El número encontrado en GANAR CHANCE no es válido: {numero}"
                log.info(mensaje_error)
                return None, mensaje_error

            log.info(f"Resultado encontrado en GANAR CHANCE | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todas las filas y no encontró resultado de hoy
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

    Cómo funciona esta página:
    - Es una SPA React que necesita JavaScript para cargar
    - Los resultados vienen en tablas HTML
    - Cada fila tiene: nombre en primera <td> | resultado en <td class="winner-number">
    - El resultado más reciente siempre está en la columna "winner-number"
    - El formato del resultado es "NUMERO-QUINTA" ejemplo: "0150-6"
    - No hay fecha por fila, la segunda columna siempre es el más reciente

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de Gana
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "0150", "quinta": "6"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando Gana para: {nombre_loteria}")

        # Gana es una SPA React que necesita JS para mostrar los resultados
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Gana tiene varias tablas — recorremos todas buscando la lotería
        tablas = soup.find_all('table')

        if not tablas:
            mensaje_error = "No se encontraron tablas de resultados en Gana"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada tabla
        for tabla in tablas:
            filas = tabla.find_all('tr')

            # Extraemos la fecha del encabezado de la tabla
            # El encabezado tiene el día más reciente en la primera columna de fechas tomamos el día y mes
            fecha_resultado = ""
            encabezado = filas[0] if filas else None
            if encabezado:
                # Buscamos los th con fechas — el primero después del nombre es el más reciente
                ths = encabezado.find_all('th')
                for th in ths:
                    texto_th = th.get_text(separator=' ').strip()
                    # Buscamos el formato "3 jul" o "4 jul"
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

            # Verificamos que la fecha del encabezado sea de hoy
            if fecha_resultado and fecha_resultado != fecha_hoy:
                log.info(f"Tabla de Gana tiene fecha {fecha_resultado}, no de hoy ({fecha_hoy})")
                continue

            # Recorremos las filas de datos (saltamos el encabezado)
            for fila in filas[2:]:
                celdas = fila.find_all('td')

                # Las filas válidas tienen al menos 2 celdas
                if len(celdas) < 2:
                    continue

                # El nombre viene en la primera celda
                nombre_en_pagina = ' '.join(celdas[0].get_text().split())
                nombre_normalizado = normalizar_texto(nombre_en_pagina)

                # Buscamos en el mapeo genérico si corresponde a la lotería buscada
                nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

                # Si no corresponde pasamos a la siguiente fila
                if nombre_mapeado != nombre_loteria:
                    continue

                # El resultado más reciente está en la celda con clase 'winner-number'
                # Formato: "0150-6" (número-quinta)
                td_winner = celdas[1].find('td', class_='winner-number') or celdas[1]
                resultado_crudo = td_winner.find('span')
                if not resultado_crudo:
                    # Buscamos el span directamente en la celda
                    resultado_crudo = celdas[1].find('span')

                if not resultado_crudo:
                    mensaje_error = f"No se encontró el resultado en Gana para {nombre_loteria}"
                    log.info(mensaje_error)
                    return None, mensaje_error

                # Separamos número y quinta por el guion
                resultado_texto = resultado_crudo.get_text().strip()
                partes = resultado_texto.split('-')

                # El número siempre es la primera parte
                numero = partes[0].strip()

                # La quinta es la segunda parte si existe
                quinta = partes[1].strip() if len(partes) > 1 else ""

                # Verificamos que el número tenga 4 dígitos
                if not re.match(r'^\d{4}$', numero):
                    mensaje_error = f"Número inválido en Gana para {nombre_loteria}: {numero}"
                    log.info(mensaje_error)
                    return None, mensaje_error

                log.info(f"Resultado encontrado en Gana | {nombre_loteria}: número={numero} | quinta={quinta}")
                return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todas las tablas sin encontrar la lotería
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

    Cómo funciona esta página:
    - Necesita JavaScript para cargar (SSL ignorado en Playwright)
    - Los resultados vienen en divs con clase 'chances_hoy'
    - Cada div tiene:
      [nombre]  en <h3><a title="Nombre Lotería">
      [fecha]   en div.fecha_resultado formato '4 Julio 2026'
      [dígitos] en span.redondoc.chance1 — los 4 primeros son el número
      [quinta]  en span.redondoc.premio5

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de Loterias de Hoy
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "0150", "quinta": "6"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando Loterias de Hoy para: {nombre_loteria}")

        # Abrimos el navegador y obtenemos el HTML completamente renderizado
        # Esta página tiene SSL inválido, se ignora con --ignore-certificate-errors
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Los resultados están en divs con clase 'chances_hoy'
        # Cada div representa una lotería con su resultado
        resultados = soup.find_all('div', class_='chances_hoy')

        if not resultados:
            mensaje_error = "No se encontraron resultados en Loterias de Hoy"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada div buscando la lotería que nos interesa
        for resultado in resultados:

            # El nombre viene en el atributo 'title' del tag <a> dentro del <h3>
            # Ejemplo: <h3><a href="/dorado-manana" title="Dorado Mañana">
            h3 = resultado.find('h3')
            if not h3:
                continue

            # Buscamos el enlace dentro del h3 para obtener el title
            enlace = h3.find('a')
            if not enlace:
                continue

            # Tomamos el title del enlace que tiene el nombre completo
            nombre_en_pagina = enlace.get('title', '').strip()
            if not nombre_en_pagina:
                # Si no hay title usamos el texto del enlace
                nombre_en_pagina = enlace.get_text().strip()

            # Normalizamos para comparar sin tildes ni mayúsculas
            nombre_normalizado = normalizar_texto(nombre_en_pagina)

            # Buscamos en el mapeo genérico si corresponde a la lotería buscada
            nombre_mapeado = MAPEO_GENERICO.get(nombre_normalizado)

            # Si no corresponde pasamos al siguiente div
            if nombre_mapeado != nombre_loteria:
                continue

            # La fecha viene en div.fecha_resultado
            # Formato: "4 Julio 2026"
            div_fecha = resultado.find('div', class_='fecha_resultado')
            if not div_fecha:
                continue

            fecha_texto = div_fecha.get_text().strip()

            # Convertimos "4 Julio 2026" a YYYY-MM-DD
            try:
                meses = {
                    'enero': '01', 'febrero': '02', 'marzo': '03',
                    'abril': '04', 'mayo': '05', 'junio': '06',
                    'julio': '07', 'agosto': '08', 'septiembre': '09',
                    'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                }
                partes = fecha_texto.lower().split()
                # partes = ['4', 'julio', '2026']
                dia  = partes[0].zfill(2)
                mes  = meses.get(partes[1], '00')
                anio = partes[2]
                fecha_resultado = f"{anio}-{mes}-{dia}"
            except Exception:
                fecha_resultado = ""

            # Verificamos que sea resultado de hoy
            if fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en Loterias de Hoy es de {fecha_texto}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los dígitos del número vienen en span con clase 'redondoc chance1'
            # Cada span contiene un dígito
            spans_numero = resultado.find_all('span', class_='chance1')
            digitos = [s.get_text().strip() for s in spans_numero]

            # Necesitamos mínimo 4 dígitos para formar el número
            if len(digitos) < 4:
                mensaje_error = f"No se pudieron extraer suficientes dígitos en Loterias de Hoy para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # Los primeros 4 dígitos forman el número ganador
            numero = ''.join(digitos[:4])

            # La quinta viene en span con clase 'redondoc premio5'
            span_quinta = resultado.find('span', class_='premio5')
            quinta = span_quinta.get_text().strip() if span_quinta else ""

            log.info(f"Resultado encontrado en Loterias de Hoy | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todos los divs sin encontrar la lotería
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

    Cómo funciona esta página:
    - Necesita JavaScript para cargar
    - Los resultados vienen en divs con clase 'result-single-page'
    - El nombre se identifica por el código en la URL de la imagen
      Ejemplo: /assets/images/loterias/1ANT.png → Antioqueñita Uno
    - El número viene como dígitos separados: "4 0 5 6 - 6"
      donde los 4 primeros son el número y el último es la quinta
    - La serie viene separada: "1 8 3" → serie=183
    - La fecha viene en formato DD/MM/YYYY

    Parámetros:
    - nombre_loteria : nombre según nuestra tabla es_config_horarios
    - url            : URL de loti
    - log            : objeto de logs

    Retorna:
    - (dict, None)  → {"numero": "4056", "quinta": "6"} si encontró
    - (None, str)   → None, "mensaje error" si no encontró o falló
    """
    try:
        log.info(f"Consultando loti para: {nombre_loteria}")

        # Abrimos el navegador y obtenemos el HTML completamente renderizado
        html, error = abrir_navegador(url, log)
        if error:
            return None, error

        # Parseamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Fecha de hoy para validar que el resultado sea actual
        fecha_hoy = fecha_actual_colombia()

        # Los resultados están en divs con clase 'result-single-page'
        paginas = soup.find_all('div', class_='result-single-page')

        if not paginas:
            mensaje_error = "No se encontraron resultados en loti"
            log.error(mensaje_error)
            return None, mensaje_error

        # Recorremos cada div buscando la lotería que nos interesa
        for pagina in paginas:

            # El nombre se identifica por el código en la URL de la imagen
            img = pagina.find('img', class_='d-block')
            if not img:
                continue

            # Extraemos el código del nombre del archivo de imagen
            src = img.get('src', '')
            codigo = src.split('/')[-1].replace('.png', '')

            # Buscamos en el diccionario de códigos el nombre de la lotería
            nombre_en_loti = CODIGOS_LOTI.get(codigo)

            # Si no corresponde a la lotería buscada pasamos al siguiente
            if nombre_en_loti != nombre_loteria:
                continue

            # Extraemos el texto completo de este div
            texto_pagina = pagina.get_text(separator=' ')

            # Normalizamos para quitar tildes (NÚMERO → NUMERO)
            texto_normalizado = normalizar_texto(texto_pagina)

            # Extraemos la fecha del resultado formato DD/MM/YYYY
            match_fecha = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto_pagina)
            if match_fecha:
                fecha_resultado = f"{match_fecha.group(3)}-{match_fecha.group(2)}-{match_fecha.group(1)}"
            else:
                fecha_resultado = ""

            # Verificamos que sea resultado de hoy
            if fecha_resultado and fecha_resultado != fecha_hoy:
                mensaje_error = f"Resultado de {nombre_loteria} en loti es de {fecha_resultado}, no de hoy"
                log.info(mensaje_error)
                return None, mensaje_error

            # El número viene como dígitos individuales separados por espacios
            # con un guion separando la quinta: "4 0 5 6 - 6"
            # Buscamos todos los dígitos entre NUMERO y SERIE
            match_bloque = re.search(
                r'NUMERO\s+([\d\s\-]+?)\s+SERIE',
                texto_normalizado,
                re.IGNORECASE
            )

            if not match_bloque:
                # Para chances que no tienen SERIE buscamos entre NUMERO y FECHA
                match_bloque = re.search(
                    r'NUMERO\s+([\d\s\-]+?)\s+FECHA',
                    texto_normalizado,
                    re.IGNORECASE
                )

            if not match_bloque:
                mensaje_error = f"No se pudo extraer el número en loti para {nombre_loteria}"
                log.info(mensaje_error)
                return None, mensaje_error

            # El bloque contiene algo como "4 0 5 6 - 6"
            bloque = match_bloque.group(1).strip()

            # Separamos por el guion para obtener número y quinta
            partes = bloque.split('-')

            # El número son los dígitos de la primera parte sin espacios
            numero = partes[0].replace(' ', '').strip()

            # La quinta son los dígitos de la segunda parte si existe
            quinta = partes[1].replace(' ', '').strip() if len(partes) > 1 else ""

            # Verificamos que el número tenga 4 dígitos
            if not re.match(r'^\d{4}$', numero):
                mensaje_error = f"Número inválido en loti para {nombre_loteria}: {numero}"
                log.info(mensaje_error)
                return None, mensaje_error

            log.info(f"Resultado encontrado en loti | {nombre_loteria}: número={numero} | quinta={quinta}")
            return {"numero": numero, "quinta": quinta}, None

        # Si recorrió todos los divs sin encontrar la lotería
        mensaje_error = f"No se encontró '{nombre_loteria}' en loti"
        log.info(mensaje_error)
        return None, mensaje_error

    except Exception as e:
        mensaje_error = f"Error inesperado en loti: {e}"
        log.error(mensaje_error)
        return None, mensaje_error