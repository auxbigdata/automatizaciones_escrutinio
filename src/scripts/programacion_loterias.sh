# PROJECT_DIR="/home/ubuntu/python/automatizaciones_escrutinio"
# PYTHON_BIN="$PROJECT_DIR/env/bin/python3"

# cd $PROJECT_DIR
# $PYTHON_BIN -m src.robots.punto_red
# /home/ubuntu/python/automatizaciones_escrutinio/env/bin/python3
PROD_PATH="/home/dia_anterior/automatizaciones_escrutinio"
PRUEBAS_PATH="/home/dia_actual/automatizaciones_escrutinio"

# 2. El script pregunta: ¿quién ejecuta? (prod corre como usuario dia_anterior)
if [ "$(whoami)" = "dia_anterior" ]; then
    PROJECT_DIR="$PROD_PATH"
    echo "Entorno detectado: PRODUCCIÓN"
else
    PROJECT_DIR="$PRUEBAS_PATH"
    echo "Entorno detectado: PRUEBAS"
fi

# 3. Configuramos el resto usando la variable detectada
PYTHON_BIN="$PROJECT_DIR/env/bin/python3"

# 4. Ejecución
# Este robot corre el navegador en modo headed (headless=False) para poder
# tomar capturas de pantalla reales del proceso.
#
# Si el usuario que ejecuta este script tiene una sesión gráfica real activa
# (ej. conectado por escritorio remoto/xrdp), se usa esa: así el navegador
# queda visible en esa pantalla. Como xrdp no mata la sesión al desconectarse
# (KillDisconnected=false), esa pantalla sigue viva aunque en este momento
# nadie esté conectado, y el navegador se abre igual ahí.
# Si no existe ninguna sesión gráfica del usuario (nunca se ha conectado por
# RDP), se usa una pantalla virtual con xvfb-run para que el proceso no falle
# por falta de display; los pantallazos de error se toman igual en ese caso.
cd "$PROJECT_DIR"

MI_DISPLAY=$(ps -u "$(whoami)" -o cmd= | grep -oP 'Xorg :\K[0-9]+' | head -1)

if [ -n "$MI_DISPLAY" ] && DISPLAY=":${MI_DISPLAY}.0" xdpyinfo >/dev/null 2>&1; then
    echo "Sesión gráfica real detectada en :$MI_DISPLAY, el navegador será visible ahí"
    export DISPLAY=":${MI_DISPLAY}.0"
    "$PYTHON_BIN" -m src.robots.programacion_loterias
else
    echo "No hay sesión gráfica activa para este usuario, se usa pantalla virtual (xvfb)"
    xvfb-run -a "$PYTHON_BIN" -m src.robots.programacion_loterias
fi
