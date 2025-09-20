#!/bin/bash

# YT-DLP Music API Portable Launcher v3.0
# Versión portable que detecta automáticamente Python

echo "🎵 === YT-DLP Music API v3.0 Portable ==="
echo "🚀 Iniciando aplicación portable..."
echo ""

# Directorio de la aplicación
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Función para verificar Python
check_python() {
    local python_cmd="$1"
    if command -v "$python_cmd" >/dev/null 2>&1; then
        local version=$($python_cmd --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
        local major=$(echo "$version" | cut -d. -f1)
        local minor=$(echo "$version" | cut -d. -f2)
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
            echo "✅ Encontrado $python_cmd (Python $version)" >&2
            echo "$python_cmd"
            return 0
        else
            echo "⚠️ $python_cmd version $version es muy antigua (requiere 3.8+)" >&2
            return 1
        fi
    fi
    return 1
}

# Buscar Python disponible
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
    if PYTHON_CMD=$(check_python "$cmd"); then
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Error: No se encontró Python 3.8+ en el sistema"
    echo "💡 Por favor instala Python 3.8 o superior desde https://python.org"
    echo "💡 O usa la distribución source_v3 que funciona perfectamente"
    exit 1
fi

echo "🔧 Verificando dependencias..."

# Verificar pip
if ! command -v pip3 >/dev/null 2>&1 && ! command -v pip >/dev/null 2>&1; then
    echo "❌ Error: pip no está disponible"
    echo "💡 Instala pip o usa la distribución source_v3"
    exit 1
fi

# Instalar dependencias si no están disponibles
if ! $PYTHON_CMD -c "import flask, flask_cors, yt_dlp" 2>/dev/null; then
    echo "📦 Instalando dependencias requeridas..."
    
    # Crear entorno virtual si no existe
    if [ ! -d ".venv" ]; then
        echo "🔧 Creando entorno virtual..."
        $PYTHON_CMD -m venv .venv
    fi
    
    # Activar entorno virtual
    source .venv/bin/activate
    
    # Actualizar pip en el entorno virtual
    python -m pip install --upgrade pip
    
    # Instalar dependencias en el entorno virtual
    pip install flask flask-cors yt-dlp
    
    echo "✅ Dependencias instaladas en entorno virtual"
    
    # El entorno virtual permanece activo para el resto del script
else
    echo "✅ Dependencias ya disponibles"
fi

# Verificar FFmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ FFmpeg encontrado: $(which ffmpeg)"
    echo "   📊 Versión: $(ffmpeg -version 2>&1 | head -1 | grep -o 'ffmpeg version [0-9]\+\.[0-9]\+[^,]*')"
else
    echo "⚠️ FFmpeg no encontrado - conversiones MP3 limitadas"
    echo "💡 Instalar: brew install ffmpeg (macOS) o apt install ffmpeg (Linux)"
fi

echo ""
echo "🚀 Iniciando servidor..."
echo "🌐 Servidor estará disponible en: http://localhost:8080"
echo "📱 Frontend: http://localhost:8080"
echo ""
echo "⏹️ Presiona Ctrl+C para detener"
echo ""

# Ejecutar la aplicación
if [ -d ".venv" ]; then
    # Si hay entorno virtual, asegurarse que esté activo
    source .venv/bin/activate
    exec python api_downloader.py
else
    # Usar el Python detectado directamente
    exec "$PYTHON_CMD" api_downloader.py
fi
