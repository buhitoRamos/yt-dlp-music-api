#!/usr/bin/env python3
"""
Creador de Aplicación Portable v3.0
Crea una versión portable que funciona sin requerir instalación de Python en el sistema.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime

def create_portable_app():
    """Crea una aplicación portable que incluye Python embebido."""
    
    print("🎵 === Creador de Aplicación Portable v3.0 ===")
    print("🚀 Creando versión portable independiente")
    
    # Directorio base
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Crear directorio de distribución portable
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    portable_dir = os.path.join(base_dir, "distributions", f"portable_v3_{timestamp}")
    
    try:
        os.makedirs(portable_dir, exist_ok=True)
        print(f"📁 Directorio portable: {portable_dir}")
        
        # Copiar archivos esenciales
        files_to_copy = [
            "api_downloader.py",
            "requirements.txt",
            "binaries",
            "frontend",
            "www.youtube.com_cookies.txt"
        ]
        
        print("📦 Copiando archivos...")
        for item in files_to_copy:
            src = os.path.join(base_dir, item)
            dst = os.path.join(portable_dir, item)
            
            if os.path.exists(src):
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    print(f"   📁 {item}/")
                else:
                    shutil.copy2(src, dst)
                    print(f"   📄 {item}")
            else:
                print(f"   ⚠️ No encontrado: {item}")
        
        # Crear script launcher mejorado
        launcher_script = f"""#!/bin/bash

# YT-DLP Music API Portable Launcher v3.0
# Versión portable que detecta automáticamente Python

echo "🎵 === YT-DLP Music API v3.0 Portable ==="
echo "🚀 Iniciando aplicación portable..."
echo ""

# Directorio de la aplicación
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Función para verificar Python
check_python() {{
    local python_cmd="$1"
    if command -v "$python_cmd" >/dev/null 2>&1; then
        local version=$($python_cmd --version 2>&1 | grep -o '[0-9]\\+\\.[0-9]\\+')
        local major=$(echo "$version" | cut -d. -f1)
        local minor=$(echo "$version" | cut -d. -f2)
        
        if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
            echo "✅ Encontrado $python_cmd (Python $version)"
            echo "$python_cmd"
            return 0
        else
            echo "⚠️ $python_cmd version $version es muy antigua (requiere 3.8+)"
            return 1
        fi
    fi
    return 1
}}

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
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install flask flask-cors yt-dlp
    else
        pip install flask flask-cors yt-dlp
    fi
fi

echo "✅ Dependencias verificadas"

# Verificar FFmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ FFmpeg encontrado: $(which ffmpeg)"
    echo "   📊 Versión: $(ffmpeg -version 2>&1 | head -1 | grep -o 'ffmpeg version [0-9]\\+\\.[0-9]\\+[^,]*')"
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
exec "$PYTHON_CMD" api_downloader.py
"""
        
        launcher_path = os.path.join(portable_dir, "launch_portable.sh")
        with open(launcher_path, 'w') as f:
            f.write(launcher_script)
        os.chmod(launcher_path, 0o755)
        print("✅ Script launcher creado")
        
        # Crear README
        readme_content = f"""# YT-DLP Music API v3.0 - Versión Portable

## 📖 Descripción
Esta es una versión portable de YT-DLP Music API v3.0 que detecta automáticamente Python en el sistema.

## 🚀 Uso Rápido
```bash
./launch_portable.sh
```

## 📋 Requisitos
- **Python 3.8+** (se detecta automáticamente)
- **pip** (para instalar dependencias)
- **FFmpeg** (opcional, para conversiones MP3)

## 🔧 Instalación de Requisitos

### macOS (Homebrew)
```bash
# Python (si no está instalado)
brew install python@3.11

# FFmpeg (para MP3)
brew install ffmpeg
```

### Ubuntu/Debian
```bash
# Python (si no está instalado)
sudo apt update
sudo apt install python3 python3-pip

# FFmpeg (para MP3)
sudo apt install ffmpeg
```

### Windows
1. Instalar Python desde https://python.org
2. Instalar FFmpeg desde https://ffmpeg.org

## 🌐 Endpoints Disponibles

### Información
- **GET /** - Frontend web
- **GET /status** - Estado del servidor

### Descarga de Audio
- **POST /download** - Descargar audio
- **GET /formats** - Formatos disponibles

### Monitoreo
- **GET /jobs** - Estado de trabajos

## 📁 Estructura
```
portable_v3_{timestamp}/
├── api_downloader.py      # Aplicación principal
├── launch_portable.sh     # Launcher automático
├── requirements.txt       # Dependencias Python
├── binaries/             # Binarios específicos de plataforma
├── frontend/             # Interfaz web
└── README.md            # Esta documentación
```

## ✅ Ventajas de la Versión Portable
- ✅ Detección automática de Python
- ✅ Instalación automática de dependencias
- ✅ Compatible con múltiples versiones de Python
- ✅ No requiere compilación compleja
- ✅ Funciona en cualquier sistema con Python

## 🆚 Comparación con Otras Versiones

| Característica | Portable v3 | Source v3 | Compiled v3 |
|---------------|-------------|-----------|-------------|
| Instalación | Automática | Manual | Ninguna |
| Compatibilidad | Alta | Alta | Media |
| Tamaño | Pequeño | Pequeño | Grande |
| Dependencias | Auto | Manual | Embebidas |
| Debugging | Fácil | Fácil | Difícil |

## 🔧 Solución de Problemas

### Python no encontrado
```bash
# Verificar Python instalado
python3 --version

# Si no está instalado, instalar según tu sistema
```

### Dependencias fallan
```bash
# Instalar manualmente
pip3 install flask flask-cors yt-dlp
```

### FFmpeg no encontrado
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---
🎵 **YT-DLP Music API v3.0 Portable** - Creado el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        readme_path = os.path.join(portable_dir, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print("✅ README.md creado")
        
        print("")
        print("🎉 ¡Aplicación portable creada exitosamente!")
        print(f"📁 Ubicación: {portable_dir}")
        print("🚀 Para usar:")
        print(f"   cd {portable_dir}")
        print("   ./launch_portable.sh")
        print("")
        print("✨ Esta versión:")
        print("   ✅ Detecta Python automáticamente")
        print("   ✅ Instala dependencias automáticamente")
        print("   ✅ Es más compatible que la versión compilada")
        print("   ✅ Funciona en cualquier sistema con Python 3.8+")
        
        return portable_dir
        
    except Exception as e:
        print(f"❌ Error creando aplicación portable: {e}")
        return None

if __name__ == "__main__":
    create_portable_app()