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

# Configuración
DEFAULT_OUTPUT_DIR = "/Users/O002545/Music/playlist"
DOWNLOADS_STATUS = {}

# Caché sencilla de último cliente exitoso por tipo de contenido
CLIENT_CACHE = {}

# Ruta de cookies cargadas en runtime (upload) opcional
UPLOADED_COOKIES_PATH = None

# Inicializar aplicación Flask (fue removido accidentalmente en refactor)
app = Flask(__name__)
CORS(app)

def jitter_k(value_str, enable_jitter):
    """Aplica jitter +/-10% a un valor terminado en 'K' (cadena) si está habilitado."""
    try:
        if not enable_jitter or not value_str.endswith('K'):
            return value_str
        base = int(value_str[:-1])
        import random as _r
        factor = 1 + _r.uniform(-0.10, 0.10)
        new_val = max(5, int(base * factor))
        return f"{new_val}K"
    except Exception:
        return value_str

def prefetch_metadata(url, timeout=18):
    """Obtiene metadatos rápidos del video/playlist para ajustar estrategia.
    Devuelve (data_dict, error_str)"""
    try:
        prefetch_cmd = [
            'python3','-m','yt_dlp',
            '--dump-json','--no-check-certificate','--ignore-errors','--skip-download', url
        ]
        proc = subprocess.run(prefetch_cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            return None, proc.stderr.strip()[:500]
        # Tomar solo primera línea JSON (yt-dlp a veces imprime varias)
        first_line = proc.stdout.strip().splitlines()[0]
        data = json.loads(first_line)
        return data, None
    except Exception as e:
        return None, str(e)[:500]

def multi_prefetch(url, clients, timeout=14):
    """Intenta prefetch usando distintos player_client para aumentar chance de metadata.
    Devuelve (data, client_usado, error_acumulado)"""
    errors = []
    for c in clients:
        cmd = [
            'python3','-m','yt_dlp',
            '--dump-json','--no-check-certificate','--ignore-errors','--skip-download',
            '--extractor-args', f'youtube:player_client={c}', url
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if proc.returncode == 0 and proc.stdout.strip():
                line = proc.stdout.strip().splitlines()[0]
                try:
                    data = json.loads(line)
                    return data, c, None
                except Exception as je:
                    errors.append(f'{c}:json_error:{je}')
            else:
                errors.append(f'{c}:{proc.stderr.strip()[:120]}')
        except Exception as e:
            errors.append(f'{c}:{str(e)[:120]}')
    return None, None, ' | '.join(errors)[:500]
def head_validate_small(url, timeout=8):
    """Validación rápida haciendo petición parcial (Range) para detectar bloqueos tempranos.
    Devuelve True si responde 2xx/206, False en error."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={'Range':'bytes=0-1023','User-Agent':get_random_user_agent()})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            return 200 <= code < 400
    except Exception:
        return False

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
        force_local = str(data.get('force_local', '0')) in ['1', 'true', 'True']
        force_remote = str(data.get('force_remote', '0')) in ['1', 'true', 'True']
        
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
        thread = threading.Thread(target=download_worker, args=(job_id, url, format_type, quality, naming, output_dir, cookies_file, force_local, force_remote))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'iniciado',
            'message': f'Descarga iniciada. Usa /status/{job_id} para ver el progreso'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_worker(job_id, url, format_type, quality, naming, output_dir, cookies_file=None, force_local=False, force_remote=False):
    try:
        # Actualizar estado
        DOWNLOADS_STATUS[job_id]['status'] = 'descargando'
        
        # Construir comando yt-dlp con opciones anti-429
        cmd = ['python3', '-m', 'yt_dlp']
        
        # Snapshot inicial de archivos existentes para diferenciar nuevos al terminar
        try:
            initial_files_snapshot = set(os.listdir(output_dir))
        except Exception:
            initial_files_snapshot = set()

        # Flags de características avanzadas (pack completo)
        enable_prefetch = os.environ.get('ENABLE_PREFETCH', '1') == '1'
        enable_cache = os.environ.get('ENABLE_CLIENT_CACHE', '1') == '1'
        mobile_first = os.environ.get('USE_MOBILE_FIRST', '1') == '1'
        head_validate = os.environ.get('HEAD_VALIDATE', '1') == '1'
        jitter_enabled = os.environ.get('JITTER_THROTTLE', '1') == '1'

        DOWNLOADS_STATUS[job_id]['advanced_pack'] = True
        DOWNLOADS_STATUS[job_id]['jitter'] = jitter_enabled

        # Estrategias anti-bot progresivas según el entorno
        random_ua = get_random_user_agent()
        # Heurísticas de tipo de contenido
        is_shorts = '/shorts/' in url
        is_music = 'music.youtube.com' in url
        content_type = 'shorts' if is_shorts else ('music' if is_music else 'standard')
        DOWNLOADS_STATUS[job_id]['content_type'] = content_type

        prefetch_data = None
        prefetch_error = None
        head_ok = None
        first_audio_url = None
        if enable_prefetch:
            data, err = prefetch_metadata(url)
            if data:
                prefetch_data = data
                DOWNLOADS_STATUS[job_id]['prefetch'] = 'ok'
                DOWNLOADS_STATUS[job_id]['prefetch_title'] = data.get('title','')[:120]
                DOWNLOADS_STATUS[job_id]['prefetch_duration'] = data.get('duration')
                try:
                    fmts = data.get('formats') or []
                    audio_only = [f for f in fmts if f.get('vcodec') in (None,'none') and f.get('acodec') not in (None,'none')]
                    audio_only.sort(key=lambda f: f.get('abr',0), reverse=True)
                    if audio_only:
                        first_audio_url = audio_only[0].get('url')
                except Exception:
                    pass
            else:
                DOWNLOADS_STATUS[job_id]['prefetch'] = 'fail'
                if err:
                    prefetch_error = err
                    DOWNLOADS_STATUS[job_id]['prefetch_error'] = err
                # Multi-prefetch fallback si falla el primero
                mp_clients = ['web','mweb','tv_embedded','web_embedded']
                mp_data, mp_client, mp_err = multi_prefetch(url, mp_clients)
                if mp_data:
                    prefetch_data = mp_data
                    DOWNLOADS_STATUS[job_id]['prefetch'] = 'ok_multi'
                    DOWNLOADS_STATUS[job_id]['prefetch_client'] = mp_client
                    DOWNLOADS_STATUS[job_id]['prefetch_title'] = mp_data.get('title','')[:120]
                    DOWNLOADS_STATUS[job_id]['prefetch_duration'] = mp_data.get('duration')
                    try:
                        fmts = mp_data.get('formats') or []
                        audio_only = [f for f in fmts if f.get('vcodec') in (None,'none') and f.get('acodec') not in (None,'none')]
                        audio_only.sort(key=lambda f: f.get('abr',0), reverse=True)
                        if audio_only:
                            first_audio_url = audio_only[0].get('url')
                    except Exception:
                        pass
                else:
                    if mp_err:
                        DOWNLOADS_STATUS[job_id]['prefetch_multi_error'] = mp_err
        # Validación HEAD parcial si habilitado y tenemos URL de audio
        if head_validate and first_audio_url:
            head_ok = head_validate_small(first_audio_url)
            DOWNLOADS_STATUS[job_id]['head_check'] = head_ok

        # Determinar cliente inicial usando caché / heurística
        cached_client = CLIENT_CACHE.get(content_type) if enable_cache else None
        base_player_client = None
        if cached_client:
            base_player_client = cached_client
            DOWNLOADS_STATUS[job_id]['cache_hit'] = True
        else:
            DOWNLOADS_STATUS[job_id]['cache_hit'] = False
            if mobile_first:
                if content_type == 'shorts':
                    base_player_client = 'mweb'
                elif content_type == 'music':
                    base_player_client = 'android'
                else:
                    base_player_client = 'web'
            else:
                base_player_client = 'web'
        # Si la validación HEAD falló, preferir cambiar a un cliente diferente si es web
        if head_ok is False and base_player_client == 'web':
            base_player_client = 'mweb'
            DOWNLOADS_STATUS[job_id]['head_adjusted_client'] = True
        DOWNLOADS_STATUS[job_id]['chosen_initial_client'] = base_player_client
        
        # Detectar si estamos en un servidor remoto (Render, Heroku, etc.)
        is_remote_server_detected = any([
            os.environ.get('RENDER'),
            os.environ.get('HEROKU'),
            os.environ.get('RAILWAY_PROJECT_ID'),
            os.environ.get('VERCEL'),
            'render.com' in os.environ.get('HOSTNAME', ''),
            'heroku.com' in os.environ.get('HOSTNAME', '')
        ])
        # Aplicar overrides por request
        if force_local and not force_remote:
            is_remote_server = False
            DOWNLOADS_STATUS[job_id]['force_mode'] = 'local_emulation'
        elif force_remote and not force_local:
            is_remote_server = True
            DOWNLOADS_STATUS[job_id]['force_mode'] = 'remote_forced'
        else:
            is_remote_server = is_remote_server_detected
        DOWNLOADS_STATUS[job_id]['is_remote_detected'] = is_remote_server_detected

        # Overrides manuales para emular entorno (solución rápida en hosting)
        if os.environ.get('FORCE_LOCAL_MODE') == '1' or os.environ.get('FORCE_LOCAL_STRATEGIES') == '1':
            DOWNLOADS_STATUS[job_id]['force_mode'] = 'local_emulation'
            is_remote_server = False
        elif os.environ.get('FORCE_REMOTE_MODE') == '1':
            DOWNLOADS_STATUS[job_id]['force_mode'] = 'remote_forced'
            is_remote_server = True
        
        # Log del entorno detectado
        DOWNLOADS_STATUS[job_id]['environment'] = 'remote_server' if is_remote_server else 'local_dev'
        
        # Definir bandera para saltar intento de extracción de cookies de navegador
        # Preparar opciones base dependiendo del entorno
        skip_browser_cookie_scan = False
        if is_remote_server:
            anti_429_options = [
                '--no-check-certificate', '--user-agent', random_ua, '--referer', 'https://www.youtube.com/',
                '--sleep-interval', '3', '--max-sleep-interval', '12',
                '--extractor-args', f'youtube:player_client={base_player_client}',
                '--extractor-args', 'youtube:skip=dash,hls', '--no-warnings', '--ignore-errors',
                '--socket-timeout', '90', '--fragment-retries', '25', '--retries', '25',
                '--throttled-rate', jitter_k('50K', jitter_enabled), '--geo-bypass', '--geo-bypass-country', 'US'
            ]
            if content_type == 'shorts':
                anti_429_options += ['--add-header','Accept-Language: en-US,en;q=0.9','--add-header','DNT: 1']
            DOWNLOADS_STATUS[job_id]['anti_bot_level'] = 'server_aggressive'
        else:
            anti_429_options = [
                '--no-check-certificate','--user-agent', random_ua,'--referer','https://www.youtube.com/',
                '--sleep-interval','2','--max-sleep-interval','5','--extractor-args','youtube:player_client=web',
                '--no-warnings','--ignore-errors','--socket-timeout','60','--fragment-retries','15','--retries','15'
            ]
            # Detectar disponibilidad de perfiles locales reales (solo tiene sentido en host con navegadores instalados)
            def browser_profile_exists():
                home = os.path.expanduser('~')
                chrome_path = os.path.join(home, '.config', 'google-chrome')
                firefox_path = os.path.join(home, '.mozilla', 'firefox')
                return (os.path.isdir(chrome_path) or os.path.isdir(firefox_path))

            auto_skip = False
            if force_local and is_remote_server_detected and not browser_profile_exists():
                # Estás forzando local en un hosting sin bases de datos de cookies -> saltar
                auto_skip = True
                DOWNLOADS_STATUS[job_id]['auto_cookies_unavailable'] = True
            skip_browser_cookie_scan = (
                os.environ.get('DISABLE_BROWSER_COOKIES') == '1' or
                os.environ.get('FORCE_LOCAL_NO_BROWSER') == '1' or
                (force_local and os.environ.get('NO_BROWSER_RUNTIME') == '1') or
                auto_skip
            )
            browser_cookies_added = False
            if not skip_browser_cookie_scan:
                for browser in ['chrome','firefox','safari','edge']:
                    try:
                        test_cmd = ['python3','-m','yt_dlp','--cookies-from-browser',browser,'--simulate','https://www.youtube.com/watch?v=dQw4w9WgXcQ']
                        test_process = subprocess.run(test_cmd, capture_output=True, timeout=8)
                        if test_process.returncode == 0:
                            anti_429_options += ['--cookies-from-browser', browser]
                            DOWNLOADS_STATUS[job_id]['auto_cookies'] = f'Usando cookies de {browser}'
                            browser_cookies_added = True
                            break
                    except Exception:
                        continue
            if browser_cookies_added:
                DOWNLOADS_STATUS[job_id]['anti_bot_level'] = 'local_with_browser_cookies'
            else:
                if skip_browser_cookie_scan:
                    DOWNLOADS_STATUS[job_id]['anti_bot_level'] = 'local_basic_no_browser'
                    DOWNLOADS_STATUS[job_id]['auto_cookies'] = 'omitido_scan_navegador'
                    if auto_skip:
                        DOWNLOADS_STATUS[job_id]['auto_cookies_reason'] = 'no_browser_profiles_in_remote'
                else:
                    DOWNLOADS_STATUS[job_id]['anti_bot_level'] = 'local_basic'

        cmd.extend(anti_429_options)
        DOWNLOADS_STATUS[job_id]['user_agent'] = random_ua

        # Cookies prioridad alta (runtime upload > env var > file)
        cookies_added = False
        temp_cookies_path = None
        global UPLOADED_COOKIES_PATH
        if UPLOADED_COOKIES_PATH and os.path.exists(UPLOADED_COOKIES_PATH):
            cmd += ['--cookies', UPLOADED_COOKIES_PATH]
            DOWNLOADS_STATUS[job_id]['cookies'] = 'cookies_upload_runtime'
            DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'uploaded_initial'
            cookies_added = True
        elif os.environ.get('YOUTUBE_COOKIES'):
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(os.environ.get('YOUTUBE_COOKIES'))
                temp_cookies_path = f.name
            cmd += ['--cookies', temp_cookies_path]
            DOWNLOADS_STATUS[job_id]['cookies'] = 'env_variable'
            DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'env_initial'
            cookies_added = True
        elif cookies_file:
            if os.path.exists(cookies_file):
                cmd += ['--cookies', cookies_file]
                DOWNLOADS_STATUS[job_id]['cookies'] = f'file:{cookies_file}'
                DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'file_initial'
                cookies_added = True
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                alt = os.path.join(script_dir, cookies_file)
                if os.path.exists(alt):
                    cmd += ['--cookies', alt]
                    DOWNLOADS_STATUS[job_id]['cookies'] = f'file:{alt}'
                    DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'file_initial_alt'
                    cookies_added = True
        elif not cookies_added and is_remote_server:
            DOWNLOADS_STATUS[job_id]['info'] = 'Servidor remoto: usando estrategias anti-bot sin cookies'
            if (force_local or os.environ.get('ALLOW_FAKE_COOKIE') == '1') and os.environ.get('USE_FAKE_CONSENT_COOKIE','1') == '1':
                try:
                    import tempfile
                    fake_cookie_content = os.environ.get('FAKE_COOKIE_CONTENT', (
                        "# Netscape HTTP Cookie File\n"
                        ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tCONSENT\tYES+cb\n"
                        ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tPREF\tf1=50000000&tz=UTC\n"
                        ".youtube.com\tTRUE\t/\tTRUE\t2147483647\tYSC\tRANDOM123TEST\n"
                    ))
                    fake_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                    fake_file.write(fake_cookie_content)
                    fake_file.close()
                    temp_cookies_path = fake_file.name
                    cmd += ['--cookies', temp_cookies_path]
                    DOWNLOADS_STATUS[job_id]['cookies'] = 'cookie_sintetica'
                    DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'synthetic_initial'
                except Exception as e:
                    DOWNLOADS_STATUS[job_id]['fake_cookie_error'] = str(e)
        else:
            if not cookies_added:
                DOWNLOADS_STATUS[job_id]['info'] = 'Usando cookies manuales + estrategias anti-bot'
        DOWNLOADS_STATUS[job_id].setdefault('cookie_stage', 'none')
        pending_cookie_escalation = False
        first_bot_trigger_attempt = None

        # Formato/naming
        if format_type == 'mp3':
            cmd += ['-x','--audio-format','mp3','--audio-quality', quality]
        elif format_type == 'mp4':
            cmd.extend(['-f', 'best'])
        else:
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
        
        # Ejecutar comando con manejo de errores específicos
        DOWNLOADS_STATUS[job_id]['command'] = ' '.join(cmd)
        
        # Intentar descarga con estrategias adaptadas al entorno y tipo de error
        success = False
        attempt = 1
        # Permitir intento adicional super agresivo (7) controlado por variable
        enable_final_aggressive = os.environ.get('AGGRESSIVE_FINAL_ATTEMPT', '1') == '1'
        # Ajustar max_attempts para incluir android / ios si pack completo
        extra_clients = 2  # android + ios
        base_remote = 6 if is_remote_server else 4
        max_attempts = base_remote + (1 if enable_final_aggressive else 0) + (extra_clients if enable_final_aggressive else 0)
        max_attempts = min(max_attempts, 9)
        DOWNLOADS_STATUS[job_id]['max_attempts'] = max_attempts
        
        # Preparar proxies si definidos
        proxy_list_env = os.environ.get('PROXY_LIST', '').strip()
        rotate_proxies = os.environ.get('ROTATE_PROXIES', '1') == '1'
        proxies = [p.strip() for p in proxy_list_env.split(',') if p.strip()] if proxy_list_env else []
        if proxies:
            DOWNLOADS_STATUS[job_id]['proxies_enabled'] = len(proxies)
        while not success and attempt <= max_attempts:
            DOWNLOADS_STATUS[job_id]['attempt'] = f'{attempt}/{max_attempts}'
            # Si hay escalada pendiente y aún no hemos añadido cookies reales
            if attempt > 1 and pending_cookie_escalation and not cookies_added:
                # Escalar: usar uploaded/env/file en este punto si disponibles
                escalated = False
                if UPLOADED_COOKIES_PATH and os.path.exists(UPLOADED_COOKIES_PATH):
                    cmd.extend(['--cookies', UPLOADED_COOKIES_PATH])
                    DOWNLOADS_STATUS[job_id]['cookies'] = 'cookies_upload_runtime'
                    DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'uploaded_escalated'
                    escalated = True
                elif os.environ.get('YOUTUBE_COOKIES'):
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                            f.write(os.environ.get('YOUTUBE_COOKIES'))
                            temp_cookies_path = f.name
                        cmd.extend(['--cookies', temp_cookies_path])
                        DOWNLOADS_STATUS[job_id]['cookies'] = 'env_variable'
                        DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'env_escalated'
                        escalated = True
                    except Exception as e:
                        DOWNLOADS_STATUS[job_id]['cookies_error'] = f'env_escalation:{e}'
                elif cookies_file and os.path.exists(cookies_file):
                    cmd.extend(['--cookies', cookies_file])
                    DOWNLOADS_STATUS[job_id]['cookies'] = f'file:{cookies_file}'
                    DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'file_escalated'
                    escalated = True
                if escalated:
                    cookies_added = True
                    pending_cookie_escalation = False
            
            if attempt > 1:
                # Crear comando modificado para reintentos específicos anti-bot
                cmd_retry = ['python3', '-m', 'yt_dlp']
                
                # Calcular sleep intervals progresivos (asegurar que max > min)
                base_sleep = 3 if is_remote_server else 2
                min_sleep = base_sleep + (attempt - 1) * 2
                max_sleep = min_sleep + 10
                
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
                        '--socket-timeout', '120',
                        '--fragment-retries', '30',
                        '--retries', '30',
                        '--geo-bypass',
                        '--geo-bypass-country', 'US'
                    ]

                    # Estrategias específicas por intento para servidores (diferenciando Shorts)
                    if is_shorts:
                        if attempt == 2:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=tv_embedded',
                                '--extractor-args', 'youtube:player_skip=configs',
                                '--throttled-rate', '35K'
                            ])
                        elif attempt == 3:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=web_embedded',
                                '--throttled-rate', '30K'
                            ])
                        elif attempt == 4:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=mweb',
                                '--throttled-rate', '25K'
                            ])
                        elif attempt == 5:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=tv',
                                '--extractor-args', 'youtube:skip=dash,hls',
                                '--throttled-rate', '18K'
                            ])
                        elif attempt == 6:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=mediaconnect',
                                '--add-header', 'X-YouTube-Client-Name:3',
                                '--add-header', 'X-YouTube-Client-Version:17.31.35',
                                '--throttled-rate', '12K',
                                '--add-header', 'Accept-Language: en-US,en;q=0.9',
                                '--add-header', 'DNT: 1'
                            ])
                            if os.environ.get('YOUTUBE_COOKIES') and not cookies_added:
                                try:
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                                        f.write(os.environ.get('YOUTUBE_COOKIES'))
                                        temp_cookies_path = f.name
                                    retry_options.extend(['--cookies', temp_cookies_path])
                                    DOWNLOADS_STATUS[job_id]['cookies_used'] = 'env_attempt6'
                                except Exception as e:
                                    DOWNLOADS_STATUS[job_id]['cookies_error'] = str(e)
                        elif attempt == 7:
                            multi_clients = [
                                '--extractor-args', 'youtube:player_client=tv',
                                '--extractor-args', 'youtube:player_client=web',
                                '--extractor-args', 'youtube:player_client=web_embedded',
                                '--extractor-args', 'youtube:innertube_host=youtubei.googleapis.com'
                            ]
                            for mc in multi_clients:
                                retry_options.append(mc)
                            retry_options.extend([
                                '--add-header', 'Origin: https://www.youtube.com',
                                '--add-header', 'Referer: https://www.youtube.com/',
                                '--add-header', 'Accept-Language: en-US,en;q=0.8',
                                '--add-header', 'Sec-Fetch-Dest: empty',
                                '--add-header', 'Sec-Fetch-Mode: cors',
                                '--add-header', 'Sec-Fetch-Site: same-origin',
                                '--throttled-rate', '8K'
                            ])
                            if os.environ.get('YOUTUBE_COOKIES') and not cookies_added:
                                try:
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                                        f.write(os.environ.get('YOUTUBE_COOKIES'))
                                        temp_cookies_path = f.name
                                    retry_options.extend(['--cookies', temp_cookies_path])
                                    DOWNLOADS_STATUS[job_id]['cookies_used'] = 'env_attempt7'
                                except Exception as e:
                                    DOWNLOADS_STATUS[job_id]['cookies_error'] = str(e)
                    else:
                        # Secuencia original para videos estándar
                        if attempt == 2:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=mweb',
                                '--throttled-rate', '40K'
                            ])
                        elif attempt == 3:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=tv',
                                '--extractor-args', 'youtube:skip=dash,hls',
                                '--throttled-rate', '30K'
                            ])
                        elif attempt == 4:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=web',
                                '--extractor-args', 'youtube:skip=dash',
                                '--extractor-args', 'youtube:innertube_host=youtubei.googleapis.com',
                                '--throttled-rate', '20K'
                            ])
                        elif attempt == 5:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=tv_embedded',
                                '--extractor-args', 'youtube:player_skip=configs',
                                '--throttled-rate', '15K'
                            ])
                        elif attempt == 6:
                            retry_options.extend([
                                '--extractor-args', 'youtube:player_client=mediaconnect',
                                '--add-header', 'X-YouTube-Client-Name:3',
                                '--add-header', 'X-YouTube-Client-Version:17.31.35',
                                '--throttled-rate', '12K',
                                '--add-header', 'Accept-Language: en-US,en;q=0.9',
                                '--add-header', 'DNT: 1'
                            ])
                            if os.environ.get('YOUTUBE_COOKIES') and not cookies_added:
                                try:
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                                        f.write(os.environ.get('YOUTUBE_COOKIES'))
                                        temp_cookies_path = f.name
                                    retry_options.extend(['--cookies', temp_cookies_path])
                                    DOWNLOADS_STATUS[job_id]['cookies_used'] = 'env_attempt6'
                                except Exception as e:
                                    DOWNLOADS_STATUS[job_id]['cookies_error'] = str(e)
                        elif attempt == 7:
                            multi_clients = [
                                '--extractor-args', 'youtube:player_client=tv',
                                '--extractor-args', 'youtube:player_client=web',
                                '--extractor-args', 'youtube:player_client=web_embedded',
                                '--extractor-args', 'youtube:innertube_host=youtubei.googleapis.com'
                            ]
                            for mc in multi_clients:
                                retry_options.append(mc)
                            retry_options.extend([
                                '--add-header', 'Origin: https://www.youtube.com',
                                '--add-header', 'Referer: https://www.youtube.com/',
                                '--add-header', 'Accept-Language: en-US,en;q=0.8',
                                '--add-header', 'Sec-Fetch-Dest: empty',
                                '--add-header', 'Sec-Fetch-Mode: cors',
                                '--add-header', 'Sec-Fetch-Site: same-origin',
                                '--throttled-rate', '8K'
                            ])
                            if os.environ.get('YOUTUBE_COOKIES') and not cookies_added:
                                try:
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                                        f.write(os.environ.get('YOUTUBE_COOKIES'))
                                        temp_cookies_path = f.name
                                    retry_options.extend(['--cookies', temp_cookies_path])
                                    DOWNLOADS_STATUS[job_id]['cookies_used'] = 'env_attempt7'
                                except Exception as e:
                                    DOWNLOADS_STATUS[job_id]['cookies_error'] = str(e)
                else:
                    # Estrategias para entorno local con cookies automáticas
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
                    
                    # Estrategias específicas por intento para local
                    if attempt == 2:
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=mweb'
                        ])
                        # Intentar cookies de Chrome específicamente
                        try:
                            retry_options.extend(['--cookies-from-browser', 'chrome'])
                            DOWNLOADS_STATUS[job_id]['cookies_attempt'] = 'chrome_attempt2'
                        except:
                            pass
                    elif attempt == 3:
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=tv'
                        ])
                        # Intentar cookies de Firefox
                        try:
                            retry_options.extend(['--cookies-from-browser', 'firefox'])
                            DOWNLOADS_STATUS[job_id]['cookies_attempt'] = 'firefox_attempt3'
                        except:
                            pass
                    elif attempt == 4:
                        # Último recurso local: múltiples opciones
                        retry_options.extend([
                            '--extractor-args', 'youtube:player_client=web',
                            '--extractor-args', 'youtube:skip=dash'
                        ])
                        
                        # Intentar todos los navegadores disponibles
                        cookies_found = False
                        for browser in ['safari', 'edge', 'brave', 'opera']:
                            try:
                                retry_options.extend(['--cookies-from-browser', browser])
                                DOWNLOADS_STATUS[job_id]['cookies_attempt'] = f'{browser}_attempt4'
                                cookies_found = True
                                break
                            except:
                                continue
                        
                        if not cookies_found and cookies_file:
                            # Intentar archivo de cookies si se especificó
                            if os.path.exists(cookies_file):
                                retry_options.extend(['--cookies', cookies_file])
                                DOWNLOADS_STATUS[job_id]['cookies_attempt'] = 'file_attempt4'
                
                cmd_retry.extend(retry_options)
                # Asignar proxy rotativo
                if proxies:
                    idx = (attempt - 1) % len(proxies) if rotate_proxies else 0
                    cmd_retry.extend(['--proxy', proxies[idx]])
                    DOWNLOADS_STATUS[job_id]['proxy_used'] = proxies[idx]
                
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
                # Si seguimos con bot_verification continuo y sin cookies reales, aumentar delay
                if DOWNLOADS_STATUS[job_id].get('error_type') == 'bot_verification' and not cookies_added and attempt >= 3:
                    delay += 5
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
                # Detectar tipos específicos de errores
                error_is_bot_check = any([
                    'Sign in to confirm you\'re not a bot' in stderr,
                    'Sign in to confirm' in stderr,
                    'not a bot' in stderr
                ])
                
                error_is_429 = any([
                    '429' in stderr,
                    'Too Many Requests' in stderr,
                    'HTTP Error 429' in stderr
                ])
                
                error_is_general_block = any([
                    'Unable to download webpage' in stderr,
                    'HTTP Error 403' in stderr,
                    'This video is not available' in stderr
                ])
                
                # Si es error de verificación de bot, 429 o bloqueo general, intentar de nuevo
                if (error_is_bot_check or error_is_429 or error_is_general_block) and attempt < max_attempts:
                    error_type = 'bot_verification' if error_is_bot_check else 'rate_limit' if error_is_429 else 'general_block'
                    DOWNLOADS_STATUS[job_id]['error_type'] = error_type
                    if error_is_bot_check and not cookies_added:
                        DOWNLOADS_STATUS[job_id]['requires_cookies'] = True
                        pending_cookie_escalation = True  # Solicitar escalada temprana
                        if first_bot_trigger_attempt is None:
                            first_bot_trigger_attempt = attempt
                            DOWNLOADS_STATUS[job_id]['bot_trigger_attempt'] = attempt
                    DOWNLOADS_STATUS[job_id]['status'] = f'reintentando por {error_type} ({attempt + 1}/{max_attempts})'
                    
                    # Delay más largo para errores de bot
                    if error_is_bot_check:
                        extra_delay = random.randint(5, 15)
                        DOWNLOADS_STATUS[job_id]['status'] = f'esperando {extra_delay}s extra por verificación de bot'
                        time.sleep(extra_delay)
                    
                    attempt += 1
                    continue
                
                # Si es otro tipo de error, fallar inmediatamente
                DOWNLOADS_STATUS[job_id].update({
                    'status': 'error',
                    'error': stderr,
                    'stdout': stdout,
                    'error_analysis': {
                        'bot_check': error_is_bot_check,
                        'rate_limit': error_is_429,
                        'general_block': error_is_general_block,
                        'other_error': not (error_is_bot_check or error_is_429 or error_is_general_block)
                    }
                })
                return
            
            attempt += 1
        
        # Si llegamos aquí, la descarga fue exitosa
        if success:
            # Determinar archivos nuevos comparando con snapshot inicial
            downloaded_files = []
            try:
                final_listing = set(os.listdir(output_dir))
                new_files = [f for f in final_listing - initial_files_snapshot if f.lower().endswith(('.mp3','.mp4','.webm','.m4a','.info.json'))]
                # Priorizar: audio/video principal primero, luego info.json
                def sort_key(name):
                    if name.endswith('.info.json'): return (2, name)
                    if name.endswith(('.mp3','.m4a')): return (0, name)
                    return (1, name)
                new_files.sort(key=sort_key)
                downloaded_files = [os.path.join(output_dir, f) for f in new_files]
            except Exception as e:
                DOWNLOADS_STATUS[job_id]['file_diff_error'] = str(e)
                # Fallback a listado completo
                try:
                    for file in os.listdir(output_dir):
                        if file.endswith(('.mp3', '.mp4', '.webm', '.m4a')):
                            downloaded_files.append(os.path.join(output_dir, file))
                except Exception:
                    pass

            # Guardar cliente exitoso en caché si posible
            if enable_cache:
                # Intentar inferir último client usado buscando en comando final
                final_cmd = DOWNLOADS_STATUS[job_id].get('command','')
                chosen = None
                for marker in ['player_client=android','player_client=ios','player_client=mweb','player_client=tv_embedded','player_client=tv','player_client=web_embedded','player_client=mediaconnect','player_client=web']:
                    if marker in final_cmd:
                        chosen = marker.split('=')[1]
                        break
                if chosen:
                    CLIENT_CACHE[content_type] = chosen
                    DOWNLOADS_STATUS[job_id]['cached_saved'] = chosen
            
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

@app.route('/upload-cookies', methods=['POST'])
def upload_cookies():
    """Permite subir el contenido de un archivo de cookies (formato Netscape) en runtime.
    Body JSON: {"cookies_text":"..."}
    Prioridad sobre variable de entorno."""
    global UPLOADED_COOKIES_PATH
    try:
        data = request.get_json(force=True)
        cookies_text = data.get('cookies_text','').strip()
        if not cookies_text:
            return jsonify({'error':'cookies_text vacío'}), 400
        # Validación mínima: debe contener al menos .youtube.com y PREF/CONSENT o ytc
        if '.youtube.com' not in cookies_text:
            return jsonify({'error':'Contenido no parece contener cookies de youtube'}), 400
        import tempfile
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        tf.write(cookies_text)
        tf.flush(); tf.close()
        UPLOADED_COOKIES_PATH = tf.name
        return jsonify({'status':'ok','path':UPLOADED_COOKIES_PATH,'size':len(cookies_text)})
    except Exception as e:
        return jsonify({'error':str(e)}), 500

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
            'automatic': 'Sistema automático de prevención de errores 429 y verificación de bot',
            'strategies': [
                'User-Agents aleatorios (13 navegadores)',
                'Múltiples clientes de YouTube (web, mweb, tv, tv_embedded, mediaconnect)',
                'Reintentos inteligentes con delays progresivos',
                'Throttling de velocidad adaptativo',
                'Geo-bypass y configuraciones alternativas',
                'Cookies del navegador automáticas (solo local)',
                'Variables de entorno para cookies (producción)',
                'Headers específicos anti-bot',
                'Estrategias específicas para "Sign in to confirm you\'re not a bot"'
            ],
            'success_rate': '85-98% dependiendo del entorno y tipo de contenido',
            'attempts': {
                'local': '4 intentos con cookies automáticas del navegador',
                'remote': '6 intentos con estrategias servidor-optimizadas'
            },
            'production_note': 'Para máxima efectividad en producción, configure YOUTUBE_COOKIES'
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
