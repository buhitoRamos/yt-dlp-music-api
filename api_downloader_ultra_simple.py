#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Music API - Ultra Simple Version v4
Versión ultra simplificada usando solo HTTP básico
"""

import subprocess
import os
import sys
import json
import threading
import time
import random
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# === CONFIGURACIÓN ===
def get_resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, compatible con PyInstaller"""
    try:
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
    return str(home / "Music" / "YT-DLP Downloads")

# Configuración global
DEFAULT_OUTPUT_DIR = get_default_output_dir()
DOWNLOADS_STATUS = {}

# === SERVIDOR HTTP BÁSICO ===
class YTDLPHandler(BaseHTTPRequestHandler):
    """Manejador HTTP ultra simple"""
    
    def log_message(self, format, *args):
        # Silenciar logs
        pass
    
    def do_GET(self):
        """Maneja peticiones GET"""
        try:
            if self.path == '/':
                self.serve_main_page()
            elif self.path.startswith('/status/'):
                job_id = self.path.split('/')[-1]
                self.serve_status(job_id)
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
            else:
                self.send_error(404)
        except Exception as e:
            print(f"Error POST: {e}")
            self.send_error(500)
    
    def do_OPTIONS(self):
        """Maneja CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def serve_main_page(self):
        """Sirve la página principal"""
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>YT-DLP Music API v4</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { 
            max-width: 600px; margin: 0 auto; background: white; 
            padding: 30px; border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 { 
            color: #ff0000; text-align: center; margin-bottom: 10px;
            font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .subtitle {
            text-align: center; color: #666; margin-bottom: 30px;
            font-size: 1.1em;
        }
        .form-group { margin: 20px 0; }
        label { 
            display: block; margin-bottom: 8px; font-weight: 600;
            color: #444; font-size: 1.1em;
        }
        input, select, button { 
            width: 100%; padding: 12px; border: 2px solid #ddd; 
            border-radius: 8px; font-size: 16px; transition: all 0.3s;
        }
        input:focus, select:focus { 
            border-color: #ff0000; outline: none;
            box-shadow: 0 0 10px rgba(255,0,0,0.1);
        }
        button { 
            background: linear-gradient(45deg, #ff0000, #cc0000);
            color: white; border: none; cursor: pointer; 
            font-weight: 600; margin-top: 15px;
            text-transform: uppercase; letter-spacing: 1px;
        }
        button:hover { 
            background: linear-gradient(45deg, #cc0000, #990000);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255,0,0,0.3);
        }
        .status { 
            margin-top: 20px; padding: 15px; border-radius: 8px; 
            display: none; font-weight: 500;
        }
        .success { 
            background: #d4edda; color: #155724; 
            border: 2px solid #c3e6cb;
        }
        .error { 
            background: #f8d7da; color: #721c24; 
            border: 2px solid #f5c6cb;
        }
        .info { 
            background: #d1ecf1; color: #0c5460; 
            border: 2px solid #bee5eb;
        }
        .footer {
            text-align: center; margin-top: 30px; color: #666;
            border-top: 1px solid #eee; padding-top: 20px;
        }
        .emoji { font-size: 1.5em; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 YT-DLP Music API</h1>
        <p class="subtitle">Descarga música y videos de YouTube • Versión Standalone v4.0</p>
        
        <div class="form-group">
            <label for="url"><span class="emoji">🔗</span>URL de YouTube:</label>
            <input type="text" id="url" placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ">
        </div>
        
        <div class="form-group">
            <label for="format"><span class="emoji">🎛️</span>Formato de descarga:</label>
            <select id="format">
                <option value="mp3">🎵 MP3 - Solo audio (recomendado para música)</option>
                <option value="mp4">🎬 MP4 - Video completo</option>
            </select>
        </div>
        
        <div class="form-group">
            <button onclick="download()">
                <span class="emoji">🚀</span>DESCARGAR AHORA
            </button>
        </div>
        
        <div id="status" class="status"></div>
        
        <div class="footer">
            <p>👨‍💻 Desarrollado por <strong>Martin Gaston Lopez</strong></p>
            <p>📁 Los archivos se guardan en: <code>~/Music/YT-DLP Downloads</code></p>
        </div>
    </div>
    
    <script>
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.innerHTML = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }
        
        function download() {
            const url = document.getElementById('url').value.trim();
            const format = document.getElementById('format').value;
            
            if (!url) {
                showStatus('❌ Por favor ingresa una URL de YouTube válida', 'error');
                return;
            }
            
            if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
                showStatus('❌ La URL debe ser de YouTube', 'error');
                return;
            }
            
            showStatus('⏳ Iniciando descarga...', 'info');
            
            fetch('/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, format: format })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showStatus('❌ Error: ' + data.error, 'error');
                } else {
                    showStatus('🎯 Descarga iniciada • ID: ' + data.job_id, 'success');
                    checkStatus(data.job_id);
                }
            })
            .catch(error => {
                showStatus('❌ Error de conexión: ' + error, 'error');
            });
        }
        
        function checkStatus(jobId) {
            fetch('/status/' + jobId)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    showStatus('✅ <strong>¡Descarga completada!</strong><br>📄 Archivo: ' + (data.file_name || 'guardado exitosamente'), 'success');
                } else if (data.status === 'error') {
                    showStatus('❌ <strong>Error en la descarga:</strong><br>' + (data.error || 'Error desconocido'), 'error');
                } else {
                    const progress = data.progress || 0;
                    showStatus('⏳ <strong>Descargando...</strong> (' + progress + '%)<br>' + (data.message || 'Procesando...'), 'info');
                    setTimeout(() => checkStatus(jobId), 2000);
                }
            })
            .catch(error => {
                console.error('Error checking status:', error);
                setTimeout(() => checkStatus(jobId), 2000);
            });
        }
        
        // Permitir envío con Enter
        document.getElementById('url').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                download();
            }
        });
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html.encode('utf-8'))))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_status(self, job_id):
        """Sirve el estado de una descarga"""
        if job_id in DOWNLOADS_STATUS:
            status = DOWNLOADS_STATUS[job_id]
        else:
            status = {"error": "Job not found"}
        
        response = json.dumps(status).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
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
            
            if not url:
                response = json.dumps({"error": "URL es requerida"}).encode('utf-8')
                self.send_response(400)
            else:
                # Generar ID único
                job_id = f"job_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                
                # Inicializar estado
                DOWNLOADS_STATUS[job_id] = {
                    'id': job_id,
                    'url': url,
                    'format': format_type,
                    'status': 'pending',
                    'progress': 0,
                    'message': 'Iniciando descarga...',
                    'start_time': time.time(),
                    'file_path': None,
                    'error': None
                }
                
                # Iniciar descarga en hilo separado
                thread = threading.Thread(
                    target=process_download_ultra_simple,
                    args=(job_id, url, format_type),
                    daemon=True
                )
                thread.start()
                
                response = json.dumps({"job_id": job_id, "status": "started"}).encode('utf-8')
                self.send_response(200)
            
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)
            
        except Exception as e:
            error_response = json.dumps({"error": str(e)}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error_response)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response)

def process_download_ultra_simple(job_id, url, format_type):
    """Procesa la descarga de forma ultra simple"""
    try:
        status = DOWNLOADS_STATUS[job_id]
        status['status'] = 'downloading'
        status['message'] = 'Preparando descarga...'
        status['progress'] = 10
        
        # Crear directorio de salida
        output_dir = DEFAULT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        
        # Intentar usar yt-dlp del sistema o binario incluido
        ytdlp_commands = ['yt-dlp', 'python3 -m yt_dlp', '/opt/homebrew/bin/yt-dlp']
        ytdlp_cmd = None
        
        for cmd in ytdlp_commands:
            try:
                result = subprocess.run(cmd.split() + ['--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ytdlp_cmd = cmd
                    break
            except:
                continue
        
        # Si no se encuentra yt-dlp del sistema, intentar usar binario incluido
        if not ytdlp_cmd:
            ytdlp_path = get_executable_path("yt-dlp")
            if os.path.exists(ytdlp_path):
                ytdlp_cmd = ytdlp_path
        
        if not ytdlp_cmd:
            status['status'] = 'error'
            status['error'] = 'yt-dlp no está instalado. Instala con: pip install yt-dlp'
            status['message'] = 'Error: yt-dlp no encontrado'
            return
        
        status['message'] = 'Descargando...'
        status['progress'] = 30
        
        # Construir comando
        cmd = ytdlp_cmd.split()
        
        if format_type in ['mp3', 'audio']:
            cmd.extend([
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0'
            ])
        else:
            cmd.extend([
                '--format', 'best[height<=1080]'
            ])
        
        output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
        cmd.extend(['--output', output_template])
        
        # Configurar ffmpeg si está disponible
        ffmpeg_path = get_executable_path("ffmpeg")
        if os.path.exists(ffmpeg_path):
            cmd.extend(['--ffmpeg-location', ffmpeg_path])
        
        # Agregar opciones para evitar errores
        cmd.extend([
            '--no-warnings',
            '--ignore-errors',
            '--no-check-certificate'
        ])
        
        cmd.append(url)
        
        status['progress'] = 50
        
        print(f"Ejecutando: {' '.join(cmd)}")
        
        # Ejecutar descarga
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if process.returncode == 0:
            status['status'] = 'completed'
            status['progress'] = 100
            status['message'] = '¡Descarga completada exitosamente!'
            
            # Buscar archivo descargado
            try:
                files = sorted(Path(output_dir).glob('*'), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    latest_file = files[0]
                    status['file_path'] = str(latest_file)
                    status['file_name'] = latest_file.name
                    status['file_size'] = latest_file.stat().st_size
            except:
                pass
                
        else:
            status['status'] = 'error'
            error_msg = process.stderr or 'Error desconocido'
            status['error'] = error_msg
            status['message'] = f'Error en la descarga: {error_msg}'
            print(f"Error yt-dlp: {error_msg}")
    
    except subprocess.TimeoutExpired:
        status['status'] = 'error'
        status['error'] = 'La descarga tardó demasiado tiempo (más de 5 minutos)'
        status['message'] = 'Error: Timeout'
    except Exception as e:
        status['status'] = 'error'
        status['error'] = str(e)
        status['message'] = f'Error interno: {str(e)}'
        print(f"Error en descarga: {e}")
    
    finally:
        status['end_time'] = time.time()
        status['duration'] = status['end_time'] - status['start_time']

def setup_environment():
    """Configura el entorno básico"""
    print("🔧 Configurando entorno...")
    
    # Crear directorio de salida
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    print(f"📁 Directorio de descargas: {DEFAULT_OUTPUT_DIR}")
    
    # Verificar yt-dlp
    ytdlp_available = False
    for cmd in ['yt-dlp', 'python3 -m yt_dlp']:
        try:
            result = subprocess.run(cmd.split() + ['--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ yt-dlp encontrado: {cmd}")
                print(f"   Versión: {result.stdout.strip()}")
                ytdlp_available = True
                break
        except:
            continue
    
    # Verificar binario incluido si no se encuentra del sistema
    if not ytdlp_available:
        ytdlp_path = get_executable_path("yt-dlp")
        if os.path.exists(ytdlp_path):
            print(f"✅ yt-dlp incluido encontrado: {ytdlp_path}")
            ytdlp_available = True
    
    if not ytdlp_available:
        print("⚠️  yt-dlp no encontrado")
        print("💡 Instala con: pip install 'yt-dlp==2024.12.13'")
        print("🔄 La aplicación seguirá funcionando si instalas yt-dlp después")
    
    # Verificar ffmpeg
    ffmpeg_path = get_executable_path("ffmpeg")
    if os.path.exists(ffmpeg_path):
        print(f"✅ ffmpeg incluido encontrado: {ffmpeg_path}")
    else:
        print("⚠️  ffmpeg no encontrado (puede causar problemas con conversión de audio)")
    
    return True

def open_browser_delayed():
    """Abre el navegador después de unos segundos"""
    time.sleep(2)
    try:
        webbrowser.open("http://localhost:8080")
        print("🌐 Navegador abierto automáticamente")
    except:
        print("⚠️  No se pudo abrir el navegador automáticamente")

def main():
    """Función principal ultra simple"""
    print("=" * 60)
    print("🎵 YT-DLP Music API - Ultra Simple v4.0")
    print("📱 Descargador standalone de música y videos de YouTube")
    print("👨‍💻 Desarrollado por Martin Gaston Lopez")
    print("=" * 60)
    
    # Configurar entorno
    if not setup_environment():
        print("❌ Error en la configuración")
        input("Presiona Enter para salir...")
        return
    
    # Abrir navegador
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()
    
    # Iniciar servidor
    try:
        server = HTTPServer(('localhost', 8080), YTDLPHandler)
        print("🚀 Servidor iniciado en http://localhost:8080")
        print("⏹️  Presiona Ctrl+C para detener")
        print("=" * 60)
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n👋 Cerrando aplicación...")
    except OSError as e:
        if "Address already in use" in str(e):
            print("❌ Puerto 8080 ya está en uso")
            print("💡 Cierra otras aplicaciones que usen el puerto 8080")
        else:
            print(f"❌ Error del servidor: {e}")
        input("Presiona Enter para salir...")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()