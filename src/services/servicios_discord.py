import requests
from src.settings.entorno import env


def enviar_discord(mensaje: str, titulo: str = None, log: object = None, color: int = 3447003):

    # los "embeds" (recuadros con color) van en una lista bajo la llave "embeds"
    payload = {
        "embeds": [
            {
                "title": titulo or "Notificación Robot Scraping",
                "description": mensaje,
                "color": color,
            }
        ]
    }

    try:
        # timeout evita que el robot se quede colgado si Discord no responde
        response = requests.post(env.WEBHOOK_DISCORD, json=payload, timeout=10)

        response.raise_for_status()  # Lanza un error si la respuesta HTTP no es 2xx

        if log:
            log.info(f"Notificación enviada a Discord")
        return True
    except requests.exceptions.RequestException as e:
        mensaje_error = f"Error al enviar notificación a Discord:{e}"
        if log:
            log.error(mensaje_error)
        return False