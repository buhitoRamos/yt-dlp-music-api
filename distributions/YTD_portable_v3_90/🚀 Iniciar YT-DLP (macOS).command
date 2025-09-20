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
        
        # Verificar que Python esté disponible
        if ! command -v python3 >/dev/null 2>&1; then
            echo '❌ Error: Python3 no está instalado'
            echo '💡 Instala Python desde: https://python.org'
            read -p 'Presiona ENTER para cerrar...'
            exit 1
        fi
        
        # Verificar que los archivos necesarios existan
        if [ ! -f 'launch_universal.py' ]; then
            echo '❌ Error: No se encontró launch_universal.py'
            echo '� Asegúrate de que todos los archivos estén presentes'
            read -p 'Presiona ENTER para cerrar...'
            exit 1
        fi
        
        # Ejecutar la aplicación con manejo de errores mejorado
        echo '🚀 Ejecutando launcher universal...'
        python3 launch_universal.py
        
        EXIT_CODE=\$?
        echo ''
        if [ \$EXIT_CODE -eq 0 ]; then
            echo '✅ La aplicación se cerró correctamente'
        else
            echo '❌ La aplicación terminó con errores (código: '\$EXIT_CODE')'
            echo '💡 Esto puede ser normal si cerraste la aplicación manualmente'
        fi
        echo ''
        echo '🔚 Puedes cerrar esta ventana ahora.'
        echo ''
        read -p 'Presiona ENTER para cerrar...'
    "
end tell
EOF