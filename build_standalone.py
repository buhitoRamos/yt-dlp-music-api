#!/usr/bin/env python3
"""
Script para crear distribuciones standalone de YT-DLP Music API
para Mac y Windows usando PyInstaller (incluyendo cross-compilation)
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import argparse

def download_binaries(target_system=None):
    """Descarga yt-dlp y ffmpeg para la plataforma especificada"""
    if target_system is None:
        target_system = platform.system().lower()
    
    # Crear directorio de binarios
    bin_dir = Path("binaries") / target_system
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Descargando binarios para {target_system}...")
    
    if target_system == "darwin":  # macOS
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
        shutil.rmtree(bin_dir / "ffmpeg-6.1.1-essentials_build", ignore_errors=True)
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
    
    with open("ytdlp-music-api.spec", "w") as f:
        f.write(spec_content)

def build_executable(target_system=None):
    """Construir el ejecutable usando PyInstaller"""
    current_system = platform.system().lower()
    if target_system is None:
        target_system = current_system
    
    print("Instalando PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    print(f"Creando archivo de especificación para {target_system}...")
    create_spec_file(target_system)
    
    print(f"Construyendo ejecutable para {target_system}...")
    
    # Para cross-compilation a Windows desde Mac, necesitamos usar Wine
    if current_system == "darwin" and target_system == "windows":
        print("⚠️  Cross-compilation a Windows desde Mac...")
        print("Nota: Esto creará un ejecutable básico. Para mejor compatibilidad, construye en Windows.")
    
    subprocess.run([sys.executable, "-m", "PyInstaller", "ytdlp-music-api.spec", "--clean"])
    
    # Crear estructura de distribución
    dist_dir = Path("distribution") / target_system
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Copiar ejecutable
    if target_system == "darwin":
        if Path("dist/YT-DLP-Music-API.app").exists():
            shutil.copytree("dist/YT-DLP-Music-API.app", 
                          dist_dir / "YT-DLP-Music-API.app", 
                          dirs_exist_ok=True)
    else:  # Windows
        if Path("dist/YT-DLP-Music-API.exe").exists():
            shutil.copy2("dist/YT-DLP-Music-API.exe", 
                        dist_dir / "YT-DLP-Music-API.exe")
        elif Path("dist/YT-DLP-Music-API").exists():
            # En caso de que se genere sin extensión
            shutil.copy2("dist/YT-DLP-Music-API", 
                        dist_dir / "YT-DLP-Music-API.exe")
    
    # Crear script de inicio
    create_launch_script(dist_dir, target_system)
    
    print(f"Distribución creada en: {dist_dir}")

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

def main():
    parser = argparse.ArgumentParser(description='Constructor de YT-DLP Music API Standalone')
    parser.add_argument('--target', choices=['darwin', 'windows', 'both'], 
                       default=None, help='Plataforma objetivo')
    parser.add_argument('--current-only', action='store_true', 
                       help='Solo construir para la plataforma actual')
    
    args = parser.parse_args()
    
    current_system = platform.system().lower()
    
    print("=== Constructor de YT-DLP Music API Standalone ===")
    print(f"Sistema actual: {current_system}")
    
    targets = []
    if args.target == 'both':
        targets = ['darwin', 'windows']
    elif args.target:
        targets = [args.target]
    elif args.current_only:
        targets = [current_system]
    else:
        # Por defecto, construir para sistema actual y Windows si estamos en Mac
        targets = [current_system]
        if current_system == 'darwin':
            print("💡 También puedes construir para Windows con: --target windows")
    
    for target in targets:
        print(f"\n🔨 Construyendo para {target}...")
        
        # Descargar binarios necesarios para el target específico
        download_binaries(target)
        
        # Construir ejecutable
        build_executable(target)
        
        print(f"✅ Distribución para {target} completada!")
    
    print(f"\n🎉 Todas las distribuciones completadas!")
    print("📁 Archivos generados en el directorio 'distribution/'")
    
    for target in targets:
        if target == 'darwin':
            print(f"🍎 Mac: usa ./distribution/darwin/launch.sh")
        else:
            print(f"🪟 Windows: usa ./distribution/windows/launch.bat")

def create_launch_script(dist_dir, system):
    """Crear script para abrir navegador automáticamente"""
    
    if system == "darwin":
        script_content = '''#!/bin/bash
echo "Iniciando YT-DLP Music API..."
open -a "YT-DLP-Music-API.app"
sleep 3
echo "Detectando puerto..."
for port in 8080 5000 8000 8888; do
    if lsof -i :$port | grep -q "YT-DLP"; then
        echo "Aplicación encontrada en puerto $port"
        open "http://localhost:$port"
        break
    fi
done
'''
        script_path = dist_dir / "launch.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
    else:  # Windows
        script_content = '''@echo off
echo Iniciando YT-DLP Music API...
start "" "YT-DLP-Music-API.exe"
timeout /t 3 /nobreak >nul
start "" "http://localhost:5000"
'''
        script_path = dist_dir / "launch.bat"
        with open(script_path, "w") as f:
            f.write(script_content)

def main():
    print("=== Constructor de YT-DLP Music API Standalone ===")
    print(f"Sistema detectado: {platform.system()}")
    
    # Descargar binarios necesarios
    download_binaries()
    
    # Construir ejecutable
    build_executable()
    
    print("\n✅ Distribución completada!")
    print("📁 Archivos generados en el directorio 'distribution/'")
    print("🚀 Usa el script launch.sh (Mac) o launch.bat (Windows) para iniciar")

if __name__ == "__main__":
    main()