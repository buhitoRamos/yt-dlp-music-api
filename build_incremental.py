#!/usr/bin/env python3
"""
Script para crear distribuciones standalone de YT-DLP Music API
para Mac y Windows usando PyInstaller (versión incremental - no borra existentes)
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import argparse
from datetime import datetime

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
        if (bin_dir / "yt-dlp").exists() and (bin_dir / "ffmpeg").exists():
            print("✅ Binarios de macOS ya existen, omitiendo descarga...")
            return
            
        # Descargar yt-dlp para macOS
        subprocess.run([
            "curl", "-L", 
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos",
            "-o", str(bin_dir / "yt-dlp")
        ])
        os.chmod(bin_dir / "yt-dlp", 0o755)
        
        # Descargar ffmpeg estático para macOS
        print("Descargando ffmpeg para macOS...")
        subprocess.run([
            "curl", "-L",
            "https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip",
            "-o", str(bin_dir / "ffmpeg.zip")
        ])
        
        # Extraer ffmpeg
        import zipfile
        with zipfile.ZipFile(bin_dir / "ffmpeg.zip", 'r') as zip_ref:
            zip_ref.extractall(bin_dir)
        os.chmod(bin_dir / "ffmpeg", 0o755)
        os.remove(bin_dir / "ffmpeg.zip")
        
    elif target_system == "windows":
        # Verificar si ya existen
        if (bin_dir / "yt-dlp.exe").exists() and (bin_dir / "ffmpeg.exe").exists():
            print("✅ Binarios de Windows ya existen, omitiendo descarga...")
            return
            
        # Descargar yt-dlp para Windows
        subprocess.run([
            "curl", "-L",
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
            "-o", str(bin_dir / "yt-dlp.exe")
        ])
        
        # Descargar ffmpeg para Windows
        print("Descargando ffmpeg para Windows...")
        subprocess.run([
            "curl", "-L",
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            "-o", str(bin_dir / "ffmpeg.zip")
        ])
        
        # Extraer ffmpeg
        import zipfile
        with zipfile.ZipFile(bin_dir / "ffmpeg.zip", 'r') as zip_ref:
            zip_ref.extractall(bin_dir)
        
        # Buscar el ejecutable de ffmpeg en la estructura extraída
        for root, dirs, files in os.walk(bin_dir):
            if "ffmpeg.exe" in files:
                shutil.copy2(os.path.join(root, "ffmpeg.exe"), bin_dir / "ffmpeg.exe")
                break
        
        # Limpiar
        for item in bin_dir.iterdir():
            if item.is_dir() and "ffmpeg" in item.name:
                shutil.rmtree(item, ignore_errors=True)
        if (bin_dir / "ffmpeg.zip").exists():
            os.remove(bin_dir / "ffmpeg.zip")

def create_spec_file(target_system=None):
    """Crear archivo .spec para PyInstaller"""
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
        ('frontend', 'frontend/'),
        ('*.md', '.'),
    ]
elif target_system == "windows":
    added_files = [
        ('binaries/windows/yt-dlp.exe', 'binaries/'),
        ('binaries/windows/ffmpeg.exe', 'binaries/'),
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
        'sys'
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
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        }}
    )
'''
    
    spec_filename = f"ytdlp-music-api-{target_system}.spec"
    with open(spec_filename, "w") as f:
        f.write(spec_content)
    return spec_filename

def build_executable(target_system=None):
    """Construir el ejecutable usando PyInstaller"""
    current_system = platform.system().lower()
    if target_system is None:
        target_system = current_system
    
    print("Instalando/Verificando PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    print(f"Creando archivo de especificación para {target_system}...")
    spec_file = create_spec_file(target_system)
    
    print(f"Construyendo ejecutable para {target_system}...")
    
    # Para cross-compilation a Windows desde Mac, necesitamos usar Wine
    if current_system == "darwin" and target_system == "windows":
        print("⚠️  Cross-compilation a Windows desde Mac...")
        print("Nota: Esto creará un ejecutable básico. Para mejor compatibilidad, construye en Windows.")
    
    subprocess.run([sys.executable, "-m", "PyInstaller", spec_file, "--clean", "--noconfirm"])
    
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
    
    print(f"Distribución creada en:")
    print(f"  📁 {dist_dir} (con timestamp)")
    print(f"  📁 {latest_dir} (latest)")

def create_launch_script(dist_dir, target_system):
    """Crear script para abrir navegador automáticamente"""
    
    if target_system == "darwin":
        script_content = '''#!/bin/bash
echo "Iniciando YT-DLP Music API..."
open -a "YT-DLP-Music-API.app"
sleep 3
echo "Abriendo navegador en puerto 8080..."
open "http://localhost:8080"
'''
        script_path = dist_dir / "launch.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        # También copiar scripts de utilidad
        if Path("check_port.sh").exists():
            shutil.copy2("check_port.sh", dist_dir / "check_port.sh")
            os.chmod(dist_dir / "check_port.sh", 0o755)
        if Path("lsof_8080.sh").exists():
            shutil.copy2("lsof_8080.sh", dist_dir / "lsof_8080.sh")
            os.chmod(dist_dir / "lsof_8080.sh", 0o755)
        
    else:  # Windows
        script_content = '''@echo off
echo Iniciando YT-DLP Music API...
start "" "YT-DLP-Music-API.exe"
timeout /t 3 /nobreak >nul
echo Abriendo navegador en puerto 8080...
start "" "http://localhost:8080"
'''
        script_path = dist_dir / "launch.bat"
        with open(script_path, "w") as f:
            f.write(script_content)
            
        # Script para verificar puerto en Windows
        port_check_script = '''@echo off
echo Verificando puerto 8080...
netstat -an | find ":8080"
if %errorlevel% == 0 (
    echo Puerto 8080 está en uso
) else (
    echo Puerto 8080 está libre
)
pause
'''
        with open(dist_dir / "check_port.bat", "w") as f:
            f.write(port_check_script)

def create_readme(dist_dir, target_system, version):
    """Crear README específico para la distribución"""
    readme_content = f"""# YT-DLP Music API - {target_system.title()} Distribution

**Versión:** {version}  
**Generado:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Plataforma:** {target_system.title()}

## 🚀 Inicio Rápido

### {target_system.title()}:
```{'bash' if target_system == 'darwin' else 'cmd'}
{'./launch.sh' if target_system == 'darwin' else 'launch.bat'}
```

## 📁 Contenido

- **YT-DLP-Music-API.{'app' if target_system == 'darwin' else 'exe'}** - Aplicación principal
- **launch.{'sh' if target_system == 'darwin' else 'bat'}** - Script de inicio
- **check_port.{'sh' if target_system == 'darwin' else 'bat'}** - Verificar puerto 8080
- **README.md** - Esta documentación

## ✅ Características

- ✅ Puerto fijo: 8080
- ✅ Sin dependencias externas
- ✅ Detección automática de playlists  
- ✅ Descargas paralelas
- ✅ Progreso en tiempo real
- ✅ Compatible con YouTube, YouTube Music

## 🔧 Solución de problemas

### Error: max_workers referenced before assignment
Este error ha sido corregido en esta versión.

### Puerto ocupado
Usar `check_port.{'sh' if target_system == 'darwin' else 'bat'}` para diagnosticar.

### La aplicación no inicia
{'- Verificar permisos: `chmod +x *.sh`' if target_system == 'darwin' else '- Ejecutar como administrador si es necesario'}
- Verificar que el puerto 8080 esté libre

---
*Construido con PyInstaller desde {platform.system()}*
"""
    
    with open(dist_dir / "README.md", "w") as f:
        f.write(readme_content)

def main():
    parser = argparse.ArgumentParser(description='Constructor Incremental de YT-DLP Music API Standalone')
    parser.add_argument('--target', choices=['darwin', 'windows', 'both'], 
                       default=None, help='Plataforma objetivo')
    parser.add_argument('--current-only', action='store_true', 
                       help='Solo construir para la plataforma actual')
    
    args = parser.parse_args()
    
    current_system = platform.system().lower()
    
    print("=== Constructor Incremental de YT-DLP Music API ===")
    print(f"Sistema actual: {current_system}")
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
                    print(f"   {dist.name}")
    
    for target in targets:
        print(f"\n🔨 Construyendo para {target}...")
        
        # Descargar binarios necesarios para el target específico
        download_binaries(target)
        
        # Construir ejecutable
        build_executable(target)
        
        print(f"✅ Distribución para {target} completada!")
    
    print(f"\n🎉 Todas las distribuciones completadas!")
    print("📁 Archivos generados en el directorio 'distributions/'")
    
    for target in targets:
        if target == 'darwin':
            print(f"🍎 Mac: usa ./distributions/darwin/launch.sh")
        else:
            print(f"🪟 Windows: usa ./distributions/windows/launch.bat")

if __name__ == "__main__":
    main()