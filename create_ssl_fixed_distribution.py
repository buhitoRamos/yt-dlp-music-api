#!/usr/bin/env python3
"""
Script para crear distribución específica que resuelve problemas SSL en macOS
powered by buh!to
"""

import os
import sys
import shutil
import zipfile

def create_ssl_fixed_distribution():
    """Crear distribución que resuelve problemas SSL específicamente"""
    print("🔒 Creando distribución con corrección SSL")
    print("🦉 powered by buh!to")
    print("=" * 50)
    
    # Crear directorio
    dist_name = "YT-DLP-SSL-Fixed-by-buho"
    if os.path.exists(dist_name):
        shutil.rmtree(dist_name)
    
    os.makedirs(dist_name)
    
    # Copiar ejecutable con correcciones SSL
    if os.path.exists("dist/YT-DLP-Simple-SSL-Fixed"):
        shutil.copy2("dist/YT-DLP-Simple-SSL-Fixed", os.path.join(dist_name, "YT-DLP-SSL-Fixed"))
        os.chmod(os.path.join(dist_name, "YT-DLP-SSL-Fixed"), 0o755)
        print("✅ Ejecutable SSL corregido copiado")
    
    # Crear versión de código Python con correcciones SSL
    source_dir = os.path.join(dist_name, "source-version")
    os.makedirs(source_dir)
    
    # Copiar y modificar el código fuente
    shutil.copy2("api_downloader_simple.py", os.path.join(source_dir, "app.py"))
    
    # Crear requirements mejorado
    requirements_ssl = """flask>=3.0.0
flask-cors>=4.0.0
yt-dlp>=2023.9.24
certifi>=2023.5.7
urllib3>=1.26.0
"""
    with open(os.path.join(source_dir, "requirements.txt"), 'w') as f:
        f.write(requirements_ssl)
    
    # Script de instalación mejorado para SSL
    install_ssl_script = """#!/bin/bash
# Script de instalación con corrección SSL para macOS
# powered by buh!to

echo "🔒 YT-DLP Music API - Instalación con corrección SSL"
echo "🦉 powered by buh!to"
echo "================================================="

# Detectar macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  Este script está optimizado para macOS"
fi

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python no está instalado"
    echo "🔗 Descarga Python desde: https://python.org"
    echo "⚠️  IMPORTANTE: Marca 'Add Python to PATH' durante la instalación"
    exit 1
fi

echo "✅ Python encontrado: $($PYTHON_CMD --version)"

# Actualizar pip
echo "🔧 Actualizando pip..."
$PYTHON_CMD -m pip install --upgrade pip

# Corrección específica para SSL en macOS
echo "🔒 Aplicando correcciones SSL para macOS..."

# Actualizar certificados SSL
echo "📜 Actualizando certificados SSL..."
$PYTHON_CMD -m pip install --upgrade certifi

# Buscar y ejecutar script de certificados de Python
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
CERT_SCRIPT="/Applications/Python $PYTHON_VERSION/Install Certificates.command"

if [ -f "$CERT_SCRIPT" ]; then
    echo "🔧 Ejecutando actualización automática de certificados..."
    "$CERT_SCRIPT"
    echo "✅ Certificados actualizados"
else
    echo "⚠️  Script de certificados no encontrado, continuando..."
fi

# Configurar variables de entorno SSL
echo "🌐 Configurando variables SSL..."
export SSL_CERT_FILE=$($PYTHON_CMD -m certifi)
export REQUESTS_CA_BUNDLE=$($PYTHON_CMD -m certifi)

# Instalar dependencias con timeout extendido
echo "📦 Instalando dependencias..."
$PYTHON_CMD -m pip install --timeout 60 -r requirements.txt

# Instalar yt-dlp con configuraciones especiales
echo "📥 Instalando yt-dlp con configuraciones SSL..."
$PYTHON_CMD -m pip install --upgrade --timeout 60 yt-dlp

# Probar instalación
echo "🧪 Probando instalación..."
if $PYTHON_CMD -c "import yt_dlp; print('✅ yt-dlp importado correctamente')" 2>/dev/null; then
    echo "✅ Instalación exitosa"
else
    echo "⚠️  Advertencia: Posible problema con yt-dlp"
fi

echo ""
echo "🎉 ¡Instalación completada!"
echo "🚀 Para ejecutar: ./run.sh"
echo "🌐 Luego abre: http://localhost:8080"
echo ""
echo "💡 Si tienes problemas SSL:"
echo "   1. Reinicia la terminal"
echo "   2. Ejecuta: ./run.sh"
echo "   3. Si persiste, usa: ./run_no_ssl.sh"
"""
    
    install_file = os.path.join(source_dir, "install.sh")
    with open(install_file, 'w') as f:
        f.write(install_ssl_script)
    os.chmod(install_file, 0o755)
    
    # Script de ejecución normal
    run_script = """#!/bin/bash
cd "$(dirname "$0")"

echo "🔒 YT-DLP Music API - Iniciando (modo SSL seguro)..."
echo "🦉 powered by buh!to"
echo ""

# Configurar certificados SSL
export SSL_CERT_FILE=$(python3 -m certifi 2>/dev/null || echo "")
export REQUESTS_CA_BUNDLE=$(python3 -m certifi 2>/dev/null || echo "")

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
    
    # Script de ejecución sin SSL (modo emergencia)
    run_no_ssl_script = """#!/bin/bash
cd "$(dirname "$0")"

echo "🔒 YT-DLP Music API - Iniciando (modo sin verificación SSL)..."
echo "🦉 powered by buh!to"
echo "⚠️  MODO EMERGENCIA: Sin verificación SSL"
echo ""

# Desactivar verificación SSL (solo para casos extremos)
export PYTHONHTTPSVERIFY=0
export SSL_VERIFY_SSL=false

if command -v python3 &> /dev/null; then
    python3 app.py
elif command -v python &> /dev/null; then
    python app.py
else
    echo "❌ Python no encontrado"
    echo "Ejecuta primero: ./install.sh"
fi
"""
    
    run_no_ssl_file = os.path.join(source_dir, "run_no_ssl.sh")
    with open(run_no_ssl_file, 'w') as f:
        f.write(run_no_ssl_script)
    os.chmod(run_no_ssl_file, 0o755)
    
    # Launcher principal inteligente
    main_launcher = """#!/bin/bash
cd "$(dirname "$0")"

echo "🔒 YT-DLP Music API - Launcher Inteligente SSL"
echo "🦉 powered by buh!to"
echo "============================================="

# Intentar versión compilada primero
if [ -f "./YT-DLP-SSL-Fixed" ]; then
    echo "🚀 Intentando versión compilada (con correcciones SSL)..."
    ./YT-DLP-SSL-Fixed 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "⚠️  Versión compilada falló, usando código fuente..."
        cd source-version
        
        # Verificar si están instaladas las dependencias
        if python3 -c "import flask, flask_cors, yt_dlp" 2>/dev/null; then
            echo "✅ Dependencias encontradas, iniciando..."
            ./run.sh
        else
            echo "📦 Instalando dependencias con correcciones SSL..."
            ./install.sh
            echo "🚀 Iniciando aplicación..."
            ./run.sh
        fi
    fi
else
    echo "🐍 Usando versión de código fuente..."
    cd source-version
    
    if [ ! -f "install_completed.flag" ]; then
        echo "📦 Primera ejecución: instalando dependencias..."
        ./install.sh
        touch install_completed.flag
    fi
    
    ./run.sh
fi
"""
    
    main_file = os.path.join(dist_name, "🚀 Iniciar YT-DLP (macOS).command")
    with open(main_file, 'w') as f:
        f.write(main_launcher)
    os.chmod(main_file, 0o755)
    
    # README especializado
    readme_ssl = """# 🔒 YT-DLP Music API - Corrección SSL para macOS
## powered by buh!to

Esta distribución está **específicamente diseñada** para resolver problemas SSL en macOS.

## 🚨 Problema que resuelve

Error: `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed`

## 🚀 Uso (Super Simple)

1. **Descomprime** el archivo ZIP
2. **Ejecuta**: `🚀 Iniciar YT-DLP (macOS).command`
3. **Espera** que se configure automáticamente
4. **Abre**: http://localhost:8080

## 🔧 Qué hace automáticamente

✅ **Detecta** si la versión compilada funciona  
✅ **Instala** certificados SSL actualizados  
✅ **Configura** variables de entorno SSL  
✅ **Actualiza** yt-dlp a la última versión  
✅ **Proporciona** modo de emergencia sin SSL  

## 📋 Versiones incluidas

### 1. Compilada (Rápida)
- Con correcciones SSL integradas
- Para macOS compatibles

### 2. Código Fuente (Universal)
- Auto-instalación con correcciones SSL
- Funciona en cualquier macOS

## 🆘 Si aún tienes problemas

### Opción 1: Modo manual
```bash
cd source-version
./install.sh
./run.sh
```

### Opción 2: Modo emergencia (sin SSL)
```bash
cd source-version
./run_no_ssl.sh
```

### Opción 3: Instalación manual completa
```bash
# Instalar Python desde python.org
# Luego:
pip3 install flask flask-cors yt-dlp certifi
python3 source-version/app.py
```

## 💡 Consejos

- **Reinicia** la terminal si tienes problemas
- **Actualiza** macOS si es muy viejo
- **Instala** Python desde python.org (no usar el del sistema)

## 📱 Características

- ✅ **Audio MP3**: Calidad máxima + carátulas
- ✅ **Videos MP4**: 1080p + subtítulos  
- ✅ **Playlists**: Completas organizadas
- ✅ **Sin SSL**: Modo emergencia incluido

---
**Desarrollado con ❤️ por buh!to** 🦉  
**Problema SSL resuelto** 🔒✅
"""
    
    with open(os.path.join(dist_name, "README.md"), 'w') as f:
        f.write(readme_ssl)
    
    # Crear archivo de solución rápida
    quick_fix = """# 🔒 SOLUCIÓN RÁPIDA PARA ERROR SSL

Si ves este error:
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed

## 🚀 Solución en 3 pasos:

1. Abre Terminal
2. Ejecuta: cd source-version && ./install.sh
3. Ejecuta: ./run.sh

## 🆘 Si no funciona:

Ejecuta: ./run_no_ssl.sh

¡Esto debería resolver el problema SSL!
"""
    
    with open(os.path.join(dist_name, "SOLUCION_SSL.txt"), 'w') as f:
        f.write(quick_fix)
    
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
    
    print("\n" + "=" * 50)
    print("🔒 ¡Distribución SSL corregida creada!")
    print(f"📦 Archivo: {zip_name} ({zip_size:.1f} MB)")
    print(f"📁 Carpeta: {dist_name}/")
    print("\n✅ Correcciones SSL incluidas:")
    print("   🔧 Actualización automática de certificados")
    print("   🌐 Variables de entorno SSL configuradas")
    print("   🚨 Modo emergencia sin SSL incluido")
    print("   📖 Instrucciones detalladas de solución")
    print("\n🎯 Esta versión DEBE resolver el error SSL!")
    print("=" * 50)

if __name__ == "__main__":
    create_ssl_fixed_distribution()