#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Music API - Standalone Builder v4
Construye versiones completamente autocontenidas para Windows y macOS
No requiere instalación de Python ni dependencias
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path
import json

class StandaloneBuilder:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.build_dir = self.root_dir / "build_standalone_v4"
        self.dist_dir = self.root_dir / "dist_standalone_v4"
        self.version = "v4.0"
        
    def clean_build_dirs(self):
        """Limpia directorios de construcción"""
        print("🧹 Limpiando directorios...")
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def prepare_source(self):
        """Prepara el código fuente optimizado"""
        print("📝 Preparando código fuente...")
        
        # Crear directorio de fuentes
        src_dir = self.build_dir / "src"
        src_dir.mkdir(exist_ok=True)
        
        # Copiar archivos principales
        shutil.copy2(self.root_dir / "api_downloader.py", src_dir / "api_downloader.py")
        shutil.copy2(self.root_dir / "requirements.txt", src_dir / "requirements.txt")
        
        # Copiar frontend
        frontend_src = self.root_dir / "frontend"
        frontend_dst = src_dir / "frontend"
        if frontend_src.exists():
            shutil.copytree(frontend_src, frontend_dst)
        
        # Copiar binarios
        binaries_src = self.root_dir / "binaries"
        binaries_dst = src_dir / "binaries"
        if binaries_src.exists():
            shutil.copytree(binaries_src, binaries_dst)
        
        # Copiar cookies si existen
        cookies_file = self.root_dir / "www.youtube.com_cookies.txt"
        if cookies_file.exists():
            shutil.copy2(cookies_file, src_dir / "www.youtube.com_cookies.txt")
        
        return src_dir
    
    def create_launcher_script(self, src_dir):
        """Crea script launcher optimizado"""
        print("🚀 Creando launcher...")
        
        launcher_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Music API - Standalone Launcher v4
Launcher autocontenido que no requiere dependencias externas
"""

import os
import sys
import webbrowser
import time
import threading
from pathlib import Path

def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, funciona para PyInstaller"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def check_and_setup_environment():
    """Verifica y configura el entorno"""
    print("🔧 Configurando entorno...")
    
    # Verificar binarios
    if sys.platform == "win32":
        ffmpeg_path = resource_path("binaries/windows/ffmpeg.exe")
        ytdlp_path = resource_path("binaries/windows/yt-dlp.exe")
    elif sys.platform == "darwin":
        ffmpeg_path = resource_path("binaries/darwin/ffmpeg")
        ytdlp_path = resource_path("binaries/darwin/yt-dlp")
    else:
        print("❌ Sistema operativo no soportado")
        return False
    
    # Verificar que existen los binarios
    if not os.path.exists(ffmpeg_path) or not os.path.exists(ytdlp_path):
        print("❌ Binarios no encontrados")
        return False
    
    # Hacer ejecutables en Unix
    if sys.platform != "win32":
        try:
            os.chmod(ffmpeg_path, 0o755)
            os.chmod(ytdlp_path, 0o755)
        except:
            pass
    
    return True

def open_browser():
    """Abre el navegador después de unos segundos"""
    time.sleep(3)
    try:
        webbrowser.open("http://localhost:8080")
        print("🌐 Navegador abierto en http://localhost:8080")
    except:
        print("⚠️  No se pudo abrir el navegador automáticamente")
        print("🔗 Abre manualmente: http://localhost:8080")

def main():
    """Función principal"""
    print("=" * 60)
    print("🎵 YT-DLP Music API - Standalone v4.0")
    print("📱 Descargador de música y videos de YouTube")
    print("👨‍💻 Desarrollado por Martin Gaston Lopez")
    print("=" * 60)
    
    # Verificar entorno
    if not check_and_setup_environment():
        input("❌ Error en la configuración. Presiona Enter para salir...")
        return
    
    print("✅ Entorno configurado correctamente")
    print("🚀 Iniciando servidor...")
    
    # Abrir navegador en un hilo separado
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Importar y ejecutar la aplicación principal
    try:
        # Agregar el directorio actual al path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Importar y ejecutar
        from api_downloader import main as api_main
        api_main()
        
    except KeyboardInterrupt:
        print("\\n👋 Cerrando aplicación...")
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()
'''
        
        launcher_path = src_dir / "launcher.py"
        launcher_path.write_text(launcher_content, encoding='utf-8')
        return launcher_path
    
    def create_pyinstaller_spec(self, src_dir, platform):
        """Crea archivo .spec para PyInstaller"""
        print(f"📋 Creando spec para {platform}...")
        
        if platform == "windows":
            exe_name = "YT-DLP-Music-API-Standalone.exe"
            icon_file = None  # Podemos agregar un .ico después
        else:  # macOS
            exe_name = "YT-DLP-Music-API-Standalone"
            icon_file = None  # Podemos agregar un .icns después
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['{src_dir}/launcher.py'],
             pathex=['{src_dir}'],
             binaries=[],
             datas=[
                 ('{src_dir}/frontend', 'frontend'),
                 ('{src_dir}/binaries', 'binaries'),
                 ('{src_dir}/www.youtube.com_cookies.txt', '.'),
             ],
             hiddenimports=[
                 'flask',
                 'flask_cors',
                 'subprocess',
                 'json',
                 'tempfile',
                 'threading',
                 'webbrowser',
                 'urllib.request',
                 'urllib.parse',
                 'http.server',
                 'socketserver',
             ],
             hookspath=[],
             hooksconfig={{}},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='{exe_name}',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
'''
        
        spec_path = self.build_dir / f"app_{platform}.spec"
        spec_path.write_text(spec_content)
        return spec_path
    
    def build_executable(self, spec_path, platform):
        """Construye el ejecutable usando PyInstaller"""
        print(f"🔨 Construyendo ejecutable para {platform}...")
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_path)
        ]
        
        result = subprocess.run(cmd, cwd=self.build_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error construyendo {platform}:")
            print(result.stderr)
            return False
        
        print(f"✅ Ejecutable {platform} construido exitosamente")
        return True
    
    def create_distribution_package(self, platform):
        """Crea el paquete de distribución final"""
        print(f"📦 Creando paquete de distribución para {platform}...")
        
        # Crear directorio de distribución
        dist_platform_dir = self.dist_dir / platform
        dist_platform_dir.mkdir(exist_ok=True)
        
        # Copiar ejecutable
        if platform == "windows":
            exe_source = self.build_dir / "dist" / "YT-DLP-Music-API-Standalone.exe"
            exe_dest = dist_platform_dir / "YT-DLP-Music-API-Standalone.exe"
        else:  # macOS
            exe_source = self.build_dir / "dist" / "YT-DLP-Music-API-Standalone"
            exe_dest = dist_platform_dir / "YT-DLP-Music-API-Standalone"
        
        if exe_source.exists():
            shutil.copy2(exe_source, exe_dest)
            # Hacer ejecutable en Unix
            if platform != "windows":
                os.chmod(exe_dest, 0o755)
        
        # Crear README específico para standalone
        readme_content = f'''# 🎵 YT-DLP Music API - Standalone {self.version}

## 🎯 ¿Qué es esto?
Una aplicación **completamente autocontenida** para descargar música y videos de YouTube.
**NO NECESITAS INSTALAR PYTHON NI DEPENDENCIAS** - ¡Todo está incluido!

## ✨ Características
- 🎵 Descarga música en MP3
- 🎬 Descarga videos en MP4
- 🎼 Listas de reproducción completas
- 🔥 YouTube Shorts
- 🌐 Interfaz web fácil de usar
- 📱 Compatible con YouTube Music

## 🚀 ¿Cómo usar? (SÚPER FÁCIL)

### 🪟 **Windows:**
1. Haz **doble clic** en `YT-DLP-Music-API-Standalone.exe`
2. Espera unos segundos
3. Se abrirá automáticamente en tu navegador
4. ¡Listo para descargar!

### 🍎 **macOS:**
1. Haz **doble clic** en `YT-DLP-Music-API-Standalone`
2. Si aparece advertencia de seguridad:
   - Ve a "Preferencias del Sistema" → "Seguridad y Privacidad"
   - Haz clic en "Abrir de todas formas"
3. Se abrirá automáticamente en tu navegador
4. ¡Listo para descargar!

## 📁 ¿Dónde se guardan las descargas?
- **Windows:** En tu carpeta `Música` por defecto
- **macOS:** En tu carpeta `Music` por defecto
- Puedes cambiar la ubicación desde la interfaz web

## 🔧 ¿Qué incluye esta versión?
- ✅ Python embebido (no necesitas instalarlo)
- ✅ Todas las dependencias incluidas
- ✅ ffmpeg y yt-dlp integrados
- ✅ Interfaz web moderna
- ✅ Sistema de cookies para YouTube
- ✅ Todo en un solo archivo ejecutable

## 🆘 Problemas comunes

### Windows
- **Antivirus bloquea el archivo:** Es normal, márcalo como seguro
- **"No se puede ejecutar":** Ejecuta como administrador

### macOS
- **"App dañada":** Control+clic → "Abrir"
- **Advertencias de seguridad:** Ve a Preferencias → Seguridad

## 🌐 Uso de la aplicación
1. **Inicia la aplicación** (se abrirá el navegador)
2. **Pega la URL** de YouTube en el campo
3. **Selecciona formato** (MP3 para música, MP4 para video)
4. **Haz clic en Descargar**
5. **Espera** y disfruta tu música

## 👨‍💻 Desarrollado por
**Martin Gaston Lopez**

## 📞 Soporte
Si tienes problemas, revisa que:
- Tienes conexión a internet
- La URL de YouTube es válida
- Tienes espacio en disco
- No hay antivirus bloqueando

---
**Versión Standalone {self.version} - No requiere instalaciones adicionales**
'''
        
        readme_path = dist_platform_dir / "README.md"
        readme_path.write_text(readme_content, encoding='utf-8')
        
        return dist_platform_dir
    
    def create_zip_package(self, platform, dist_dir):
        """Crea el archivo ZIP final"""
        print(f"🗜️  Creando ZIP para {platform}...")
        
        zip_name = f"YT-DLP-Music-API-Standalone-{self.version}-{platform}.zip"
        zip_path = self.dist_dir / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in dist_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(dist_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ ZIP creado: {zip_path}")
        return zip_path
    
    def build_for_platform(self, platform):
        """Construye para una plataforma específica"""
        print(f"\n🎯 Construyendo para {platform.upper()}")
        print("=" * 50)
        
        # Preparar código fuente
        src_dir = self.prepare_source()
        
        # Crear launcher
        self.create_launcher_script(src_dir)
        
        # Crear spec de PyInstaller
        spec_path = self.create_pyinstaller_spec(src_dir, platform)
        
        # Construir ejecutable
        if not self.build_executable(spec_path, platform):
            return None
        
        # Crear paquete de distribución
        dist_platform_dir = self.create_distribution_package(platform)
        
        # Crear ZIP final
        zip_path = self.create_zip_package(platform, dist_platform_dir)
        
        return zip_path
    
    def build_all(self):
        """Construye para todas las plataformas"""
        print("🚀 Iniciando construcción standalone v4")
        print("=" * 60)
        
        # Limpiar directorios
        self.clean_build_dirs()
        
        results = {}
        platforms = ["windows", "macos"]
        
        for platform in platforms:
            try:
                zip_path = self.build_for_platform(platform)
                if zip_path:
                    results[platform] = zip_path
                    print(f"✅ {platform}: {zip_path}")
                else:
                    print(f"❌ {platform}: Error en la construcción")
            except Exception as e:
                print(f"❌ {platform}: {e}")
        
        print("\n" + "=" * 60)
        print("📋 RESUMEN DE CONSTRUCCIÓN")
        print("=" * 60)
        
        if results:
            print("✅ Paquetes creados exitosamente:")
            for platform, path in results.items():
                print(f"   🎯 {platform.upper()}: {path.name}")
                print(f"      📁 Tamaño: {path.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            print("❌ No se crearon paquetes")
        
        print("\n🎉 ¡Construcción completada!")
        print("📝 Los archivos están listos para distribución")
        print("🚀 Los usuarios ya NO necesitarán instalar Python ni dependencias")
        
        return results

def main():
    """Función principal"""
    builder = StandaloneBuilder()
    results = builder.build_all()
    return results

if __name__ == "__main__":
    main()