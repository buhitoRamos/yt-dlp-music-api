#!/bin/bash

# 🚀 YT-DLP Music API - Launcher Simple para macOS
# Desarrollado por Martin Gaston Lopez
# 
# Este script inicia automáticamente la aplicación YT-DLP Music API
# Funciona con doble clic desde Finder

# Obtener el directorio donde está este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Crear un nuevo Terminal y ejecutar la aplicación
osascript <<EOF
tell application "Terminal"
    activate
    do script "
        clear
        echo '╔══════════════════════════════════════════════════════╗'
        echo '║  🎵 YT-DLP Music API - Launcher para macOS          ║'
        echo '║     Desarrollado por Martin Gaston Lopez             ║'
        echo '╚══════════════════════════════════════════════════════╝'
        echo ''
        echo '🔄 Iniciando aplicación...'
        echo '📁 Directorio: $SCRIPT_DIR'
        echo ''
        cd '$SCRIPT_DIR'
        python3 launch_universal.py
        echo ''
        echo '🔚 La aplicación se ha cerrado.'
        echo '❌ Puedes cerrar esta ventana ahora.'
        echo ''
        read -p 'Presiona ENTER para cerrar...'
    "
end tell
EOF