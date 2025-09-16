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
import re
import concurrent.futures

# Configuración
DEFAULT_OUTPUT_DIR = "/Users/O002545/Music/playlist"
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

def detect_cookies_strength():
    """Evalúa fuerza de cookies en variable de entorno YOUTUBE_COOKIES.
    Devuelve 'strong', 'synthetic', 'none'. (Synthetic se infiere por cookie_stage más adelante)."""
    ck = os.environ.get('YOUTUBE_COOKIES') or ''
    if not ck:
        return 'none'
    strong_markers = ['SID=', 'SAPISID', '__Secure-1PSID', '__Secure-3PSID', 'LOGIN_INFO', 'VISITOR_INFO1_LIVE']
    for m in strong_markers:
        if m in ck:
            return 'strong'
    return 'none'

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
        
        # DEBUG: Verificar qué datos está recibiendo el servidor
        print(f"🔍 [DEBUG] URL recibida en servidor: {data.get('url')}")
        print(f"🔍 [DEBUG] Datos completos: {data}")
        
        # Validar datos requeridos
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL es requerida'}), 400
        
        # Parámetros opcionales con valores por defecto
        format_type = data.get('format', 'mp3')  # mp3, mp4, best
        quality = data.get('quality', '0')  # 0=mejor, 320K, 256K, 128K
        naming = data.get('naming', 'artist-title')  # title, artist-title
        output_dir_raw = data.get('output_dir')  # Ahora es obligatorio especificar la carpeta
        output_dir = None
        cookies_file = data.get('cookies_file')  # Archivo de cookies opcional
        force_local = str(data.get('force_local', '0')) in ['1', 'true', 'True']
        force_remote = str(data.get('force_remote', '0')) in ['1', 'true', 'True']
        reuse_existing = str(data.get('reuse_existing', '0')) in ['1','true','True']
        
        # Validar que se especifique output_dir
        if not output_dir_raw:
            return jsonify({
                'error': 'output_dir es obligatorio. Especifica la carpeta donde guardar los archivos',
                'ejemplo': {'output_dir': '/Users/tuusuario/Downloads/musica'}
            }), 400
        # Expandir ~ y variables de entorno de forma segura
        try:
            expanded = os.path.expanduser(os.path.expandvars(output_dir_raw.strip()))
            if not expanded:
                raise ValueError('Ruta vacía tras expansión')
            output_dir = expanded
        except Exception as e:
            return jsonify({'error':'No se pudo expandir output_dir','detalle':str(e)}), 400
        
        # Crear directorio si no existe
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return jsonify({'error':'No se pudo crear la carpeta destino','detalle':str(e),'ruta':output_dir}), 400
        
        # Generar ID único para el trabajo
        job_id = f"job_{int(time.time())}_{len(DOWNLOADS_STATUS)}"
        
        # Inicializar estado
        DOWNLOADS_STATUS[job_id] = {
            'status': 'iniciando',
            'url': url,
            'created_at': datetime.now().isoformat(),
            'progress': 0,
            'files': [],
            'error': None,
            'requested_output_dir': output_dir_raw,
            'resolved_output_dir': output_dir
        }
        
        # Ejecutar descarga en hilo separado
        thread = threading.Thread(target=download_worker, args=(job_id, url, format_type, quality, naming, output_dir, cookies_file, force_local, force_remote, reuse_existing))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'iniciado',
            'message': f'Descarga iniciada. Usa /status/{job_id} para ver el progreso'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def download_worker(job_id, url, format_type, quality, naming, output_dir, cookies_file=None, force_local=False, force_remote=False, reuse_existing=False):
    try:
        def extract_playlist_urls(playlist_url):
            """Extrae todas las URLs de una playlist usando yt-dlp --flat-playlist --print url"""
            try:
                cmd = [
                    'python3', '-m', 'yt_dlp', '--flat-playlist', '--print', 'url', '--no-warnings', '--ignore-errors', playlist_url
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if proc.returncode == 0:
                    urls = [line.strip() for line in proc.stdout.splitlines() if line.strip().startswith('http')]
                    return urls
                else:
                    return []
            except Exception as e:
                return []

        # Actualizar estado
        DOWNLOADS_STATUS[job_id]['status'] = 'descargando'

        def extract_video_id(u: str):
            try:
                lu = u.lower()
                m = re.search(r'[?&]v=([a-z0-9_-]{6,})', lu)
                if m:
                    return m.group(1)
                m = re.search(r'youtu\.be/([a-z0-9_-]{6,})', lu)
                if m:
                    return m.group(1)
                m = re.search(r'/shorts/([a-z0-9_-]{6,})', lu)
                if m:
                    return m.group(1)
            except Exception:
                pass
            return None

        video_id = extract_video_id(url)
        if video_id:
            DOWNLOADS_STATUS[job_id]['video_id_detected'] = video_id

        # Detectar si es playlist
        is_playlist = False
        if 'list=' in url or '/playlist?' in url:
            is_playlist = True

        # Si es playlist, extraer URLs y descargar en paralelo
        # Si es playlist, extraer URLs y descargar en paralelo
        if is_playlist:
            playlist_urls = extract_playlist_urls(url)
            DOWNLOADS_STATUS[job_id]['playlist_urls_count'] = len(playlist_urls)
            
            # --- Diagnóstico previo: ejecutar yt-dlp en modo dry-run para el primer video de la playlist y loguear resultado ---
            if playlist_urls and len(playlist_urls) > 0:
                dry_cmd = ['python3', '-m', 'yt_dlp', '--simulate', '--no-warnings', '--ignore-errors', playlist_urls[0]]
                try:
                    print(f"[DIAG] Ejecutando dry-run yt-dlp: {' '.join(dry_cmd)}")
                    dry_proc = subprocess.run(dry_cmd, capture_output=True, text=True, timeout=60)
                    print(f"[DIAG] yt-dlp dry-run returncode: {dry_proc.returncode}")
                    print(f"[DIAG] yt-dlp dry-run stdout:\n{dry_proc.stdout}")
                    print(f"[DIAG] yt-dlp dry-run stderr:\n{dry_proc.stderr}")
                except Exception as diag_ex:
                    print(f"[DIAG] Error ejecutando dry-run yt-dlp: {diag_ex}")
            
            if not playlist_urls:
                DOWNLOADS_STATUS[job_id]['status'] = 'error'
                DOWNLOADS_STATUS[job_id]['error'] = 'No se pudieron extraer los videos de la playlist.'
                return
            
            DOWNLOADS_STATUS[job_id]['playlist_count'] = len(playlist_urls)
            DOWNLOADS_STATUS[job_id]['playlist_urls'] = playlist_urls

            # --- Configurar modo descarga: secuencial por defecto para estabilidad ---
            use_sequential = os.environ.get('FORCE_SEQUENTIAL', '1') == '1'  # Por defecto secuencial
            use_single_command = os.environ.get('USE_SINGLE_COMMAND', '1') == '1'  # Usar un solo comando yt-dlp para toda la playlist
            
            # Definir max_workers siempre, independientemente del modo
            max_workers = 3 if use_sequential else min(3, len(playlist_urls))
            
            if use_single_command:
                print(f"[PLAYLIST] Descargando playlist completa con un solo comando yt-dlp (modo clásico)")
                # Usar el método original: un solo comando yt-dlp para toda la playlist
                DOWNLOADS_STATUS[job_id]['download_mode'] = 'single_command_playlist'
                # Continuar con el código normal de descarga (no como playlist individual)
                is_playlist = False  # Tratar como descarga normal
            else:
                print(f"[PLAYLIST] Procesando {len(playlist_urls)} URLs en modo {'secuencial' if use_sequential else f'paralelo ({max_workers} workers)'}")
                
                results = [None] * len(playlist_urls)
                files_downloaded = []
                progress_map = [0] * len(playlist_urls)
                # Nuevo: lista de progreso detallado por archivo
                parallel_progress = [
                    {'index': idx, 'progress': 0, 'current_file': None, 'status': 'pendiente'}
                    for idx in range(len(playlist_urls))
                ]
                DOWNLOADS_STATUS[job_id]['parallel_progress'] = parallel_progress


                def download_single(idx, video_url):
                    """Descarga un solo video/canción usando yt-dlp y actualiza progreso individual y nombre actual"""
                    import re
                    single_cmd = ['python3', '-m', 'yt_dlp']
                    if format_type == 'mp3':
                        single_cmd += ['-x', '--audio-format', 'mp3', '--audio-quality', quality]
                    elif format_type == 'bestaudio':
                        single_cmd += ['-f', 'bestaudio']
                    elif format_type == 'mp4':
                        single_cmd += ['-f', 'best']
                    else:
                        single_cmd += ['-f', 'best']
                    if naming == 'title':
                        template = '%(title)s.%(ext)s'
                    elif naming == 'artist-title':
                        template = '%(artist|uploader|Unknown)s - %(title)s.%(ext)s'
                    else:
                        template = '%(title)s.%(ext)s'
                    output_template = os.path.join(output_dir, template)
                    single_cmd += ['-o', output_template]
                    if cookies_file and os.path.exists(cookies_file):
                        single_cmd += ['--cookies', cookies_file]
                    archive_path = os.path.join(output_dir, '.downloaded.txt')
                    single_cmd += ['--download-archive', archive_path]
                    single_cmd.append(video_url)

                    # Progreso en tiempo real: leer stdout línea a línea
                    try:
                        proc = subprocess.Popen(single_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=1)
                        current_filename = None
                        stdout_lines = []
                        stderr_lines = []
                        while True:
                            line = proc.stdout.readline()
                            if not line:
                                break
                            stdout_lines.append(line)
                            # Buscar nombre de archivo en la línea
                            match = re.search(r'Destination: (.+\.(mp3|mp4|m4a|webm|opus))', line)
                            if match:
                                current_filename = match.group(1)
                                DOWNLOADS_STATUS[job_id]['current_file'] = f"{current_filename} (descargando)"
                                parallel_progress[idx]['current_file'] = current_filename
                                parallel_progress[idx]['status'] = 'descargando'
                            # Buscar progreso
                            percent_match = re.search(r'(\d+\.?\d*)% of', line)
                            if percent_match:
                                progress_map[idx] = float(percent_match.group(1))
                                parallel_progress[idx]['progress'] = float(percent_match.group(1))
                            # Actualizar progreso global y paralelo
                            completed = sum([1 for p in progress_map if p == 100])
                            total = len(progress_map)
                            percent = int((completed / total) * 100)
                            DOWNLOADS_STATUS[job_id]['progress'] = percent
                            if current_filename:
                                DOWNLOADS_STATUS[job_id]['current_file'] = f"{current_filename} ({percent}%)"
                            DOWNLOADS_STATUS[job_id]['parallel_progress'] = parallel_progress
                        # Leer stderr completo
                        stderr_out, _ = proc.communicate()
                        if stderr_out:
                            stderr_lines.append(stderr_out)
                        proc.wait()
                        # Al terminar, marcar como 100%
                        progress_map[idx] = 100
                        parallel_progress[idx]['progress'] = 100
                        parallel_progress[idx]['status'] = 'completado' if proc.returncode == 0 else 'error'
                        parallel_progress[idx]['stdout'] = ''.join(stdout_lines)[-2000:]
                        parallel_progress[idx]['stderr'] = ''.join(stderr_lines)[-2000:]
                        parallel_progress[idx]['returncode'] = proc.returncode
                        DOWNLOADS_STATUS[job_id]['parallel_progress'] = parallel_progress
                        # Buscar archivo descargado
                        files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4'))]
                        files_downloaded.append(files)
                        return proc.returncode == 0
                    except Exception as ex:
                        progress_map[idx] = 100
                        parallel_progress[idx]['progress'] = 100
                        parallel_progress[idx]['status'] = 'error'
                        parallel_progress[idx]['error'] = str(ex)
                        DOWNLOADS_STATUS[job_id]['parallel_progress'] = parallel_progress
                        return False

                # Lanzar descargas en paralelo
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_idx = {executor.submit(download_single, idx, vurl): idx for idx, vurl in enumerate(playlist_urls)}
                    total = len(playlist_urls)
                    completed = 0
                    while completed < total:
                        done, _ = concurrent.futures.wait(future_to_idx, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
                        completed = sum([1 for p in progress_map if p == 100])
                        # Actualizar progreso global
                        percent = int((completed / total) * 100)
                        DOWNLOADS_STATUS[job_id]['progress'] = percent
                        DOWNLOADS_STATUS[job_id]['current_file'] = f"{completed}/{total} completados"
                    # Esperar a que terminen todos
                    concurrent.futures.wait(future_to_idx)

                # Al finalizar, actualizar archivos descargados
                all_files = []
                for sublist in files_downloaded:
                    all_files.extend(sublist)
                DOWNLOADS_STATUS[job_id].update({
                    'status': 'completado',
                    'progress': 100,
                    'files': [os.path.join(output_dir, f) for f in set(all_files)],
                    'playlist_parallel': True
                })
                return

        # Reusar archivos existentes sin re-descargar si reuse_existing=1
        if reuse_existing:
            try:
                existing = []
                if os.path.isdir(output_dir):
                    for fname in os.listdir(output_dir):
                        if fname.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4')):
                            existing.append(os.path.join(output_dir, fname))
                if existing:
                    DOWNLOADS_STATUS[job_id].update({
                        'status': 'completado',
                        'progress': 100,
                        'files': existing,
                        'reused_existing': True,
                        'reuse_count': len(existing)
                    })
                    return
                else:
                    DOWNLOADS_STATUS[job_id]['reuse_existing_empty'] = True
            except Exception as _reuse_e:
                DOWNLOADS_STATUS[job_id]['reuse_existing_error'] = str(_reuse_e)

        # Limpieza previa opcional de la carpeta destino (antes de snapshot) si PRE_CLEAN_OUTPUT=1
        # Seguridad: solo procede si el directorio existe, es realmente un directorio y no es raíz ni home.
        pre_clean_flag = os.environ.get('PRE_CLEAN_OUTPUT','0') == '1'
        if pre_clean_flag:
            # Nueva lógica: sólo borrar archivos cuya antigüedad > N horas (default 3)
            try:
                min_age_hours = float(os.environ.get('PRE_CLEAN_MIN_AGE_HOURS', '3'))
            except ValueError:
                min_age_hours = 3.0
            min_age_seconds = min_age_hours * 3600.0
            now_ts = time.time()
            safe = True
            dangerous_roots = {'/', os.path.expanduser('~'), '/home', '/root'}
            norm_out = os.path.abspath(output_dir)
            try:
                if norm_out in dangerous_roots:
                    safe = False
                # Evitar borrar si la ruta es muy corta (heurística defensiva)
                if len(norm_out) < 5:
                    safe = False
                if safe and os.path.isdir(norm_out):
                    # Contar archivos antes
                    try:
                        before_listing = os.listdir(norm_out)
                    except Exception:
                        before_listing = []
                    removed_count = 0
                    skipped_count = 0
                    for entry in before_listing:
                        fp = os.path.join(norm_out, entry)
                        try:
                            # Determinar edad del archivo/directorio (usar mtime)
                            try:
                                mtime = os.path.getmtime(fp)
                                age = now_ts - mtime
                            except Exception:
                                age = 0
                            if age < min_age_seconds:
                                skipped_count += 1
                                continue
                            if os.path.isfile(fp) or os.path.islink(fp):
                                os.remove(fp)
                                removed_count += 1
                            elif os.path.isdir(fp):
                                import shutil
                                shutil.rmtree(fp, ignore_errors=True)
                                removed_count += 1
                        except Exception:
                            pass
                    DOWNLOADS_STATUS[job_id]['pre_clean'] = True
                    DOWNLOADS_STATUS[job_id]['pre_clean_removed'] = removed_count
                    DOWNLOADS_STATUS[job_id]['pre_clean_skipped'] = skipped_count
                    DOWNLOADS_STATUS[job_id]['pre_clean_min_age_h'] = min_age_hours
                else:
                    DOWNLOADS_STATUS[job_id]['pre_clean'] = False
                    if not safe:
                        DOWNLOADS_STATUS[job_id]['pre_clean_warning'] = 'Ruta no segura para limpieza automática'
            except Exception as e:
                DOWNLOADS_STATUS[job_id]['pre_clean_error'] = str(e)
        
        # Construir comando yt-dlp con opciones anti-429
        cmd = ['python3', '-m', 'yt_dlp']
        
        # Snapshot inicial de archivos existentes para diferenciar nuevos al terminar
        try:
            initial_files_snapshot = set(os.listdir(output_dir))
        except Exception:
            initial_files_snapshot = set()
        # Guardar snapshot para futura limpieza selectiva
        try:
            DOWNLOADS_STATUS[job_id]['initial_snapshot'] = list(initial_files_snapshot)
        except Exception:
            DOWNLOADS_STATUS[job_id]['initial_snapshot'] = []

        # SPEED_MODE: modo rápido (menos latencia, sin transcode mp3)
        speed_mode = os.environ.get('SPEED_MODE','0') == '1'
        if speed_mode:
            DOWNLOADS_STATUS[job_id]['speed_mode'] = True
            # En speed mode siempre desactivar prefetch y validaciones que añaden latencia
            os_prefetch_override = True
        else:
            os_prefetch_override = False
        # Flags de características avanzadas (pack completo)
        # Prefetch control:
        # New environment variables:
        #   PREFETCH_MODE: off | fast | full | auto (default auto)
        #       off  -> nunca hace prefetch
        #       fast -> solo intento simple (prefetch_metadata) sin multi_prefetch
        #       full -> intenta prefetch + multi_prefetch
        #       auto -> salta prefetch para playlists (porque añade mucha latencia y a menudo timeouts),
        #                para un solo video hace modo 'fast'
        #   PREFETCH_TIMEOUT: seg para timeout (-m yt_dlp --dump-json) (default 12 single, 18 legacy if not set)
        prefetch_mode = os.environ.get('PREFETCH_MODE', 'auto').lower().strip()
        if speed_mode:
            prefetch_mode = 'off'
        raw_prefetch_timeout = os.environ.get('PREFETCH_TIMEOUT')
        # Heurística playlist refinada:
        # - Considerar playlist solo si URL principal es de tipo playlist ( /playlist? ) o NO contiene parámetro v= (es decir, apunta a la vista de playlist completa)
        # - Un video individual que trae list= como contexto (watch?v=...&list=...) debe tratarse como single video para permitir filtrado de saltado.
        lowered_url = url.lower()
        has_list = 'list=' in lowered_url or '/playlist?' in lowered_url
        has_video_id = ('watch?v=' in lowered_url) or ('youtu.be/' in lowered_url) or ('/shorts/' in lowered_url)
        if has_list and not has_video_id:
            is_playlist = True
        else:
            is_playlist = False
        # Definir si habilitamos prefetch según modo
        if prefetch_mode not in ('off','fast','full','auto'):
            prefetch_mode = 'auto'
        if prefetch_mode == 'off':
            enable_prefetch = False
        elif prefetch_mode == 'auto':
            # Auto: saltar prefetch para playlists grandes; hacerlo modo fast para single
            enable_prefetch = not is_playlist
        else:
            enable_prefetch = True
        # Ajustar tipo de prefetch (fast vs full)
        prefetch_full = (prefetch_mode == 'full') or (prefetch_mode == 'auto' and not is_playlist)
        if prefetch_mode == 'fast':
            prefetch_full = False  # solo intento simple
        # Timeout dinámico
        if raw_prefetch_timeout and raw_prefetch_timeout.isdigit():
            prefetch_timeout = int(raw_prefetch_timeout)
        else:
            prefetch_timeout = 12 if not is_playlist else 16  # reducir single video para acelerar

        DOWNLOADS_STATUS[job_id]['prefetch_mode'] = prefetch_mode
        DOWNLOADS_STATUS[job_id]['is_playlist'] = is_playlist
        # Controles de reducción de salida / límites
        reduce_output = os.environ.get('REDUCE_OUTPUT','0') == '1'
        playlist_limit_env = os.environ.get('PLAYLIST_LIMIT')
        single_item_mode = os.environ.get('SINGLE_ITEM','0') == '1'
        if reduce_output:
            DOWNLOADS_STATUS[job_id]['reduction'] = 'reduced'
        if playlist_limit_env and playlist_limit_env.isdigit():
            DOWNLOADS_STATUS[job_id]['playlist_limit'] = int(playlist_limit_env)
        if single_item_mode:
            DOWNLOADS_STATUS[job_id]['single_item_mode'] = True
        enable_cache = os.environ.get('ENABLE_CLIENT_CACHE', '1') == '1'
        mobile_first = os.environ.get('USE_MOBILE_FIRST', '1') == '1'
        head_validate = os.environ.get('HEAD_VALIDATE', '1') == '1'
        jitter_enabled = os.environ.get('JITTER_THROTTLE', '1') == '1'
        if speed_mode:
            head_validate = False
            jitter_enabled = False

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
            # Intento simple
            try:
                data, err = prefetch_metadata(url, timeout=prefetch_timeout)
            except TypeError:
                # Compatibilidad si firma anterior sin timeout param
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
                if prefetch_full:
                    # Multi-prefetch fallback solo si modo full
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
        else:
            DOWNLOADS_STATUS[job_id]['prefetch'] = 'skipped'
            if is_playlist:
                DOWNLOADS_STATUS[job_id]['prefetch_reason'] = 'auto_skip_playlist'
            elif prefetch_mode == 'off':
                DOWNLOADS_STATUS[job_id]['prefetch_reason'] = 'disabled_env'
            else:
                DOWNLOADS_STATUS[job_id]['prefetch_reason'] = 'mode_fast_no_prefetch_needed'
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
        
        # Detectar si estamos en un servidor remoto (Render, Heroku, etc.) - forzado a remoto según requerimiento
        is_remote_server_detected = True  # Forzado: siempre remoto
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
        # Fuerza final a remoto
        is_remote_server = True
        DOWNLOADS_STATUS[job_id]['force_mode'] = 'remote_forced'
        
        # Log del entorno detectado
        DOWNLOADS_STATUS[job_id]['environment'] = 'remote_server' if is_remote_server else 'local_dev'
        
        # Definir bandera para saltar intento de extracción de cookies de navegador
        # Preparar opciones base dependiendo del entorno
        skip_browser_cookie_scan = False
        # Forzar siempre estrategia server_aggressive única
        anti_429_options = [
            '--no-check-certificate', '--user-agent', random_ua, '--referer', 'https://www.youtube.com/',
            '--extractor-args', f'youtube:player_client={base_player_client}',
            '--extractor-args', 'youtube:skip=dash,hls', '--no-warnings', '--ignore-errors',
            '--socket-timeout', '90', '--fragment-retries', '25', '--retries', '25',
            '--geo-bypass', '--geo-bypass-country', 'US'
        ]
        if content_type == 'shorts':
            anti_429_options += ['--add-header','Accept-Language: en-US,en;q=0.9','--add-header','DNT: 1']
        DOWNLOADS_STATUS[job_id]['anti_bot_level'] = 'server_aggressive'

        cmd.extend(anti_429_options)
        DOWNLOADS_STATUS[job_id]['user_agent'] = random_ua

        # Cookies prioridad alta (runtime upload > env var > file)
        cookies_added = False
        temp_cookies_path = None
        global UPLOADED_COOKIES_PATH
        cookies_strength = 'none'
        if UPLOADED_COOKIES_PATH and os.path.exists(UPLOADED_COOKIES_PATH):
            cmd += ['--cookies', UPLOADED_COOKIES_PATH]
            DOWNLOADS_STATUS[job_id]['cookies'] = 'cookies_upload_runtime'
            DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'uploaded_initial'
            cookies_added = True
            cookies_strength = 'strong'  # Asumimos que si el usuario subió, son buenas
        elif os.environ.get('YOUTUBE_COOKIES'):
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(os.environ.get('YOUTUBE_COOKIES'))
                temp_cookies_path = f.name
            cmd += ['--cookies', temp_cookies_path]
            DOWNLOADS_STATUS[job_id]['cookies'] = 'env_variable'
            DOWNLOADS_STATUS[job_id]['cookie_stage'] = 'env_initial'
            cookies_added = True
            cookies_strength = detect_cookies_strength()
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

        # Fast mode: si strong cookies en entorno remoto, habilitar ruta rápida
        fast_mode = False
        if is_remote_server and cookies_strength == 'strong':
            fast_mode = True
            DOWNLOADS_STATUS[job_id]['fast_mode'] = True
            DOWNLOADS_STATUS[job_id]['fast_mode_reason'] = 'strong_cookies_remote'
        DOWNLOADS_STATUS[job_id]['cookies_strength'] = cookies_strength

        # Formato/naming (agrega bestaudio). En SPEED_MODE mp3 => bestaudio
        original_request_format = format_type
        if format_type == 'bestaudio':
            # bestaudio directo (sin transcodificar)
            cmd.extend(['-f','bestaudio'])
        elif format_type == 'mp3':
            if speed_mode:
                format_type = 'bestaudio'
                DOWNLOADS_STATUS[job_id]['speed_mode_format_override'] = 'bestaudio'
                cmd.extend(['-f','bestaudio'])
            else:
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

        # Aplicar límites de playlist / single item
        if single_item_mode:
            cmd.append('--no-playlist')
        else:
            if playlist_limit_env and playlist_limit_env.isdigit():
                # Si es playlist, limitar el final
                if is_playlist:
                    cmd.extend(['--playlist-end', playlist_limit_env])
        
        # Agregar opciones adicionales (en fast_mode omitimos write-info-json para velocidad)
        if fast_mode:
            if not is_playlist:
                cmd.append('--no-playlist')
        else:
            if not reduce_output:
                cmd.append('--write-info-json')
            # Si reduce_output, evitar metadata pesada
            if reduce_output:
                cmd.append('--no-write-playlist-metafiles')
            if not is_playlist:
                cmd.append('--no-playlist')
        # Archivo de registro de descargas para saltar ítems ya procesados (activado por defecto)
        archive_path = os.path.join(output_dir, '.downloaded.txt')
        cmd.extend(['--download-archive', archive_path])
        DOWNLOADS_STATUS[job_id]['download_archive'] = archive_path
        # Detección temprana: si URL (o video_id) ya fue descargada y está en archivo, marcar y salir rápido
        try:
            if os.path.exists(archive_path):
                with open(archive_path, 'r', encoding='utf-8', errors='ignore') as ar:
                    lines = ar.readlines()
                # Normalizar para búsqueda flexible
                lower_lines = [ln.lower() for ln in lines]
                already = False
                if video_id:
                    vid_low = video_id.lower()
                    # Formato típico de yt-dlp archive: 'youtube <id>'
                    if any(vid_low in ln for ln in lower_lines):
                        already = True
                if not already:
                    # Canonicalizar url para comparación (quedarse con parte antes de &si= etc.)
                    can_url = url.split('&si=')[0].replace('music.youtube.com','www.youtube.com').strip().lower()
                    if any(can_url in ln for ln in lower_lines):
                        already = True
                if already:
                    # Recolectar archivos existentes compatibles en el directorio (audio/video típicos)
                    existing_files = []
                    single_video = not is_playlist  # heurística: url no contiene playlist markers
                    meta_title = None
                    meta_artist = None
                    # video_id ya obtenido antes (variable externa)
                    # Intentar obtener metadata mínima para filtrar (solo para single video)
                    if single_video:
                        try:
                            meta_cmd = [
                                'python3','-m','yt_dlp','--dump-json','--skip-download','--no-playlist', url
                            ]
                            meta_proc = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=14)
                            if meta_proc.returncode == 0 and meta_proc.stdout.strip():
                                first_line = meta_proc.stdout.strip().splitlines()[0]
                                md = json.loads(first_line)
                                meta_title = (md.get('title') or '').strip()
                                meta_artist = (md.get('artist') or md.get('uploader') or '').strip()
                                DOWNLOADS_STATUS[job_id]['skip_meta'] = True
                        except Exception as _sm_e:
                            DOWNLOADS_STATUS[job_id]['skip_meta_error'] = str(_sm_e)
                    # Construir posibles patrones de nombre según plantilla usada
                    candidate_patterns = []
                    if single_video and meta_title:
                        # naming = artist-title o title
                        base_title = meta_title
                        safe_title = base_title.replace('/', '_').replace('\n',' ').replace('\r',' ').strip()
                        candidate_patterns.append(safe_title.lower())
                        if meta_artist:
                            combo = f"{meta_artist} - {base_title}".replace('/', '_').strip().lower()
                            candidate_patterns.append(combo)
                        # Normalizaciones adicionales (sin acentos / quitar caracteres especiales básicos)
                        try:
                            import unicodedata
                            def norm_txt(t):
                                nf = unicodedata.normalize('NFKD', t)
                                nf = ''.join(c for c in nf if not unicodedata.combining(c))
                                nf = nf.replace('_',' ').replace('-', ' ').replace('  ',' ').strip().lower()
                                return nf
                            norm_title = norm_txt(base_title)
                            candidate_patterns.append(norm_title)
                            if meta_artist:
                                candidate_patterns.append(norm_txt(meta_artist + ' ' + base_title))
                        except Exception:
                            pass
                    if single_video and video_id:
                        candidate_patterns.append(video_id.lower())
                        # Variante dentro de paréntesis o entre espacios por si el nombre incluye ID
                        candidate_patterns.append(f'({video_id.lower()})')
                    try:
                        for fname in os.listdir(output_dir):
                            lower = fname.lower()
                            if not lower.endswith(('.mp3','.m4a','.opus','.webm','.mp4')):
                                continue
                            fullp = os.path.join(output_dir, fname)
                            if single_video and candidate_patterns:
                                # Aceptar si cualquier patrón aparece (startswith o in)
                                if any(p in lower for p in candidate_patterns):
                                    existing_files.append(fullp)
                            else:
                                existing_files.append(fullp)
                        # Si filtramos y quedó vacío, fallback a todos
                        if single_video and candidate_patterns and not existing_files:
                            for fname in os.listdir(output_dir):
                                if fname.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4')):
                                    existing_files.append(os.path.join(output_dir, fname))
                                    break  # solo 1 para single
                        # Si filtrado devolvió más de 1 para single, reducir a mejor candidato
                        if single_video and len(existing_files) > 1:
                            scoring_info = []
                            def token_norm(txt):
                                import unicodedata
                                t = unicodedata.normalize('NFKD', txt)
                                t = ''.join(c for c in t if not unicodedata.combining(c))
                                t = t.lower()
                                for ch in ['_', '-', '(', ')', '[', ']', '.', ',', '  ']:
                                    t = t.replace(ch, ' ')
                                return [w for w in t.split() if len(w) > 1]
                            title_tokens = token_norm(meta_title) if meta_title else []
                            artist_tokens = token_norm(meta_artist) if meta_artist else []
                            id_tokens = [video_id.lower()] if video_id else []
                            def score(path):
                                name = os.path.basename(path).lower()
                                tokens = token_norm(name)
                                st = 0
                                if title_tokens:
                                    common_t = len(set(tokens) & set(title_tokens))
                                    st += common_t * 4
                                if artist_tokens:
                                    common_a = len(set(tokens) & set(artist_tokens))
                                    st += common_a * 3
                                if id_tokens and any(t in name for t in id_tokens):
                                    st += 8
                                # longitud de tokens (más largo ligeramente mayor peso)
                                st += min(len(tokens), 12) * 0.2
                                try:
                                    st += os.path.getsize(path) / 400000.0  # cada ~400KB suma 1
                                except Exception:
                                    pass
                                try:
                                    st += (os.path.getmtime(path) % 1000) / 2000.0
                                except Exception:
                                    pass
                                scoring_info.append({'file': os.path.basename(path), 'score': round(st,2)})
                                return st
                            existing_files.sort(key=score, reverse=True)
                            best = existing_files[0]
                            existing_files = [best]
                            DOWNLOADS_STATUS[job_id]['skip_multi_reduced'] = True
                            DOWNLOADS_STATUS[job_id]['skip_scoring'] = scoring_info
                        # Si no había patrones (metadata falló) y es single, elegir archivo más reciente solamente
                        if single_video and not candidate_patterns:
                            candidates = [p for p in existing_files if p.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4'))]
                            if len(candidates) > 1:
                                try:
                                    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                                    existing_files = [candidates[0]]
                                    DOWNLOADS_STATUS[job_id]['skip_recent_used'] = True
                                except Exception:
                                    existing_files = [candidates[0]]
                    except Exception as _list_e:
                        DOWNLOADS_STATUS[job_id]['archive_list_error'] = str(_list_e)
                    if single_video:
                        DOWNLOADS_STATUS[job_id]['skip_filtered_single'] = True
                        # Filtro temprano adicional: si tenemos prefetch_title y video_id intentar match directo
                        try:
                            early_title = DOWNLOADS_STATUS[job_id].get('prefetch_title')
                            if early_title and len(existing_files) > 1:
                                et_norm = early_title.lower().replace('_',' ').replace('-',' ').strip()
                                vid_low = (video_id or '').lower()
                                early_matches = []
                                for p in existing_files:
                                    bn = os.path.basename(p).lower()
                                    bn_norm = bn.replace('_',' ').replace('-',' ').strip()
                                    if et_norm in bn_norm:
                                        if (not vid_low) or (vid_low in bn_norm):
                                            early_matches.append(p)
                                if len(early_matches) == 1:
                                    existing_files = [early_matches[0]]
                                    DOWNLOADS_STATUS[job_id]['skip_early_prefetch_match'] = True
                                elif len(early_matches) > 1:
                                    # si varios, priorizar el que contenga video_id
                                    vid_filtered = [p for p in early_matches if vid_low and vid_low in os.path.basename(p).lower()]
                                    if len(vid_filtered) == 1:
                                        existing_files = [vid_filtered[0]]
                                        DOWNLOADS_STATUS[job_id]['skip_early_prefetch_match'] = True
                                    else:
                                        DOWNLOADS_STATUS[job_id]['skip_early_prefetch_ambiguous'] = len(early_matches)
                        except Exception as _early_e:
                            DOWNLOADS_STATUS[job_id]['skip_early_prefetch_error'] = str(_early_e)
                        # Reducción forzada final: si por alguna razón persisten >1 archivos
                        if len(existing_files) > 1:
                            try:
                                # Nuevo: intentar obtener filename exacto usando yt-dlp --get-filename con la misma plantilla
                                expected_name = None
                                try:
                                    # Replicar parte de la lógica de plantilla (naming ya elegido arriba como 'template')
                                    # Necesitamos recalcular template localmente (duplicamos mini-lógica simplificada)
                                    if naming == 'title':
                                        tmpl_probe = '%(title)s.%(ext)s'
                                    elif naming == 'artist-title':
                                        tmpl_probe = '%(artist|uploader|Unknown)s - %(title)s.%(ext)s'
                                    else:
                                        tmpl_probe = '%(title)s.%(ext)s'
                                    probe_cmd = [
                                        'python3','-m','yt_dlp','--no-playlist','--skip-download','--get-filename'
                                    ]
                                    # Imitar opciones de conversión para que la extensión esperada coincida (mp3 / bestaudio etc.)
                                    if format_type == 'mp3':
                                        probe_cmd += ['-x','--audio-format','mp3']
                                    elif format_type == 'bestaudio':
                                        probe_cmd += ['-f','bestaudio']
                                    elif format_type == 'mp4':
                                        probe_cmd += ['-f','best']
                                    probe_cmd += ['-o', tmpl_probe, url]
                                    probe_proc = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=18)
                                    if probe_proc.returncode == 0:
                                        line = probe_proc.stdout.strip().splitlines()[-1].strip()
                                        if line:
                                            expected_name = line
                                            DOWNLOADS_STATUS[job_id]['skip_expected_name'] = expected_name
                                except Exception as _exp_e:
                                    DOWNLOADS_STATUS[job_id]['skip_expected_name_error'] = str(_exp_e)
                                if expected_name:
                                    exp_lower = expected_name.lower()
                                    exp_stem, exp_ext = os.path.splitext(exp_lower)
                                    allowed_exts = ['.mp3','.m4a','.opus','.webm','.mp4']
                                    # 1) Exacto
                                    matches = [p for p in existing_files if os.path.basename(p).lower() == exp_lower]
                                    # 2) Mismo stem distinta extensión (p.e. sondas sin -x devolvieron .webm pero existe .mp3)
                                    if not matches:
                                        for p in existing_files:
                                            bn = os.path.basename(p).lower()
                                            stem, ext = os.path.splitext(bn)
                                            if stem == exp_stem and (ext in allowed_exts or exp_ext in allowed_exts):
                                                matches.append(p)
                                                break
                                    # 3) Normalización flexible (espacios/guiones/underscores)
                                    if not matches:
                                        def norm_basic(txt):
                                            return txt.replace('_',' ').replace('-',' ').replace('  ',' ').strip()
                                        norm_target = norm_basic(exp_stem)
                                        for p in existing_files:
                                            bn = os.path.basename(p).lower()
                                            stem, _ = os.path.splitext(bn)
                                            if norm_basic(stem) == norm_target:
                                                matches.append(p)
                                                break
                                    if matches:
                                        existing_files = [matches[0]]
                                        DOWNLOADS_STATUS[job_id]['skip_expected_match'] = True
                                    else:
                                        DOWNLOADS_STATUS[job_id]['skip_expected_match'] = False
                                prefetch_title2 = DOWNLOADS_STATUS[job_id].get('prefetch_title')
                                def simple_score(p):
                                    base = os.path.basename(p).lower()
                                    sc = 0
                                    if video_id and video_id.lower() in base:
                                        sc += 20
                                    if prefetch_title2 and prefetch_title2.lower() in base:
                                        sc += 10
                                    # tokens
                                    toks = [t for t in base.replace('-',' ').replace('_',' ').split() if len(t)>1]
                                    if prefetch_title2:
                                        want = [t for t in prefetch_title2.lower().replace('-',' ').split() if len(t)>1]
                                        sc += len(set(toks) & set(want)) * 2
                                    try:
                                        sc += os.path.getsize(p)/500000.0
                                    except Exception:
                                        pass
                                    return sc
                                existing_files.sort(key=simple_score, reverse=True)
                                best = existing_files[0]
                                existing_files = [best]
                                DOWNLOADS_STATUS[job_id]['skip_force_reduced'] = True
                            except Exception as _fr_e:
                                DOWNLOADS_STATUS[job_id]['skip_force_reduce_error'] = str(_fr_e)
                    DOWNLOADS_STATUS[job_id].update({
                        'status': 'saltado',
                        'skipped_reason': 'ya_descargado_en_archive',
                        'progress': 100,
                        'files': existing_files,
                        'already_downloaded': True,
                        'provided_cached_files': True
                    })
                    return
        except Exception as _arch_e:
            DOWNLOADS_STATUS[job_id]['archive_precheck_error'] = str(_arch_e)
        cmd = [x for x in cmd if x]  # Remover strings vacíos
        
        cmd.append(url)
        
        # Ejecutar comando con manejo de errores específicos
        DOWNLOADS_STATUS[job_id]['command'] = ' '.join(cmd)
        
        # Intentar descarga con estrategias adaptadas al entorno y tipo de error
        success = False
        attempt = 1
        # Modo estricto 2 intentos configurable (por defecto ON). Fallback adaptativo opcional.
        strict_two_attempts = os.environ.get('STRICT_TWO_ATTEMPTS','1') == '1'
        allow_fallback = os.environ.get('ALLOW_FALLBACK','1') == '1'
        if speed_mode:
            strict_two_attempts = True
            max_attempts = 2
        else:
            max_attempts = 2 if strict_two_attempts else (6 if is_remote_server else 4)
        DOWNLOADS_STATUS[job_id]['max_attempts'] = max_attempts
        DOWNLOADS_STATUS[job_id]['strict_two_attempts'] = strict_two_attempts
        DOWNLOADS_STATUS[job_id]['allow_fallback'] = allow_fallback
        fallback_engaged = False
        
        # Preparar proxies si definidos
        proxy_list_env = os.environ.get('PROXY_LIST', '').strip()
        rotate_proxies = os.environ.get('ROTATE_PROXIES', '1') == '1'
        proxies = [p.strip() for p in proxy_list_env.split(',') if p.strip()] if proxy_list_env else []
        if proxies:
            DOWNLOADS_STATUS[job_id]['proxies_enabled'] = len(proxies)
        while not success and attempt <= max_attempts:
            DOWNLOADS_STATUS[job_id]['attempt'] = attempt
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
                        '--no-check-certificate','--user-agent', new_ua,'--referer','https://www.youtube.com/',
                        '--no-warnings','--ignore-errors','--socket-timeout','120','--fragment-retries','30','--retries','30','--geo-bypass','--geo-bypass-country','US'
                    ]
                    # Sin sleeps adicionales ni throttling en segundo intento

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
                # Ajustes especiales si venimos de un error de tab parse (playlist Music)
                if DOWNLOADS_STATUS[job_id].get('tab_parse_recovery'):
                    # Inyectar recuperación con un solo --extractor-args agregando múltiples clientes en cadena.
                    # Evitamos múltiples pares que en algunos entornos terminaban generando tokens sueltos
                    # que yt-dlp interpretaba como URLs ("youtube:player_client=web").
                    if '--flat-playlist' not in cmd_retry:
                        cmd_retry.append('--flat-playlist')
                    # Eliminar duplicados previos de --extractor-args player_client para limpiar
                    cleaned = []
                    skip_next = False
                    for i,tok in enumerate(cmd_retry):
                        if skip_next:
                            skip_next = False
                            continue
                        if tok == '--extractor-args' and i+1 < len(cmd_retry):
                            argval = cmd_retry[i+1]
                            if argval.startswith('youtube:player_client='):
                                # Saltar este par (lo reconstruiremos abajo)
                                skip_next = True
                                continue
                        cleaned.append(tok)
                    cmd_retry = cleaned
                    # Añadir args combinados (lista separada por ; si yt-dlp lo admite, si no usar última prioridad)
                    # yt-dlp actualmente acepta una sola asignación; estrategia: preferencia android luego web para Music
                    # Para evitar error, solo uno: elegimos android si playlist music.
                    combined_client = 'android' if 'music.youtube.com' in url else 'web'
                    cmd_retry.extend(['--extractor-args', f'youtube:player_client={combined_client}'])
                    DOWNLOADS_STATUS[job_id]['recovery_injected'] = True
                    DOWNLOADS_STATUS[job_id]['recovery_client'] = combined_client
                # Asignar proxy rotativo
                if proxies:
                    idx = (attempt - 1) % len(proxies) if rotate_proxies else 0
                    cmd_retry.extend(['--proxy', proxies[idx]])
                    DOWNLOADS_STATUS[job_id]['proxy_used'] = proxies[idx]
                
                # Configurar formato (mantener configuración original)
                if format_type == 'mp3':
                    cmd_retry.extend(['-x', '--audio-format', 'mp3', '--audio-quality', quality])
                elif format_type == 'bestaudio':
                    cmd_retry.extend(['-f', 'bestaudio'])
                elif format_type == 'mp4':
                    cmd_retry.extend(['-f', 'best'])
                else:
                    cmd_retry.extend(['-f', 'best'])
                
                cmd_retry.extend(['-o', output_template])
                # Reaplicar banderas de reducción/playlist en reintentos
                if not fast_mode and not reduce_output:
                    cmd_retry.append('--write-info-json')
                if reduce_output:
                    cmd_retry.append('--no-write-playlist-metafiles')
                if single_item_mode:
                    cmd_retry.append('--no-playlist')
                else:
                    if not is_playlist:
                        cmd_retry.append('--no-playlist')
                    elif playlist_limit_env and playlist_limit_env.isdigit():
                        cmd_retry.extend(['--playlist-end', playlist_limit_env])
                if os.environ.get('DOWNLOAD_ARCHIVE','0') == '1':
                    archive_path = os.path.join(output_dir, '.downloaded.txt')
                    cmd_retry.extend(['--download-archive', archive_path])
                cmd_retry = [x for x in cmd_retry if x]
                cmd_retry.append(url)
                
                DOWNLOADS_STATUS[job_id]['status'] = f'reintentando {attempt}'
                
                cmd = cmd_retry
                DOWNLOADS_STATUS[job_id]['command'] = ' '.join(cmd)
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Guardar el proceso para poder cancelarlo
            DOWNLOADS_STATUS[job_id]['process'] = process
            
            # Monitorear progreso en tiempo real
            stdout_lines = []
            stderr_lines = []
            
            def parse_progress_line(line):
                """Parsea líneas de yt-dlp para extraer progreso"""
                try:
                    line = line.strip()
                    
                    # [download]  45.2% of   12.34MiB at  234.56KiB/s ETA 00:23
                    if '[download]' in line and '%' in line and 'of' in line:
                        # Extraer porcentaje
                        import re
                        percentage_match = re.search(r'(\d+\.?\d*)%', line)
                        if percentage_match:
                            progress = float(percentage_match.group(1))
                            
                            # Extraer información adicional
                            size_match = re.search(r'of\s+([0-9.]+\w+)', line)
                            speed_match = re.search(r'at\s+([0-9.]+\w+/s)', line)
                            eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
                            
                            # Extraer nombre del archivo si está presente
                            file_name = "Descargando archivo..."
                            if ']' in line:
                                after_bracket = line.split(']', 1)[-1].strip()
                                # Buscar patrón: filename.ext: progress%
                                name_match = re.search(r'^([^:]+\.(mp3|mp4|m4a|webm|opus)):', after_bracket)
                                if name_match:
                                    file_name = name_match.group(1)
                            
                            progress_info = {
                                'progress': min(progress, 99),  # No llegar a 100% hasta terminar
                                'current_file': file_name
                            }
                            
                            if size_match:
                                progress_info['total_size'] = size_match.group(1)
                            if speed_match:
                                progress_info['speed'] = speed_match.group(1)
                            if eta_match:
                                progress_info['eta'] = eta_match.group(1)
                                
                            return progress_info
                    
                    # [youtube] VideoID: Downloading webpage
                    elif '[youtube]' in line and ('Downloading webpage' in line or 'Extracting URL' in line):
                        video_id = ""
                        if ':' in line:
                            parts = line.split(':', 2)
                            if len(parts) >= 2:
                                video_id = parts[1].strip()
                        
                        return {
                            'progress': 10,
                            'current_file': f'Obteniendo información: {video_id[:11] if video_id else "video"}...',
                            'stage': 'metadata'
                        }
                    
                    # [youtube:tab] Extracting URL: playlist_url
                    elif '[youtube:tab]' in line and 'Extracting URL' in line:
                        return {
                            'progress': 5,
                            'current_file': 'Analizando playlist...',
                            'stage': 'playlist'
                        }
                    
                    # [download] Downloading playlist: PlaylistName
                    elif '[download] Downloading playlist:' in line:
                        playlist_name = line.split('Downloading playlist:')[-1].strip()
                        return {
                            'progress': 15,
                            'current_file': f'Procesando playlist: {playlist_name}',
                            'stage': 'playlist',
                            'playlist_name': playlist_name
                        }
                    
                    # [download] Downloading item 3 of 10
                    elif '[download] Downloading item' in line and 'of' in line:
                        match = re.search(r'item\s+(\d+)\s+of\s+(\d+)', line)
                        if match:
                            current_item = int(match.group(1))
                            total_items = int(match.group(2))
                            playlist_progress = (current_item / total_items) * 80 + 15  # 15% base + 80% para items
                            
                            return {
                                'progress': min(playlist_progress, 95),
                                'current_file': f'Descargando item {current_item} de {total_items}',
                                'stage': 'playlist_item',
                                'current_item': current_item,
                                'total_items': total_items
                            }
                    
                    # [info] VideoID: Downloading title
                    elif '[info]' in line and ('Downloading' in line or 'Writing' in line):
                        return {
                            'progress': 20,
                            'current_file': 'Procesando información del video...',
                            'stage': 'info'
                        }
                    
                    # Detectar nombres de archivos en cualquier línea que los contenga
                    elif any(ext in line for ext in ['.mp3', '.mp4', '.m4a', '.webm', '.opus']):
                        # Buscar patrón de archivo de audio/video
                        import re
                        file_match = re.search(r'([^/\\]+\.(mp3|mp4|m4a|webm|opus))', line)
                        if file_match:
                            filename = file_match.group(1)
                            return {
                                'progress': 25,
                                'current_file': f'Procesando: {filename}',
                                'stage': 'processing'
                            }
                
                except Exception as e:
                    print(f"❌ [DEBUG] Error parsing line: {e} - Line: {line[:100]}")
                return None
            
            # Leer salida en tiempo real
            while True:
                # Leer stdout
                stdout_line = process.stdout.readline()
                if stdout_line:
                    stdout_lines.append(stdout_line)
                    print(f"📤 [STDOUT] {stdout_line.strip()}")  # Debug: todas las líneas
                    progress_info = parse_progress_line(stdout_line)
                    if progress_info:
                        DOWNLOADS_STATUS[job_id].update(progress_info)
                        print(f"📊 [DEBUG] Progreso actualizado: {progress_info}")
                
                # Leer stderr
                stderr_line = process.stderr.readline()
                if stderr_line:
                    stderr_lines.append(stderr_line)
                    print(f"📥 [STDERR] {stderr_line.strip()}")  # Debug: todas las líneas de error
                    progress_info = parse_progress_line(stderr_line)
                    if progress_info:
                        DOWNLOADS_STATUS[job_id].update(progress_info)
                        print(f"📊 [DEBUG] Progreso actualizado (stderr): {progress_info}")
                
                # Verificar si el proceso terminó
                if process.poll() is not None:
                    # Leer líneas restantes
                    remaining_stdout = process.stdout.read()
                    remaining_stderr = process.stderr.read()
                    if remaining_stdout:
                        stdout_lines.extend(remaining_stdout.splitlines(True))
                    if remaining_stderr:
                        stderr_lines.extend(remaining_stderr.splitlines(True))
                    break
                
                # Verificar si fue cancelado
                if process.returncode == -15:  # SIGTERM
                    break
            
            # Unir todas las líneas para el manejo posterior
            stdout = ''.join(stdout_lines)
            stderr = ''.join(stderr_lines)
            
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
                    'This video is not available' in stderr,
                    'Unable to recognize tab page' in stderr
                ])
                if 'Unable to recognize tab page' in stderr:
                    DOWNLOADS_STATUS[job_id]['tab_parse_detected'] = True
                
                # Si es error de verificación de bot, 429 o bloqueo general, intentar de nuevo / o activar fallback
                if (error_is_bot_check or error_is_429 or error_is_general_block):
                    # Manejo especializado para error de tab page (playlist Music)
                    tab_parse_issue = 'tab_parse_detected' in DOWNLOADS_STATUS[job_id]
                    if tab_parse_issue and 'tab_parse_recovery' not in DOWNLOADS_STATUS[job_id]:
                        DOWNLOADS_STATUS[job_id]['tab_parse_recovery'] = True
                        # Forzar expansión si está en modo estricto y aún en intento 1
                        if strict_two_attempts and allow_fallback and attempt == 1 and not fallback_engaged:
                            fallback_engaged = True
                            strict_two_attempts = False
                            max_attempts = 6 if is_remote_server else 4
                            DOWNLOADS_STATUS[job_id]['max_attempts'] = max_attempts
                            DOWNLOADS_STATUS[job_id]['fallback_engaged'] = True
                            DOWNLOADS_STATUS[job_id]['fallback_reason'] = 'tab_parse_force_expand'
                            DOWNLOADS_STATUS[job_id]['strict_two_attempts'] = False
                        # Inyectar pista para próximo retry afinando extractor-args (se aplicará al construir cmd_retry)
                        DOWNLOADS_STATUS[job_id]['status'] = 'recuperando tab parse'
                    # Fallback: si estamos en modo estricto, es intento 1, y es bot_verification, ampliamos attempts si permitido
                    if (error_is_bot_check and strict_two_attempts and allow_fallback and attempt == 1 and not fallback_engaged):
                        fallback_engaged = True
                        strict_two_attempts = False
                        # Expandir a estrategia completa
                        max_attempts = 6 if is_remote_server else 4
                        DOWNLOADS_STATUS[job_id]['max_attempts'] = max_attempts
                        DOWNLOADS_STATUS[job_id]['fallback_engaged'] = True
                        DOWNLOADS_STATUS[job_id]['fallback_reason'] = 'bot_verification_after_fast_attempt1'
                        DOWNLOADS_STATUS[job_id]['strict_two_attempts'] = False
                        DOWNLOADS_STATUS[job_id]['status'] = 'activando fallback extendido'
                        # Pequeña pausa estratégica antes de reintentar con nuevo set
                        time.sleep(random.randint(3,6))
                    if attempt < max_attempts:
                        error_type = 'bot_verification' if error_is_bot_check else 'rate_limit' if error_is_429 else 'general_block'
                        DOWNLOADS_STATUS[job_id]['error_type'] = error_type
                        if error_is_bot_check and not cookies_added:
                            DOWNLOADS_STATUS[job_id]['requires_cookies'] = True
                            pending_cookie_escalation = True  # Solicitar escalada temprana
                            if first_bot_trigger_attempt is None:
                                first_bot_trigger_attempt = attempt
                                DOWNLOADS_STATUS[job_id]['bot_trigger_attempt'] = attempt
                        DOWNLOADS_STATUS[job_id]['status'] = f'reintentando por {error_type} ({attempt + 1}/{max_attempts})'
                        # Delay específico
                        base_delay = 0
                        if error_is_bot_check:
                            base_delay = random.randint(4,10) if not fallback_engaged else random.randint(6,12)
                        elif error_is_429:
                            base_delay = random.randint(3,8)
                        elif error_is_general_block:
                            base_delay = random.randint(2,6)
                        if base_delay:
                            DOWNLOADS_STATUS[job_id]['status'] = f'esperando {base_delay}s antes de intento {attempt+1}'
                            time.sleep(base_delay)
                        attempt += 1
                        continue
                    # Sin más intentos: registrar error final
                    final_hint = None
                    if error_is_bot_check:
                        if not cookies_added:
                            final_hint = 'El servidor necesita cookies fuertes (SID, SAPISID). Sube cookies o define YOUTUBE_COOKIES.'
                        elif strict_two_attempts and not allow_fallback:
                            final_hint = 'Modo estricto 2 intentos activo. Desactiva STRICT_TWO_ATTEMPTS=0 para más estrategias.'
                        else:
                            final_hint = 'Bot verification persistente tras múltiples estrategias.'
                    elif error_is_429:
                        final_hint = 'Rate limit persistente. Añade cookies o activa fallback.'
                    elif error_is_general_block:
                        final_hint = 'Bloqueo general. Revisa URL o cookies.'
                    DOWNLOADS_STATUS[job_id].update({
                        'status': 'error',
                        'error': stderr,
                        'stdout': stdout,
                        'final_hint': final_hint,
                        'error_analysis': {
                            'bot_check': error_is_bot_check,
                            'rate_limit': error_is_429,
                            'general_block': error_is_general_block,
                            'other_error': not (error_is_bot_check or error_is_429 or error_is_general_block)
                        }
                    })
                    return
                # Si no entra en el bloque anterior, es otro error no recuperable y se maneja abajo
                
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
                # Usar siempre la ruta resuelta (por si ~ fue expandido)
                resolved_dir = DOWNLOADS_STATUS[job_id].get('resolved_output_dir', output_dir)
                final_listing = set(os.listdir(resolved_dir))
                # Incluir extensiones típicas de bestaudio (opus puede venir como .opus o .webm)
                new_files = [f for f in final_listing - initial_files_snapshot if f.lower().endswith(('.mp3','.mp4','.webm','.m4a','.opus','.info.json'))]
                # Priorizar: audio/video principal primero, luego info.json
                def sort_key(name):
                    if name.endswith('.info.json'): return (2, name)
                    if name.endswith(('.mp3','.m4a')): return (0, name)
                    return (1, name)
                new_files.sort(key=sort_key)
                downloaded_files = [os.path.join(resolved_dir, f) for f in new_files]
                # Fallback: si no se detectaron archivos nuevos pero stdout contiene rutas destino, intentar parsear
                if not downloaded_files:
                    try:
                        import re
                        dest_pattern = re.compile(r"Destination: (.+)\n")
                        # También capturar líneas de 'has already been downloaded'
                        # Formato real típico: "[download] /ruta/o/nombre.mp3 has already been downloaded"
                        already_pattern = re.compile(r"^\[download\]\s+(?P<path>.+?\.(?:mp3|m4a|opus|webm|mp4)) has already been downloaded$", re.IGNORECASE | re.MULTILINE)
                        matches = dest_pattern.findall(stdout)
                        for m in matches:
                            m = m.strip()
                            if os.path.exists(m) and m.lower().endswith(('.mp3','.mp4','.webm','.m4a','.opus')):
                                downloaded_files.append(m)
                        # Extra: si todavía vacío, intentar con already_pattern
                        if not downloaded_files:
                            for m in already_pattern.findall(stdout):
                                p = m.strip()
                                if os.path.exists(p) and p not in downloaded_files:
                                    downloaded_files.append(p)
                        if downloaded_files:
                            DOWNLOADS_STATUS[job_id]['parsed_from_stdout'] = True
                    except Exception as _pe:
                        DOWNLOADS_STATUS[job_id]['parse_stdout_error'] = str(_pe)
                # Fallback adicional: si NO hay nuevos archivos, ni parseo stdout produjo, reutilizar snapshot inicial
                if not downloaded_files:
                    try:
                        snapshot_candidates = []
                        for name in initial_files_snapshot:
                            if name.lower().endswith(('.mp3','.mp4','.webm','.m4a','.opus')):
                                fullp = os.path.join(resolved_dir, name)
                                if os.path.exists(fullp):
                                    snapshot_candidates.append(fullp)
                        if snapshot_candidates:
                            downloaded_files = snapshot_candidates
                            DOWNLOADS_STATUS[job_id]['reused_snapshot_files'] = True
                    except Exception as _snap_e:
                        DOWNLOADS_STATUS[job_id]['snapshot_fallback_error'] = str(_snap_e)
            except Exception as e:
                DOWNLOADS_STATUS[job_id]['file_diff_error'] = str(e)
                # Fallback a listado completo
                try:
                    for file in os.listdir(resolved_dir):
                        if file.endswith(('.mp3', '.mp4', '.webm', '.m4a', '.opus')):
                            downloaded_files.append(os.path.join(resolved_dir, file))
                except Exception:
                    pass

            # --- Nuevo filtrado final para single video ---
            try:
                is_playlist_flag = DOWNLOADS_STATUS[job_id].get('is_playlist')
                vid_id = DOWNLOADS_STATUS[job_id].get('video_id_detected')
                # Solo aplicar si NO es playlist y tenemos más de un archivo candidate
                if not is_playlist_flag and len(downloaded_files) > 1:
                    # Intentar extraer título/artist desde metadata rápida (si no la tenemos ya del prefetch)
                    meta_title2 = DOWNLOADS_STATUS[job_id].get('prefetch_title')
                    meta_artist2 = None  # no siempre está disponible; se podría parsear de stdout si quisiéramos
                    import unicodedata
                    def norm_txt(t):
                        if not t: return ''
                        nf = unicodedata.normalize('NFKD', t)
                        nf = ''.join(c for c in nf if not unicodedata.combining(c))
                        nf = nf.lower().replace('_',' ').replace('-', ' ')
                        return nf
                    patterns = []
                    if meta_title2:
                        patterns.append(norm_txt(meta_title2))
                    if meta_artist2 and meta_title2:
                        patterns.append(norm_txt(meta_artist2 + ' ' + meta_title2))
                    if vid_id:
                        patterns.append(vid_id.lower())
                        patterns.append(f'({vid_id.lower()})')
                    # Scoring similar al usado en rama saltado
                    def token_norm(txt):
                        if not txt: return []
                        import unicodedata as _u
                        x = _u.normalize('NFKD', txt)
                        x = ''.join(c for c in x if not _u.combining(c))
                        for ch in ['_', '-', '(', ')', '[', ']', '.', ',', '  ']:
                            x = x.replace(ch, ' ')
                        return [w for w in x.lower().split() if len(w) > 1]
                    title_tokens = token_norm(meta_title2)
                    artist_tokens = token_norm(meta_artist2) if meta_artist2 else []
                    id_tokens = [vid_id.lower()] if vid_id else []
                    scoring_info2 = []
                    def score2(path):
                        name = os.path.basename(path)
                        low = name.lower()
                        tokens = token_norm(low)
                        s = 0
                        if title_tokens:
                            s += len(set(tokens) & set(title_tokens)) * 4
                        if artist_tokens:
                            s += len(set(tokens) & set(artist_tokens)) * 3
                        if id_tokens and any(t in low for t in id_tokens):
                            s += 10
                        try:
                            s += os.path.getsize(path)/500000.0
                        except Exception:
                            pass
                        scoring_info2.append({'file': name, 'score': round(s,2)})
                        return s
                    # Si tenemos un patrón que coincide claramente con un único archivo, seleccionar directamente
                    direct_matches = []
                    if patterns:
                        for f in downloaded_files:
                            nlow = os.path.basename(f).lower()
                            if any(p and p in nlow for p in patterns):
                                direct_matches.append(f)
                    chosen = None
                    if len(direct_matches) == 1:
                        chosen = direct_matches[0]
                    elif len(direct_matches) > 1:
                        direct_matches.sort(key=score2, reverse=True)
                        chosen = direct_matches[0]
                    else:
                        # usar scoring global
                        downloaded_files.sort(key=score2, reverse=True)
                        chosen = downloaded_files[0]
                    if chosen:
                        if chosen not in downloaded_files:
                            downloaded_files.append(chosen)
                        # Reducir a uno
                        if len(downloaded_files) > 1:
                            downloaded_files = [chosen]
                            DOWNLOADS_STATUS[job_id]['single_completion_reduced'] = True
                            DOWNLOADS_STATUS[job_id]['single_completion_scoring'] = scoring_info2
            except Exception as _single_final_e:
                DOWNLOADS_STATUS[job_id]['single_completion_filter_error'] = str(_single_final_e)

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
            
            # Debug: listado final completo (limitado)
            try:
                DOWNLOADS_STATUS[job_id]['final_dir_listing'] = list(sorted(os.listdir(resolved_dir)))[:80]
            except Exception:
                pass

            DOWNLOADS_STATUS[job_id].update({
                'status': 'completado',
                'progress': 100,
                'files': downloaded_files,
                'stdout': stdout,
                'attempts_used': attempt - 1
            })

            # Post-clean automático si se solicita (POST_CLEAN_OUTPUT=1)
            try:
                if os.environ.get('POST_CLEAN_OUTPUT','0') == '1':
                    removed = []
                    for fp in list(downloaded_files):
                        try:
                            if os.path.isfile(fp):
                                os.remove(fp)
                                removed.append(os.path.basename(fp))
                        except Exception:
                            pass
                    DOWNLOADS_STATUS[job_id]['post_clean'] = True
                    DOWNLOADS_STATUS[job_id]['post_clean_removed'] = len(removed)
                    # Si además REMOVE_EMPTY_DIR=1 y directorio quedó vacío, eliminarlo
                    resolved_dir = DOWNLOADS_STATUS[job_id].get('resolved_output_dir', output_dir)
                    if os.environ.get('REMOVE_EMPTY_DIR','0') == '1':
                        try:
                            if resolved_dir and os.path.isdir(resolved_dir) and len(os.listdir(resolved_dir)) == 0:
                                os.rmdir(resolved_dir)
                                DOWNLOADS_STATUS[job_id]['dir_removed'] = True
                        except Exception:
                            pass
                    # Vaciar lista ya que fueron borrados
                    DOWNLOADS_STATUS[job_id]['files'] = []
                else:
                    # Si no hay post clean global, podemos limpiar selectivamente los .info.json salvo que se pida conservarlos
                    keep_info = os.environ.get('KEEP_INFO_JSON','0') == '1'
                    if not keep_info:
                        info_removed = 0
                        remaining_files = []
                        for fp in downloaded_files:
                            if fp.lower().endswith('.info.json'):
                                try:
                                    if os.path.isfile(fp):
                                        os.remove(fp)
                                        info_removed += 1
                                except Exception:
                                    pass
                            else:
                                remaining_files.append(fp)
                        if info_removed:
                            DOWNLOADS_STATUS[job_id]['info_json_purged'] = info_removed
                            DOWNLOADS_STATUS[job_id]['files'] = remaining_files
            except Exception as pe:
                DOWNLOADS_STATUS[job_id]['post_clean_error'] = str(pe)
        else:
            DOWNLOADS_STATUS[job_id].update({
                'status': 'error',
                'error': 'Falló después de múltiples intentos',
                'stdout': stdout,
                'attempts_used': max_attempts
            })
            
    except Exception as e:
        # Error inesperado fuera del flujo normal
        DOWNLOADS_STATUS.setdefault(job_id, {})
        DOWNLOADS_STATUS[job_id].update({
            'status': 'error',
            'unexpected_error': True,
            'error': str(e),
            'error_note': 'Excepción no controlada en download_worker'
        })

@app.route('/environment', methods=['GET'])
def get_environment_info():
    """Obtener información del entorno y estrategias aplicadas"""
    GLOBAL_METRICS['download_requests'] += 1
    # Detectar entorno
    is_remote_server = any([
        os.environ.get('RENDER'),
        os.environ.get('HEROKU'),
        os.environ.get('RAILWAY_PROJECT_ID'),
        os.environ.get('VERCEL'),
        'render.com' in os.environ.get('HOSTNAME', ''),
        'heroku.com' in os.environ.get('HOSTNAME', '')
    ])
    
    # Versiones
    yt_dlp_version = None
    try:
        import yt_dlp as _yt
        yt_dlp_version = getattr(_yt, '__version__', 'unknown')
    except Exception as _e:
        yt_dlp_version = f'error:{_e.__class__.__name__}'
    import sys as _sys

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
        'hostname': os.environ.get('HOSTNAME', 'unknown'),
        'python_version': _sys.version.split(' ')[0],
        'yt_dlp_version': yt_dlp_version
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
    # Fallback: si no hay files pero el job terminó (saltado/completado) y tenemos un directorio, intentar re-listar
    if not status.get('files') and status.get('status') in ('completado','saltado'):
        resolved_dir = status.get('resolved_output_dir') or status.get('requested_output_dir')
        try:
            if resolved_dir and os.path.isdir(resolved_dir):
                relisted = []
                for fname in os.listdir(resolved_dir):
                    if fname.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4')):
                        relisted.append(os.path.join(resolved_dir, fname))
                # Evitar sobrescribir si estaba vacío porque se limpiaron realmente todos
                if relisted:
                    DOWNLOADS_STATUS[job_id]['files'] = relisted
                    status['files'] = relisted
                    status['files_relisted'] = True
        except Exception as _relist_e:
            status['relist_error'] = str(_relist_e)
    # Incluir URLs de descarga si se han generado archivos
    files = status.get('files') or []
    if files:
        base_urls = []
        for idx, _f in enumerate(files):
            base_urls.append(f"/file/{job_id}/{idx}")
        status['download_urls'] = base_urls
        status['cleanup_available'] = True
    else:
        status['cleanup_available'] = False
        # Diagnóstico si terminó pero no hay archivos
        if status.get('status') in ('completado','saltado'):
            reasons = []
            if status.get('post_clean'):
                reasons.append('post_clean_enabled')
            if os.environ.get('POST_CLEAN_OUTPUT','0') == '1':
                reasons.append('env_POST_CLEAN_OUTPUT=1')
            if os.environ.get('AUTO_WIPE_DIR','0') == '1':
                reasons.append('env_AUTO_WIPE_DIR=1')
            if status.get('already_downloaded') and not status.get('files'):
                reasons.append('archive_marked_but_files_missing')
            if not reasons:
                reasons.append('unknown_empty_final')
            status['debug_no_files_reason'] = reasons
    
    # Contador de polls a nivel global y por job
    GLOBAL_METRICS['status_requests'] += 1
    job_stats = DOWNLOADS_STATUS[job_id]
    job_stats['status_polls'] = job_stats.get('status_polls', 0) + 1
    status['status_polls'] = job_stats['status_polls']
    return jsonify(status)

@app.route('/metrics', methods=['GET'])
def metrics():
    # Calcular métricas agregadas sencillas
    active = sum(1 for v in DOWNLOADS_STATUS.values() if v.get('status') not in ('completado','error','cancelado'))
    GLOBAL_METRICS['active_jobs_peak'] = max(GLOBAL_METRICS.get('active_jobs_peak',0), active)
    # Resumen por estados
    states = {}
    for v in DOWNLOADS_STATUS.values():
        st = v.get('status','unknown')
        states[st] = states.get(st,0)+1
    return jsonify({
        'global': GLOBAL_METRICS,
        'states': states,
        'jobs_total': len(DOWNLOADS_STATUS),
        'timestamp': datetime.utcnow().isoformat()+'Z'
    })

@app.route('/file/<job_id>/<int:index>', methods=['GET'])
def serve_downloaded_file(job_id, index):
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error':'Job ID no encontrado'}), 404
    files = DOWNLOADS_STATUS[job_id].get('files') or []
    if index < 0 or index >= len(files):
        return jsonify({'error':'Índice inválido'}), 400
    path = files[index]
    if not os.path.exists(path):
        return jsonify({'error':'Archivo no existe en servidor'}), 404
    try:
        delete_after = request.args.get('delete') == '1'
        resp = send_file(path, as_attachment=True)
        if delete_after:
            try:
                os.remove(path)
                # Actualizar lista en estado
                remaining = [p for i,p in enumerate(DOWNLOADS_STATUS[job_id].get('files', [])) if i != index]
                DOWNLOADS_STATUS[job_id]['files'] = remaining
            except Exception as de:
                DOWNLOADS_STATUS[job_id]['cleanup_error'] = str(de)
        # Auto wipe condicional: si no quedan archivos y variable activa, borrar carpeta
        try:
            if os.environ.get('AUTO_WIPE_DIR','0') == '1':
                job = DOWNLOADS_STATUS.get(job_id, {})
                out_dir = job.get('resolved_output_dir') or job.get('requested_output_dir')
                if out_dir and os.path.isdir(out_dir):
                    remaining_files = job.get('files') or []
                    if not remaining_files:
                        # Limpiar archivos nuevos que pudieran quedar (comparar con snapshot inicial)
                        initial_snapshot = set(job.get('initial_snapshot') or [])
                        current_listing = []
                        try:
                            current_listing = os.listdir(out_dir)
                        except Exception:
                            current_listing = []
                        for fname in list(current_listing):
                            if fname in initial_snapshot:
                                continue  # respetar archivos previos
                            fpath = os.path.join(out_dir, fname)
                            try:
                                if os.path.isfile(fpath):
                                    os.remove(fpath)
                            except Exception:
                                pass
                        # Intentar borrar directorio si está vacío y flag REMOVE_EMPTY_DIR=1
                        if os.environ.get('REMOVE_EMPTY_DIR','0') == '1':
                            try:
                                if len(os.listdir(out_dir)) == 0:
                                    os.rmdir(out_dir)
                                    DOWNLOADS_STATUS[job_id]['dir_removed'] = True
                            except Exception:
                                pass
                        DOWNLOADS_STATUS[job_id]['auto_wiped'] = True
        except Exception as e_aw:
            DOWNLOADS_STATUS[job_id]['auto_wipe_error'] = str(e_aw)
        return resp
    except Exception as e:
        return jsonify({'error':'No se pudo enviar el archivo','detalle':str(e)}), 500

@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup_job(job_id):
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error':'Job ID no encontrado'}), 404
    files = DOWNLOADS_STATUS[job_id].get('files') or []
    deleted = []
    errors = []
    for p in files:
        try:
            if os.path.exists(p):
                os.remove(p)
                deleted.append(os.path.basename(p))
        except Exception as e:
            errors.append({'file':p,'error':str(e)})
    DOWNLOADS_STATUS[job_id]['files'] = []
    return jsonify({'status':'ok','deleted':deleted,'errors':errors})

@app.route('/wipe/<job_id>', methods=['POST'])
def wipe_job_directory(job_id):
    """Elimina todos los archivos nuevos generados por el job y opcionalmente el directorio si queda vacío.
    Respeta snapshot inicial (no borra archivos previos). Controlado además por REMOVE_EMPTY_DIR."""
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error':'Job ID no encontrado'}), 404
    job = DOWNLOADS_STATUS[job_id]
    out_dir = job.get('resolved_output_dir') or job.get('requested_output_dir')
    if not out_dir or not os.path.isdir(out_dir):
        return jsonify({'error':'Directorio inválido'}), 400
    initial_snapshot = set(job.get('initial_snapshot') or [])
    try:
        current_listing = os.listdir(out_dir)
    except Exception as e:
        return jsonify({'error':'No se pudo listar directorio','detalle':str(e)}), 500
    removed = []
    errors = []
    for fname in list(current_listing):
        if fname in initial_snapshot:
            continue
        fpath = os.path.join(out_dir, fname)
        try:
            if os.path.isfile(fpath):
                os.remove(fpath)
                removed.append(fname)
        except Exception as e:
            errors.append({'file':fname,'error':str(e)})
    dir_removed = False
    if os.environ.get('REMOVE_EMPTY_DIR','0') == '1':
        try:
            if len(os.listdir(out_dir)) == 0:
                os.rmdir(out_dir)
                dir_removed = True
        except Exception:
            pass
    job['manual_wipe'] = True
    if removed:
        job['auto_wiped'] = True
    return jsonify({'status':'ok','removed':removed,'dir_removed':dir_removed,'errors':errors})

@app.route('/delete-file/<job_id>/<int:index>', methods=['POST'])
def delete_single_file(job_id, index):
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error':'Job ID no encontrado'}), 404
    files = DOWNLOADS_STATUS[job_id].get('files') or []
    if index < 0 or index >= len(files):
        return jsonify({'error':'Índice inválido'}), 400
    path = files[index]
    try:
        if os.path.exists(path):
            os.remove(path)
        remaining = [p for i,p in enumerate(files) if i != index]
        DOWNLOADS_STATUS[job_id]['files'] = remaining
        return jsonify({'status':'ok','deleted':os.path.basename(path),'remaining':len(remaining)})
    except Exception as e:
        return jsonify({'error':'No se pudo borrar','detalle':str(e)}), 500

@app.route('/job-files/<job_id>', methods=['GET'])
def job_files(job_id):
    """Devuelve siempre un listado fresco de archivos existentes en disco para el job,
    generando también URLs de descarga, incluso si el estado original tenía files vacío."""
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error':'Job ID no encontrado'}), 404
    job = DOWNLOADS_STATUS[job_id]
    resolved_dir = job.get('resolved_output_dir') or job.get('requested_output_dir')
    if not resolved_dir or not os.path.isdir(resolved_dir):
        return jsonify({'error':'Directorio no disponible'}), 400
    try:
        fresh = []
        for fname in os.listdir(resolved_dir):
            if fname.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4')):
                fresh.append(os.path.join(resolved_dir, fname))
        job['files'] = fresh
        urls = [f"/file/{job_id}/{i}" for i,_ in enumerate(fresh)]
        return jsonify({'status':'ok','files':fresh,'download_urls':urls,'count':len(fresh)})
    except Exception as e:
        return jsonify({'error':'Listado falló','detalle':str(e)}), 500

@app.route('/regen-files/<job_id>', methods=['POST'])
def regenerate_files(job_id):
    """Regenera la lista de archivos para un job ya completado/saltado cuando el frontend no recibió download_urls.
    Útil si se limpió la memoria del navegador o falló el polling final. No re-descarga nada, solo re-lista el directorio."""
    if job_id not in DOWNLOADS_STATUS:
        return jsonify({'error':'Job ID no encontrado'}), 404
    job = DOWNLOADS_STATUS[job_id]
    if job.get('status') not in ('completado','saltado'):
        return jsonify({'error':'Job aún en progreso o con error','status':job.get('status')}), 400
    resolved_dir = job.get('resolved_output_dir') or job.get('requested_output_dir')
    if not resolved_dir or not os.path.isdir(resolved_dir):
        return jsonify({'error':'Directorio no disponible'}), 400
    try:
        new_list = []
        for fname in os.listdir(resolved_dir):
            if fname.lower().endswith(('.mp3','.m4a','.opus','.webm','.mp4')):
                new_list.append(os.path.join(resolved_dir, fname))
        if not new_list:
            return jsonify({'warning':'No se encontraron archivos de audio/video'}), 200
        job['files'] = new_list
        return jsonify({'status':'ok','files':new_list,'count':len(new_list)})
    except Exception as e:
        return jsonify({'error':'Fallo re-listado','detalle':str(e)}), 500

@app.route('/upload-cookies', methods=['POST'])
def upload_cookies():
    """Permite subir el contenido de un archivo de cookies (formato Netscape) en runtime.
    Body JSON: {"cookies_text":"..."}
    Prioridad sobre variable de entorno."""
    global UPLOADED_COOKIES_PATH
    try:
        data = request.get_json(force=True)
        raw_text = data.get('cookies_text','')
        cookies_text = raw_text.strip()
        if not cookies_text:
            return jsonify({'error':'cookies_text vacío'}), 400
        if '.youtube.com' not in cookies_text:
            return jsonify({'error':'Contenido no parece contener cookies de youtube'}), 400
        # Sanitizar: agregar cabecera Netscape si falta
        header = '# Netscape HTTP Cookie File'
        lines = cookies_text.splitlines()
        if lines and not lines[0].startswith('# Netscape'):
            lines.insert(0, header)
        # Normalizar separadores: permitir espacios múltiples -> tabs simples
        norm_lines = []
        for ln in lines:
            if not ln.strip() or ln.strip().startswith('#'):
                norm_lines.append(ln)
                continue
            # Si la línea ya contiene tabs suficientes, dejarla
            if '\t' in ln:
                norm_lines.append(ln)
                continue
            # Convertir bloques de espacios a tabs (mínimo 6 columnas requerido por formato Netscape)
            parts = [p for p in ln.split(' ') if p!='']
            if len(parts) >= 7:
                norm_lines.append('\t'.join(parts))
            else:
                # Dejar la línea original por seguridad
                norm_lines.append(ln)
        final_text = '\n'.join(norm_lines).strip() + '\n'
        import tempfile
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        tf.write(final_text)
        tf.flush(); tf.close()
        UPLOADED_COOKIES_PATH = tf.name
        return jsonify({'status':'ok','path':UPLOADED_COOKIES_PATH,'size':len(final_text),'added_header': header in final_text,'normalized': True})
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
