#!/usr/bin/env python3
"""
Script para crear distribuciones standalone de YT-DLP Music API
para Mac y Windows usando PyInstaller
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def download_binaries():
    """Descarga yt-dlp y ffmpeg para la plataforma actual"""
    system = platform.system().lower()
    
    # Crear directorio de binarios
    bin_dir = Path("binaries") / system
    bin_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Descargando binarios para {system}...")
    
    if system == "darwin":  # macOS
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
        
    elif system == "windows":
        # Descargar yt-dlp para Windows
        subprocess.run([
            "curl", "-L",
            "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe",
            "-o", str(bin_dir / "yt-dlp.exe")
        ])
        
        # Descargar ffmpeg para Windows
        print("Descarga ffmpeg desde: https://www.gyan.dev/ffmpeg/builds/")
        print("Extrae ffmpeg.exe al directorio binaries/windows/")

def create_spec_file():
    """Crear archivo .spec para PyInstaller"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Detectar archivos adicionales según la plataforma
import platform
system = platform.system().lower()

added_files = []
if system == "darwin":
    added_files = [
        ('binaries/darwin/yt-dlp', 'binaries/'),
        ('binaries/darwin/ffmpeg', 'binaries/'),
        ('frontend', 'frontend/'),
        ('*.md', '.'),
    ]
elif system == "windows":
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
    hooksconfig={},
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
if platform.system() == "Darwin":
    app = BUNDLE(
        exe,
        name='YT-DLP-Music-API.app',
        icon=None,
        bundle_identifier='com.ytdlp.musicapi',
        info_plist={
            'CFBundleName': 'YT-DLP Music API',
            'CFBundleDisplayName': 'YT-DLP Music API',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        }
    )
'''
    
    with open("ytdlp-music-api.spec", "w") as f:
        f.write(spec_content)

def build_executable():
    """Construir el ejecutable usando PyInstaller"""
    system = platform.system().lower()
    
    print("Instalando PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    print("Creando archivo de especificación...")
    create_spec_file()
    
    print("Construyendo ejecutable...")
    subprocess.run([sys.executable, "-m", "PyInstaller", "ytdlp-music-api.spec", "--clean"])
    
    # Crear estructura de distribución
    dist_dir = Path("distribution") / system
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Copiar ejecutable
    if system == "darwin":
        if Path("dist/YT-DLP-Music-API.app").exists():
            shutil.copytree("dist/YT-DLP-Music-API.app", 
                          dist_dir / "YT-DLP-Music-API.app", 
                          dirs_exist_ok=True)
    else:
        if Path("dist/YT-DLP-Music-API.exe").exists():
            shutil.copy2("dist/YT-DLP-Music-API.exe", 
                        dist_dir / "YT-DLP-Music-API.exe")
    
    # Crear script de inicio
    create_launch_script(dist_dir, system)
    
    print(f"Distribución creada en: {dist_dir}")

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