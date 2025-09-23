#!/usr/bin/env python3
"""
YT-DLP Music API - Versión Minimalista
Versión completamente independiente para compilar con PyInstaller
"""

import os
import sys
import subprocess
import json
import urllib.parse
import threading
from socketserver import TCPServer, BaseRequestHandler
import time

# Puerto por defecto
PORT = 8080

class YTDLPMinimalHandler(BaseRequestHandler):
    """Handler minimalista para solicitudes HTTP"""
    
    def handle(self):
        try:
            # Leer la solicitud HTTP
            data = self.request.recv(4096).decode('utf-8', errors='ignore')
            if not data:
                return
                
            lines = data.split('\n')
            if not lines:
                return
                
            request_line = lines[0]
            parts = request_line.split()
            if len(parts) < 2:
                return
                
            method = parts[0]
            path = parts[1]
            
            # Procesar la solicitud
            if method == 'GET':
                if path == '/' or path == '/index.html':
                    self.send_html()
                elif path.startswith('/download'):
                    self.handle_download(path)
                else:
                    self.send_404()
            elif method == 'POST':
                if path == '/download':
                    content_length = 0
                    for line in lines:
                        if line.lower().startswith('content-length:'):
                            content_length = int(line.split(':')[1].strip())
                            break
                    
                    if content_length > 0:
                        # Leer el cuerpo de la solicitud
                        body = self.request.recv(content_length).decode('utf-8', errors='ignore')
                        self.handle_post_download(body)
                    else:
                        self.send_400()
                else:
                    self.send_404()
            else:
                self.send_405()
                
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_500()
    
    def send_response(self, status_code, content_type, content):
        """Enviar respuesta HTTP"""
        try:
            response = f"HTTP/1.1 {status_code}\r\n"
            response += f"Content-Type: {content_type}\r\n"
            response += "Access-Control-Allow-Origin: *\r\n"
            response += "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            response += "Access-Control-Allow-Headers: Content-Type\r\n"
            response += f"Content-Length: {len(content.encode('utf-8'))}\r\n"
            response += "\r\n"
            response += content
            
            self.request.sendall(response.encode('utf-8'))
        except:
            pass
    
    def send_html(self):
        """Enviar página HTML principal"""
        html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YT-DLP Music API - Minimalista</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f0f0f0; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .input-group { margin: 20px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 15px; border-radius: 5px; display: none; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .progress { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 YT-DLP Music API - UltraSimple Completa</h1>
        
        <div class="input-group">
            <label for="url">URL del video/playlist:</label>
            <input type="text" id="url" placeholder="https://www.youtube.com/watch?v=... | Playlists | Shorts | Cualquier video">
        </div>
        
        <div class="input-group">
            <label for="format">Tipo de descarga:</label>
            <select id="format">
                <option value="audio">🎵 Audio MP3 (Mejor Calidad)</option>
                <option value="video">🎬 Video MP4 (1080p)</option>
                <option value="playlist_audio">📂 Playlist - Audio MP3</option>
                <option value="playlist_video">📂 Playlist - Video MP4</option>
                <option value="shorts">🎬 YouTube Shorts</option>
            </select>
        </div>
        
        <button onclick="startDownload()">Iniciar Descarga</button>
        
        <div id="result" class="result"></div>
    </div>

    <script>
        async function startDownload() {
            const url = document.getElementById('url').value.trim();
            const format = document.getElementById('format').value;
            const resultDiv = document.getElementById('result');
            
            if (!url) {
                showResult('Por favor ingresa una URL', 'error');
                return;
            }
            
            const formatText = {
                'audio': 'audio MP3 (mejor calidad)',
                'video': 'video MP4 (1080p)',
                'playlist_audio': 'playlist en audio MP3',
                'playlist_video': 'playlist en video MP4',
                'shorts': 'YouTube Shorts'
            };
            
            showResult(`Procesando descarga de ${formatText[format]}...`, 'progress');
            
            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `url=${encodeURIComponent(url)}&format=${encodeURIComponent(format)}`
                });
                
                const result = await response.text();
                
                if (response.ok) {
                    showResult('✅ ' + result, 'success');
                } else {
                    showResult('❌ Error: ' + result, 'error');
                }
            } catch (error) {
                showResult('❌ Error de conexión: ' + error.message, 'error');
            }
        }
        
        function showResult(message, type) {
            const resultDiv = document.getElementById('result');
            resultDiv.textContent = message;
            resultDiv.className = 'result ' + type;
            resultDiv.style.display = 'block';
        }
    </script>
</body>
</html>"""
        self.send_response("200 OK", "text/html; charset=utf-8", html)
    
    def handle_download(self, path):
        """Manejar descarga GET"""
        # Parsear URL
        if '?' in path:
            query = path.split('?')[1]
            params = urllib.parse.parse_qs(query)
            url = params.get('url', [''])[0]
            format_type = params.get('format', ['audio'])[0]
            
            if url:
                result = self.process_download(url, format_type)
                self.send_response("200 OK", "text/plain", result)
            else:
                self.send_response("400 Bad Request", "text/plain", "URL requerida")
        else:
            self.send_response("400 Bad Request", "text/plain", "URL requerida")
    
    def handle_post_download(self, body):
        """Manejar descarga POST"""
        # Parsear body
        params = urllib.parse.parse_qs(body)
        url = params.get('url', [''])[0]
        format_type = params.get('format', ['audio'])[0]
        
        if url:
            result = self.process_download(url, format_type)
            self.send_response("200 OK", "text/plain", result)
        else:
            self.send_response("400 Bad Request", "text/plain", "URL requerida")
    
    def process_download(self, url, format_type='audio'):
        """Procesar descarga de audio/video/playlists/shorts"""
        try:
            # Configurar directorios según el tipo
            base_dir = os.path.expanduser("~/Downloads/Music")
            
            if format_type.startswith('playlist'):
                download_dir = os.path.join(base_dir, "Playlists")
            elif format_type == 'video':
                download_dir = os.path.join(base_dir, "Videos")
            elif format_type == 'shorts':
                download_dir = os.path.join(base_dir, "Shorts")
            else:  # audio
                download_dir = base_dir
            
            os.makedirs(download_dir, exist_ok=True)
            
            # Obtener el path del ejecutable yt-dlp
            ytdlp_path = self.get_ytdlp_path()
            if not ytdlp_path:
                return "Error: yt-dlp no encontrado"
            
            # Construir comando base
            cmd = [ytdlp_path]
            
            # Configuración según formato
            if format_type in ['audio', 'playlist_audio']:
                # Audio MP3 - Mejor calidad
                cmd.extend([
                    '-x',  # Extraer audio
                    '--audio-format', 'mp3',
                    '--audio-quality', '0',  # Mejor calidad disponible
                    '--embed-metadata',
                    '--add-metadata',
                    '--embed-thumbnail',  # Incluir carátula
                ])
            elif format_type in ['video', 'playlist_video', 'shorts']:
                # Video MP4 - Mejor calidad hasta 1080p
                cmd.extend([
                    '--format', 'best[height<=1080]/best',
                    '--merge-output-format', 'mp4',
                    '--embed-subs',
                    '--write-auto-sub',
                    '--embed-metadata',
                ])
            
            # Configuración de playlist vs individual
            if format_type.startswith('playlist'):
                cmd.extend([
                    '--yes-playlist',
                    '-o', os.path.join(download_dir, '%(playlist_title)s/%(title)s.%(ext)s'),
                ])
            else:
                cmd.extend([
                    '--no-playlist',
                    '-o', os.path.join(download_dir, '%(title)s.%(ext)s'),
                ])
            
            # Agregar cookies si existen
            cookies_path = "./www.youtube.com_cookies.txt"
            if os.path.exists(cookies_path):
                cmd.extend(['--cookies', cookies_path])
            
            cmd.append(url)
            
            # Timeout según tipo (playlists necesitan más tiempo)
            timeout = 900 if format_type.startswith('playlist') else 300
            
            # Ejecutar comando
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if process.returncode == 0:
                format_names = {
                    'audio': 'Audio MP3 (mejor calidad)',
                    'video': 'Video MP4 (1080p)', 
                    'playlist_audio': 'Playlist en Audio MP3',
                    'playlist_video': 'Playlist en Video MP4',
                    'shorts': 'YouTube Shorts'
                }
                return f"✅ {format_names[format_type]} descargado en {download_dir}"
            else:
                return f"❌ Error en descarga: {process.stderr}"
                
        except subprocess.TimeoutExpired:
            timeout_msg = "15 min" if format_type.startswith('playlist') else "5 min"
            return f"❌ Error: Descarga cancelada por timeout ({timeout_msg})"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def get_ytdlp_path(self):
        """Obtener path de yt-dlp"""
        # Buscar en varios lugares
        paths = [
            "./binaries/darwin/yt-dlp",
            "./binaries/windows/yt-dlp.exe",
            "/usr/local/bin/yt-dlp",
            "yt-dlp"
        ]
        
        for path in paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        # Intentar usar which
        try:
            result = subprocess.run(['which', 'yt-dlp'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def send_404(self):
        self.send_response("404 Not Found", "text/plain", "Not Found")
    
    def send_400(self):
        self.send_response("400 Bad Request", "text/plain", "Bad Request")
    
    def send_405(self):
        self.send_response("405 Method Not Allowed", "text/plain", "Method Not Allowed")
    
    def send_500(self):
        self.send_response("500 Internal Server Error", "text/plain", "Internal Server Error")

def find_free_port():
    """Encontrar un puerto libre"""
    import socket
    for port in range(8080, 8090):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return 8080

def main():
    """Función principal"""
    port = find_free_port()
    
    print(f"🎵 YT-DLP Music API - UltraSimple Completa")
    print(f"🚀 Iniciando servidor en puerto {port}")
    print(f"🌐 Accede a: http://localhost:{port}")
    print(f"📁 Audio: ~/Downloads/Music")
    print(f"🎬 Videos: ~/Downloads/Music/Videos")
    print(f"📱 Shorts: ~/Downloads/Music/Shorts")
    print(f"📂 Playlists: ~/Downloads/Music/Playlists")
    print("✨ Presiona Ctrl+C para detener\n")
    
    try:
        server = TCPServer(('', port), YTDLPMinimalHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido")
    except Exception as e:
        print(f"❌ Error del servidor: {e}")

if __name__ == "__main__":
    main()