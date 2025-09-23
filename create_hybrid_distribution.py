#!/usr/bin/env python3
"""
Script para crear distribución portátil con mayor compatibilidad para macOS
Crea versiones tanto compiladas como de código fuente
"""

import os
import sys
import urllib.request
import zipfile
import tarfile
import shutil
import stat
from pathlib import Path

def create_python_source_version():
    """Crear versión de código fuente Python como respaldo"""
    print("📦 Creando versión de código fuente Python...")
    
    source_dir = "YT-DLP-Source-by-buho"
    if os.path.exists(source_dir):
        shutil.rmtree(source_dir)
    
    os.makedirs(source_dir)
    
    # Copiar el código fuente principal
    shutil.copy2("api_downloader_simple.py", os.path.join(source_dir, "app.py"))
    
    # Crear requirements.txt
    requirements = """flask>=3.0.0
flask-cors>=4.0.0
"""
    with open(os.path.join(source_dir, "requirements.txt"), 'w') as f:
        f.write(requirements)
    
    # Crear script de instalación universal
    install_script = """#!/bin/bash
# Script de instalación universal para YT-DLP Music API
# powered by buh!to

echo "🎵 YT-DLP Music API - Instalación Universal"
echo "🦉 powered by buh!to"
echo "======================================"

# Detectar sistema operativo
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="Windows"
else
    OS="Desconocido"
fi

echo "Sistema detectado: $OS"

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python no está instalado"
    echo "Por favor instala Python 3.8+ desde https://python.org"
    exit 1
fi

echo "✅ Python encontrado: $($PYTHON_CMD --version)"

# Instalar dependencias
echo "📦 Instalando dependencias..."
$PYTHON_CMD -m pip install -r requirements.txt

# Instalar yt-dlp
echo "📥 Instalando yt-dlp..."
$PYTHON_CMD -m pip install yt-dlp

echo ""
echo "🎉 ¡Instalación completada!"
echo "🚀 Para ejecutar: $PYTHON_CMD app.py"
echo "🌐 Luego abre: http://localhost:8080"
"""
    
    install_file = os.path.join(source_dir, "install.sh")
    with open(install_file, 'w') as f:
        f.write(install_script)
    os.chmod(install_file, 0o755)
    
    # Script de ejecución
    run_script = """#!/bin/bash
cd "$(dirname "$0")"
echo "🎵 YT-DLP Music API - Iniciando..."
echo "🦉 powered by buh!to"
echo ""

if command -v python3 &> /dev/null; then
    python3 app.py
elif command -v python &> /dev/null; then
    python app.py
else
    echo "❌ Python no encontrado"
    echo "Ejecuta primero: ./install.sh"
fi
"""
    
    run_file = os.path.join(source_dir, "run.sh")
    with open(run_file, 'w') as f:
        f.write(run_script)
    os.chmod(run_file, 0o755)
    
    # Crear README para la versión fuente
    readme_source = """# 🎵 YT-DLP Music API - Versión Código Fuente
## powered by buh!to

Esta es la versión de código fuente Python, compatible con cualquier sistema que tenga Python 3.8+

## 🚀 Instalación Rápida

### Automática (Recomendada)
```bash
./install.sh
./run.sh
```

### Manual
```bash
# Instalar dependencias
pip install flask flask-cors yt-dlp

# Ejecutar
python3 app.py
```

## 🌐 Uso
1. Ejecuta la aplicación
2. Abre tu navegador en: http://localhost:8080
3. ¡Disfruta descargando música y videos!

## 📋 Requisitos
- Python 3.8 o superior
- Conexión a internet
- 50MB de espacio libre

## ✨ Ventajas de esta versión
- ✅ **Máxima compatibilidad**: Funciona en cualquier sistema con Python
- ✅ **Actualizaciones automáticas**: yt-dlp se mantiene actualizado
- ✅ **Menor tamaño**: Solo código fuente
- ✅ **Fácil modificación**: Código abierto

---
**Desarrollado con ❤️ por buh!to** 🦉
"""
    
    with open(os.path.join(source_dir, "README.md"), 'w') as f:
        f.write(readme_source)
    
    print(f"✅ Versión fuente creada en: {source_dir}/")
    return source_dir

def create_hybrid_distribution():
    """Crear distribución híbrida con ejecutable + código fuente"""
    print("🎵 Creando distribución híbrida YT-DLP Music API")
    print("🦉 powered by buh!to")
    print("=" * 60)
    
    # Crear directorio principal
    dist_name = "YT-DLP-Hybrid-by-buho"
    if os.path.exists(dist_name):
        shutil.rmtree(dist_name)
    
    os.makedirs(dist_name)
    
    # Crear versión de código fuente
    source_dir = create_python_source_version()
    
    # Mover la versión fuente al directorio híbrido
    shutil.move(source_dir, os.path.join(dist_name, "source-version"))
    
    # Copiar el ejecutable si existe
    executable_path = "dist/YT-DLP-Simple-Complete-BestQuality"
    if os.path.exists(executable_path):
        shutil.copy2(executable_path, os.path.join(dist_name, "YT-DLP-Simple-Complete-BestQuality"))
        os.chmod(os.path.join(dist_name, "YT-DLP-Simple-Complete-BestQuality"), 0o755)
        print("✅ Ejecutable copiado")
    
    # Crear scripts de lanzamiento inteligentes
    
    # macOS launcher que detecta compatibilidad
    macos_smart_launcher = """#!/bin/bash
cd "$(dirname "$0")"

echo "🎵 YT-DLP Music API - Iniciando..."
echo "🦉 powered by buh!to"
echo ""

# Intentar ejecutar versión compilada primero
if [ -f "./YT-DLP-Simple-Complete-BestQuality" ]; then
    echo "🚀 Intentando ejecutar versión compilada..."
    ./YT-DLP-Simple-Complete-BestQuality 2>/dev/null
    
    # Si falló, usar versión fuente
    if [ $? -ne 0 ]; then
        echo "⚠️  Versión compilada incompatible, usando código fuente..."
        echo "📦 Verificando dependencias..."
        
        cd source-version
        
        # Verificar si ya están instaladas las dependencias
        if python3 -c "import flask, flask_cors" 2>/dev/null; then
            echo "✅ Dependencias encontradas"
            python3 app.py
        else
            echo "📦 Instalando dependencias..."
            ./install.sh
            echo "🚀 Iniciando aplicación..."
            python3 app.py
        fi
    fi
else
    echo "🐍 Usando versión de código fuente Python..."
    cd source-version
    ./run.sh
fi
"""
    
    macos_file = os.path.join(dist_name, "🚀 Iniciar YT-DLP (macOS).command")
    with open(macos_file, 'w') as f:
        f.write(macos_smart_launcher)
    os.chmod(macos_file, 0o755)
    
    # README híbrido
    hybrid_readme = """# 🎵 YT-DLP Music API - Distribución Híbrida
## powered by buh!to

Esta distribución incluye **DOS VERSIONES** para máxima compatibilidad:

## 🚀 Uso Automático (Recomendado)

### macOS
1. Ejecuta: `🚀 Iniciar YT-DLP (macOS).command`
2. El sistema automáticamente elegirá la mejor versión
3. Abre tu navegador en: http://localhost:8080

**El launcher automáticamente:**
- ✅ Intenta la versión compilada (más rápida)
- ✅ Si falla, usa la versión Python (más compatible)
- ✅ Instala dependencias si es necesario

## 📦 Versiones Incluidas

### 1. Versión Compilada (Rápida)
- **Archivo**: `YT-DLP-Simple-Complete-BestQuality`
- **Ventajas**: Inicio inmediato, no necesita Python
- **Limitación**: Solo para macOS 10.15+ (Catalina o superior)

### 2. Versión Código Fuente (Compatible)
- **Carpeta**: `source-version/`
- **Ventajas**: Funciona en cualquier macOS con Python 3.8+
- **Requisito**: Necesita Python instalado

## 🔧 Uso Manual

### Si prefieres la versión compilada:
```bash
./YT-DLP-Simple-Complete-BestQuality
```

### Si prefieres la versión Python:
```bash
cd source-version
./install.sh  # Solo la primera vez
./run.sh
```

## 📱 Características

- ✅ **Audio MP3**: Calidad máxima con carátulas
- ✅ **Videos MP4**: Hasta 1080p con subtítulos
- ✅ **Playlists completas**: Audio y video
- ✅ **YouTube Shorts**: Soporte incluido
- ✅ **Multiplataforma**: Windows, macOS, Linux
- ✅ **Sin instalaciones**: Todo incluido o auto-instalación

## 🆘 Solución de Problemas

### Si la versión compilada no funciona:
- Tu macOS es anterior a 10.15 (Catalina)
- Usa la versión de código fuente: `cd source-version && ./run.sh`

### Si la versión Python no funciona:
- Instala Python desde: https://python.org
- Ejecuta: `cd source-version && ./install.sh`

---
**Desarrollado con ❤️ por buh!to** 🦉

¡Disfruta descargando música y videos! 🎵🎬
"""
    
    with open(os.path.join(dist_name, "README.md"), 'w') as f:
        f.write(hybrid_readme)
    
    # Crear ZIP
    zip_name = f"{dist_name}.zip"
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_name):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, dist_name)
                zipf.write(file_path, arc_path)
    
    zip_size = os.path.getsize(zip_name) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print("🎉 ¡Distribución híbrida creada exitosamente!")
    print(f"📦 Archivo: {zip_name} ({zip_size:.1f} MB)")
    print(f"📁 Carpeta: {dist_name}/")
    print("\n✨ Características:")
    print("   ✅ Doble compatibilidad (compilado + fuente)")
    print("   ✅ Auto-detección de mejor versión")
    print("   ✅ Funciona en macOS viejos y nuevos")
    print("   ✅ Auto-instalación de dependencias")
    print("   ✅ README con instrucciones completas")
    print("\n🚀 Esta versión funcionará en CUALQUIER Mac!")
    print("=" * 60)

if __name__ == "__main__":
    create_hybrid_distribution()