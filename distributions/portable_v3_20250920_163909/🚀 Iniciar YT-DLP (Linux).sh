#!/bin/bash

# 🚀 YT-DLP Music API - Launcher para Linux
# Desarrollado por Martin Gaston Lopez
# 
# Este script inicia automáticamente la aplicación YT-DLP Music API
# No necesitas conocimientos técnicos, solo haz doble clic!

# Configuración de colores para mejor experiencia visual
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin color

# Función para mostrar mensajes con colores
show_message() {
    echo -e "${2}${1}${NC}"
}

# Función para mostrar el banner de inicio
show_banner() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}          ${CYAN}🎵 YT-DLP Music API - Descargador de YouTube${NC}          ${PURPLE}║${NC}"
    echo -e "${PURPLE}║${NC}                 ${YELLOW}Desarrollado por Martin Gaston Lopez${NC}                ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Función para pausar y esperar que el usuario presione Enter
pause_for_user() {
    echo ""
    echo -e "${CYAN}Presiona ENTER para continuar...${NC}"
    read -r
}

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Función para mostrar error y salir
show_error_and_exit() {
    show_message "❌ ERROR: $1" "$RED"
    echo ""
    show_message "💡 SOLUCIÓN:" "$YELLOW"
    echo -e "   Instala Python desde: ${CYAN}https://python.org/downloads/${NC}"
    echo -e "   O usa el gestor de paquetes de tu distribución:"
    echo -e "   ${CYAN}• Ubuntu/Debian: sudo apt install python3 python3-pip${NC}"
    echo -e "   ${CYAN}• Fedora: sudo dnf install python3 python3-pip${NC}"
    echo -e "   ${CYAN}• Arch: sudo pacman -S python python-pip${NC}"
    echo ""
    pause_for_user
    exit 1
}

# Función principal
main() {
    show_banner
    
    show_message "🔍 Verificando sistema..." "$BLUE"
    
    # Verificar si Python está instalado
    if command_exists python3; then
        PYTHON_CMD="python3"
        show_message "✅ Python3 encontrado" "$GREEN"
    elif command_exists python; then
        PYTHON_CMD="python"
        # Verificar que sea Python 3
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
        if [[ $PYTHON_VERSION == *"Python 3"* ]]; then
            show_message "✅ Python encontrado" "$GREEN"
        else
            show_error_and_exit "Necesitas Python 3.8 o superior. Encontrado: $PYTHON_VERSION"
        fi
    else
        show_error_and_exit "Python no está instalado en tu sistema"
    fi
    
    # Verificar versión de Python
    PYTHON_VERSION_FULL=$($PYTHON_CMD --version 2>&1)
    show_message "📋 Versión: $PYTHON_VERSION_FULL" "$CYAN"
    
    # Cambiar al directorio del script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR" || {
        show_message "❌ No se pudo cambiar al directorio del script" "$RED"
        pause_for_user
        exit 1
    }
    
    show_message "📁 Directorio de trabajo: $SCRIPT_DIR" "$CYAN"
    echo ""
    
    # Verificar si existe el launcher universal
    if [ ! -f "launch_universal.py" ]; then
        show_message "❌ ERROR: No se encontró launch_universal.py" "$RED"
        show_message "Asegúrate de que todos los archivos estén en la misma carpeta" "$YELLOW"
        pause_for_user
        exit 1
    fi
    
    show_message "🚀 Iniciando YT-DLP Music API..." "$GREEN"
    show_message "⏳ Configurando entorno automáticamente..." "$YELLOW"
    echo ""
    
    # Ejecutar el launcher universal
    $PYTHON_CMD launch_universal.py
    
    # Verificar el código de salida
    EXIT_CODE=$?
    
    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        show_message "✅ La aplicación se cerró correctamente" "$GREEN"
    else
        show_message "❌ La aplicación se cerró con errores (código: $EXIT_CODE)" "$RED"
        show_message "💡 Esto puede ser normal si cerraste la aplicación manualmente" "$YELLOW"
    fi
    
    echo ""
    show_message "🔚 ¡Gracias por usar YT-DLP Music API!" "$PURPLE"
    echo ""
    pause_for_user
}

# Ejecutar la función principal
main "$@"