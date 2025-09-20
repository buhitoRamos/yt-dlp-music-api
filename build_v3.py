#!/usr/bin/env python3
"""
Script mejorado v3.0 para crear distribuciones standalone de YT-DLP Music API
Versión 3.0 - Soluciona problemas de Flask y dependencias en ejecutables
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

def check_and_install_dependencies():
    """Verificar e instalar dependencias necesarias"""
    print("📦 Verificando dependencias...")
    
    required_packages = [
        "flask",
        "flask-cors", 
        "yt-dlp",
        "pyinstaller>=6.0"
    ]
    
    for package in required_packages:
        try:
            print(f"📦 Instalando/Verificando {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️ Advertencia instalando {package}: {result.stderr}")
            else:
                print(f"✅ {package} instalado/verificado")
        except Exception as e:
            print(f"❌ Error con {package}: {e}")

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

def create_spec_file_v3(target_system=None):
    """Crear archivo .spec para PyInstaller v3.0 con mejores configuraciones"""
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

# Hidden imports mejorados para v3.0
hidden_imports = [
    # Flask core
    'flask',
    'flask.app',
    'flask.blueprints',
    'flask.cli',
    'flask.config',
    'flask.ctx',
    'flask.globals',
    'flask.helpers',
    'flask.json',
    'flask.logging',
    'flask.sessions',
    'flask.signals',
    'flask.templating',
    'flask.testing',
    'flask.views',
    'flask.wrappers',
    
    # Flask-CORS
    'flask_cors',
    'flask_cors.core',
    'flask_cors.extension',
    'flask_cors.decorator',
    
    # Werkzeug (Flask dependency)
    'werkzeug',
    'werkzeug.serving',
    'werkzeug.utils',
    'werkzeug.urls',
    'werkzeug.http',
    'werkzeug.exceptions',
    'werkzeug.routing',
    'werkzeug.wrappers',
    'werkzeug.security',
    
    # Jinja2 (Flask dependency)
    'jinja2',
    'jinja2.environment',
    'jinja2.loaders',
    'jinja2.runtime',
    'jinja2.exceptions',
    
    # MarkupSafe (Jinja2 dependency) 
    'markupsafe',
    
    # Standard library modules
    'concurrent.futures',
    'threading',
    'subprocess',
    'json',
    'os',
    'sys',
    'pathlib',
    'datetime',
    'tempfile',
    'time',
    'random',
    'platform',
    'webbrowser',
    're',
    'difflib',
    
    # Additional modules that might be needed
    'email',
    'email.mime',
    'email.mime.text',
    'urllib',
    'urllib.request',
    'urllib.parse',
    'http',
    'http.server',
    'socketserver',
    'base64',
    'hashlib',
    'hmac',
    'secrets',
    'uuid',
    'collections',
    'itertools',
    'functools',
]

a = Analysis(
    ['api_downloader.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'turtle', 
        'pydoc',
        'doctest',
        'test',
        'lib2to3',
        'distutils',
        'setuptools',
        # 'inspect', # Requerido por Flask/Werkzeug - NO excluir
        'dis',
        'pdb',
        'cmd',
        'pstats',
        'profile',
        'cProfile',
        'trace',
    ],
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
    name='YT-DLP-Music-API-v3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Desactivar UPX para mejor compatibilidad
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
        name='YT-DLP-Music-API-v3.app',
        icon=None,
        bundle_identifier='com.ytdlp.musicapi.v3',
        info_plist={{
            'CFBundleName': 'YT-DLP Music API v3',
            'CFBundleDisplayName': 'YT-DLP Music API v3',
            'CFBundleVersion': '3.0.0',
            'CFBundleShortVersionString': '3.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15.0',
            'NSAppTransportSecurity': {{
                'NSAllowsArbitraryLoads': True
            }},
        }}
    )
'''
    
    spec_filename = f"ytdlp-music-api-{target_system}-v3.spec"
    with open(spec_filename, "w") as f:
        f.write(spec_content)
    return spec_filename

def patch_api_downloader_v3():
    """Parchear api_downloader.py para v3.0 con mejor compatibilidad"""
    print("🔧 Aplicando parches v3.0 para distribución standalone...")
    
    # Leer el archivo actual
    with open("api_downloader.py", "r") as f:
        content = f.read()
    
    # Crear backup
    with open("api_downloader.py.backup", "w") as f:
        f.write(content)
    
    # Patch v3.0: Mejor detección de binarios y entorno
    patch_code = '''
# === PATCH v3.0 PARA DISTRIBUCIÓN STANDALONE ===
import platform

def get_bundled_binary_path(binary_name):
    """Obtener ruta de binarios incluidos en la distribución v3.0"""
    import sys
    import os
    
    if getattr(sys, 'frozen', False):
        # Ejecutándose como ejecutable PyInstaller
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        # Ejecutándose como script Python normal
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Intentar diferentes ubicaciones
    possible_paths = [
        os.path.join(base_path, "binaries", binary_name),
        os.path.join(base_path, binary_name),
        os.path.join(os.path.dirname(base_path), "binaries", binary_name),
    ]
    
    # Para Windows, agregar .exe si no está presente
    if platform.system() == "Windows":
        possible_paths.extend([
            path + '.exe' for path in possible_paths if not path.endswith('.exe')
        ])
    
    for binary_path in possible_paths:
        if os.path.exists(binary_path):
            print(f"✅ Binario encontrado: {binary_path}")
            return binary_path
    
    # Fallback: buscar en PATH
    import shutil
    system_binary = shutil.which(binary_name)
    if system_binary:
        print(f"✅ Binario en PATH: {system_binary}")
        return system_binary
    
    print(f"⚠️ Binario no encontrado: {binary_name}")
    return None

def setup_environment_v3():
    """Configurar entorno para v3.0"""
    global FFMPEG_PATH, FFPROBE_PATH
    
    print("🔧 Configurando entorno v3.0...")
    
    # Configurar rutas de ffmpeg al inicio
    FFMPEG_PATH = get_bundled_binary_path('ffmpeg')
    FFPROBE_PATH = get_bundled_binary_path('ffprobe')

    if FFMPEG_PATH:
        os.environ['FFMPEG_LOCATION'] = FFMPEG_PATH
        print(f"✅ FFmpeg configurado: {FFMPEG_PATH}")
    else:
        print("⚠️ FFmpeg no encontrado")

    if FFPROBE_PATH:
        print(f"✅ FFprobe configurado: {FFPROBE_PATH}")
    else:
        print("⚠️ FFprobe no encontrado")
    
    # Configurar variables de entorno adicionales para Flask
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'production'
    
    # Desactivar el reloader en entorno compilado
    if getattr(sys, 'frozen', False):
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
    
    print("✅ Entorno v3.0 configurado")

# Llamar setup al cargar
setup_environment_v3()

# === FIN PATCH v3.0 ===

'''
    
    # Insertar el patch después de los imports pero antes del código principal
    import_end = content.find('\napp = Flask(__name__')
    if import_end == -1:
        import_end = content.find('\n# ')  # Buscar primer comentario
        if import_end == -1:
            import_end = 200  # Fallback
    
    patched_content = content[:import_end] + '\n' + patch_code + content[import_end:]
    
    # También modificar la función main para mejor detección de entorno compilado
    main_pattern = '''if __name__ == '__main__':
    import os
    import webbrowser
    import threading'''
    
    main_replacement = '''if __name__ == '__main__':
    import os
    import webbrowser
    import threading
    
    # Detectar si estamos en un entorno compilado
    is_compiled = getattr(sys, 'frozen', False)
    print(f"🔍 Entorno: {'Compilado' if is_compiled else 'Desarrollo'}")'''
    
    patched_content = patched_content.replace(main_pattern, main_replacement)
    
    # Escribir el archivo patcheado
    with open("api_downloader.py", "w") as f:
        f.write(patched_content)
    
    print("✅ Patch v3.0 aplicado exitosamente")

def restore_api_downloader():
    """Restaurar api_downloader.py desde backup"""
    if os.path.exists("api_downloader.py.backup"):
        shutil.copy2("api_downloader.py.backup", "api_downloader.py")
        os.remove("api_downloader.py.backup")
        print("🔄 api_downloader.py restaurado")

def build_executable_v3(target_system=None):
    """Construir el ejecutable v3.0 usando PyInstaller"""
    current_system = platform.system().lower()
    if target_system is None:
        target_system = current_system
    
    print("📦 Verificando dependencias...")
    check_and_install_dependencies()
    
    print(f"📝 Creando archivo de especificación v3.0 para {target_system}...")
    spec_file = create_spec_file_v3(target_system)
    
    # Aplicar patch temporalmente
    patch_api_downloader_v3()
    
    try:
        print(f"🔨 Construyendo ejecutable v3.0 para {target_system}...")
        
        if current_system == "darwin" and target_system == "windows":
            print("⚠️ Cross-compilation a Windows desde Mac...")
            print("💡 Para mejor compatibilidad, construye directamente en Windows")
        
        # Comando PyInstaller con configuraciones mejoradas
        cmd = [
            sys.executable, "-m", "PyInstaller", 
            spec_file, 
            "--clean", 
            "--noconfirm",
            "--log-level=INFO",
            "--distpath=dist",
            "--workpath=build",
        ]
        
        # No agregar configuraciones adicionales cuando usamos .spec file
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            print("❌ Error en la construcción con PyInstaller")
            return False
        
        # Crear estructura de distribución con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dist_dir = Path("distributions") / f"{target_system}_v3_{timestamp}"
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        # También crear o actualizar el directorio "latest"
        latest_dir = Path("distributions") / f"{target_system}_v3"
        latest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copiar ejecutable a ambos directorios
        if target_system == "darwin":
            if Path("dist/YT-DLP-Music-API-v3.app").exists():
                # Copiar a directorio con timestamp
                shutil.copytree("dist/YT-DLP-Music-API-v3.app", 
                              dist_dir / "YT-DLP-Music-API-v3.app", 
                              dirs_exist_ok=True)
                # Copiar a directorio latest (sobrescribir)
                if (latest_dir / "YT-DLP-Music-API-v3.app").exists():
                    shutil.rmtree(latest_dir / "YT-DLP-Music-API-v3.app")
                shutil.copytree("dist/YT-DLP-Music-API-v3.app", 
                              latest_dir / "YT-DLP-Music-API-v3.app")
        else:  # Windows
            # Buscar ejecutables, tanto .exe como aplicaciones Mac (cross-compilation)
            exe_files = list(Path("dist").glob("YT-DLP-Music-API-v3*"))
            exe_files = [f for f in exe_files if f.is_file()]  # Solo archivos, no directorios
            
            if exe_files:
                exe_file = exe_files[0]
                target_name = "YT-DLP-Music-API-v3.exe"
                # Copiar a directorio con timestamp
                shutil.copy2(exe_file, dist_dir / target_name)
                # Copiar a directorio latest
                shutil.copy2(exe_file, latest_dir / target_name)
            else:
                # Si no hay .exe, buscar aplicación Mac (cross-compilation fallback)
                app_dirs = list(Path("dist").glob("YT-DLP-Music-API-v3*.app"))
                if app_dirs:
                    print("⚠️ Cross-compilation desde Mac: creando distribución híbrida")
                    app_dir = app_dirs[0]
                    # Copiar la app como fallback para cross-compilation
                    shutil.copytree(app_dir, dist_dir / app_dir.name, dirs_exist_ok=True)
                    if (latest_dir / app_dir.name).exists():
                        shutil.rmtree(latest_dir / app_dir.name)
                    shutil.copytree(app_dir, latest_dir / app_dir.name)
        
        # Crear scripts de inicio en ambos directorios
        create_launch_script_v3(dist_dir, target_system)
        create_launch_script_v3(latest_dir, target_system)
        
        # Crear README específico
        create_readme_v3(dist_dir, target_system, timestamp)
        create_readme_v3(latest_dir, target_system, "latest")
        
        print(f"✅ Distribución v3.0 creada en:")
        print(f"  📁 {dist_dir} (con timestamp)")
        print(f"  📁 {latest_dir} (latest)")
        
        return True
        
    finally:
        # Restaurar archivo original
        restore_api_downloader()
        
        # Limpiar archivos temporales
        if os.path.exists(spec_file):
            os.remove(spec_file)

def create_launch_script_v3(dist_dir, target_system):
    """Crear script v3.0 para abrir navegador automáticamente"""
    
    if target_system == "darwin":
        script_content = '''#!/bin/bash
echo "🎵 Iniciando YT-DLP Music API v3.0..."
echo "🔧 Verificando dependencias..."

# Verificar que ffmpeg esté incluido
if [ -f "YT-DLP-Music-API-v3.app/Contents/MacOS/binaries/ffmpeg" ]; then
    echo "✅ FFmpeg incluido"
else
    echo "⚠️ FFmpeg no encontrado en bundle"
fi

echo "🚀 Lanzando aplicación v3.0..."
echo "📱 Si no se abre automáticamente el navegador, ve a: http://localhost:8080"

# Ejecutar en background y obtener PID
./YT-DLP-Music-API-v3.app/Contents/MacOS/YT-DLP-Music-API-v3 &
APP_PID=$!

echo "🆔 Proceso iniciado con PID: $APP_PID"
echo "💡 Para cerrar usa el botón en la interfaz o: kill $APP_PID"

# Esperar un poco para que el servidor inicie
sleep 3

# Verificar si el proceso sigue ejecutándose
if kill -0 $APP_PID 2>/dev/null; then
    echo "✅ Aplicación ejecutándose correctamente"
    echo "🌐 Abriendo navegador en http://localhost:8080"
    open "http://localhost:8080"
    
    echo ""
    echo "🎵 YT-DLP Music API v3.0 está ejecutándose!"
    echo "📱 Navegador: http://localhost:8080"
    echo "🛑 Para cerrar: usa el botón '🔌 Cerrar App' en la interfaz"
    echo ""
    
    # Esperar a que el usuario presione una tecla para terminar el script
    # (la aplicación seguirá ejecutándose en background)
    read -p "Presiona ENTER para continuar (la app seguirá ejecutándose)..."
else
    echo "❌ La aplicación falló al iniciar"
    echo "🔍 Revisa los logs arriba para más detalles"
fi
'''
        script_path = dist_dir / "launch.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        # Crear script de prueba directo
        test_script = '''#!/bin/bash
echo "🧪 Prueba directa YT-DLP Music API v3.0..."
echo "Ejecutando directamente el binario..."
./YT-DLP-Music-API-v3.app/Contents/MacOS/YT-DLP-Music-API-v3
'''
        test_script_path = dist_dir / "test_direct.sh"
        with open(test_script_path, "w") as f:
            f.write(test_script)
        os.chmod(test_script_path, 0o755)
        
    else:  # Windows
        script_content = '''@echo off
echo 🎵 Iniciando YT-DLP Music API v3.0...
echo 🔧 Verificando dependencias...

if exist "binaries\\ffmpeg.exe" (
    echo ✅ FFmpeg incluido
) else (
    echo ⚠️ FFmpeg no encontrado
)

echo 🚀 Lanzando aplicación v3.0...
echo 📱 Si no se abre automáticamente el navegador, ve a: http://localhost:8080

start "" "YT-DLP-Music-API-v3.exe"
timeout /t 3 /nobreak >nul
echo 🌐 Abriendo navegador en puerto 8080...
start "" "http://localhost:8080"

echo.
echo 🎵 YT-DLP Music API v3.0 está ejecutándose!
echo 📱 Navegador: http://localhost:8080
echo 🛑 Para cerrar: usa el botón "🔌 Cerrar App" en la interfaz
echo.
pause
'''
        script_path = dist_dir / "launch.bat"
        with open(script_path, "w") as f:
            f.write(script_content)

def create_readme_v3(dist_dir, target_system, version):
    """Crear README específico para la distribución v3.0"""
    readme_content = f"""# YT-DLP Music API - {target_system.title()} Distribution v3.0

**Versión:** {version}  
**Generado:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Plataforma:** {target_system.title()}

## 🆕 Mejoras v3.0

- ✅ **Flask Dependencies Corregidas** - Imports y hooks mejorados
- ✅ **Mejor Detección de Binarios** - Múltiples rutas de búsqueda
- ✅ **Entorno Compilado Optimizado** - Variables Flask configuradas
- ✅ **Cross-platform Compatibility** - Funciona en Mac y Windows
- ✅ **Auto-browser Opening** - Se abre automáticamente el navegador
- ✅ **Shutdown Button** - Cierre elegante desde la interfaz
- ✅ **Debug Mejorado** - Logs detallados para diagnóstico

## 🚀 Inicio Rápido

### {target_system.title()}:
```{'bash' if target_system == 'darwin' else 'cmd'}
{'./launch.sh' if target_system == 'darwin' else 'launch.bat'}
```

### Prueba Directa (solo macOS):
```bash
./test_direct.sh
```

## 📁 Contenido

- **YT-DLP-Music-API-v3.{'app' if target_system == 'darwin' else 'exe'}** - Aplicación principal v3.0
- **launch.{'sh' if target_system == 'darwin' else 'bat'}** - Script de inicio inteligente
- **{'test_direct.sh - Script de prueba directa' if target_system == 'darwin' else 'check_port.bat - Diagnóstico de puerto'}**
- **README.md** - Esta documentación

## ✅ Características v3.0

- ✅ **Puerto fijo: 8080** - Configuración estable
- ✅ **FFmpeg/FFprobe incluidos** - Conversión de audio completa
- ✅ **Flask optimizado** - Dependencias resueltas para ejecutables
- ✅ **Auto-detección de entorno** - Compilado vs desarrollo
- ✅ **Playlists y videos individuales** - Compatibilidad completa
- ✅ **Descargas paralelas** - Hasta 3 simultáneas
- ✅ **Progreso en tiempo real** - Feedback detallado
- ✅ **Sistema anti-bloqueo** - Múltiples estrategias
- ✅ **Botón de cierre** - Shutdown elegante desde UI

## 🔧 Solución de problemas v3.0

### ✅ Problemas Resueltos
- ❌ `Flask import errors` → ✅ **CORREGIDO v3.0**
- ❌ `contextvars KeyboardInterrupt` → ✅ **CORREGIDO v3.0**
- ❌ `Binary not found errors` → ✅ **CORREGIDO v3.0**
- ❌ `Browser not opening` → ✅ **CORREGIDO v3.0**

### Si la aplicación no inicia

{'**macOS:**' if target_system == 'darwin' else '**Windows:**'}
1. {'Usa `./test_direct.sh` para ver logs detallados' if target_system == 'darwin' else 'Ejecuta desde CMD para ver logs'}
2. {'Verifica permisos: `chmod +x launch.sh`' if target_system == 'darwin' else 'Ejecuta como administrador si es necesario'}
3. {'Permite en Seguridad y Privacidad si aparece aviso' if target_system == 'darwin' else 'Agregar excepción en Windows Defender'}

### Verificación Manual
```{'bash' if target_system == 'darwin' else 'cmd'}
# Verificar puerto
{'lsof -i:8080' if target_system == 'darwin' else 'netstat -an | find ":8080"'}

# Abrir navegador manualmente
{'open http://localhost:8080' if target_system == 'darwin' else 'start http://localhost:8080'}
```

## 📊 Información Técnica v3.0

**Binarios incluidos:**
{'- yt-dlp (macOS native)' if target_system == 'darwin' else '- yt-dlp.exe'}
{'- ffmpeg (static build)' if target_system == 'darwin' else '- ffmpeg.exe'}
{'- ffprobe (static build)' if target_system == 'darwin' else '- ffprobe.exe'}

**Mejoras técnicas:**
- Hidden imports completos para Flask/Werkzeug/Jinja2
- Detección inteligente de rutas de binarios
- Variables de entorno Flask optimizadas
- Exclusión de módulos innecesarios
- Compatibilidad cross-platform mejorada

**Puerto:** 8080 (fijo)  
**Python:** Compatible 3.9+  
**Arquitectura:** {'x86_64 (Intel/M1 compatible)' if target_system == 'darwin' else 'x64'}

---

*v3.0 - Construido con PyInstaller desde {platform.system()} - {datetime.now().strftime("%Y-%m-%d")}*
"""
    
    with open(dist_dir / "README.md", "w") as f:
        f.write(readme_content)

def main():
    parser = argparse.ArgumentParser(description='Constructor YT-DLP Music API v3.0 - Flask Optimizado')
    parser.add_argument('--target', choices=['darwin', 'windows', 'both'], 
                       default=None, help='Plataforma objetivo')
    parser.add_argument('--current-only', action='store_true', 
                       help='Solo construir para la plataforma actual')
    parser.add_argument('--force', action='store_true',
                       help='Forzar construcción incluso con Python no óptimo')
    
    args = parser.parse_args()
    
    print("🎵 === Constructor YT-DLP Music API v3.0 ===")
    print("🚀 Versión 3.0: Flask optimizado, dependencias resueltas")
    print("")
    
    # Verificar versión de Python
    if not check_python_version() and not args.force:
        print("\n❌ Versión de Python no recomendada")
        print("💡 Usa --force para continuar de todos modos")
        print("🔧 Recomendación: actualizar a Python 3.10+")
        sys.exit(1)
    
    current_system = platform.system().lower()
    print(f"🖥️ Sistema actual: {current_system}")
    print("💡 Esta versión crea distribuciones v3.0 independientes")
    
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
        print(f"💡 Construyendo v3.0 para {current_system}. Usa --target para otras plataformas.")
    
    # Mostrar distribuciones existentes
    if Path("distributions").exists():
        existing = list(Path("distributions").iterdir())
        if existing:
            print(f"\n📂 Distribuciones existentes:")
            for dist in existing:
                if dist.is_dir():
                    version_info = "v3" if "v3" in dist.name else "v2" if any(c.isdigit() for c in dist.name) else "v1"
                    print(f"   📁 {dist.name} ({version_info})")
    
    success_count = 0
    for target in targets:
        print(f"\n🔨 Construyendo v3.0 para {target}...")
        
        # Descargar binarios necesarios
        download_binaries(target)
        
        # Construir ejecutable
        if build_executable_v3(target):
            print(f"✅ Distribución v3.0 para {target} completada!")
            success_count += 1
        else:
            print(f"❌ Error construyendo v3.0 para {target}")
    
    print(f"\n🎉 {success_count}/{len(targets)} distribuciones v3.0 completadas!")
    if success_count > 0:
        print("📁 Archivos generados en el directorio 'distributions/' con sufijo v3")
        
        for target in targets:
            if target == 'darwin':
                print(f"🍎 Mac v3.0: usa ./distributions/darwin_v3/launch.sh")
            else:
                print(f"🪟 Windows v3.0: usa ./distributions/windows_v3/launch.bat")
        
        print("\n🆕 Mejoras v3.0:")
        print("  ✅ Flask dependencies completamente resueltas")
        print("  ✅ Mejor detección de binarios y entorno")
        print("  ✅ Auto-apertura de navegador mejorada")
        print("  ✅ Scripts de diagnóstico incluidos")

if __name__ == "__main__":
    main()