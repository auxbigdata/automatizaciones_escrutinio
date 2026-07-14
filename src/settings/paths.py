import os

# obtiene la ruta absoluta del directorio base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def robot_archivos(name):
    '''
    Docstring for robot_archivos
    
    :param name: Nombre de la carpeta del robot donde se dejaran los archivos en caso de necesitarlo
    '''
    # Construye la ruta: BASE_DIR/resources/<name>/archivos
    path = os.path.join(robot_path(name), "archivos")
    
    # Crea la carpeta "archivos" si no existe.
    # exist_ok=True evita error si la carpeta ya existe
    os.makedirs(path, exist_ok=True)
    
    # Retorna la ruta completa de la carpeta de archivos
    return path


def robot_path(name):
    # Construye y retorna la ruta base del robot:
    # BASE_DIR/resources/<name>
    return os.path.join(BASE_DIR, "resources", name)


def robot_logs(name):
    # Construye y retorna la ruta de logs del robot:
    # BASE_DIR/resources/<name>/logs
    # A diferencia de robot_archivos, NO crea la carpeta automáticamente
    return os.path.join(robot_path(name), "logs")