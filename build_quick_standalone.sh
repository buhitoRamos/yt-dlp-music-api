#!/bin/bash
# -*- coding: utf-8 -*-
"""
Construcción rápida de versión standalone para la plataforma actual
"""

# Configurar Python y dependencias
echo "🔧 Instalando PyInstaller y dependencias..."
pip install pyinstaller flask flask-cors yt-dlp beepy

# Verificar que los binarios existen
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    PLATFORM="darwin"
    if [ ! -f "binaries/darwin/ffmpeg" ] || [ ! -f "binaries/darwin/yt-dlp" ]; then
        echo "❌ Binarios de macOS no encontrados en binaries/darwin/"
        echo "💡 Descarga ffmpeg y yt-dlp para macOS"
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    PLATFORM="windows"
    if [ ! -f "binaries/windows/ffmpeg.exe" ] || [ ! -f "binaries/windows/yt-dlp.exe" ]; then
        echo "❌ Binarios de Windows no encontrados en binaries/windows/"
        echo "💡 Descarga ffmpeg.exe y yt-dlp.exe para Windows"
        exit 1
    fi
else
    echo "❌ Plataforma no soportada: $OSTYPE"
    exit 1
fi

echo "✅ Binarios encontrados para $PLATFORM"

# Construir con PyInstaller
echo "🔨 Construyendo ejecutable standalone..."

pyinstaller --onefile \
    --name "YT-DLP-Music-API-v4" \
    --add-data "frontend:frontend" \
    --add-data "binaries:binaries" \
    --add-data "www.youtube.com_cookies.txt:." \
    --hidden-import "flask" \
    --hidden-import "flask_cors" \
    --hidden-import "subprocess" \
    --hidden-import "json" \
    --hidden-import "tempfile" \
    --hidden-import "threading" \
    --hidden-import "webbrowser" \
    --hidden-import "urllib.request" \
    --hidden-import "urllib.parse" \
    --hidden-import "http.server" \
    --hidden-import "socketserver" \
    --clean \
    --noconfirm \
    api_downloader_standalone.py

if [ $? -eq 0 ]; then
    echo "✅ Construcción exitosa!"
    
    # Crear paquete final
    DIST_DIR="dist_standalone_v4"
    mkdir -p "$DIST_DIR"
    
    if [[ "$PLATFORM" == "darwin" ]]; then
        cp "dist/YT-DLP-Music-API-v4" "$DIST_DIR/"
        chmod +x "$DIST_DIR/YT-DLP-Music-API-v4"
        EXE_SIZE=$(du -m "dist/YT-DLP-Music-API-v4" | cut -f1)
    else
        cp "dist/YT-DLP-Music-API-v4.exe" "$DIST_DIR/"
        EXE_SIZE=$(du -m "dist/YT-DLP-Music-API-v4.exe" | cut -f1)
    fi
    
    # Crear README
    cat > "$DIST_DIR/README.md" << 'EOF'
# 🎵 YT-DLP Music API - Standalone v4.0

## 🎯 ¿Qué es esto?
Una aplicación **completamente autocontenida** para descargar música y videos de YouTube.
**NO NECESITAS INSTALAR PYTHON NI DEPENDENCIAS** - ¡Todo está incluido!

## 🚀 ¿Cómo usar? (SÚPER FÁCIL)

### 🪟 **Windows:**
1. Haz **doble clic** en `YT-DLP-Music-API-v4.exe`
2. Espera unos segundos
3. Se abrirá automáticamente en tu navegador
4. ¡Listo para descargar!

### 🍎 **macOS:**
1. Haz **doble clic** en `YT-DLP-Music-API-v4`
2. Si aparece advertencia de seguridad:
   - Ve a "Preferencias del Sistema" → "Seguridad y Privacidad"
   - Haz clic en "Abrir de todas formas"
3. Se abrirá automáticamente en tu navegador
4. ¡Listo para descargar!

## ✨ Características
- 🎵 Descarga música en MP3
- 🎬 Descarga videos en MP4
- 🎼 Listas de reproducción completas
- 🔥 YouTube Shorts
- 🌐 Interfaz web fácil de usar
- 📱 Compatible con YouTube Music

## 👨‍💻 Desarrollado por
**Martin Gaston Lopez**

---
**Versión Standalone v4.0 - No requiere instalaciones adicionales**
EOF
    
    echo "📦 Paquete creado en: $DIST_DIR"
    echo "📁 Tamaño del ejecutable: ${EXE_SIZE}MB"
    echo "🎉 ¡Listo para distribución!"
    
else
    echo "❌ Error en la construcción"
    exit 1
fi