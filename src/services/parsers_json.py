"""
Parsers para orígenes JSON (APIs). Reciben el JSON ya parseado y devuelven
una lista de dicts estandarizados via utils_scraping.construir_resultado.
"""
from urllib.parse import urlparse
from src.services.utils_scraping import construir_resultado, normalizar_fecha, fecha_hoy_iso, homologar_nombre_sorteo


def parsear_supergiros_norte_valle(data: dict, url: str) -> list[dict]:

    hoy = fecha_hoy_iso()  # Formato "YYYY-MM-DD"

    resultados = []

    items = data.get("resultados", []) if isinstance(data, dict) else []

    for item in items:
        if not isinstance(item, dict):
            continue

        numero = item.get("number")
        if not numero:
            continue

        played_at = item.get("played_at", "")
        # Extraer fecha (YYYY-MM-DD) de played_at
        fecha_extraida = played_at.split(" ")[0] if played_at else None

        # Solo resultados de hoy
        if fecha_extraida != hoy:
            continue

        fecha_iso = normalizar_fecha(fecha_extraida)

        lottery = item.get("lottery") or {}
        nombre = lottery.get("display_name") or lottery.get("name") or "Desconocido"
        # Usar nombre homologado
        nombre = homologar_nombre_sorteo(nombre)

        zodiac_raw = item.get("zodiac_sign") or ""
        quinta = None
        signo = None

        if zodiac_raw.lower().startswith("serie:"):
            serie_completa = zodiac_raw.split(":", 1)[1].strip()
            quinta = serie_completa[-1] if serie_completa else None
        elif zodiac_raw:
            signo = zodiac_raw.strip().title()

        resultados.append(construir_resultado(
            nombre_sorteo=nombre,
            numero=numero,
            fecha_iso=fecha_iso,
            quinta=quinta,
            signo=signo,
            fuente=url,
        ))
    return resultados


# Parsers JSON por dominio; el dispatcher busca coincidencia de substring en la URL.
PARSERS_JSON_POR_DOMINIO = {
    "supergirosnortedelvalle.com": parsear_supergiros_norte_valle,
}


def obtener_parser_json(url: str):
    """Devuelve el parser JSON para esta URL, o None. Compara por hostname real (evita colisiones entre dominios similares)."""
    hostname = (urlparse(url).hostname or "").lower()
    for dominio, parser in PARSERS_JSON_POR_DOMINIO.items():
        dominio = dominio.lower()
        if hostname == dominio or hostname.endswith("." + dominio):
            return parser
    return None
