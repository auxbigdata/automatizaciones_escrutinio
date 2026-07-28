import psycopg2  # Librería para conectarse a bases de datos PostgreSQL
from src.settings.entorno import env 

def get_connection():
    return psycopg2.connect(
        host=env.DB_HOST,      
        port=env.DB_PORT,      
        dbname=env.DB_NAME,    
        user=env.DB_USER,      
        password=env.DB_PASS   
    )


def ejecutar_query(sql, params=None):
    conn = get_connection()  # Abre una conexión nueva para este query
    try: 
        with conn.cursor()as cur:
            cur.execute(sql, params or ())  # Ejecuta la consulta SQL con los parámetros proporcionados
            if cur.description:
                return cur.fetchall()  # Devuelve los resultados si la consulta devuelve filas
            
            # si no hay cur.description fue un insert, update o delete
            conn.commit()  # Confirma los cambios en la base de datos
            return None  # Devuelve None si no hay resultados
        

    finally:
        conn.close()  # Cierra la conexión

# Ejecuta varias queries (sql, params) en UNA sola conexión/transacción. Si alguna falla, se hace rollback de todas.
def ejecutar_transaccion(queries:list[tuple]):
    try:
        conn=get_connection()
        with conn.cursor() as cur:
            for sql, params in queries:
                cur. execute(sql, params or ())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
