#!/usr/bin/env python3
"""
YT-DLP Music API - Universal Portable Launcher v3.0
Compatible con Windows, macOS y Linux
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def detect_python():
    """Detecta la mejor versión de Python disponible."""
    candidates = []
    
    if platform.system() == "Windows":
        # Windows: python, py, python3
        candidates = ["python", "py", "python3"]
    else:
        # Unix/macOS: python3.x, python3, python
        candidates = ["python3.12", "python3.11", "python3.10", "python3.9", "python3", "python"]
    
    for cmd in candidates:
        try:
            if shutil.which(cmd):
                result = subprocess.run([cmd, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    # Extraer número de versión
                    import re
                    version_match = re.search(r'(\d+)\.(\d+)', version_str)
                    if version_match:
                        major, minor = map(int, version_match.groups())
                        if major == 3 and minor >= 8:
                            print(f"✅ Encontrado {cmd} ({version_str})")
                            return cmd
                        else:
                            print(f"⚠️ {cmd} versión {major}.{minor} muy antigua (requiere 3.8+)")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            continue
    
    return None

def setup_virtual_env(python_cmd):
    """Configura el entorno virtual."""
    venv_path = Path(".venv")
    
    if not venv_path.exists():
        print("🔧 Creando entorno virtual...")
        result = subprocess.run([python_cmd, "-m", "venv", ".venv"])
        if result.returncode != 0:
            print("❌ Error creando entorno virtual")
            return False
    
    # Determinar el ejecutable de Python en el venv
    if platform.system() == "Windows":
        python_venv = venv_path / "Scripts" / "python.exe"
        pip_venv = venv_path / "Scripts" / "pip.exe"
    else:
        python_venv = venv_path / "bin" / "python"
        pip_venv = venv_path / "bin" / "pip"
    
    if not python_venv.exists():
        print("❌ Error: No se pudo crear el entorno virtual correctamente")
        return False
    
    return str(python_venv), str(pip_venv)

def install_dependencies(pip_cmd):
    """Instala las dependencias necesarias."""
    dependencies = ["flask", "flask-cors", "yt-dlp"]
    
    print("📦 Verificando dependencias...")
    
    # Verificar si ya están instaladas
    try:
        result = subprocess.run([pip_cmd, "show"] + dependencies, 
                              capture_output=True, text=True)
        if "Name:" in result.stdout:
            print("✅ Dependencias ya instaladas")
            return True
    except:
        pass
    
    print("📦 Instalando dependencias requeridas...")
    
    # Actualizar pip primero
    subprocess.run([pip_cmd, "install", "--upgrade", "pip"], 
                   capture_output=True)
    
    # Instalar dependencias
    result = subprocess.run([pip_cmd, "install"] + dependencies)
    
    if result.returncode == 0:
        print("✅ Dependencias instaladas correctamente")
        return True
    else:
        print("❌ Error instalando dependencias")
        return False

def check_ffmpeg():
    """Verifica si FFmpeg está disponible."""
    ffmpeg_cmd = shutil.which("ffmpeg")
    if ffmpeg_cmd:
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"✅ FFmpeg encontrado: {ffmpeg_cmd}")
                print(f"   📊 {version_line}")
                return True
        except:
            pass
    
    print("⚠️ FFmpeg no encontrado - conversiones MP3 limitadas")
    if platform.system() == "Windows":
        print("💡 Instalar desde: https://ffmpeg.org/download.html")
    elif platform.system() == "Darwin":  # macOS
        print("💡 Instalar: brew install ffmpeg")
    else:  # Linux
        print("💡 Instalar: sudo apt install ffmpeg")
    
    return False

def main():
    """Función principal del launcher."""
    print("🎵 === YT-DLP Music API v3.0 Universal Portable ===")
    print("🚀 Iniciando aplicación portable...")
    print(f"🖥️ Sistema: {platform.system()} {platform.release()}")
    print("")
    
    # Cambiar al directorio del script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    print(f"📁 Directorio de trabajo: {script_dir}")
    
    # Detectar Python
    python_cmd = detect_python()
    if not python_cmd:
        print("❌ Error: No se encontró Python 3.8+ en el sistema")
        print("💡 Por favor instala Python 3.8 o superior desde https://python.org")
        return 1
    
    # Configurar entorno virtual
    venv_result = setup_virtual_env(python_cmd)
    if not venv_result:
        return 1
    
    python_venv, pip_venv = venv_result
    
    # Instalar dependencias
    if not install_dependencies(pip_venv):
        return 1
    
    # Verificar FFmpeg
    check_ffmpeg()
    
    print("")
    print("🚀 Iniciando servidor...")
    print("🌐 Servidor estará disponible en: http://localhost:8080")
    print("📱 Frontend: http://localhost:8080")
    print("")
    print("⏹️ Presiona Ctrl+C para detener")
    print("")
    
    # Ejecutar la aplicación
    try:
        result = subprocess.run([python_venv, "api_downloader.py"])
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Aplicación detenida por el usuario")
        return 0
    except Exception as e:
        print(f"❌ Error ejecutando aplicación: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())