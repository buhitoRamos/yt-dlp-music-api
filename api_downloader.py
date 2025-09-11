# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import subprocess
import os
import json
import tempfile
import threading
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permite requests desde cualquier origen

# Configuración
DEFAULT_OUTPUT_DIR = "/Users/O002545/Music/playlist"
DOWNLOADS_STATUS = {}

@app.route('/api')
def api_info():
    return jsonify({
        'message': 'yt-dlp Music Downloader API',
        'version': '1.0',
        'endpoints': {
            'POST /download': 'Descargar música/playlist - REQUIERE url y output_dir',
            'GET /status/<job_id>': 'Ver estado de descarga',
            'POST /cancel/<job_id>': 'Cancelar descarga en progreso',
            'GET /formats': 'Ver formatos disponibles y campos requeridos',
            'GET /suggest-directories': 'Sugerencias de carpetas comunes',
            'GET /jobs': 'Listar todos los trabajos',
            'POST /clear-jobs': 'Limpiar historial de trabajos'
        },
        'example_request': {
            'url': 'https://music.youtube.com/playlist?list=...',
            'output_dir': '~/Downloads/musica',
            'format': 'mp3',
            'quality': '320K',
            'naming': 'artist-title',
            'cookies_file': 'cookies.txt'
        },
        'required_fields': ['url', 'output_dir'],
        'cookies_info': {
            'note': 'Para evitar error 429 (Too Many Requests), usa cookies de YouTube',
            'local_dev': 'Exporta cookies.txt con la extensión "Get cookies.txt" desde youtube.com',
            'production': 'En producción (Render/Heroku), usa la variable de entorno YOUTUBE_COOKIES',
            'placement': 'Coloca cookies.txt en la misma carpeta que este script',
            'env_var': 'Variable de entorno YOUTUBE_COOKIES con contenido del archivo cookies.txt'
        }
    })

@app.route('/')
def serve_frontend():
    """Sirve el frontend HTML"""
    return send_file('frontend/index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Sirve archivos estáticos si los necesitas"""
    return send_from_directory('.', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Sirve archivos CSS"""
    return send_from_directory('frontend/css', filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Sirve archivos JavaScript"""
    return send_from_directory('frontend/js', filename)

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL es requerida'}), 400
        
        # Parámetros opcionales con valores por defecto
        format_type = data.get('format', 'mp3')  # mp3, mp4, best
        quality = data.get('quality', '0')  # 0=mejor, 320K, 256K, 128K
        naming = data.get('naming', 'artist-title')  # title, artist-title
        output_dir = data.get('output_dir')  # Ahora es obligatorio especificar la carpeta
        cookies_file = data.get('cookies_file')  # Archivo de cookies opcional
        
        # Validar que se especifique output_dir
        if not output_dir:
            return jsonify({
                'error': 'output_dir es obligatorio. Especifica la carpeta donde guardar los archivos',
                'ejemplo': {'output_dir': '/Users/tuusuario/Downloads/musica'}
            }), 400
        
        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Generar ID único para el trabajo
        job_id = f"job_{int(time.time())}_{len(DOWNLOADS_STATUS)}"
        
        # Inicializar estado
        DOWNLOADS_STATUS[job_id] = {
            'status': 'iniciando',
            'url': url,
            'created_at': datetime.now().isoformat(),
            'progress': 0,
            'files': [],
            'error': None
        }
        
        # Ejecutar descarga en hilo separado
        thread = threading.Thread(target=download_worker, args=(job_id, url, format_type, quality, naming, output_dir, cookies_file))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'iniciado',
            'message': f'Descarga iniciada. Usa /status/{job_id} para ver el progreso'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_worker(job_id, url, format_type, quality, naming, output_dir, cookies_file=None):
    try:
        # Actualizar estado
        DOWNLOADS_STATUS[job_id]['status'] = 'descargando'
        
        # Construir comando yt-dlp
        cmd = ['python3', '-m', 'yt_dlp']
        
        # Agregar cookies si se especifica el archivo o variable de entorno
        cookies_added = False
        
        # Opción 1: Usar variable de entorno YOUTUBE_COOKIES (para producción)
        if os.environ.get('YOUTUBE_COOKIES'):
            # Crear archivo temporal con las cookies
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(os.environ.get('YOUTUBE_COOKIES'))
                temp_cookies_path = f.name
            cmd.extend(['--cookies', temp_cookies_path])
            DOWNLOADS_STATUS[job_id]['cookies'] = 'Usando cookies desde variable de entorno'
            cookies_added = True
        
        # Opción 2: Usar archivo cookies.txt (para desarrollo)
        elif cookies_file:
            # Verificar si el archivo existe
            if os.path.exists(cookies_file):
                cmd.extend(['--cookies', cookies_file])
                DOWNLOADS_STATUS[job_id]['cookies'] = f'Usando cookies: {cookies_file}'
                cookies_added = True
            else:
                # Buscar en la carpeta actual del script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                cookies_path = os.path.join(script_dir, cookies_file)
                if os.path.exists(cookies_path):
                    cmd.extend(['--cookies', cookies_path])
                    DOWNLOADS_STATUS[job_id]['cookies'] = f'Usando cookies: {cookies_path}'
                    cookies_added = True
                else:
                    DOWNLOADS_STATUS[job_id]['warning'] = f'Archivo de cookies no encontrado: {cookies_file}'
        
        # Si no se encontraron cookies, agregar advertencia
        if not cookies_added:
            DOWNLOADS_STATUS[job_id]['warning'] = 'Sin cookies configuradas - pueden ocurrir errores 429'
        
        # Configurar formato
        if format_type == 'mp3':
            cmd.extend(['-x', '--audio-format', 'mp3'])
            cmd.extend(['--audio-quality', quality])
        elif format_type == 'mp4':
            cmd.extend(['-f', 'best'])
        else:  # best
            cmd.extend(['-f', 'best'])
        
        # Configurar plantilla de nombres
        if naming == 'title':
            template = '%(title)s.%(ext)s'
        elif naming == 'artist-title':
            template = '%(artist|uploader|Unknown)s - %(title)s.%(ext)s'
        else:
            template = '%(title)s.%(ext)s'
        
        output_template = os.path.join(output_dir, template)
        cmd.extend(['-o', output_template])
        
        # Agregar opciones adicionales
        cmd.extend(['--write-info-json', '--no-playlist' if 'playlist' not in url else ''])
        cmd = [x for x in cmd if x]  # Remover strings vacíos
        
        cmd.append(url)
        
        # Ejecutar comando
        DOWNLOADS_STATUS[job_id]['command'] = ' '.join(cmd)
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True
        )
        
        # Guardar el proceso para poder cancelarlo
        DOWNLOADS_STATUS[job_id]['process'] = process
        
        stdout, stderr = process.communicate()
        
        # Verificar si fue cancelado
        if process.returncode == -15:  # SIGTERM
            DOWNLOADS_STATUS[job_id].update({
                'status': 'cancelado',
                'error': 'Descarga cancelada por el usuario'
            })
            return
        
        if process.returncode == 0:
            # Buscar archivos descargados
            downloaded_files = []
            for file in os.listdir(output_dir):
                if file.endswith(('.mp3', '.mp4', '.webm', '.m4a')):
                    downloaded_files.append(os.path.join(output_dir, file))
            
            DOWNLOADS_STATUS[job_id].update({
                'status': 'completado',
                'progress': 100,
                'files': downloaded_files,
                'stdout': stdout
            })
        else:
            DOWNLOADS_STATUS[job_id].update({
                'status': 'error',
                'error': stderr,
                'stdout': stdout
            })
            
    except Exception as e:
        DOWNLOADS_STATUS[job_id].update({
            'status': 'error',
            'error': str(e)
        })
    finally:
        # Limpiar archivo temporal de cookies si se creó
        if 'temp_cookies_path' in locals():
            try:
                os.unlink(temp_cookies_path)
            except:
                pass

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error': 'Job ID no encontrado'}), 404
    
    # Crear una copia del estado sin el objeto proceso (no serializable)
    status = DOWNLOADS_STATUS[job_id].copy()
    if 'process' in status:
        del status['process']
    
    return jsonify(status)

@app.route('/formats', methods=['GET'])
def get_formats():
    return jsonify({
        'formats': {
            'mp3': 'Solo audio en formato MP3',
            'mp4': 'Video completo en MP4',
            'best': 'Mejor calidad disponible'
        },
        'qualities': {
            '0': 'Mejor calidad (VBR)',
            '320K': '320 kbps',
            '256K': '256 kbps',
            '192K': '192 kbps',
            '128K': '128 kbps'
        },
        'naming_options': {
            'title': 'Solo título del video',
            'artist-title': 'Artista - Título'
        },
        'required_fields': {
            'url': 'URL del video o playlist (obligatorio)',
            'output_dir': 'Carpeta donde guardar los archivos (obligatorio)'
        },
        'optional_fields': {
            'cookies_file': 'Archivo de cookies para evitar bloqueos (cookies.txt)'
        },
        'cookies_help': {
            'why': 'Las cookies evitan el error 429 (Too Many Requests) de YouTube',
            'how': '1. Instala la extensión "Get cookies.txt" en tu navegador',
            'step2': '2. Ve a youtube.com e inicia sesión',
            'step3': '3. Exporta las cookies a cookies.txt',
            'step4': '4. Coloca cookies.txt en la misma carpeta que el script',
            'usage': 'Agrega "cookies_file": "cookies.txt" a tu request'
        },
        'suggested_directories': {
            'downloads': '~/Downloads',
            'music': '~/Music',
            'desktop': '~/Desktop',
            'custom': '/ruta/personalizada'
        }
    })

@app.route('/suggest-directories', methods=['GET'])
def suggest_directories():
    import os.path
    user_home = os.path.expanduser('~')
    
    suggestions = {
        'common_paths': [
            f"{user_home}/Downloads",
            f"{user_home}/Music",
            f"{user_home}/Desktop",
            f"{user_home}/Downloads/YouTube",
            f"{user_home}/Music/YouTube",
            "/tmp/downloads"
        ],
        'examples': {
            'downloads_folder': f"{user_home}/Downloads",
            'music_folder': f"{user_home}/Music/Playlists",
            'custom_folder': "/path/to/your/custom/folder"
        },
        'note': 'La carpeta se creará automáticamente si no existe'
    }
    
    return jsonify(suggestions)

@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_download(job_id):
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error': 'Job ID no encontrado'}), 404
    
    job = DOWNLOADS_STATUS[job_id]
    
    # Verificar si el trabajo está en progreso
    if job['status'] not in ['iniciando', 'descargando']:
        return jsonify({'error': 'El trabajo no está en progreso'}), 400
    
    # Intentar terminar el proceso
    if 'process' in job and job['process']:
        try:
            job['process'].terminate()
            # Esperar un poco para que termine
            job['process'].wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Si no termina, forzar la terminación
            job['process'].kill()
        except Exception as e:
            return jsonify({'error': f'Error al cancelar: {str(e)}'}), 500
    
    # Actualizar estado
    DOWNLOADS_STATUS[job_id].update({
        'status': 'cancelado',
        'error': 'Descarga cancelada por el usuario'
    })
    
    return jsonify({'message': 'Descarga cancelada exitosamente'})

@app.route('/jobs', methods=['GET'])
def list_jobs():
    return jsonify({
        'jobs': list(DOWNLOADS_STATUS.keys()),
        'total': len(DOWNLOADS_STATUS)
    })

@app.route('/clear-jobs', methods=['POST'])
def clear_jobs():
    global DOWNLOADS_STATUS
    DOWNLOADS_STATUS = {}
    return jsonify({'message': 'Historial de trabajos limpiado'})

if __name__ == '__main__':
    import os
    
    print("🎵 API de descarga de música iniciada")
    print("📍 Endpoints disponibles:")
    print("   POST /download - Descargar música")
    print("   GET /status/<job_id> - Ver progreso")
    print("   GET /formats - Ver formatos disponibles")
    print("   GET /jobs - Listar trabajos")
    
    # Puerto para producción (Heroku, Railway, etc.) o desarrollo
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🌐 Servidor corriendo en {host}:{port}")
    
    app.run(debug=debug, host=host, port=port)
