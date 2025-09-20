#!/usr/bin/env python3
"""
Script mejorado para crear distribuciones standalone de YT-DLP Music API
Soluciona: Python 3.9 deprecated, ffmpeg not found, mejores binarios
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import argparse
from datetime import datetime

def check_python_version():
    """Verificar que la versión de Python sea compatible"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor} - Compatible")
        return True
    elif version.major == 3 and version.minor == 9:
        print(f"⚠️ Python {version.major}.{version.minor} - Deprecated pero funcional")
        print("💡 Se recomienda actualizar a Python 3.10+ para mejor compatibilidad")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} - No compatible")
        print("🔧 Actualiza a Python 3.10 o superior")
        return False

def download_binaries(target_system=None):
    """Descarga yt-dlp y ffmpeg para la plataforma especificada"""
    if target_system is None:
        target_system = platform.system().lower()
    
    # Crear directorio de binarios
    bin_dir = Path("binaries") / target_system
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Descargando binarios para {target_system}...")
    
    if target_system == "darwin":  # macOS
        # Verificar si ya existen
        if (bin_dir / "yt-dlp").exists() and (bin_dir / "ffmpeg").exists() and (bin_dir / "ffprobe").exists():
            print("✅ Binarios de macOS ya existen, omitiendo descarga...")
            return
            
        # Descargar yt-dlp para macOS
        print("📥 Descargando yt-dlp para macOS...")
        subprocess.run([
            "curl", "-L", 
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
            "-o", str(bin_dir / "yt-dlp")
        ])
        os.chmod(bin_dir / "yt-dlp", 0o755)
        
        # Descargar ffmpeg completo con ffprobe para macOS
        print("📥 Descargando ffmpeg + ffprobe para macOS...")
        subprocess.run([
            "curl", "-L",
            "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip",
            "-o", str(bin_dir / "ffmpeg.zip")
        ])
        
        subprocess.run([
            "curl", "-L",
            "https://evermeet.cx/ffmpeg/ffprobe-6.1.zip", 
            "-o", str(bin_dir / "ffprobe.zip")
        ])
        
        # Extraer ffmpeg y ffprobe
        import zipfile
        with zipfile.ZipFile(bin_dir / "ffmpeg.zip", 'r') as zip_ref:
            zip_ref.extractall(bin_dir)
        with zipfile.ZipFile(bin_dir / "ffprobe.zip", 'r') as zip_ref:
            zip_ref.extractall(bin_dir)
            
        os.chmod(bin_dir / "ffmpeg", 0o755)
        os.chmod(bin_dir / "ffprobe", 0o755)
        os.remove(bin_dir / "ffmpeg.zip")
        os.remove(bin_dir / "ffprobe.zip")
        
    elif target_system == "windows":
        # Verificar si ya existen
        if (bin_dir / "yt-dlp.exe").exists() and (bin_dir / "ffmpeg.exe").exists() and (bin_dir / "ffprobe.exe").exists():
            print("✅ Binarios de Windows ya existen, omitiendo descarga...")
            return
            
        # Descargar yt-dlp para Windows
        print("📥 Descargando yt-dlp para Windows...")
        subprocess.run([
            "curl", "-L",
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
            "-o", str(bin_dir / "yt-dlp.exe")
        ])
        
        # Descargar ffmpeg completo para Windows
        print("📥 Descargando ffmpeg + ffprobe para Windows...")
        ffmpeg_zip = bin_dir / "ffmpeg.zip"
        subprocess.run([
            "curl", "-L",
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            "-o", str(ffmpeg_zip)
        ])
        
        # Extraer ffmpeg y ffprobe con manejo mejorado
        import zipfile
        try:
            with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
                # Crear directorio temporal para extracción
                temp_extract_dir = bin_dir / "temp_extract"
                temp_extract_dir.mkdir(exist_ok=True)
                zip_ref.extractall(temp_extract_dir)
                
                # Buscar los ejecutables en la estructura extraída
                ffmpeg_found = False
                ffprobe_found = False
                
                for root, dirs, files in os.walk(temp_extract_dir):
                    if "ffmpeg.exe" in files and not ffmpeg_found:
                        source_path = os.path.join(root, "ffmpeg.exe")
                        target_path = bin_dir / "ffmpeg.exe"
                        if not target_path.exists():
                            shutil.copy2(source_path, target_path)
                            ffmpeg_found = True
                            print(f"✅ ffmpeg.exe copiado desde {source_path}")
                    
                    if "ffprobe.exe" in files and not ffprobe_found:
                        source_path = os.path.join(root, "ffprobe.exe")
                        target_path = bin_dir / "ffprobe.exe"
                        if not target_path.exists():
                            shutil.copy2(source_path, target_path)
                            ffprobe_found = True
                            print(f"✅ ffprobe.exe copiado desde {source_path}")
                    
                    if ffmpeg_found and ffprobe_found:
                        break
                
                # Limpiar directorio temporal
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
                
                if not ffmpeg_found:
                    print("⚠️ No se encontró ffmpeg.exe en el archivo descargado")
                if not ffprobe_found:
                    print("⚠️ No se encontró ffprobe.exe en el archivo descargado")
                    
        except Exception as e:
            print(f"❌ Error extrayendo ffmpeg: {e}")
        
        # Limpiar archivo zip
        if ffmpeg_zip.exists():
            ffmpeg_zip.unlink()
            print("🧹 Archivo zip limpiado")

def create_spec_file(target_system=None):
    """Crear archivo .spec para PyInstaller con binarios mejorados"""
    if target_system is None:
        target_system = platform.system().lower()
    
    spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Archivos adicionales según la plataforma objetivo
target_system = "{target_system}"

added_files = []
if target_system == "darwin":
    added_files = [
        ('binaries/darwin/yt-dlp', 'binaries/'),
        ('binaries/darwin/ffmpeg', 'binaries/'),
        ('binaries/darwin/ffprobe', 'binaries/'),
        ('frontend', 'frontend/'),
        ('*.md', '.'),
    ]
elif target_system == "windows":
    added_files = [
        ('binaries/windows/yt-dlp.exe', 'binaries/'),
        ('binaries/windows/ffmpeg.exe', 'binaries/'),
        ('binaries/windows/ffprobe.exe', 'binaries/'),
        ('frontend', 'frontend/'),
        ('*.md', '.'),
    ]

a = Analysis(
    ['api_downloader.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'flask',
        'concurrent.futures',
        'threading',
        'subprocess',
        'json',
        'os',
        'sys',
        'pathlib',
        'datetime'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='YT-DLP-Music-API',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Para macOS, crear un bundle .app
if target_system == "darwin":
    app = BUNDLE(
        exe,
        name='YT-DLP-Music-API.app',
        icon=None,
        bundle_identifier='com.ytdlp.musicapi',
        info_plist={{
            'CFBundleName': 'YT-DLP Music API',
            'CFBundleDisplayName': 'YT-DLP Music API',
            'CFBundleVersion': '2.0.0',
            'CFBundleShortVersionString': '2.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15.0',
        }}
    )
'''
    
    spec_filename = f"ytdlp-music-api-{target_system}-v2.spec"
    with open(spec_filename, "w") as f:
        f.write(spec_content)
    return spec_filename

def patch_api_downloader():
    """Parchear api_downloader.py para manejar mejor las rutas de ffmpeg"""
    print("🔧 Aplicando parches para distribución standalone...")
    
    # Leer el archivo actual
    with open("api_downloader.py", "r") as f:
        content = f.read()
    
    # Crear backup
    with open("api_downloader.py.backup", "w") as f:
        f.write(content)
    
    # Patch: Agregar detección de binarios incluidos
    patch_code = '''
# === PATCH PARA DISTRIBUCIÓN STANDALONE ===
def get_bundled_binary_path(binary_name):
    """Obtener ruta de binarios incluidos en la distribución"""
    import sys
    
    if getattr(sys, 'frozen', False):
        # Ejecutándose como ejecutable PyInstaller
        base_path = sys._MEIPASS
    else:
        # Ejecutándose como script Python normal
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    binary_path = os.path.join(base_path, "binaries", binary_name)
    
    # Para Windows, agregar .exe si no está presente
    if platform.system() == "Windows" and not binary_path.endswith('.exe'):
        binary_path += '.exe'
    
    if os.path.exists(binary_path):
        return binary_path
    
    # Fallback: buscar en PATH
    import shutil
    system_binary = shutil.which(binary_name)
    if system_binary:
        return system_binary
    
    return None

# Configurar rutas de ffmpeg al inicio
FFMPEG_PATH = get_bundled_binary_path('ffmpeg')
FFPROBE_PATH = get_bundled_binary_path('ffprobe')

if FFMPEG_PATH:
    os.environ['FFMPEG_LOCATION'] = FFMPEG_PATH
    print(f"✅ FFmpeg encontrado: {FFMPEG_PATH}")
else:
    print("⚠️ FFmpeg no encontrado")

if FFPROBE_PATH:
    print(f"✅ FFprobe encontrado: {FFPROBE_PATH}")
else:
    print("⚠️ FFprobe no encontrado")

# === FIN PATCH ===

'''
    
    # Insertar el patch después de los imports pero antes del código principal
    import_end = content.find('\napp = Flask(__name__')
    if import_end == -1:
        import_end = content.find('\n# ')  # Buscar primer comentario
        if import_end == -1:
            import_end = 200  # Fallback
    
    patched_content = content[:import_end] + '\n' + patch_code + content[import_end:]
    
    # Escribir el archivo patcheado
    with open("api_downloader.py", "w") as f:
        f.write(patched_content)
    
    print("✅ Patch aplicado exitosamente")

def restore_api_downloader():
    """Restaurar api_downloader.py desde backup"""
    if os.path.exists("api_downloader.py.backup"):
        shutil.copy2("api_downloader.py.backup", "api_downloader.py")
        os.remove("api_downloader.py.backup")
        print("🔄 api_downloader.py restaurado")

def build_executable(target_system=None):
    """Construir el ejecutable usando PyInstaller"""
    current_system = platform.system().lower()
    if target_system is None:
        target_system = current_system
    
    print("📦 Instalando/Verificando PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])
    
    print(f"📝 Creando archivo de especificación para {target_system}...")
    spec_file = create_spec_file(target_system)
    
    # Aplicar patch temporalmente
    patch_api_downloader()
    
    try:
        print(f"🔨 Construyendo ejecutable para {target_system}...")
        
        if current_system == "darwin" and target_system == "windows":
            print("⚠️ Cross-compilation a Windows desde Mac...")
            print("💡 Para mejor compatibilidad, construye directamente en Windows")
        
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            spec_file, 
            "--clean", 
            "--noconfirm",
            "--log-level=INFO"
        ])
        
        if result.returncode != 0:
            print("❌ Error en la construcción con PyInstaller")
            return False
        
        # Crear estructura de distribución con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dist_dir = Path("distributions") / f"{target_system}_{timestamp}"
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        # También crear o actualizar el directorio "latest"
        latest_dir = Path("distributions") / target_system
        latest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copiar ejecutable a ambos directorios
        if target_system == "darwin":
            if Path("dist/YT-DLP-Music-API.app").exists():
                # Copiar a directorio con timestamp
                shutil.copytree("dist/YT-DLP-Music-API.app", 
                              dist_dir / "YT-DLP-Music-API.app", 
                              dirs_exist_ok=True)
                # Copiar a directorio latest (sobrescribir)
                if (latest_dir / "YT-DLP-Music-API.app").exists():
                    shutil.rmtree(latest_dir / "YT-DLP-Music-API.app")
                shutil.copytree("dist/YT-DLP-Music-API.app", 
                              latest_dir / "YT-DLP-Music-API.app")
        else:  # Windows
            exe_files = list(Path("dist").glob("YT-DLP-Music-API*"))
            if exe_files:
                exe_file = exe_files[0]
                # Copiar a directorio con timestamp
                shutil.copy2(exe_file, dist_dir / "YT-DLP-Music-API.exe")
                # Copiar a directorio latest
                shutil.copy2(exe_file, latest_dir / "YT-DLP-Music-API.exe")
        
        # Crear scripts de inicio en ambos directorios
        create_launch_script(dist_dir, target_system)
        create_launch_script(latest_dir, target_system)
        
        # Crear README específico
        create_readme(dist_dir, target_system, timestamp)
        create_readme(latest_dir, target_system, "latest")
        
        print(f"✅ Distribución creada en:")
        print(f"  📁 {dist_dir} (con timestamp)")
        print(f"  📁 {latest_dir} (latest)")
        
        return True
        
    finally:
        # Restaurar archivo original
        restore_api_downloader()
        
        # Limpiar archivos temporales
        if os.path.exists(spec_file):
            os.remove(spec_file)

def create_launch_script(dist_dir, target_system):
    """Crear script para abrir navegador automáticamente"""
    
    if target_system == "darwin":
        script_content = '''#!/bin/bash
echo "🎵 Iniciando YT-DLP Music API v2.0..."
echo "🔧 Verificando dependencias..."

# Verificar que ffmpeg esté incluido
if [ -f "YT-DLP-Music-API.app/Contents/MacOS/binaries/ffmpeg" ]; then
    echo "✅ FFmpeg incluido"
else
    echo "⚠️ FFmpeg no encontrado en bundle"
fi

echo "🚀 Lanzando aplicación..."
open -a "YT-DLP-Music-API.app"
sleep 3
echo "🌐 Abriendo navegador en puerto 8080..."
open "http://localhost:8080"
'''
        script_path = dist_dir / "launch.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        # También copiar scripts de utilidad actualizados
        if Path("check_port.sh").exists():
            shutil.copy2("check_port.sh", dist_dir / "check_port.sh")
            os.chmod(dist_dir / "check_port.sh", 0o755)
        if Path("lsof_8080.sh").exists():
            shutil.copy2("lsof_8080.sh", dist_dir / "lsof_8080.sh")
            os.chmod(dist_dir / "lsof_8080.sh", 0o755)
        
    else:  # Windows
        script_content = '''@echo off
echo 🎵 Iniciando YT-DLP Music API v2.0...
echo 🔧 Verificando dependencias...

if exist "binaries\\ffmpeg.exe" (
    echo ✅ FFmpeg incluido
) else (
    echo ⚠️ FFmpeg no encontrado
)

echo 🚀 Lanzando aplicación...
start "" "YT-DLP-Music-API.exe"
timeout /t 3 /nobreak >nul
echo 🌐 Abriendo navegador en puerto 8080...
start "" "http://localhost:8080"
'''
        script_path = dist_dir / "launch.bat"
        with open(script_path, "w") as f:
            f.write(script_content)
            
        # Script para verificar puerto en Windows
        port_check_script = '''@echo off
echo 🔍 Verificando puerto 8080...
netstat -an | find ":8080"
if %errorlevel% == 0 (
    echo ✅ Puerto 8080 está en uso
) else (
    echo ❌ Puerto 8080 está libre
)
echo.
echo 🔧 Para cerrar la aplicación:
echo taskkill /f /im "YT-DLP-Music-API.exe"
pause
'''
        with open(dist_dir / "check_port.bat", "w") as f:
            f.write(port_check_script)

def create_readme(dist_dir, target_system, version):
    """Crear README específico para la distribución v2"""
    readme_content = f"""# YT-DLP Music API - {target_system.title()} Distribution v2.0

**Versión:** {version}  
**Generado:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Plataforma:** {target_system.title()}

## 🆕 Mejoras v2.0

- ✅ **Python 3.9+ Compatible** - Soporte para versiones modernas
- ✅ **FFmpeg + FFprobe Incluidos** - Sin dependencias externas
- ✅ **Error max_workers Corregido** - Playlists funcionan perfectamente
- ✅ **Puerto Fijo 8080** - Sin conflictos
- ✅ **Detección Automática de Binarios** - Rutas auto-configuradas
- ✅ **Mejor Logging** - Diagnóstico mejorado

## 🚀 Inicio Rápido

### {target_system.title()}:
```{'bash' if target_system == 'darwin' else 'cmd'}
{'./launch.sh' if target_system == 'darwin' else 'launch.bat'}
```

## 📁 Contenido

- **YT-DLP-Music-API.{'app' if target_system == 'darwin' else 'exe'}** - Aplicación principal v2.0
- **launch.{'sh' if target_system == 'darwin' else 'bat'}** - Script de inicio con verificaciones
- **check_port.{'sh' if target_system == 'darwin' else 'bat'}** - Diagnóstico de puerto 8080
- **README.md** - Esta documentación

## ✅ Características

- ✅ **Puerto fijo: 8080** - Sin conflictos automáticos
- ✅ **Sin dependencias externas** - FFmpeg y FFprobe incluidos
- ✅ **Detección automática de playlists** - Individual o lote
- ✅ **Descargas paralelas** - Hasta 3 simultáneas
- ✅ **Progreso en tiempo real** - Feedback visual detallado
- ✅ **Compatible con YouTube, YouTube Music** - URLs variadas
- ✅ **Múltiples formatos** - MP3, MP4, bestaudio
- ✅ **Sistema anti-bloqueo** - Estrategias automáticas

## 🔧 Solución de problemas

### ✅ Errores Corregidos en v2.0
- ❌ `max_workers referenced before assignment` → ✅ **CORREGIDO**
- ❌ `ffprobe and ffmpeg not found` → ✅ **CORREGIDO**
- ❌ `Python 3.9 deprecated` → ✅ **COMPATIBLE**

### Diagnóstico Básico
```{'bash' if target_system == 'darwin' else 'cmd'}
# Verificar puerto
{'./check_port.sh' if target_system == 'darwin' else 'check_port.bat'}
```

### Si la aplicación no inicia
{'**Mac:**' if target_system == 'darwin' else '**Windows:**'}
{'- Verificar permisos: `chmod +x launch.sh`' if target_system == 'darwin' else '- Ejecutar como administrador si es necesario'}
{'- Permitir aplicaciones no firmadas en Preferencias del Sistema' if target_system == 'darwin' else '- Agregar excepción en Windows Defender si es necesario'}

### Variables de entorno útiles
```bash
# Modo rápido (sin conversión MP3)
SPEED_MODE=1

# Limpiar antes de descargar  
PRE_CLEAN_OUTPUT=1

# Limitar playlists grandes
PLAYLIST_LIMIT=50
```

## 📊 Información Técnica

**Binarios incluidos:**
{'- yt-dlp (macOS native)' if target_system == 'darwin' else '- yt-dlp.exe'}
{'- ffmpeg (static build)' if target_system == 'darwin' else '- ffmpeg.exe'}
{'- ffprobe (static build)' if target_system == 'darwin' else '- ffprobe.exe'}

**Puerto:** 8080 (fijo)  
**Python:** Compatible 3.9+  
**Arquitectura:** {'x86_64 (Intel/M1 compatible)' if target_system == 'darwin' else 'x64'}

---

*v2.0 - Construido con PyInstaller desde {platform.system()} - {datetime.now().strftime("%Y-%m-%d")}*
"""
    
    with open(dist_dir / "README.md", "w") as f:
        f.write(readme_content)

def main():
    parser = argparse.ArgumentParser(description='Constructor YT-DLP Music API v2.0 - Versión Mejorada')
    parser.add_argument('--target', choices=['darwin', 'windows', 'both'], 
                       default=None, help='Plataforma objetivo')
    parser.add_argument('--current-only', action='store_true', 
                       help='Solo construir para la plataforma actual')
    parser.add_argument('--force', action='store_true',
                       help='Forzar construcción incluso con Python no óptimo')
    
    args = parser.parse_args()
    
    print("🎵 === Constructor YT-DLP Music API v2.0 ===")
    print("🚀 Versión mejorada: ffmpeg incluido, Python 3.9+ compatible")
    print("")
    
    # Verificar versión de Python
    if not check_python_version() and not args.force:
        print("\n❌ Versión de Python no recomendada")
        print("💡 Usa --force para continuar de todos modos")
        print("🔧 Recomendación: actualizar a Python 3.10+")
        sys.exit(1)
    
    current_system = platform.system().lower()
    print(f"🖥️ Sistema actual: {current_system}")
    print("💡 Esta versión NO borra distribuciones existentes")
    
    targets = []
    if args.target == 'both':
        targets = ['darwin', 'windows']
    elif args.target:
        targets = [args.target]
    elif args.current_only:
        targets = [current_system]
    else:
        # Por defecto, construir para sistema actual
        targets = [current_system]
        print(f"💡 Construyendo para {current_system}. Usa --target para otras plataformas.")
    
    # Mostrar distribuciones existentes
    if Path("distributions").exists():
        existing = list(Path("distributions").iterdir())
        if existing:
            print(f"\n📂 Distribuciones existentes:")
            for dist in existing:
                if dist.is_dir():
                    print(f"   📁 {dist.name}")
    
    success_count = 0
    for target in targets:
        print(f"\n🔨 Construyendo v2.0 para {target}...")
        
        # Descargar binarios necesarios (incluyendo ffprobe)
        download_binaries(target)
        
        # Construir ejecutable
        if build_executable(target):
            print(f"✅ Distribución v2.0 para {target} completada!")
            success_count += 1
        else:
            print(f"❌ Error construyendo para {target}")
    
    print(f"\n🎉 {success_count}/{len(targets)} distribuciones completadas!")
    if success_count > 0:
        print("📁 Archivos generados en el directorio 'distributions/'")
        
        for target in targets:
            if target == 'darwin':
                print(f"🍎 Mac: usa ./distributions/darwin/launch.sh")
            else:
                print(f"🪟 Windows: usa ./distributions/windows/launch.bat")
        
        print("\n🆕 Mejoras v2.0:")
        print("  ✅ FFmpeg + FFprobe incluidos")
        print("  ✅ Python 3.9+ compatible") 
        print("  ✅ Error max_workers corregido")
        print("  ✅ Detección automática de binarios")

if __name__ == "__main__":
    main()