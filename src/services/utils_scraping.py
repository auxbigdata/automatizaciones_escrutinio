import unicodedata
import re
from datetime import datetime, date, timedelta
from typing import Optional, Tuple


def normalizar_texto(texto: str) -> str:
    texto = texto.upper().strip()
    # Ñ se reemplaza por N antes de quitar tildes (no es una N con tilde)
    texto = texto.replace('Ñ', 'N')
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto


MAPEO_GENERICO = {

    # ----------ANTIOQUEÑITA
    "ANTIOQUEÑITA DIA":         "Antioqueñita Uno",
    "ANTIOQUEÑITA 1":           "Antioqueñita Uno",
    "ANTIOQUENITA 1":           "Antioqueñita Uno",
    "ANTIOQUENITA DIA":         "Antioqueñita Uno",
    "ANTIOQUEÑITA MAÑANA":      "Antioqueñita Uno",
    "ANTIOQUENITA":             "Antioqueñita Uno",
    "ANTIOQ1":                  "Antioqueñita Uno",
    "ANTIOQUEÑITA TARDE":       "Antioqueñita Dos",
    "ANTIOQUEÑITA 2":           "Antioqueñita Dos",
    "ANTIOQUENITA 2":           "Antioqueñita Dos",
    "ANTIOQUENITA TARDE":       "Antioqueñita Dos",
    "ANTIOQUEÑITA NOCHE":       "Antioqueñita Dos",
    "ANTIOQ2":                  "Antioqueñita Dos",

    # ----------DORADO
    "DORADO DIA":               "Dorado Mañana",
    "DORADO MAÑANA":            "Dorado Mañana",
    "DORADO MANANA":            "Dorado Mañana",
    "DORDIA":                   "Dorado Mañana",
    "DORADO TARDE":             "Dorado Tarde",
    "DORTARDE":                 "Dorado Tarde",
    "DORADO NOCHE":             "Dorado Noche",
    "DORNOCHE":                 "Dorado Noche",

    # ----------ASTRO
    "ASTRO SOL":                "Astro Sol",
    "SUPER ASTRO SOL":          "Astro Sol",
    "ASTROSOL":                 "Astro Sol",
    "ASTRO LUNA":               "Astro Luna",
    "SUPER ASTRO LUNA":         "Astro Luna",
    "ASTROLUNA":                "Astro Luna",

    # ----------CHONTICO
    "CHONTICO DIA":             "Chontico Millonario",
    "CHONTICO":                 "Chontico Millonario",
    "SUPER CHONTICO":           "Chontico Millonario",
    "CHONTICO MILLONARIO":      "Chontico Millonario",
    "CHONDIA":                  "Chontico Millonario",
    "CHONTICO NOCHE":           "Chontico Noche",
    "CHONNOCHE":                "Chontico Noche",

    # ----------PAISITA
    "PAISITA DIA":              "Paisita Uno",
    "PAISITA 1":                "Paisita Uno",
    "PAISDIA":                  "Paisita Uno",
    "PAISITA NOCHE":            "Paisita Dos",
    "PAISITA 2":                "Paisita Dos",
    "PAISNOCHE":                "Paisita Dos",
    "PAISITA 3 SABADO":         "Paisita Tres",
    "PAISITA TRES":             "Paisita Tres",
    "PAISSAB":                  "Paisita Tres",
    "PAISITA 3":                "Paisita Tres",        # GanaGana

    # ----------CAFETERITO
    "CAFETERITO DIA":           "Cafeterito Día",
    "CAFETERITO TARDE":         "Cafeterito Día",
    "CAFETARDE":                "Cafeterito Día",
    "CAFETERITO":               "Cafeterito Día",      # Perla Todo
    "CAFETERITO NOCHE":         "Cafeterito Noche",
    "CAFENOCHE":                "Cafeterito Noche",

    # ----------CARIBEÑA
    "CARIBEÑA DIA":             "Caribeña Día",
    "CARIBENA DIA":             "Caribeña Día",
    "CARIBDIA":                 "Caribeña Día",
    "CARIBENA":                 "Caribeña Día",        # Perla Todo
    "CARIBEÑA NOCHE":           "Caribeña Noche",
    "CARIBENA NOCHE":           "Caribeña Noche",
    "CARIBNOCHE":               "Caribeña Noche",

    # ----------CULONA
    "CULONA DIA":               "Culona Día",
    "LA CULONA DIA":            "Culona Día",
    "CULODIA":                  "Culona Día",
    "CULONA":                   "Culona Día",          # Perla Todo / GANAR CHANCE
    "CULONA NOCHE":             "Culona Noche",
    "CULONOCHE":                "Culona Noche",

    # ----------FANTÁSTICA
    "FANTASTICA DIA":           "Fantástica Día",
    "LA FANTASTICA DIA":        "Fantástica Día",
    "FANTADIA":                 "Fantástica Día",
    "FANTASTICA":               "Fantástica Día",      # Perla Todo
    "LA FANTASTICA 1":          "Fantástica Día",      # GanaGana
    "FANTASTICA NOCHE":         "Fantástica Noche",
    "LA FANTASTICA NOCHE":      "Fantástica Noche",
    "FANTANOCHE":               "Fantástica Noche",
    "LA FANTASTICA 2":          "Fantástica Noche",    # GanaGana

    # ----------MOTILÓN
    "MOTILON DIA":              "Motilón Tarde",
    "MOTILO DIA":               "Motilón Tarde",
    "MOTILON TARDE":            "Motilón Tarde",
    "MOTIDIA":                  "Motilón Tarde",
    "MOTILON":                  "Motilón Tarde",       # Perla Todo
    "MOTILON NOCHE":            "Motilón Noche",
    "EL MOTILON":               "Motilón Noche",
    "MOTINOCHE":                "Motilón Noche",

    # ----------SINUANO
    "SINUANO DIA":              "Sinuano Día",
    "SINUDIA":                  "Sinuano Día",
    "SINUANO":                  "Sinuano Día",         # Perla Todo
    "SINUANO NOCHE":            "Sinuano Noche",
    "SINUNOCHE":                "Sinuano Noche",

    # ----------PIJAO
    "PIJAO":                    "El Pijao de Oro",
    "PIJAO NOCHE":              "El Pijao de Oro",
    "EL PIJAO DE ORO":          "El Pijao de Oro",
    "PIJAO DE ORO":             "El Pijao de Oro",    # JER
    "PIJAO ORO":                "El Pijao de Oro",    # GANAR CHANCE

    # ----------SAMÁN
    "SAMAN":                    "El Samán de la Suerte",
    "SAMAN DE LA SUERTE":       "El Samán de la Suerte",
    "EL SAMAN DE LA SUERTE":    "El Samán de la Suerte",
    "SAMANDIA":                 "El Samán de la Suerte",
    "SAMAN DIA":                "El Samán de la Suerte",  # GANAR CHANCE

    # ----------LOTERÍAS TRADICIONALES
    "CUNDINAMARCA":             "Lotería Cundinamarca",
    "LOTERIA DE CUNDINAMARCA":  "Lotería Cundinamarca",
    "LOTERIA CUNDINAMARCA":     "Lotería Cundinamarca",   # GANAR CHANCE
    "TOLIMA":                   "Lotería Tolima",
    "LOTERIA DEL TOLIMA":       "Lotería Tolima",
    "LOTERIA TOLIMA":           "Lotería Tolima",         # GANAR CHANCE
    "CRUZROJA":                 "Lotería Cruz Roja",
    "CRUZ ROJA":                "Lotería Cruz Roja",
    "LOTERIA CRUZ ROJA":        "Lotería Cruz Roja",
    "HUILA":                    "Lotería Huila",
    "LOTERIA DEL HUILA":        "Lotería Huila",
    "LOTERIA HUILA":            "Lotería Huila",          # GANAR CHANCE
    "META":                     "Lotería Meta",
    "LOTERIA DEL META":         "Lotería Meta",
    "LOTERIA META":             "Lotería Meta",           # GANAR CHANCE
    "BOGOTA":                   "Lotería Bogotá",
    "LOTERIA DE BOGOTA":        "Lotería Bogotá",
    "LOTERIA BOGOTA":           "Lotería Bogotá",         # GANAR CHANCE
    "MEDELLIN":                 "Lotería Medellín",
    "LOTERIA DE MEDELLIN":      "Lotería Medellín",
    "LOTERIA MEDELLIN":         "Lotería Medellín",       # GANAR CHANCE
    "SANTANDER":                "Lotería Santander",
    "LOTERIA DE SANTANDER":     "Lotería Santander",
    "LOTERIA SANTANDER":        "Lotería Santander",      # GANAR CHANCE
    "RISARALDA":                "Lotería Risaralda",
    "LOTERIA DE RISARALDA":     "Lotería Risaralda",
    "LOTERIA RISARALDA":        "Lotería Risaralda",      # GANAR CHANCE
    "BOYACA":                   "Lotería Boyacá",
    "LOTERIA DE BOYACA":        "Lotería Boyacá",
    "LOTERIA BOYACA":           "Lotería Boyacá",         # GANAR CHANCE
    "MANIZALES":                "Lotería Manizales",
    "LOTERIA DE MANIZALES":     "Lotería Manizales",
    "LOTERIA MANIZALES":        "Lotería Manizales",      # GANAR CHANCE
    "QUINDIO":                  "Lotería Quindío",
    "LOTERIA DEL QUINDIO":      "Lotería Quindío",
    "LOTERIA QUINDIO":          "Lotería Quindío",        # GANAR CHANCE
    "VALLE":                    "Lotería Valle",
    "LOTERIA DEL VALLE":        "Lotería Valle",
    "LOTERIA VALLE":            "Lotería Valle",          # GANAR CHANCE
    "CAUCA":                    "Lotería Cauca",
    "LOTERIA DEL CAUCA":        "Lotería Cauca",
    "LOTERIA CAUCA":            "Lotería Cauca",          # GANAR CHANCE
    "EXTRA":                    "Extra de Colombia",
    "EXTRA DE COLOMBIA":        "Extra de Colombia",
}


# ==========================================================
# MAPEO DE SIGNOS ZODIACALES (Astro Sol / Astro Luna)
# Sinónimos de signos (ej. Escorpio/Escorpión); claves ya pasadas por normalizar_texto()
# ==========================================================
MAPEO_SIGNOS = {
    "ARIES":        "ARIES",
    "TAURO":        "TAURO",
    "GEMINIS":      "GEMINIS",
    "CANCER":       "CANCER",
    "LEO":          "LEO",
    "VIRGO":        "VIRGO",
    "LIBRA":        "LIBRA",
    "ESCORPIO":     "ESCORPIO",
    "ESCORPION":    "ESCORPIO",
    "SAGITARIO":    "SAGITARIO",
    "CAPRICORNIO":  "CAPRICORNIO",
    "ACUARIO":      "ACUARIO",
    "PISCIS":       "PISCIS",
}


# ==========================================================
# SLUGS DE GANAR CHANCE: para construir https://www.ganarchance.com/resultado/{slug}
# ==========================================================
SLUGS_GANAR_CHANCE = {
    "Antioqueñita Uno":     "antioquenita-dia",
    "Antioqueñita Dos":     "antioquenita-tarde",
    "Dorado Mañana":        "dorado-manana",
    "Dorado Tarde":         "dorado-tarde",
    "Dorado Noche":         "dorado-noche",
    "Chontico Millonario":  "chontico-dia",
    "Chontico Noche":       "chontico-noche",
    "Astro Sol":            "astro-sol",
    "Astro Luna":           "astro-luna",
    "Paisita Uno":          "paisita-dia",
    "Paisita Dos":          "paisita-noche",
    "Paisita Tres":         "paisita-3-sabado",
    "Cafeterito Día":       "cafeterito-tarde",
    "Cafeterito Noche":     "cafeterito-noche",
    "Culona Día":           "culona",
    "Culona Noche":         "culona-noche",
    "El Samán de la Suerte":"saman-dia",
    "El Pijao de Oro":      "pijao-oro",
    "Caribeña Día":         "caribena-dia",
    "Caribeña Noche":       "caribena-noche",
    "Motilón Tarde":        "motilon-tarde",
    "Motilón Noche":        "motilon-noche",
    "Fantástica Día":       "fantastica-dia",
    "Fantástica Noche":     "fantastica-noche",
    "Sinuano Día":          "sinuano-dia",
    "Sinuano Noche":        "sinuano-noche",
    "Lotería Cundinamarca": "loteria-cundinamarca",
    "Lotería Cruz Roja":    "loteria-cruz-roja",
    "Lotería Valle":        "loteria-valle",
    "Lotería Bogotá":       "loteria-bogota",
    "Lotería Medellín":     "loteria-medellin",
    "Lotería Boyacá":       "loteria-boyaca",
    "Lotería Tolima":       "loteria-tolima",
    "Lotería Huila":        "loteria-huila",
    "Lotería Meta":         "loteria-meta",
    "Lotería Manizales":    "loteria-manizales",
    "Lotería Quindío":      "loteria-quindio",
    "Lotería Santander":    "loteria-santander",
    "Lotería Risaralda":    "loteria-risaralda",
    "Lotería Cauca":        "loteria-cauca",
}


# ==========================================================
# CÓDIGOS DE LOTI
# ==========================================================
CODIGOS_LOTI = {
    # Loterías tradicionales
    "SANT":  "Lotería Santander",
    "RISA":  "Lotería Risaralda",
    "MEDE":  "Lotería Medellín",
    "BOGO":  "Lotería Bogotá",
    "META":  "Lotería Meta",
    "MANI":  "Lotería Manizales",
    "VALL":  "Lotería Valle",
    "HUIL":  "Lotería Huila",
    "TOLI":  "Lotería Tolima",
    "CUND":  "Lotería Cundinamarca",
    "CRUZ":  "Lotería Cruz Roja",
    "EXCO":  "Extra de Colombia",
    "CAUC":  "Lotería Cauca",
    "BOYA":  "Lotería Boyacá",
    # Chances
    "CAFT":  "Cafeterito Día",
    "CAFN":  "Cafeterito Noche",
    "DORD":  "Dorado Mañana",
    "DORT":  "Dorado Tarde",
    "DORN":  "Dorado Noche",
    "1ANT":  "Antioqueñita Uno",
    "2ANT":  "Antioqueñita Dos",
    "1PAI":  "Paisita Uno",
    "2PAI":  "Paisita Dos",
    "2PAF":  "Paisita Dos",
    "3PAI":  "Paisita Tres",
    "CHOD":  "Chontico Millonario",
    "CHON":  "Chontico Noche",
    "MOTN":  "Motilón Noche",
    "CRBD":  "Caribeña Día",
    "CRBN":  "Caribeña Noche",
    "ASOL":  "Astro Sol",
    "ALUN":  "Astro Luna",
    "PIJA":  "El Pijao de Oro",
    "CLNO":  "Culona Noche",
    "SIND":  "Sinuano Día",
    "SINN":  "Sinuano Noche",
    "FANN":  "Fantástica Noche",
    # Pendientes de confirmar
    "EMFI":  None,
    "SEXN":  None,
    "EMCO":  None,
    "PI3N":  None,
    "PI4N":  None,
    "PI4D":  None,
    "PI3D":  None,
}

# ==========================================================
# HERRAMIENTAS DEL SCRAPING DE RESPALDO (segundo scraping)
# A diferencia de MAPEO_GENERICO (sin tildes, vía normalizar_texto), este usa
# homologar_nombre_sorteo() que solo limpia espacios/mayúsculas, por eso conserva tildes/Ñ
# ==========================================================

# Signos zodiacales válidos (para Astro Sol / Astro Luna)
SIGNOS_ZODIACALES = {
    "aries", "tauro", "geminis", "géminis", "cancer", "cáncer", "leo",
    "virgo", "libra", "escorpion", "escorpión", "sagitario", "capricornio",
    "acuario", "piscis",
}

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

DIAS_SEMANA_ES = {
    "lunes", "martes", "miercoles", "miércoles", "jueves", "viernes",
    "sabado", "sábado", "domingo",
}

# Diccionario propio del scraping de respaldo, claves con tildes/Ñ (ver nota arriba)
MAPEO_GENERICO_HOMOLOGACION = {
    # ---------- ANTIOQUEÑITA ----------
    "ANTIOQUEÑITA DÍA":         "Antioqueñita Uno",
    "ANTIOQUEÑITA MAÑANA":      "Antioqueñita Uno",
    "ANTIOQUEÑITA 1":           "Antioqueñita Uno",
    "ANTIOQUEÑITA":             "Antioqueñita Uno",
    "ANTIOQUENITA DIA":         "Antioqueñita Uno",
    "ANTIOQ1":                  "Antioqueñita Uno",
    "1ANT":                     "Antioqueñita Uno",
    "ANTIOQUEÑITA TARDE":       "Antioqueñita Dos",
    "ANTIOQUENITA TARDE":       "Antioqueñita Dos",
    "ANTIOQUEÑITA 2":           "Antioqueñita Dos",
    "2ANT":                     "Antioqueñita Dos",
    "ANTIOQUEÑITA NOCHE":       "Antioqueñita Dos",

    # ---------- DORADO ----------
    "DORADO DÍA":               "Dorado Mañana",
    "DORADO MAÑANA":            "Dorado Mañana",
    "DORADO MANANA":            "Dorado Mañana",
    "DORDIA":                   "Dorado Mañana",
    "DORD":                     "Dorado Mañana",
    "DORADO TARDE":             "Dorado Tarde",
    "DORTARDE":                 "Dorado Tarde",
    "DORT":                     "Dorado Tarde",
    "DORADO NOCHE":             "Dorado Noche",

    # ---------- CHONTICO ----------
    "CHONTICO DÍA":             "Chontico Millonario",
    "CHONTICO DIA":             "Chontico Millonario",
    "CHONTICO":                 "Chontico Millonario",
    "CHONTICO MILLONARIO":      "Chontico Millonario",
    "CHONTMILLONARIO":          "Chontico Millonario",
    "CHONTICO NOCHE":           "Chontico Noche",

    # ---------- PAISITA ----------
    "PAISITA DÍA":              "Paisita Uno",
    "PAISITA DIA":              "Paisita Uno",
    "PAISITA 1":                "Paisita Uno",
    "PAISITA1":                 "Paisita Uno",
    "1PAI":                     "Paisita Uno",
    "PAISITA NOCHE":            "Paisita Dos",
    "PAISITA 2":                "Paisita Dos",
    "PAISITA 3 SABADO":         "Paisita Tres",
    "PAISITA TRES":             "Paisita Tres",

    # ---------- CAFETERITO ----------
    "CAFETERITO DÍA":           "Cafeterito Día",
    "CAFETERITO DIA":           "Cafeterito Día",
    "CAFETERITO TARDE":         "Cafeterito Tarde",
    "CAFETERO TARDE":           "Cafeterito Tarde",
    "CAFETARDE":                "Cafeterito Tarde",
    "CAFT":                     "Cafeterito Tarde",
    "CAFETERITO NOCHE":         "Cafeterito Noche",

    # ---------- CARIBEÑA ----------
    "CARIBEÑA DÍA":             "Caribeña Día",
    "CARIBEÑA":                 "Caribeña Día",
    "LA CARIBEÑA DÍA":          "Caribeña Día",
    "CARIBENA DIA":             "Caribeña Día",
    "LA CARIBENA DIA":          "Caribeña Día",
    "LA CARIBEÑA 1":            "Caribeña Día",
    "CARIBDIA":                 "Caribeña Día",
    "CARIBEÑA NOCHE":           "Caribeña Noche",

    # ---------- CULONA ----------
    "CULONA DÍA":               "Culona Día",
    "LA CULONA DÍA":            "Culona Día",
    "LA CULONA DIA":            "Culona Día",
    "CULONA":                   "Culona Día",
    "LA CULONA":                "Culona Día",
    "CULONA NOCHE":             "Culona Noche",

    # ---------- FANTÁSTICA ----------
    "FANTÁSTICA DÍA":           "Fantástica Día",
    "FANTASTICA DÍA":           "Fantástica Día",
    "FANTASTICA DIA":           "Fantástica Día",
    "LA FANTASTICA DIA":        "Fantástica Día",
    "LA FANTÁSTICA DÍA":        "Fantástica Día",
    "LA FANTÁSTICA 1":          "Fantástica Día",
    "RESULTADOS LA FANTÁSTICA DÍA": "Fantástica Día",
    "RESULTADOS LA FANTASTICA DIA": "Fantástica Día",
    "FANTÁSTICA NOCHE":         "Fantástica Noche",

    # ---------- MOTILÓN ----------
    "MOTILÓN DÍA":              "Motilón Tarde",
    "MOTILO DÍA":               "Motilón Tarde",
    "MOTILO DIA":               "Motilón Tarde",
    "MOTILÓN TARDE":            "Motilón Tarde",
    "MOTILON TARDE":            "Motilón Tarde",
    "EL MOTILÓN 1":             "Motilón Tarde",
    "MOTILÓN NOCHE":            "Motilón Noche",

    # ---------- SINUANO ----------
    "SINUANO DÍA":              "Sinuano Día",
    "SINUDIA":                  "Sinuano Día",
    "SINUANO NOCHE":            "Sinuano Noche",

    # ---------- PIJAO Y SAMÁN ----------
    "PIJAO":                    "El Pijao de Oro",
    "PIJA":                     "El Pijao de Oro",
    "PIJAO DE ORO":             "El Pijao de Oro",
    "EL PIJAO DE ORO":          "El Pijao de Oro",
    "SAMÁN":                    "El Samán de la Suerte",
    "SAMAN":                    "El Samán de la Suerte",
    "SAMÁN DÍA":                "El Samán de la Suerte",
    "SAMAN DÍA":                "El Samán de la Suerte",
    "SAMÁN DE LA SUERTE":       "El Samán de la Suerte",
    "SAMAN DE LA SUERTE":       "El Samán de la Suerte",
    "EL SAMÁN DE LA SUERTE":    "El Samán de la Suerte",
    "EL SAMAN DE LA SUERTE":    "El Samán de la Suerte",

    # ---------- ASTRO ----------
    "ASTRO SOL":                "Astro Sol",
    "SUPER ASTRO SOL":          "Astro Sol",
    "ASTROSOL":                 "Astro Sol",
    "ASTRO LUNA":               "Astro Luna",
    "SUPER ASTRO LUNA":         "Astro Luna",
    "ASTROLUNA":                "Astro Luna",

    # ---------- AMERICANOS ----------
    "CASH THREE DÍA":           "Pick 3 Día",
    "CASH DÍA":                 "Pick 3 Día",
    "PICK 3 DÍA":               "Pick 3 Día",
    "PIC3DIA":                  "Pick 3 Día",
    "PLAY FOUR DÍA":            "Pick 4 Día",
    "PICK 4 DÍA":               "Pick 4 Día",
    "PIC4DIA":                  "Pick 4 Día",
    "PIC4DÍA":                  "Pick 4 Día",

    # ---------- LOTERÍAS ----------
    "CUNDINAMARCA":             "Lotería Cundinamarca",
    "CUNDINAM":                 "Lotería Cundinamarca",
    "TOLIMA":                   "Lotería Tolima",
    "HUILA":                    "Lotería Huila",
}


def homologar_nombre_sorteo(nombre_sucio: str) -> str:
    """Limpia espacios, pasa a MAYÚSCULAS y busca en MAPEO_GENERICO_HOMOLOGACION. A diferencia de normalizar_texto(), conserva tildes y Ñ."""
    if not nombre_sucio or not isinstance(nombre_sucio, str):
        return ""

    nombre_limpio = nombre_sucio.upper().strip()
    nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio)

    # Si no está en el diccionario, retorna el nombre limpio tal cual
    return MAPEO_GENERICO_HOMOLOGACION.get(nombre_limpio, nombre_limpio)


def limpiar_texto(texto: str) -> str:
    """Elimina espacios y saltos de línea extra."""
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def es_signo_zodiacal(texto: str) -> bool:
    return limpiar_texto(texto).lower() in SIGNOS_ZODIACALES


def separar_numero_y_extra(texto: str) -> Tuple[Optional[str], Optional[str]]:

    if not texto:
        return None, None

    t = limpiar_texto(texto)
    # Junta dígitos separados por espacios (ej: loteriasdehoy trae "3 1 9 0" en vez de "3190")
    t_sin_espacios_internos = re.sub(r"(?<=\d)\s+(?=\d)", "", t)

    m = re.match(r"^(\d{3,4})(.*)$", t_sin_espacios_internos)
    if not m:
        return None, None

    numero = m.group(1)
    resto = m.group(2).strip(" -()")
    return numero, (resto if resto else None)


def clasificar_extra(extra: Optional[str]) -> dict:

    resultado = {"serie": None, "quinta": None, "signo": None, "extra_sin_clasificar": None}
    if not extra:
        return resultado

    extra = extra.strip()
    if es_signo_zodiacal(extra):
        resultado["signo"] = extra.title()
        return resultado

    grupos = re.findall(r"\d+", extra)
    if not grupos:
        resultado["extra_sin_clasificar"] = extra
        return resultado

    # Heurística: 1 dígito=quinta, 3 dígitos=serie, ambos=quinta+serie
    if len(grupos) == 1:
        if len(grupos[0]) == 1:
            resultado["quinta"] = grupos[0]
        elif len(grupos[0]) == 3:
            resultado["serie"] = grupos[0]
        else:
            resultado["extra_sin_clasificar"] = extra
    elif len(grupos) == 2:
        cortos = [g for g in grupos if len(g) == 1]
        largos = [g for g in grupos if len(g) == 3]
        if cortos:
            # Tomamos el último para evitar capturar el '5' si el texto dice "La 5ta: 6"
            resultado["quinta"] = cortos[-1]
        if largos:
            resultado["serie"] = largos[0]
        if not cortos and not largos:
            resultado["extra_sin_clasificar"] = extra
    else:
        resultado["extra_sin_clasificar"] = extra

    return resultado


def normalizar_fecha(texto_fecha: str, fecha_referencia: Optional[date] = None) -> Optional[str]:
    """Normaliza distintos formatos de fecha (ISO, dd/mm/yyyy, texto en español) a ISO. Retorna None si no reconoce el formato."""
    if not texto_fecha:
        return None

    t = limpiar_texto(texto_fecha).lower()
    t = t.replace("del ", "de ")  # "19 de junio del 2026" -> "19 de junio de 2026"
    t = t.replace("de ", "")  # "19 de junio de 2026" -> "19 junio 2026"

    # Ya en ISO
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
    if m:
        return t

    # dd/mm/yyyy
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", t)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    # dd-mm-yyyy
    m = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", t)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    # "19 junio 2026" o "viernes 19 junio 2026"
    m = re.search(r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})", t)
    if m:
        d, mes_txt, y = m.groups()
        mes_num = MESES_ES.get(mes_txt)
        if mes_num:
            return f"{y}-{mes_num:02d}-{int(d):02d}"

    return None


def extraer_fecha_de_texto_libre(texto: str) -> Optional[str]:
    """A diferencia de normalizar_fecha (que asume que todo el texto es la fecha), busca un patrón de fecha embebido en un texto más largo (usado en el fallback genérico)."""
    if not texto:
        return None

    # ISO embebido: 2026-06-19
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", texto)
    if m:
        return m.group(0)

    # dd/mm/yyyy embebido
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", texto)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    # "19 junio 2026" embebido
    m = re.search(r"\b(\d{1,2})\s+(de\s+)?([a-záéíóú]+)\s+(de\s+)?(\d{4})\b", texto.lower())
    if m:
        d, _, mes_txt, _, y = m.groups()
        mes_num = MESES_ES.get(mes_txt)
        if mes_num:
            return f"{y}-{mes_num:02d}-{int(d):02d}"

    return None


def fecha_hoy_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def construir_resultado(
    nombre_sorteo: str,
    numero: str,
    fecha_iso: Optional[str],
    serie: Optional[str] = None,
    quinta: Optional[str] = None,
    signo: Optional[str] = None,
    extra_sin_clasificar: Optional[str] = None,
    fuente: Optional[str] = None,
    fecha_aproximada: bool = False,
) -> dict:
    """Construye el dict estandarizado de salida para un resultado de sorteo."""
    return {
        "nombre_sorteo": limpiar_texto(nombre_sorteo),
        "numero": numero,
        "fecha": fecha_iso,
        "fecha_aproximada": fecha_aproximada,
        "serie": serie,
        "quinta": quinta,
        "signo": signo,
        "extra_sin_clasificar": extra_sin_clasificar,
        "fuente": fuente,
    }


def obtener_fecha_ayer():
    ayer = datetime.now() - timedelta(days=1)
    return ayer.strftime("%Y/%m/%d")