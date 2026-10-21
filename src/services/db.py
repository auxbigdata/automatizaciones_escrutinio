import psycopg2
from src.settings.entorno import env

def get_connection():
    return psycopg2.connect(
        host=env.DB_HOST,
        port=env.DB_PORT,
        dbname=env.DB_NAME,
        user=env.DB_USER,
        password=env.DB_PASS,
        connect_timeout=10  # si la BD no responde en 10 segundos falla en vez de quedarse colgado
    )


def ejecutar_query(sql, params=None, devolver_rowcount=False):
    conn = get_connection()  # Abre una conexión nueva para este query
    try:
        with conn.cursor()as cur:
            cur.execute(sql, params or ())  # Ejecuta la consulta SQL con los parámetros proporcionados
            if cur.description:
                return cur.fetchall()  # Devuelve los resultados si la consulta devuelve filas

            # si no hay cur.description fue un insert, update o delete
            filas_afectadas = cur.rowcount
            conn.commit()  # Confirma los cambios en la base de datos
            return filas_afectadas if devolver_rowcount else None


    finally:
        conn.close()  # Cierra la conexión

# Ejecuta varias queries (sql, params) en UNA sola conexión/transacción. Si alguna falla, se hace rollback de todas.
def ejecutar_transaccion(queries:list[tuple]):
    conn = None  # si get_connection() falla, conn queda en None y evitamos "local variable 'conn'
    try:
        conn=get_connection()
        with conn.cursor() as cur:
            for sql, params in queries:
                cur. execute(sql, params or ())
        conn.commit()
    except Exception as e:
        if conn is not None:
            conn.rollback()
        raise e
    finally:
        if conn is not None:
            conn.close()
