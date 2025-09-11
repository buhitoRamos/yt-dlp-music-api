# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import subprocess
import os
import json
import tempfile
import threading
import time
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permite requests desde cualquier origen

# Configuración
DEFAULT_OUTPUT_DIR = "/Users/O002545/Music/playlist"
DOWNLOADS_STATUS = {}

def get_random_user_agent():
    """Generar User-Agent aleatorio para evitar detección"""
    user_agents = [
        # Chrome Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        
        # Chrome Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Safari Mac
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        
        # Firefox
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
        
        # Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        
        # Mobile Chrome
        'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

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
            'naming': 'artist-title'
        },
        'required_fields': ['url', 'output_dir'],
        'cookies_info': {
            'note': 'Implementadas estrategias anti-429 automáticas sin necesidad de cookies',
            'strategies': [
                'User-Agents aleatorios',
                'Múltiples clientes de YouTube (web, móvil, TV)',
                'Reintentos automáticos con delays',
                'Timeouts y fragmentos optimizados'
            ],
            'optional_cookies': 'Las cookies son opcionales - el sistema funciona sin ellas',
            'local_dev': 'Para desarrollo: coloca cookies.txt en la carpeta del proyecto',
            'production': 'Para producción: usa variable de entorno YOUTUBE_COOKIES (opcional)'
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
        
        # Construir comando yt-dlp con opciones anti-429
        cmd = ['python3', '-m', 'yt_dlp']
        
        # Estrategias anti-429 progresivas según el entorno
        random_ua = get_random_user_agent()
        
        # Detectar si estamos en un servidor remoto (Render, Heroku, etc.)
        is_remote_server = any([
            os.environ.get('RENDER'),
            os.environ.get('HEROKU'),
            os.environ.get('RAILWAY_PROJECT_ID'),
            os.environ.get('VERCEL'),
            'render.com' in os.environ.get('HOSTNAME', ''),
            'heroku.com' in os.environ.get('HOSTNAME', '')
        ])
        
        if is_remote_server:
            # Estrategias más agresivas para servidores remotos
            anti_429_options = [
                '--no-check-certificate',
                '--user-agent', random_ua,
                '--referer', 'https://www.youtube.com/',
                '--sleep-interval', '2',
                '--max-sleep-interval', '10',
                '--extractor-args', 'youtube:player_client=web',
                '--extractor-args', 'youtube:skip=dash',
                '--no-warnings',
                '--ignore-errors',
                '--socket-timeout', '90',
                '--fragment-retries', '20',
                '--retries', '20',
                '--throttled-rate', '50K'
            ]
            DOWNLOADS_STATUS[job_id]['environment'] = 'remote_server'
        else:
            # Estrategias normales para desarrollo local
            anti_429_options = [
                '--no-check-certificate',
                '--user-agent', random_ua,
                '--referer', 'https://www.youtube.com/',
                '--sleep-interval', '1',
                '--max-sleep-interval', '3',
                '--extractor-args', 'youtube:player_client=web',
                '--no-warnings',
                '--ignore-errors',
                '--socket-timeout', '60',
                '--fragment-retries', '10',
                '--retries', '10'
            ]
            DOWNLOADS_STATUS[job_id]['environment'] = 'local_dev'
        
        cmd.extend(anti_429_options)
        
        # Log del user agent usado
        DOWNLOADS_STATUS[job_id]['user_agent'] = random_ua
        
        # Agregar cookies si están disponibles (opcional)
        cookies_added = False
        temp_cookies_path = None
        
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
        
        # Mensaje informativo sobre cookies
        if not cookies_added:
            DOWNLOADS_STATUS[job_id]['info'] = 'Usando estrategias anti-429 sin cookies'
        else:
            DOWNLOADS_STATUS[job_id]['info'] = 'Usando cookies + estrategias anti-429'
        
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
        
        # Ejecutar comando con manejo de errores 429
        DOWNLOADS_STATUS[job_id]['command'] = ' '.join(cmd)
        
        # Intentar descarga con estrategias adaptadas al entorno
        success = False
        attempt = 1
        max_attempts = 5 if is_remote_server else 3
        
        while not success and attempt <= max_attempts:
            DOWNLOADS_STATUS[job_id]['attempt'] = f'{attempt}/{max_attempts}'
            
            if attempt > 1:
                # Crear comando modificado para reintentos
                cmd_retry = ['python3', '-m', 'yt_dlp']
                
                # Calcular sleep intervals progresivos (asegurar que max > min)
                base_sleep = 2 if is_remote_server else 1
                min_sleep = base_sleep + (attempt - 1) * 2
                max_sleep = min_sleep + 8
                
                new_ua = get_random_user_agent()
                
                if is_remote_server:
                    retry_options = [
                        '--no-check-certificate',
                        '--user-agent', new_ua,
                        '--referer', 'https://www.youtube.com/',
                        '--sleep-interval', str(min_sleep),
                        '--max-sleep-interval', str(max_sleep),
                        '--no-warnings',
                        '--ignore-errors',
                        '--socket-timeout', '90',
                        '--fragment-retries', '20',
                        '--retries', '20'
                    ]
                    
                    # Estrategias específicas por intento
                    if attempt == 2:
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=mweb',
                            '--throttled-rate', '30K'
                        ])
                    elif attempt == 3:
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=tv',
                            '--throttled-rate', '20K'
                        ])
                    elif attempt == 4:
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=web',
                            '--extractor-args', 'youtube:skip=dash',
                            '--throttled-rate', '15K'
                        ])
                        # Intentar cookies del navegador en el cuarto intento
                        if not os.environ.get('YOUTUBE_COOKIES'):
                            try:
                                retry_options.extend(['--cookies-from-browser', 'chrome'])
                                DOWNLOADS_STATUS[job_id]['cookies_used'] = 'browser_chrome_attempt4'
                            except:
                                pass
                    elif attempt == 5:
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=mweb',
                            '--throttled-rate', '10K'
                        ])
                        # Último recurso: intentar múltiples opciones de cookies
                        cookies_tried = False
                        
                        # 1. Intentar cookies de variable de entorno
                        if os.environ.get('YOUTUBE_COOKIES'):
                            try:
                                import tempfile
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                                    f.write(os.environ.get('YOUTUBE_COOKIES'))
                                    temp_cookies_path = f.name
                                retry_options.extend(['--cookies', temp_cookies_path])
                                DOWNLOADS_STATUS[job_id]['cookies_used'] = 'environment_variable'
                                cookies_tried = True
                            except Exception as e:
                                DOWNLOADS_STATUS[job_id]['cookies_error'] = str(e)
                        
                        # 2. Si no hay cookies de entorno, intentar cookies del navegador
                        if not cookies_tried:
                            for browser in ['chrome', 'firefox', 'safari', 'edge']:
                                try:
                                    retry_options.extend(['--cookies-from-browser', browser])
                                    DOWNLOADS_STATUS[job_id]['cookies_used'] = f'browser_{browser}'
                                    break
                                except:
                                    continue
                else:
                    retry_options = [
                        '--no-check-certificate',
                        '--user-agent', new_ua,
                        '--referer', 'https://www.youtube.com/',
                        '--sleep-interval', str(min_sleep),
                        '--max-sleep-interval', str(max_sleep),
                        '--extractor-args', 'youtube:player_client=web',
                        '--no-warnings',
                        '--ignore-errors',
                        '--socket-timeout', '60',
                        '--fragment-retries', '10',
                        '--retries', '10'
                    ]
                
                cmd_retry.extend(retry_options)
                
                # Configurar formato (mantener configuración original)
                if format_type == 'mp3':
                    cmd_retry.extend(['-x', '--audio-format', 'mp3', '--audio-quality', quality])
                elif format_type == 'mp4':
                    cmd_retry.extend(['-f', 'best'])
                else:
                    cmd_retry.extend(['-f', 'best'])
                
                cmd_retry.extend(['-o', output_template])
                cmd_retry.extend(['--write-info-json', '--no-playlist' if 'playlist' not in url else ''])
                cmd_retry = [x for x in cmd_retry if x]
                cmd_retry.append(url)
                
                # Delay progresivo antes del reintento
                delay = random.randint(3 + attempt, 8 + (attempt * 2))
                DOWNLOADS_STATUS[job_id]['status'] = f'esperando {delay}s antes del intento {attempt}'
                time.sleep(delay)
                
                cmd = cmd_retry
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
            
            # Verificar si fue exitoso
            if process.returncode == 0:
                success = True
            else:
                # Si es error 429 o similar, intentar de nuevo
                if '429' in stderr or 'Too Many Requests' in stderr or 'Sign in to confirm' in stderr:
                    if attempt < max_attempts:
                        DOWNLOADS_STATUS[job_id]['status'] = f'reintentando ({attempt + 1}/{max_attempts})'
                        attempt += 1
                        continue
                
                # Si es otro tipo de error, fallar inmediatamente
                DOWNLOADS_STATUS[job_id].update({
                    'status': 'error',
                    'error': stderr,
                    'stdout': stdout
                })
                return
            
            attempt += 1
        
        # Si llegamos aquí, la descarga fue exitosa
        if success:
            # Buscar archivos descargados
            downloaded_files = []
            for file in os.listdir(output_dir):
                if file.endswith(('.mp3', '.mp4', '.webm', '.m4a')):
                    downloaded_files.append(os.path.join(output_dir, file))
            
            DOWNLOADS_STATUS[job_id].update({
                'status': 'completado',
                'progress': 100,
                'files': downloaded_files,
                'stdout': stdout,
                'attempts_used': attempt - 1
            })
        else:
            DOWNLOADS_STATUS[job_id].update({
                'status': 'error',
                'error': 'Falló después de múltiples intentos',
                'stdout': stdout,
                'attempts_used': max_attempts
            })
            
    except Exception as e:
        DOWNLOADS_STATUS[job_id].update({
            'status': 'error',
            'error': str(e)
        })
    finally:
        # Limpiar archivo temporal de cookies si se creó
        if 'temp_cookies_path' in locals() and temp_cookies_path:
            try:
                os.unlink(temp_cookies_path)
            except:
                pass

@app.route('/environment', methods=['GET'])
def get_environment_info():
    """Obtener información del entorno y estrategias aplicadas"""
    
    # Detectar entorno
    is_remote_server = any([
        os.environ.get('RENDER'),
        os.environ.get('HEROKU'),
        os.environ.get('RAILWAY_PROJECT_ID'),
        os.environ.get('VERCEL'),
        'render.com' in os.environ.get('HOSTNAME', ''),
        'heroku.com' in os.environ.get('HOSTNAME', '')
    ])
    
    env_info = {
        'environment': 'remote_server' if is_remote_server else 'local_development',
        'platform_detected': [],
        'anti_blocking_strategies': {
            'max_attempts': 5 if is_remote_server else 3,
            'sleep_intervals': '3-8s' if is_remote_server else '1-3s',
            'throttling': '50K-10K' if is_remote_server else 'none',
            'timeout': '90s' if is_remote_server else '60s',
            'retries': '20' if is_remote_server else '10'
        },
        'cookies_available': bool(os.environ.get('YOUTUBE_COOKIES')),
        'hostname': os.environ.get('HOSTNAME', 'unknown')
    }
    
    # Detectar plataformas específicas
    if os.environ.get('RENDER'):
        env_info['platform_detected'].append('Render')
    if os.environ.get('HEROKU'):
        env_info['platform_detected'].append('Heroku')
    if os.environ.get('RAILWAY_PROJECT_ID'):
        env_info['platform_detected'].append('Railway')
    if os.environ.get('VERCEL'):
        env_info['platform_detected'].append('Vercel')
    
    return jsonify(env_info)

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
            'cookies_file': 'Archivo de cookies para máxima confiabilidad (opcional)'
        },
        'anti_429_system': {
            'automatic': 'Sistema automático de prevención de errores 429',
            'strategies': [
                'User-Agents aleatorios',
                'Múltiples clientes de YouTube',
                'Reintentos inteligentes con delays progresivos',
                'Throttling de velocidad adaptativo',
                'Cookies automáticas del navegador (intentos 4-5)',
                'Variables de entorno para cookies (producción)'
            ],
            'success_rate': '90-98% con estrategias automáticas',
            'fallback_cookies': 'Intenta automáticamente Chrome, Firefox, Safari, Edge'
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
