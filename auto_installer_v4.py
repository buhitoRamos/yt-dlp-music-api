#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Music API - Auto Installer v4
Instalador automático de Python y dependencias para usuarios sin conocimientos técnicos
"""

import os
import sys
import platform
import subprocess
import urllib.request
import tempfile
import zipfile
import shutil
from pathlib import Path
import json

class AutoInstaller:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.temp_dir = Path(tempfile.gettempdir()) / "ytdlp_installer"
        self.install_dir = self.root_dir / "python_portable"
        self.system = platform.system().lower()
        
    def create_temp_dir(self):
        """Crea directorio temporal"""
        self.temp_dir.mkdir(exist_ok=True)
        
    def cleanup_temp(self):
        """Limpia archivos temporales"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def check_python_installed(self):
        """Verifica si Python está instalado"""
        try:
            result = subprocess.run([sys.executable, "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ Python encontrado: {version}")
                return True
        except:
            pass
        
        print("❌ Python no encontrado o no funcional")
        return False
    
    def download_file(self, url, filename):
        """Descarga un archivo con barra de progreso"""
        filepath = self.temp_dir / filename
        
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded * 100) // total_size)
                print(f"\r📥 Descargando {filename}: {percent}%", end="", flush=True)
        
        try:
            urllib.request.urlretrieve(url, filepath, progress_hook)
            print(f"\n✅ {filename} descargado")
            return filepath
        except Exception as e:
            print(f"\n❌ Error descargando {filename}: {e}")
            return None
    
    def install_python_windows(self):
        """Instala Python portable en Windows"""
        print("🐍 Instalando Python portable para Windows...")
        
        # URL de Python embebido
        python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        
        # Descargar Python embebido
        python_zip = self.download_file(python_url, "python-embed.zip")
        if not python_zip:
            return False
        
        # Extraer Python
        print("📂 Extrayendo Python...")
        with zipfile.ZipFile(python_zip, 'r') as zip_ref:
            zip_ref.extractall(self.install_dir)
        
        # Descargar get-pip.py
        pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip = self.download_file(pip_url, "get-pip.py")
        if not get_pip:
            return False
        
        # Configurar pth file para imports
        pth_content = """import site; site.main()
../Lib
../lib/site-packages
"""
        pth_file = self.install_dir / "python311._pth"
        pth_file.write_text(pth_content)
        
        # Instalar pip
        python_exe = self.install_dir / "python.exe"
        cmd = [str(python_exe), str(get_pip), "--target", str(self.install_dir / "lib" / "site-packages")]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error instalando pip: {result.stderr}")
            return False
        
        print("✅ Python portable instalado correctamente")
        return True
    
    def install_python_macos(self):
        """Instala Python usando Homebrew en macOS"""
        print("🐍 Verificando Python en macOS...")
        
        # Intentar usar el Python del sistema primero
        system_pythons = [
            "/usr/bin/python3",
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3"
        ]
        
        for python_path in system_pythons:
            if Path(python_path).exists():
                try:
                    result = subprocess.run([python_path, "--version"], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"✅ Usando Python del sistema: {python_path}")
                        # Crear symlink en nuestro directorio
                        self.install_dir.mkdir(exist_ok=True)
                        python_link = self.install_dir / "python"
                        if python_link.exists():
                            python_link.unlink()
                        python_link.symlink_to(python_path)
                        return True
                except:
                    continue
        
        print("❌ No se encontró Python funcional en macOS")
        print("💡 Por favor instala Python desde python.org o usando Homebrew")
        return False
    
    def install_dependencies(self):
        """Instala las dependencias de Python"""
        print("📦 Instalando dependencias...")
        
        if self.system == "windows":
            python_exe = self.install_dir / "python.exe"
            pip_cmd = [str(python_exe), "-m", "pip"]
        else:
            python_exe = self.install_dir / "python"
            if python_exe.exists():
                pip_cmd = [str(python_exe), "-m", "pip"]
            else:
                pip_cmd = [sys.executable, "-m", "pip"]
        
        # Instalar dependencias
        requirements = ["flask==3.1.2", "flask-cors==6.0.1", "yt-dlp", "beepy"]
        
        for req in requirements:
            print(f"📥 Instalando {req}...")
            if self.system == "windows":
                install_cmd = pip_cmd + ["install", req, "--target", 
                                       str(self.install_dir / "lib" / "site-packages")]
            else:
                install_cmd = pip_cmd + ["install", req, "--user"]
            
            result = subprocess.run(install_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Error instalando {req}: {result.stderr}")
                return False
            else:
                print(f"✅ {req} instalado")
        
        return True
    
    def create_launcher(self):
        """Crea launcher optimizado"""
        print("🚀 Creando launcher...")
        
        if self.system == "windows":
            launcher_content = f'''@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0;%~dp0\\lib\\site-packages
"%~dp0\\python_portable\\python.exe" api_downloader.py
pause
'''
            launcher_file = self.root_dir / "🚀 Iniciar YT-DLP (Windows Auto).bat"
            launcher_file.write_text(launcher_content, encoding='utf-8')
            
        else:  # macOS/Linux
            launcher_content = f'''#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$PWD:$PWD/lib/site-packages"
{self.install_dir}/python api_downloader.py
'''
            launcher_file = self.root_dir / "🚀 Iniciar YT-DLP (macOS Auto).command"
            launcher_file.write_text(launcher_content, encoding='utf-8')
            os.chmod(launcher_file, 0o755)
        
        print(f"✅ Launcher creado: {launcher_file.name}")
        return launcher_file
    
    def install(self):
        """Proceso principal de instalación"""
        print("=" * 60)
        print("🔧 YT-DLP Music API - Auto Installer v4")
        print("🎯 Configuración automática para usuarios no técnicos")
        print("=" * 60)
        
        try:
            # Crear directorio temporal
            self.create_temp_dir()
            
            # Verificar si Python ya está disponible
            if self.check_python_installed():
                print("✅ Python ya está disponible")
                if self.install_dependencies():
                    print("✅ Dependencias instaladas")
                    self.create_launcher()
                    print("🎉 ¡Instalación completada!")
                    return True
                else:
                    print("❌ Error instalando dependencias")
                    return False
            
            # Instalar Python según el sistema
            if self.system == "windows":
                if not self.install_python_windows():
                    return False
            elif self.system == "darwin":
                if not self.install_python_macos():
                    return False
            else:
                print("❌ Sistema operativo no soportado")
                return False
            
            # Instalar dependencias
            if not self.install_dependencies():
                return False
            
            # Crear launcher
            self.create_launcher()
            
            print("\n🎉 ¡Instalación completada exitosamente!")
            print("🚀 Usa el nuevo launcher para ejecutar la aplicación")
            
            return True
            
        except Exception as e:
            print(f"❌ Error durante la instalación: {e}")
            return False
        
        finally:
            # Limpiar archivos temporales
            self.cleanup_temp()

def main():
    """Función principal"""
    installer = AutoInstaller()
    success = installer.install()
    
    if not success:
        print("\n❌ La instalación falló")
        print("💡 Opciones alternativas:")
        print("   1. Instala Python manualmente desde python.org")
        print("   2. Usa la versión standalone (si está disponible)")
        print("   3. Contacta al desarrollador para soporte")
    
    input("\nPresiona Enter para continuar...")
    return success

if __name__ == "__main__":
    main()