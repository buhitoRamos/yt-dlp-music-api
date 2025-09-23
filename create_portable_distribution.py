#!/usr/bin/env python3
"""
Script para crear distribución portátil completa de YT-DLP Music API
Incluye todos los binarios necesarios para Windows, macOS y Linux
"""

import os
import sys
import urllib.request
import zipfile
import tarfile
import shutil
import stat
from pathlib import Path

# URLs de los binarios necesarios
BINARIES = {
    'yt-dlp': {
        'windows': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
        'darwin': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos',
        'linux': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp'
    },
    'ffmpeg': {
        'windows': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
        'darwin': 'https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip',
        'linux': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz'
    }
}

def download_file(url, filepath):
    """Descargar archivo con progreso"""
    print(f"📥 Descargando {os.path.basename(filepath)}...")
    try:
        urllib.request.urlretrieve(url, filepath)
        print(f"✅ Descargado: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"❌ Error descargando {url}: {e}")
        return False

def extract_ffmpeg_windows(zip_path, target_dir):
    """Extraer ffmpeg.exe y ffprobe.exe de Windows"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.filelist:
            if file_info.filename.endswith(('ffmpeg.exe', 'ffprobe.exe')):
                # Extraer solo el ejecutable, no toda la estructura
                filename = os.path.basename(file_info.filename)
                source = zip_ref.open(file_info)
                target = open(os.path.join(target_dir, filename), 'wb')
                shutil.copyfileobj(source, target)
                target.close()
                source.close()
                print(f"✅ Extraído: {filename}")

def extract_ffmpeg_darwin(zip_path, target_dir):
    """Extraer ffmpeg de macOS"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall('/tmp/ffmpeg_temp')
    
    # Encontrar y copiar ffmpeg
    for root, dirs, files in os.walk('/tmp/ffmpeg_temp'):
        for file in files:
            if file == 'ffmpeg':
                shutil.copy2(os.path.join(root, file), os.path.join(target_dir, 'ffmpeg'))
                os.chmod(os.path.join(target_dir, 'ffmpeg'), 0o755)
                print("✅ Extraído: ffmpeg")
    
    # Para ffprobe, necesitaremos descargarlo por separado o usar otra fuente
    ffprobe_url = 'https://evermeet.cx/ffmpeg/ffprobe-6.0.zip'
    ffprobe_zip = '/tmp/ffprobe.zip'
    if download_file(ffprobe_url, ffprobe_zip):
        with zipfile.ZipFile(ffprobe_zip, 'r') as zip_ref:
            zip_ref.extractall('/tmp/ffprobe_temp')
        
        for root, dirs, files in os.walk('/tmp/ffprobe_temp'):
            for file in files:
                if file == 'ffprobe':
                    shutil.copy2(os.path.join(root, file), os.path.join(target_dir, 'ffprobe'))
                    os.chmod(os.path.join(target_dir, 'ffprobe'), 0o755)
                    print("✅ Extraído: ffprobe")

def extract_ffmpeg_linux(tar_path, target_dir):
    """Extraer ffmpeg y ffprobe de Linux"""
    with tarfile.open(tar_path, 'r:xz') as tar_ref:
        for member in tar_ref:
            if member.name.endswith(('ffmpeg', 'ffprobe')) and 'bin/' in member.name:
                # Extraer solo el ejecutable
                filename = os.path.basename(member.name)
                member.name = filename
                tar_ref.extract(member, target_dir)
                os.chmod(os.path.join(target_dir, filename), 0o755)
                print(f"✅ Extraído: {filename}")

def create_launcher_scripts(dist_dir, executable_name):
    """Crear scripts de lanzamiento para cada plataforma"""
    
    # Script para Windows (.bat)
    windows_script = f"""@echo off
title YT-DLP Music API
echo 🎵 YT-DLP Music API - Iniciando...
echo.
"{executable_name}"
pause
"""
    
    with open(os.path.join(dist_dir, "🚀 Iniciar YT-DLP (Windows).bat"), 'w', encoding='utf-8') as f:
        f.write(windows_script)
    
    # Script para macOS (.command)
    macos_script = f"""#!/bin/bash
cd "$(dirname "$0")"
echo "🎵 YT-DLP Music API - Iniciando..."
echo ""
./{executable_name}
"""
    
    macos_file = os.path.join(dist_dir, "🚀 Iniciar YT-DLP (macOS).command")
    with open(macos_file, 'w', encoding='utf-8') as f:
        f.write(macos_script)
    os.chmod(macos_file, 0o755)
    
    # Script para Linux (.sh)
    linux_script = f"""#!/bin/bash
cd "$(dirname "$0")"
echo "🎵 YT-DLP Music API - Iniciando..."
echo ""
./{executable_name}
"""
    
    linux_file = os.path.join(dist_dir, "🚀 Iniciar YT-DLP (Linux).sh")
    with open(linux_file, 'w', encoding='utf-8') as f:
        f.write(linux_script)
    os.chmod(linux_file, 0o755)

def create_readme(dist_dir):
    """Crear README con instrucciones"""
    readme_content = """# 🎵 YT-DLP Music API - Distribución Portátil
## powered by buh!to

## 🚀 Instrucciones de Uso

### Windows
1. Ejecuta: `🚀 Iniciar YT-DLP (Windows).bat`
2. Abre tu navegador en: http://localhost:8080

### macOS
1. Ejecuta: `🚀 Iniciar YT-DLP (macOS).command`
2. Abre tu navegador en: http://localhost:8080

### Linux
1. Ejecuta: `🚀 Iniciar YT-DLP (Linux).sh`
2. Abre tu navegador en: http://localhost:8080

## 📁 Carpetas de Descarga

- **Audio MP3**: `~/Downloads/Music/YT-DLP Downloads/`
- **Videos MP4**: `~/Downloads/Music/YT-DLP Downloads/Videos/`
- **Playlists**: `~/Downloads/Music/YT-DLP Downloads/Playlists/`

## ✨ Características

- ✅ **Sin instalaciones**: Todo incluido
- ✅ **Multiplataforma**: Windows, macOS, Linux
- ✅ **Mejor calidad**: Audio en calidad máxima
- ✅ **Metadatos**: Carátulas y información completa
- ✅ **Playlists completas**: Descarga listas enteras
- ✅ **Videos HD**: Hasta 1080p con subtítulos

## 🆘 Soporte

Si tienes problemas:
1. Asegúrate de tener conexión a internet
2. Verifica que el puerto 8080 esté libre
3. En macOS/Linux, da permisos de ejecución si es necesario

## 🔧 Contenido del Paquete

```
YT-DLP-Portable-by-buho/
├── YT-DLP-Simple-Complete-BestQuality  # Aplicación principal
├── binaries/                           # Herramientas necesarias
│   ├── windows/
│   ├── darwin/
│   └── linux/
├── 🚀 Iniciar YT-DLP (Windows).bat
├── 🚀 Iniciar YT-DLP (macOS).command
├── 🚀 Iniciar YT-DLP (Linux).sh
└── README.md
```

---
**Desarrollado con ❤️ por buh!to** 🦉

¡Disfruta descargando música y videos! 🎵🎬
"""
    
    with open(os.path.join(dist_dir, "README.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)

def main():
    """Función principal"""
    print("🎵 Creando distribución portátil de YT-DLP Music API")
    print("🦉 powered by buh!to")
    print("=" * 60)
    
    # Verificar que existe el ejecutable
    executable_path = "dist/YT-DLP-Simple-Complete-BestQuality(ok best)"
    if not os.path.exists(executable_path):
        print(f"❌ No se encuentra el ejecutable: {executable_path}")
        return
    
    # Crear directorio de distribución
    dist_name = "YT-DLP-Portable-by-buho"
    if os.path.exists(dist_name):
        shutil.rmtree(dist_name)
    
    os.makedirs(dist_name)
    print(f"📁 Creado directorio: {dist_name}")
    
    # Copiar ejecutable principal
    executable_name = "YT-DLP-Simple-Complete-BestQuality"
    shutil.copy2(executable_path, os.path.join(dist_name, executable_name))
    os.chmod(os.path.join(dist_name, executable_name), 0o755)
    print(f"✅ Copiado ejecutable principal")
    
    # Crear estructura de binarios
    for platform in ['windows', 'darwin', 'linux']:
        platform_dir = os.path.join(dist_name, 'binaries', platform)
        os.makedirs(platform_dir, exist_ok=True)
    
    # Descargar y configurar binarios
    temp_dir = '/tmp/yt_dlp_downloads'
    os.makedirs(temp_dir, exist_ok=True)
    
    print("\n📥 Descargando binarios necesarios...")
    
    # Descargar yt-dlp para cada plataforma
    for platform, url in BINARIES['yt-dlp'].items():
        filename = 'yt-dlp.exe' if platform == 'windows' else 'yt-dlp'
        temp_file = os.path.join(temp_dir, f"yt-dlp_{platform}")
        target_file = os.path.join(dist_name, 'binaries', platform, filename)
        
        if download_file(url, temp_file):
            shutil.copy2(temp_file, target_file)
            if platform != 'windows':
                os.chmod(target_file, 0o755)
    
    # Descargar y extraer FFmpeg
    print("\n📥 Descargando FFmpeg...")
    
    # Windows FFmpeg
    ffmpeg_win_zip = os.path.join(temp_dir, 'ffmpeg_win.zip')
    if download_file(BINARIES['ffmpeg']['windows'], ffmpeg_win_zip):
        extract_ffmpeg_windows(ffmpeg_win_zip, os.path.join(dist_name, 'binaries', 'windows'))
    
    # macOS FFmpeg
    ffmpeg_mac_zip = os.path.join(temp_dir, 'ffmpeg_mac.zip')
    if download_file(BINARIES['ffmpeg']['darwin'], ffmpeg_mac_zip):
        extract_ffmpeg_darwin(ffmpeg_mac_zip, os.path.join(dist_name, 'binaries', 'darwin'))
    
    # Linux FFmpeg
    ffmpeg_linux_tar = os.path.join(temp_dir, 'ffmpeg_linux.tar.xz')
    if download_file(BINARIES['ffmpeg']['linux'], ffmpeg_linux_tar):
        extract_ffmpeg_linux(ffmpeg_linux_tar, os.path.join(dist_name, 'binaries', 'linux'))
    
    # Crear scripts de lanzamiento
    print("\n📝 Creando scripts de lanzamiento...")
    create_launcher_scripts(dist_name, executable_name)
    
    # Crear README
    print("📄 Creando documentación...")
    create_readme(dist_name)
    
    # Limpiar archivos temporales
    shutil.rmtree(temp_dir, ignore_errors=True)
    shutil.rmtree('/tmp/ffmpeg_temp', ignore_errors=True)
    shutil.rmtree('/tmp/ffprobe_temp', ignore_errors=True)
    
    # Crear ZIP final
    print(f"\n📦 Creando archivo ZIP...")
    zip_name = f"{dist_name}.zip"
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_name):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, dist_name)
                zipf.write(file_path, arc_path)
    
    # Calcular tamaño
    zip_size = os.path.getsize(zip_name) / (1024 * 1024)  # MB
    
    print("\n" + "=" * 60)
    print("🎉 ¡Distribución portátil creada exitosamente!")
    print(f"📦 Archivo: {zip_name} ({zip_size:.1f} MB)")
    print(f"📁 Carpeta: {dist_name}/")
    print("\n✨ Características:")
    print("   ✅ Multiplataforma (Windows, macOS, Linux)")
    print("   ✅ Sin instalaciones necesarias")
    print("   ✅ Incluye todos los binarios")
    print("   ✅ Scripts de lanzamiento para cada OS")
    print("   ✅ Documentación completa")
    print("\n🚀 Para distribuir: Comparte el archivo ZIP")
    print("=" * 60)

if __name__ == "__main__":
    main()