import os 

def identificar_tipo(valor):
    """Evalúa el valor del .env e infiere su tipo de dato para Python."""
    valor = valor.strip()

    # si es un booleano
    if valor.lower() in ('true', 'false'):
        return 'bool'
    # si es un entero
    if valor.lstrip('-').isdigit():
        return 'int'
    
    # si es float
    try:
        float(valor)
        return 'float'
    except ValueError:
        pass
    # si no es ningun valor de los anteriores, es un string
    return 'str'

def cargar_variables_entorno():
    archivo_env = '.env'
    archivo_ejemplo = '.env_ej.md'
    archivo_python = 'src/settings/entorno.py' 

    if not os.path.exists(archivo_env):
        print(f"Error: No se encontró {archivo_env}")
        return

    variables_y_tipos = {}
    lineas_originales = []
    # 1. Leer el .env, inferir tipos y guardar todo el contenido literal
    with open(archivo_env, 'r', encoding='utf-8') as f:
        for linea in f:
            lineas_originales.append(linea) # Guardamos la línea intacta (con comentarios y valores)
            
            linea_limpia = linea.strip()
            # Ignorar comentarios y líneas vacías para la extracción de Pydantic
            if linea_limpia and not linea_limpia.startswith('#') and '=' in linea_limpia:
                clave, valor = linea_limpia.split('=', 1)
                clave = clave.strip()
                tipo_inferido = identificar_tipo(valor)
                variables_y_tipos[clave] = tipo_inferido
    
    # 2. Generar el .env_ej.md copiando exactamente lo del .env
    with open(archivo_ejemplo, 'w', encoding='utf-8') as f:
        for linea in lineas_originales:
            f.write(linea)
    print(f"✅ {archivo_ejemplo} actualizado con los valores exactos y comentarios.")

    # 3. Generar el código Python con Pydantic
    atributos_clase = "\n".join([f"    {clave}: {tipo}" for clave, tipo in variables_y_tipos.items()])

    codigo_python = f"""# Archivo autogenerado por sync_env.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Entorno(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    
{atributos_clase}

# Instancia global lista para ser importada
env = Entorno()
"""
    
    directorio_destino = os.path.dirname(archivo_python)
    if directorio_destino: # Solo intenta crearla si la ruta incluye carpetas
        os.makedirs(directorio_destino, exist_ok=True)


    with open(archivo_python, 'w', encoding='utf-8') as f:
        f.write(codigo_python)

    print(f"{archivo_python} autogenerado con éxito usando Pydantic.")

if __name__ == "__main__":
    cargar_variables_entorno()