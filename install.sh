#!/bin/bash

# Detener el script si ocurre cualquier error
set -e 

PYTHON_VERSION="3.10"
VENV_DIR="env"

echo "--- Verificando Python $PYTHON_VERSION y componentes ---"

# 1. Verificación mejorada: intentamos importar venv y ensurepip directamente
if ! python3.10 -c "import venv, ensurepip" &> /dev/null; then
    echo "(!) Falta el módulo venv o ensurepip (típico en Ubuntu/Debian)."
    echo "--- Instalando dependencias completas (requiere sudo) ---"
    sudo apt update
    sudo apt install -y python3.10 python3.10-venv python3.10-dev
else
    echo "(+) Python 3.10 y sus módulos están listos."
fi

# 2. Verificación de la carpeta del entorno virtual
# Si la carpeta existe pero no tiene el script 'activate', está rota.
if [ -d "$VENV_DIR" ] && [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "(!) Se detectó una carpeta '$VENV_DIR' incompleta. Eliminando para recrear..."
    rm -rf "$VENV_DIR"
fi

# 3. Crear entorno virtual si no existe
if [ ! -d "$VENV_DIR" ]; then
    echo "--- Creando entorno virtual en '$VENV_DIR'... ---"
    python3.10 -m venv $VENV_DIR
    echo "(+) Entorno creado exitosamente."
else
    echo "--- El entorno virtual ya existe y parece correcto. ---"
fi

echo "--- Activando entorno virtual... ---"
source $VENV_DIR/bin/activate

echo "--- Actualizando pip dentro del entorno... ---"
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "--- Instalando dependencias desde requirements.txt... ---"
    pip install -r requirements.txt
else
    echo "(!) requirements.txt no encontrado. Saltando."
fi

echo "--- Configuración finalizada con éxito ---"
echo "Para empezar, ejecuta:"
echo "   source $VENV_DIR/bin/activate"