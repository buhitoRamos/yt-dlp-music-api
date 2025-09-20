#!/bin/bash

# YT-DLP Music API Launcher v3.0
# Ejecuta directamente desde código fuente con todas las funcionalidades

echo "🎵 === YT-DLP Music API v3.0 Launcher ==="
echo "🚀 Ejecutando desde código fuente (más estable)"
echo ""

# Navegar al directorio de la aplicación
APP_DIR="/Users/O002545/Documents/martin/projects/yt-dlp-music-api"
cd "$APP_DIR" || {
    echo "❌ Error: No se pudo acceder al directorio de la aplicación"
    echo "📁 Directorio esperado: $APP_DIR"
    exit 1
}

echo "📁 Directorio de trabajo: $(pwd)"

# Verificar que Python3 está disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado o no está en PATH"
    echo "💡 Instala Python 3.9 o superior"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Verificar que el archivo principal existe
if [ ! -f "api_downloader.py" ]; then
    echo "❌ Error: api_downloader.py no encontrado en el directorio actual"
    ls -la *.py 2>/dev/null || echo "No hay archivos .py en este directorio"
    exit 1
fi

echo "✅ Script principal encontrado: api_downloader.py"

# Verificar dependencias básicas
echo "🔧 Verificando dependencias..."
python3 -c "import flask, flask_cors, yt_dlp" 2>/dev/null || {
    echo "⚠️ Algunas dependencias faltan. Instalando..."
    python3 -m pip install flask flask-cors yt-dlp
}

echo "✅ Dependencias verificadas"

# Verificar puerto 8080
if lsof -i:8080 &> /dev/null; then
    echo "⚠️ Puerto 8080 está ocupado. Cerrando procesos..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

echo "✅ Puerto 8080 disponible"

# Mensaje de inicio
echo ""
echo "🚀 Iniciando YT-DLP Music API v3.0..."
echo "📱 El navegador se abrirá automáticamente en http://localhost:8080"
echo "🛑 Para cerrar: usa el botón '🔌 Cerrar App' en la interfaz"
echo "⌨️ O presiona Ctrl+C en esta terminal"
echo ""

# Ejecutar la aplicación
exec python3 api_downloader.py