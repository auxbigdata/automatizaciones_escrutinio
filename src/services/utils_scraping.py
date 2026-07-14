import unicodedata


def normalizar_texto(texto: str) -> str:
    texto = texto.upper().strip()
    # Reemplazamos Ñ por N antes de quitar tildes
    # porque Ñ no es simplemente una N con tilde
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

    # ----------CAFETERITO
    "CAFETERITO DIA":           "Cafeterito Día",
    "CAFETERITO TARDE":         "Cafeterito Día",
    "CAFETARDE":                "Cafeterito Día",
    "CAFETERITO NOCHE":         "Cafeterito Noche",
    "CAFENOCHE":                "Cafeterito Noche",

    # ----------CARIBEÑA
    "CARIBEÑA DIA":             "Caribeña Día",
    "CARIBENA DIA":             "Caribeña Día",
    "CARIBDIA":                 "Caribeña Día",
    "CARIBEÑA NOCHE":           "Caribeña Noche",
    "CARIBENA NOCHE":           "Caribeña Noche",
    "CARIBNOCHE":               "Caribeña Noche",

    # ----------CULONA
    "CULONA DIA":               "Culona Día",
    "LA CULONA DIA":            "Culona Día",
    "CULODIA":                  "Culona Día",
    "CULONA NOCHE":             "Culona Noche",
    "CULONOCHE":                "Culona Noche",

    # ----------FANTÁSTICA
    "FANTASTICA DIA":           "Fantástica Día",
    "LA FANTASTICA DIA":        "Fantástica Día",
    "FANTADIA":                 "Fantástica Día",
    "FANTASTICA NOCHE":         "Fantástica Noche",
    "LA FANTASTICA NOCHE":      "Fantástica Noche",
    "FANTANOCHE":               "Fantástica Noche",

    # ----------MOTILÓN
    "MOTILON DIA":              "Motilón Tarde",
    "MOTILO DIA":               "Motilón Tarde",
    "MOTILON TARDE":            "Motilón Tarde",
    "MOTIDIA":                  "Motilón Tarde",
    "MOTILON NOCHE":            "Motilón Noche",
    "EL MOTILON":               "Motilón Noche",
    "MOTINOCHE":                "Motilón Noche",

    # ----------SINUANO
    "SINUANO DIA":              "Sinuano Día",
    "SINUDIA":                  "Sinuano Día",
    "SINUANO NOCHE":            "Sinuano Noche",
    "SINUNOCHE":                "Sinuano Noche",

    # ----------PIJAO
    "PIJAO":                    "El Pijao de Oro",
    "PIJAO NOCHE":              "El Pijao de Oro",
    "EL PIJAO DE ORO":          "El Pijao de Oro",

    # ----------SAMÁN
    "SAMAN":                    "El Samán de la Suerte",
    "SAMAN DE LA SUERTE":       "El Samán de la Suerte",
    "EL SAMAN DE LA SUERTE":    "El Samán de la Suerte",
    "SAMANDIA":                 "El Samán de la Suerte",

    # ----------LOTERÍAS TRADICIONALES
    "CUNDINAMARCA":             "Lotería Cundinamarca",
    "LOTERIA DE CUNDINAMARCA":  "Lotería Cundinamarca",
    "TOLIMA":                   "Lotería Tolima",
    "LOTERIA DEL TOLIMA":       "Lotería Tolima",
    "CRUZROJA":                 "Lotería Cruz Roja",
    "CRUZ ROJA":                "Lotería Cruz Roja",
    "LOTERIA CRUZ ROJA":        "Lotería Cruz Roja",
    "HUILA":                    "Lotería Huila",
    "LOTERIA DEL HUILA":        "Lotería Huila",
    "META":                     "Lotería Meta",
    "LOTERIA DEL META":         "Lotería Meta",
    "BOGOTA":                   "Lotería Bogotá",
    "LOTERIA DE BOGOTA":        "Lotería Bogotá",
    "MEDELLIN":                 "Lotería Medellín",
    "LOTERIA DE MEDELLIN":      "Lotería Medellín",
    "SANTANDER":                "Lotería Santander",
    "LOTERIA DE SANTANDER":     "Lotería Santander",
    "RISARALDA":                "Lotería Risaralda",
    "LOTERIA DE RISARALDA":     "Lotería Risaralda",
    "BOYACA":                   "Lotería Boyacá",
    "LOTERIA DE BOYACA":        "Lotería Boyacá",
    "MANIZALES":                "Lotería Manizales",
    "LOTERIA DE MANIZALES":     "Lotería Manizales",
    "QUINDIO":                  "Lotería Quindío",
    "LOTERIA DEL QUINDIO":      "Lotería Quindío",
    "VALLE":                    "Lotería Valle",
    "LOTERIA DEL VALLE":        "Lotería Valle",
    "CAUCA":                    "Lotería Cauca",
    "LOTERIA DEL CAUCA":        "Lotería Cauca",
    "EXTRA":                    "Extra de Colombia",
    "EXTRA DE COLOMBIA":        "Extra de Colombia",
}


# ==========================================================
# SLUGS DE GANAR CHANCE
# Se usa para construir la sub-URL específica de cada lotería:
# https://www.ganarchance.com/resultado/{slug}
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
# Mapea el código de la imagen al nombre en nuestra tabla

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