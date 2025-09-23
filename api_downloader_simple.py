#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YT-DLP Music API - Standalone Simple Version v4
Versión simplificada sin multiprocessing para PyInstaller
"""

from flask import Flask, request, jsonify
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
import webbrowser
from pathlib import Path

# === CONFIGURACIÓN STANDALONE ===
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
    if sys.platform == "win32":
        return str(home / "Music" / "YT-DLP Downloads")
    elif sys.platform == "darwin":
        return str(home / "Music" / "YT-DLP Downloads")
    else:
        return str(home / "Music" / "YT-DLP Downloads")

# Configuración
DEFAULT_OUTPUT_DIR = get_default_output_dir()
DOWNLOADS_STATUS = {}

# === APLICACIÓN FLASK ===
app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Página principal"""
    try:
        frontend_path = get_resource_path("frontend/index.html")
        if os.path.exists(frontend_path):
            with open(frontend_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return """
<!DOCTYPE html>
<html>
<head>
    <title>YT-DLP Music API</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #ff0000; text-align: center; }
        .form-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select, button { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #ff0000; color: white; border: none; cursor: pointer; margin-top: 10px; }
        button:hover { background: #cc0000; }
        .status { margin-top: 20px; padding: 10px; border-radius: 5px; display: none; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    </style>
</head>
<body>
            <div class="container">
            <h1>🎵 YT-DLP Music API - powered by buh!to</h1>
            <p>Descarga música y videos de YouTube con la mejor calidad</p>
            
            <div class="form-group">
                <label for="url">URL del video/playlist:</label>
                <input type="text" id="url" placeholder="https://www.youtube.com/watch?v=... o https://www.youtube.com/playlist?list=...">
            </div>
            
            <div class="form-group">
                <label for="format">Formato de descarga:</label>
                <select id="format">
                    <option value="mp3">🎵 Solo Audio (MP3)</option>
                    <option value="mp4">🎬 Video + Audio (MP4)</option>
                    <option value="playlist_mp3">📂 Playlist - Solo Audio</option>
                    <option value="playlist_mp4">📂 Playlist - Video + Audio</option>
                </select>
            </div>
        
        <div class="form-group">
            <button onclick="download()">🚀 Descargar</button>
        </div>
        
        <div id="status" class="status"></div>
    </div>
    
    <script>
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
            status.style.display = 'block';
        }
        
        function download() {
            const url = document.getElementById('url').value.trim();
            const format = document.getElementById('format').value;
            
            if (!url) {
                showStatus('Por favor ingresa una URL de YouTube', 'error');
                return;
            }
            
            showStatus('Iniciando descarga...', 'info');
            
            fetch('/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, format: format })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showStatus('Error: ' + data.error, 'error');
                } else {
                    showStatus('Descarga iniciada. ID: ' + data.job_id, 'success');
                    checkStatus(data.job_id);
                }
            })
            .catch(error => {
                showStatus('Error de conexión: ' + error, 'error');
            });
        }
        
        function checkStatus(jobId) {
            fetch('/status/' + jobId)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    showStatus('✅ Descarga completada: ' + (data.file_name || 'archivo guardado'), 'success');
                } else if (data.status === 'error') {
                    showStatus('❌ Error: ' + (data.error || 'Error desconocido'), 'error');
                } else {
                    showStatus('⏳ ' + (data.message || 'Procesando...'), 'info');
                    setTimeout(() => checkStatus(jobId), 2000);
                }
            })
            .catch(error => {
                console.error('Error checking status:', error);
                setTimeout(() => checkStatus(jobId), 2000);
            });
        }
    </script>
</body>
</html>
            """
    except Exception as e:
        return f"Error: {e}"

@app.route('/download', methods=['POST'])
def download():
    """Maneja peticiones de descarga"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        format_type = data.get('format', 'mp3')
        output_dir = data.get('output_dir', DEFAULT_OUTPUT_DIR)
        
        if not url:
            return jsonify({"error": "URL es requerida"}), 400
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
        # Generar ID único
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
            target=process_download_simple,
            args=(job_id, url, format_type, output_dir),
            daemon=True
        )
        thread.start()
        
        return jsonify({"job_id": job_id, "status": "started"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status/<job_id>')
def status(job_id):
    """Consulta el estado de una descarga"""
    if job_id in DOWNLOADS_STATUS:
        return jsonify(DOWNLOADS_STATUS[job_id])
    else:
        return jsonify({"error": "Job not found"}), 404

def process_download_simple(job_id, url, format_type, output_dir):
    """Procesa la descarga de forma simple"""
    try:
        status = DOWNLOADS_STATUS[job_id]
        status['status'] = 'downloading'
        status['message'] = 'Descargando...'
        
        # Intentar usar yt-dlp del sistema primero
        ytdlp_commands = ['yt-dlp', 'python3 -m yt_dlp']
        ytdlp_path = None
        
        # Verificar si yt-dlp está disponible
        for cmd in ytdlp_commands:
            try:
                result = subprocess.run(cmd.split() + ['--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    ytdlp_path = cmd
                    break
            except:
                continue
        
        if not ytdlp_path:
            # Intentar usar binario incluido
            ytdlp_path = get_executable_path("yt-dlp")
            if not os.path.exists(ytdlp_path):
                raise Exception("yt-dlp no encontrado. Instala yt-dlp: pip install yt-dlp")
        
        # Construir comando
        if isinstance(ytdlp_path, str) and ' ' in ytdlp_path:
            cmd = ytdlp_path.split()
        else:
            cmd = [ytdlp_path]
        
        # Configurar ffmpeg
        ffmpeg_path = get_executable_path("ffmpeg")
        if os.path.exists(ffmpeg_path):
            cmd.extend(['--ffmpeg-location', ffmpeg_path])
        
        # Configuración SSL para macOS (solucionar problemas de certificados)
        cmd.extend([
            '--no-check-certificate',  # Omitir verificación SSL si es necesario
            '--ignore-errors',  # Continuar con errores menores
            '--no-warnings'     # Reducir warnings SSL
        ])
        
        # Configuración de formato y directorio
        if format_type.startswith('playlist'):
            # Para playlists
            cmd.extend(['--yes-playlist'])
            if format_type == 'playlist_mp3':
                cmd.extend([
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',  # Mejor calidad disponible
                    '--embed-metadata',
                    '--add-metadata',
                    '--embed-thumbnail'  # Incluir carátula
                ])
                playlist_dir = os.path.join(output_dir, 'Playlists')
            else:  # playlist_mp4
                cmd.extend([
                    '--format', 'best[height<=1080]',
                    '--merge-output-format', 'mp4'
                ])
                playlist_dir = os.path.join(output_dir, 'Playlists')
            
            os.makedirs(playlist_dir, exist_ok=True)
            output_template = os.path.join(playlist_dir, '%(playlist_title)s/%(title)s.%(ext)s')
        else:
            # Para videos individuales
            cmd.extend(['--no-playlist'])
            if format_type in ['mp3', 'audio']:
                cmd.extend([
                    '--extract-audio',
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',  # Mejor calidad disponible
                    '--embed-metadata',
                    '--add-metadata',
                    '--embed-thumbnail'  # Incluir carátula
                ])
            else:  # mp4, video
                cmd.extend([
                    '--format', 'best[height<=1080]',
                    '--merge-output-format', 'mp4'
                ])
                video_dir = os.path.join(output_dir, 'Videos')
                os.makedirs(video_dir, exist_ok=True)
                output_template = os.path.join(video_dir, '%(title)s.%(ext)s')
            
            if format_type in ['mp3', 'audio']:
                output_template = os.path.join(output_dir, '%(title)s.%(ext)s')
        cmd.extend(['--output', output_template])
        
        # Agregar cookies si existen
        cookies_path = get_resource_path("www.youtube.com_cookies.txt")
        if os.path.exists(cookies_path):
            cmd.extend(['--cookies', cookies_path])
        
        cmd.append(url)
        
        print(f"Ejecutando: {' '.join(cmd)}")
        
        # Ejecutar comando (timeout mayor para playlists)
        timeout = 600 if format_type.startswith('playlist') else 300
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if process.returncode == 0:
            status['status'] = 'completed'
            status['progress'] = 100
            status['message'] = 'Descarga completada exitosamente'
            
            # Buscar archivo descargado
            files = list(Path(output_dir).glob('*'))
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                status['file_path'] = str(latest_file)
                status['file_name'] = latest_file.name
                status['file_size'] = latest_file.stat().st_size
        else:
            status['status'] = 'error'
            status['error'] = process.stderr or 'Error desconocido durante la descarga'
            status['message'] = f'Error: {status["error"]}'
            print(f"Error yt-dlp: {process.stderr}")
    
    except subprocess.TimeoutExpired:
        status['status'] = 'error'
        status['error'] = 'La descarga tardó demasiado tiempo'
        status['message'] = 'Error: Timeout'
    except Exception as e:
        status['status'] = 'error'
        status['error'] = str(e)
        status['message'] = f'Error interno: {str(e)}'
        print(f"Error process_download: {e}")
    
    finally:
        status['end_time'] = time.time()
        status['duration'] = status['end_time'] - status['start_time']

def setup_environment():
    """Configura el entorno"""
    print("🔧 Configurando entorno...")
    
    # Crear directorio de salida por defecto
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    
    print("✅ Entorno configurado")
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
    print("🎵 YT-DLP Music API - Standalone Simple Complete v4.0")
    print("=" * 50)
    
    # Configurar entorno
    if not setup_environment():
        print("❌ Error en la configuración del entorno")
        input("Presiona Enter para salir...")
        return
    
    # Abrir navegador en hilo separado
    browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
    browser_thread.start()
    
    print("🚀 Iniciando servidor en puerto 8080...")
    print("🌐 Abre tu navegador en: http://localhost:8080")
    print(f"📁 Audio: {DEFAULT_OUTPUT_DIR}")
    print(f"🎬 Videos: {DEFAULT_OUTPUT_DIR}/Videos")
    print(f"📂 Playlists: {DEFAULT_OUTPUT_DIR}/Playlists")
    print("⏹️  Presiona Ctrl+C para detener")
    print("=" * 50)
    
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Cerrando aplicación...")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()