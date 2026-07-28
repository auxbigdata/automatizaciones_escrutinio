# PROJECT_DIR="/home/ubuntu/python/automatizaciones_escrutinio"
# PYTHON_BIN="$PROJECT_DIR/env/bin/python3"

# cd $PROJECT_DIR
# $PYTHON_BIN -m src.robots.punto_red
# /home/ubuntu/python/automatizaciones_escrutinio/env/bin/python3
PROD_PATH="/home/dia_anterior/automatizaciones_escrutinio"
PRUEBAS_PATH="/home/ubuntu/python/automatizaciones_escrutinio"

# 2. El script pregunta: ¿Existe la carpeta de producción?
if [ -d "$PROD_PATH" ]; then
    PROJECT_DIR="$PROD_PATH"
    echo "Entorno detectado: PRODUCCIÓN"
else
    PROJECT_DIR="$PRUEBAS_PATH"
    echo "Entorno detectado: PRUEBAS"
fi

# 3. Configuramos el resto usando la variable detectada
PYTHON_BIN="$PROJECT_DIR/env/bin/python3"

# 4. Ejecución
cd "$PROJECT_DIR"
$PYTHON_BIN -m src.robots.scraping