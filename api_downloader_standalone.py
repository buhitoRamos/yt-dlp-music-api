#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Music API - Standalone Version v4
Versión optimizada para empaquetado standalone con PyInstaller
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import subprocess
import os
import sys
import json
import tempfile
import threading
import time
import random
from datetime import datetime
import re
import concurrent.futures
import webbrowser
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
from pathlib import Path

# === CONFIGURACIÓN STANDALONE ===
def get_resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, compatible con PyInstaller"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_executable_path(executable_name):
    """Obtiene la ruta del ejecutable según el sistema operativo"""
    if sys.platform == "win32":
        return get_resource_path(f"binaries/windows/{executable_name}.exe")
    elif sys.platform == "darwin":
        return get_resource_path(f"binaries/darwin/{executable_name}")
    else:
        return get_resource_path(f"binaries/linux/{executable_name}")

def get_default_output_dir():
    """Obtiene el directorio de salida por defecto según el sistema"""
    home = Path.home()
    if sys.platform == "win32":
        return str(home / "Music" / "YT-DLP Downloads")
    elif sys.platform == "darwin":
        return str(home / "Music" / "YT-DLP Downloads")
    else:
        return str(home / "Music" / "YT-DLP Downloads")

# Configuración
DEFAULT_OUTPUT_DIR = get_default_output_dir()
DOWNLOADS_STATUS = {}
GLOBAL_METRICS = {
    'status_requests': 0,
    'download_requests': 0,
    'active_jobs_peak': 0
}

# Caché sencilla de último cliente exitoso por tipo de contenido
CLIENT_CACHE = {}

# Ruta de cookies cargadas en runtime (upload) opcional
UPLOADED_COOKIES_PATH = None

# === SERVIDOR HTTP STANDALONE ===
class StandaloneHTTPHandler(BaseHTTPRequestHandler):
    """Servidor HTTP optimizado para versión standalone"""
    
    def log_message(self, format, *args):
        # Silenciar logs automáticos del servidor
        pass
    
    def send_cors_headers(self):
        """Envía headers CORS"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_GET(self):
        """Maneja peticiones GET"""
        try:
            if self.path == '/':
                self.serve_frontend_file('index.html', 'text/html')
            elif self.path.startswith('/css/'):
                file_path = self.path[1:]  # Remove leading /
                self.serve_frontend_file(file_path, 'text/css')
            elif self.path.startswith('/js/'):
                file_path = self.path[1:]  # Remove leading /
                self.serve_frontend_file(file_path, 'application/javascript')
            elif self.path.startswith('/status/'):
                job_id = self.path.split('/')[-1]
                self.handle_status(job_id)
            elif self.path == '/formats':
                self.handle_formats()
            elif self.path == '/jobs':
                self.handle_jobs()
            elif self.path == '/environment':
                self.handle_environment()
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Error GET: {e}")
            self.send_error(500)
    
    def do_POST(self):
        """Maneja peticiones POST"""
        try:
            if self.path == '/download':
                self.handle_download()
            elif self.path == '/shutdown':
                self.handle_shutdown()
            elif self.path.startswith('/cancel/'):
                job_id = self.path.split('/')[-1]
                self.handle_cancel(job_id)
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Error POST: {e}")
            self.send_error(500)
    
    def do_OPTIONS(self):
        """Maneja peticiones OPTIONS para CORS preflight"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def serve_frontend_file(self, file_path, content_type):
        """Sirve archivos del frontend"""
        try:
            full_path = get_resource_path(f"frontend/{file_path}")
            
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)
                
        except Exception as e:
            print(f"Error sirviendo archivo {file_path}: {e}")
            self.send_error(500)
    
    def handle_status(self, job_id):
        """Maneja consultas de estado"""
        global GLOBAL_METRICS
        GLOBAL_METRICS['status_requests'] += 1
        
        if job_id in DOWNLOADS_STATUS:
            status = DOWNLOADS_STATUS[job_id]
            response = json.dumps(status).encode('utf-8')
        else:
            response = json.dumps({"error": "Job not found"}).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response)
    
    def handle_formats(self):
        """Maneja consulta de formatos disponibles"""
        formats = {
            "audio": [
                {"id": "mp3", "name": "MP3 (Mejor calidad)", "ext": "mp3"},
                {"id": "m4a", "name": "M4A (iTunes)", "ext": "m4a"}
            ],
            "video": [
                {"id": "mp4", "name": "MP4 (1080p)", "ext": "mp4"},
                {"id": "webm", "name": "WebM", "ext": "webm"}
            ]
        }
        
        response = json.dumps(formats).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response)
    
    def handle_jobs(self):
        """Maneja consulta de trabajos activos"""
        active_jobs = {
            job_id: {
                'url': status.get('url', ''),
                'format': status.get('format', ''),
                'status': status.get('status', 'unknown'),
                'progress': status.get('progress', 0)
            }
            for job_id, status in DOWNLOADS_STATUS.items()
            if status.get('status') in ['downloading', 'processing', 'pending']
        }
        
        response = json.dumps(active_jobs).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response)
    
    def handle_environment(self):
        """Maneja consulta del entorno"""
        env_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "default_output_dir": DEFAULT_OUTPUT_DIR,
            "ffmpeg_path": get_executable_path("ffmpeg"),
            "ytdlp_path": get_executable_path("yt-dlp"),
            "is_standalone": hasattr(sys, '_MEIPASS'),
            "version": "4.0-standalone"
        }
        
        response = json.dumps(env_info).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response)
    
    def handle_download(self):
        """Maneja peticiones de descarga"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            url = data.get('url', '').strip()
            format_type = data.get('format', 'mp3')
            output_dir = data.get('output_dir', DEFAULT_OUTPUT_DIR)
            
            if not url:
                self.send_json_response({"error": "URL is required"}, 400)
                return
            
            # Crear directorio de salida si no existe
            os.makedirs(output_dir, exist_ok=True)
            
            # Generar ID único para el trabajo
            job_id = f"job_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            
            # Inicializar estado
            DOWNLOADS_STATUS[job_id] = {
                'id': job_id,
                'url': url,
                'format': format_type,
                'output_dir': output_dir,
                'status': 'pending',
                'progress': 0,
                'message': 'Iniciando descarga...',
                'start_time': time.time(),
                'file_path': None,
                'error': None
            }
            
            # Iniciar descarga en hilo separado
            thread = threading.Thread(
                target=self.process_download,
                args=(job_id, url, format_type, output_dir),
                daemon=True
            )
            thread.start()
            
            global GLOBAL_METRICS
            GLOBAL_METRICS['download_requests'] += 1
            
            self.send_json_response({"job_id": job_id, "status": "started"})
            
        except Exception as e:
            print(f"Error en handle_download: {e}")
            self.send_json_response({"error": str(e)}, 500)
    
    def send_json_response(self, data, status_code=200):
        """Envía respuesta JSON"""
        response = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response)
    
    def process_download(self, job_id, url, format_type, output_dir):
        """Procesa la descarga en segundo plano"""
        try:
            status = DOWNLOADS_STATUS[job_id]
            status['status'] = 'processing'
            status['message'] = 'Preparando descarga...'
            
            # Construir comando yt-dlp
            ytdlp_path = get_executable_path("yt-dlp")
            ffmpeg_path = get_executable_path("ffmpeg")
            
            cmd = [ytdlp_path]
            
            # Configuración de formato
            if format_type in ['mp3', 'audio']:
                cmd.extend([
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',
                    '--embed-metadata',
                    '--add-metadata'
                ])
                output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
            else:  # video
                cmd.extend([
                    '--format', 'best[height<=1080]',
                    '--merge-output-format', 'mp4'
                ])
                output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
            
            cmd.extend([
                '--output', output_template,
                '--ffmpeg-location', ffmpeg_path,
                '--no-warnings',
                '--ignore-errors'
            ])
            
            # Agregar cookies si existen
            cookies_path = get_resource_path("www.youtube.com_cookies.txt")
            if os.path.exists(cookies_path):
                cmd.extend(['--cookies', cookies_path])
            
            cmd.append(url)
            
            status['status'] = 'downloading'
            status['message'] = 'Descargando...'
            
            # Ejecutar comando
            print(f"Ejecutando: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=output_dir
            )
            
            # Monitorear progreso
            while process.poll() is None:
                time.sleep(1)
                status['progress'] = min(90, status.get('progress', 0) + 5)
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                status['status'] = 'completed'
                status['progress'] = 100
                status['message'] = 'Descarga completada exitosamente'
                
                # Buscar archivo descargado
                files = list(Path(output_dir).glob('*'))
                if files:
                    # Tomar el archivo más reciente
                    latest_file = max(files, key=lambda f: f.stat().st_mtime)
                    status['file_path'] = str(latest_file)
                    status['file_name'] = latest_file.name
                    status['file_size'] = latest_file.stat().st_size
                
            else:
                status['status'] = 'error'
                status['error'] = stderr or 'Error desconocido durante la descarga'
                status['message'] = f'Error: {status["error"]}'
                print(f"Error yt-dlp: {stderr}")
            
        except Exception as e:
            status['status'] = 'error'
            status['error'] = str(e)
            status['message'] = f'Error interno: {str(e)}'
            print(f"Error process_download: {e}")
        
        finally:
            status['end_time'] = time.time()
            status['duration'] = status['end_time'] - status['start_time']
    
    def handle_cancel(self, job_id):
        """Maneja cancelación de trabajos"""
        if job_id in DOWNLOADS_STATUS:
            status = DOWNLOADS_STATUS[job_id]
            if status['status'] in ['pending', 'downloading', 'processing']:
                status['status'] = 'cancelled'
                status['message'] = 'Descarga cancelada por el usuario'
                self.send_json_response({"message": "Job cancelled"})
            else:
                self.send_json_response({"error": "Job cannot be cancelled"}, 400)
        else:
            self.send_json_response({"error": "Job not found"}, 404)
    
    def handle_shutdown(self):
        """Maneja cierre del servidor"""
        self.send_json_response({"message": "Shutting down..."})
        # Enviar señal de cierre en hilo separado
        threading.Thread(target=self.delayed_shutdown, daemon=True).start()
    
    def delayed_shutdown(self):
        """Cierre retrasado del servidor"""
        time.sleep(1)
        os._exit(0)

# === FUNCIONES PRINCIPALES ===
def start_standalone_server(port=8080):
    """Inicia el servidor standalone"""
    print(f"🌐 Iniciando servidor en puerto {port}...")
    
    try:
        with socketserver.TCPServer(("", port), StandaloneHTTPHandler) as httpd:
            print(f"✅ Servidor iniciado en http://localhost:{port}")
            print("🎵 YT-DLP Music API v4.0 - Standalone")
            print("👨‍💻 Desarrollado por Martin Gaston Lopez")
            print("=" * 50)
            print("🌐 Abre tu navegador en: http://localhost:8080")
            print("⏹️  Presiona Ctrl+C para detener")
            print("=" * 50)
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Cerrando servidor...")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Puerto {port} ya está en uso")
            print("💡 Prueba con otro puerto o cierra otras aplicaciones")
        else:
            print(f"❌ Error del servidor: {e}")

def setup_environment():
    """Configura el entorno standalone"""
    print("🔧 Configurando entorno standalone...")
    
    # Verificar binarios
    ffmpeg_path = get_executable_path("ffmpeg")
    ytdlp_path = get_executable_path("yt-dlp")
    
    if not os.path.exists(ffmpeg_path):
        print(f"❌ FFmpeg no encontrado en: {ffmpeg_path}")
        return False
    
    if not os.path.exists(ytdlp_path):
        print(f"❌ yt-dlp no encontrado en: {ytdlp_path}")
        return False
    
    # Hacer ejecutables en Unix
    if sys.platform != "win32":
        try:
            os.chmod(ffmpeg_path, 0o755)
            os.chmod(ytdlp_path, 0o755)
        except:
            pass
    
    # Crear directorio de salida por defecto
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    
    print("✅ Entorno configurado correctamente")
    return True

def open_browser_delayed():
    """Abre el navegador después de unos segundos"""
    time.sleep(3)
    try:
        webbrowser.open("http://localhost:8080")
        print("🌐 Navegador abierto automáticamente")
    except:
        print("⚠️  No se pudo abrir el navegador automáticamente")
        print("🔗 Abre manualmente: http://localhost:8080")

def main():
    """Función principal"""
    print("🎵 YT-DLP Music API - Standalone v4.0")
    print("=" * 50)
    
    # Configurar entorno
    if not setup_environment():
        print("❌ Error en la configuración del entorno")
        input("Presiona Enter para salir...")
        return
    
    # Abrir navegador en hilo separado
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()
    
    # Iniciar servidor
    try:
        start_standalone_server()
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()