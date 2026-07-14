import logging
import os
from datetime import datetime
from src.settings.paths import robot_archivos

# RUTA RAIZ DEL PROYECTO (sube 3 niveles desde este archivo)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# funcion donde inicializamos el logger configurado y la ruta descargada de archivos del robot
def parametrizar_logs_y_ruta_archivos(robot_name:str):
    log = get_logger(robot_name)
    ruta_archivos = robot_archivos(robot_name) # viene de pahts.py crea la carpeta si no existe
    return log, ruta_archivos

# crea y configura el logger exclusivo para el robot indicado
def get_logger(robot_name:str):

    LOGS_DIR = os.path.join(BASE_DIR,"resources",robot_name,"logs")
    os.makedirs(LOGS_DIR, exist_ok=True) # crea la carpeta de logs si no existe

    # nombre del archivo de log con fecha y hora actual
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOGS_DIR,f"{timestamp}.log")

    # crea un logger con el nombre del robot
    logger = logging.getLogger(f"{robot_name}_logger")
    logger.setLevel(logging.DEBUG)  # Captura todos los niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL

    # formato de cada liena de log
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s]%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # escribe los logs en el archivo .log
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # muestra los logs en la consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Evita duplicar mensajes si get_logger() se llama más de una vez con el mismo robot_name
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger



