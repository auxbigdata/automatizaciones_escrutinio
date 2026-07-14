from email.utils import formatdate
import smtplib
from email.message import EmailMessage
import mimetypes
import os
import imaplib
import email
from email.header import decode_header
import os
import socket
import ssl
import pytz
from datetime import datetime

def enviar_email(destinatario: str, mensaje: str, asunto: str, titulo_mensaje: str, prioridad: int=0, adjuntos: str =None):
    mensaje = mensaje
    titulo_mensaje = titulo_mensaje
    plantilla = f"""<head>  
    <meta charset="utf-8">  
    <meta name="viewport" content="width=device-width,initial-scale=1">  
    <meta name="x-apple-disable-message-reformatting">  
    <title></title>  
    <style>  
        table, td, div, h1, p {{  
        font-family: Arial, sans-serif;  
        }}  
        @media screen and (max-width: 530px) {{  
        .unsub {{  
            display: block;  
            padding: 8px;  
            margin-top: 14px;  
            border-radius: 6px;  
            background-color: #555555;  
            text-decoration: none !important;  
            font-weight: bold;  
        }}  
        .col-lge {{  
            max-width: 100% !important;  
        }}  
        }}  
        @media screen and (min-width: 531px) {{  
        .col-sml {{  
            max-width: 27% !important;  
        }}  
        .col-lge {{  
            max-width: 73% !important;  
        }}  
        }}  
    </style>  
    </head>  
    <body style="margin:0;padding:0;word-spacing:normal;background-color:#939297;">  
    <div role="article" aria-roledescription="email" lang="en" style="text-size-adjust:100%;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;background-color:#1086FF;"> 
        <table role="presentation" style="width:100%;border:none;border-spacing:0;">  
        <tr>  
            <td align="center" style="padding:0;">    
            <table role="presentation" style="width:94%;max-width:600px;border:none;border-spacing:0;text-align:left;font-family:Arial,sans-serif;font-size:16px;line-height:22px;color:#363636;"> 
                <tr>  
                <td style="padding:40px 30px 30px 30px;text-align:center;font-size:24px;font-weight:bold;">  
                </td>  
                </tr>  
                <tr>  
                <td style="padding:30px;background-color:#ffffff;">  
                    <h1 style="margin-top:0;margin-bottom:16px;font-size:26px;line-height:32px;font-weight:bold;letter-spacing:-0.02em;"> 

    {titulo_mensaje}
    </h1>  
                    <p style="margin:0;"> 
                    
    Cordial saludo,
    <br><br>
    {mensaje}
    </div>  
                </td>  
                </tr>  
                </tr>  
                <tr>  
                <td style="padding:30px;background-color:#ffffff;">  
                    <p style="margin:0;">Cordialmente,  
    <br><br><br>
                    Automatización Robotica de Procesos Consuerte
                    <br>
                    auxanalista@consuerte.com.co 
    </p>
                </td>  
                </tr>  
                <tr>  
                <td style="padding:30px;text-align:center;font-size:12px;background-color:#404040;color:#cccccc;">  
                    <p style="margin:0;font-size:14px;line-height:20px;">&reg; Consuerte Villavicencio - Meta<br><a class="unsub" href="https://www.consuerte.com.co" style="color:#cccccc;text-decoration:underline;">Dirección: Calle 15 N° 40 - 01 Centro Comercial Primavera Urbana - Oficina 1001 
                    Teléfono: (608) 670 98 98 - 320 831 42 93</a></p>  
                </td>  
                </tr>  
            </table>   
            </td>  
        </tr>  
        </table>  
    </div>  
    </body>  
    </html> 
    """ 

    remitente = "auxanalista@consuerte.com.co"
    password = "C0nsu324*"
    msg = EmailMessage()
    msg["From"] = remitente
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg["Date"] = formatdate(localtime=True)
    # enviar correo como importante
    if prioridad == 1:
        msg["Importance"] = "High"
        msg["X-Priority"] = "1"
        msg["X-MSMail-Priority"] = "High"

    msg.set_content(plantilla, subtype="html")

    # ==============================
    # Adjuntar archivos si existen
    # ==============================
    if adjuntos is not None:

        # Si viene un solo archivo, lo convertimos en lista
        if isinstance(adjuntos, str):
            adjuntos = [adjuntos]

        for ruta in adjuntos:
            if not os.path.isfile(ruta):
                raise FileNotFoundError(f"Adjunto no encontrado: {ruta}")

            tipo, encoding = mimetypes.guess_type(ruta)
            if tipo is None:
                tipo = "application/octet-stream"

            maintype, subtype = tipo.split("/", 1)

            with open(ruta, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(ruta)
                )

    smtp = smtplib.SMTP("10.1.1.1", 587)
    smtp.login(remitente, password)
    smtp.send_message(msg)
    smtp.quit()


# obtener fecha actual colombia
def fecha_actual_colombia() -> str:
        zona_colombia = pytz.timezone("America/Bogota")
        return datetime.now(zona_colombia).strftime("%Y-%m-%d")
