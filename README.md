# 🎵 YouTube Music Downloader API

Una API web moderna para descargar música de YouTube y YouTube Music con interfaz web intuitiva.

![Demo](https://img.shields.io/badge/Status-Funcionando-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-API-green)

## ✨ Características

- 🎯 **Interfaz Web Moderna**: Frontend responsive con CSS3 y JavaScript ES6+
- 🚀 **API RESTful**: Endpoints completos para descarga y monitoreo
- 🛡️ **Sistema Anti-Bloqueo Inteligente**: Detecta automáticamente el entorno y aplica estrategias específicas
- ❌ **Cancelación en Tiempo Real**: Botón para cancelar descargas en progreso
- 📁 **Selector de Carpetas**: Integración con File System Access API
- 📊 **Monitoreo de Progreso**: Status de las descargas (polling adaptativo)
- 🧪 **Métricas en Vivo**: Endpoint `/metrics` con contadores globales y por estado
- 🎵 **Múltiples Formatos**: MP3, MP4, y ahora **bestaudio (sin convertir, más rápido)**
- ⚡ **SPEED_MODE**: Modo turbo que evita transcodificar a MP3, desactiva prefetch y validaciones extra, y fuerza la mejor pista de audio directamente
- 🎨 **Diseño Responsive**: Compatible con móviles y escritorio
- 🌐 **Optimizado para Hosting**: Funciona automáticamente en Render, Heroku, Railway

## 🛠️ Instalación

1. **Clonar el repositorio**:
```bash
git clone https://github.com/buhitoRamos/yt-dlp-music-api.git
cd yt-dlp-music-api
```

2. **Instalar dependencias**:
```bash
pip install flask flask-cors yt-dlp
```

3. **Ejecutar la aplicación**:

**Versión original**:
```bash
python3 api_downloader.py
```

**Versión standalone simple (recomendada)**:
```bash
python3 api_downloader_simple.py
```

**Versión ultra simple (más confiable)**:
```bash
python3 api_downloader_minimal.py
```

4. **Abrir en el navegador**:
```
http://localhost:8080
```

## 📦 Distribuciones Standalone

Para evitar problemas de instalación de dependencias y Python, hemos creado versiones standalone:

### 🚀 Versiones Disponibles

- **`api_downloader_simple.py`**: Versión Flask optimizada con branding personalizado y bypass SSL
- **`api_downloader_minimal.py`**: Versión ultra-confiable con servidor TCP puro (sin Flask)
- **`api_downloader_standalone.py`**: Versión independiente con auto-instalación de dependencias

### 🛠️ Crear Distribución Ejecutable

Para crear ejecutables standalone sin requerir Python:

```bash
# Distribución híbrida (ejecutable + código fuente de respaldo)
python3 create_hybrid_distribution.py

# Distribución completa con binarios para todas las plataformas
python3 create_portable_distribution.py

# Distribución específica para problemas SSL en macOS
python3 create_ssl_fixed_distribution.py
```

Estas distribuciones incluyen:
- ✅ Ejecutables compilados para macOS y Windows
- ✅ Binarios de `yt-dlp`, `ffmpeg` y `ffprobe`
- ✅ Branding personalizado "YT-DLP-Portable-by-buho"
- ✅ Interface web con marca "powered by buh!to"
- ✅ Bypass automático de certificados SSL
- ✅ Scripts de lanzamiento para diferentes sistemas

## 🎯 Uso

### Interfaz Web
1. Ingresa la URL de YouTube o YouTube Music
2. Selecciona la carpeta de destino
3. Configura formato y calidad
4. Haz clic en "🚀 Iniciar Descarga"
5. Usa "❌ Cancelar" si necesitas detener la descarga

### API Endpoints

- `POST /download` - Iniciar descarga
- `GET /status/<job_id>` - Ver progreso (incluye `status_polls` por job)
- `POST /cancel/<job_id>` - Cancelar descarga
- `GET /formats` - Formatos disponibles
- `GET /environment` - Información del entorno y versiones (Python y yt-dlp)
- `GET /metrics` - Métricas agregadas (`status_requests`, `download_requests`, `active_jobs_peak`, resumen por estado)
- `GET /jobs` - Listar trabajos

## 📁 Estructura del Proyecto

```
├── api_downloader.py              # API Flask original
├── api_downloader_simple.py       # Versión Flask optimizada (recomendada)
├── api_downloader_minimal.py      # Versión ultra-confiable TCP
├── api_downloader_standalone.py   # Versión con auto-instalación
├── create_hybrid_distribution.py  # Crear distribución ejecutable+código
├── create_portable_distribution.py # Crear distribución completa
├── create_ssl_fixed_distribution.py # Crear distribución SSL-fixed
├── build_standalone_v4.py         # Script de compilación PyInstaller
├── auto_installer_v4.py           # Instalador automático de dependencias
├── frontend/
│   ├── index.html                 # Interfaz web
│   ├── css/
│   │   └── styles.css            # Estilos responsivos
│   └── js/
│       └── app.js                # Lógica del frontend
├── binaries/                      # Binarios yt-dlp, ffmpeg, ffprobe
│   ├── darwin/                   # Binarios para macOS
│   └── windows/                  # Binarios para Windows
├── requirements.txt               # Dependencias Python
└── README.md                     # Documentación
```

## 🚀 Despliegue

Compatible con:
- Railway
- Render
- Heroku
- Cualquier servidor que soporte Flask

### Variables de entorno clave

Anti-bloqueo / Estrategia:
| Variable | Valores | Descripción |
|----------|---------|-------------|
| `YOUTUBE_COOKIES` | texto | Cookies Netscape reales (prioridad alta) |
| `USE_FAKE_CONSENT_COOKIE` | 0/1 | Inserta cookie sintética mínima si no hay reales (default 1) |
| `STRICT_TWO_ATTEMPTS` | 0/1 | Limita a 2 intentos máx (default 1) |
| `ALLOW_FALLBACK` | 0/1 | Permite ampliar estrategias en reintentos (default 1) |
| `PROXY_LIST` | host:puerto,... | Lista separada por comas para rotar proxies |
| `ROTATE_PROXIES` | 0/1 | Alternar proxy por intento (default 1) |

Reducción de salida / rapidez:
| Variable | Valores | Efecto |
|----------|---------|--------|
| `REDUCE_OUTPUT` | 0/1 | Elimina `--write-info-json` y metadatos de playlist pesados |
| `PLAYLIST_LIMIT` | N (int) | Aplica `--playlist-end N` para limitar items |
| `SINGLE_ITEM` | 0/1 | Fuerza `--no-playlist` (solo 1 elemento incluso en playlist) |
| `DOWNLOAD_ARCHIVE` | 0/1 | Usa `.downloaded.txt` para saltar ya procesados |
| `AUTO_WIPE_DIR` | 0/1 | Limpia automáticamente archivos generados tras servirlos (cuando ya no quedan) |
| `REMOVE_EMPTY_DIR` | 0/1 | Si la carpeta queda vacía tras wipe la elimina |
| `PRE_CLEAN_OUTPUT` | 0/1 | Borra TODO el contenido de la carpeta destino antes de iniciar un job (precaución) |
| `POST_CLEAN_OUTPUT` | 0/1 | Borra los archivos descargados inmediatamente tras completar (no disponibles para frontend) |
| `SPEED_MODE` | 0/1 | Fuerza modo ultra rápido: desactiva prefetch, `HEAD_VALIDATE`, `JITTER_THROTTLE`, limita a 2 intentos y si el usuario pidió MP3 lo sustituye por `bestaudio` (evita transcodificar) |

Prefetch (metadata rápida) - para acelerar inicio y evitar timeouts en playlists grandes:
| Variable | Valores | Descripción |
|----------|---------|-------------|
| `PREFETCH_MODE` | off / fast / full / auto | `auto` (default) salta playlists y hace fast para videos sueltos |
| `PREFETCH_TIMEOUT` | seg (int) | Ajusta timeout del prefetch individual |

Otros:
| Variable | Valores | Descripción |
|----------|---------|-------------|
| `DOWNLOAD_ARCHIVE` | 0/1 | Evita re-descargar (yt-dlp `--download-archive`) |
| `USE_MOBILE_FIRST` | 0/1 | Prioriza cliente móvil/Android para Music/Shorts |
| `ENABLE_CLIENT_CACHE` | 0/1 | Reutiliza último client exitoso por tipo de contenido |
| `HEAD_VALIDATE` | 0/1 | HEAD parcial previo a descarga para cambiar client si falla |
| `JITTER_THROTTLE` | 0/1 | Aplica jitter a parámetros K para simular variabilidad |

### 🔊 Formato `bestaudio` y SPEED_MODE

Cuando seleccionas en el frontend la opción "Audio rápido (sin convertir)" se solicita directamente la mejor pista de audio disponible (normalmente opus/webm) sin pasar por una transcodificación a MP3. Esto reduce:

- Tiempo de CPU (no se ejecuta ffmpeg para convertir)
- Latencia total percibida
- Tamaño temporal de archivos intermedios

Si además exportas `SPEED_MODE=1`:

- Se fuerza `bestaudio` incluso si el usuario eligió MP3 (para máxima velocidad)
- `PREFETCH_MODE` se pone internamente en `off`
- Se desactivan `HEAD_VALIDATE` y `JITTER_THROTTLE`
- Reintentos máximos: 2 (rápido failover)
- Menos argumentos accesorio → menor riesgo de bloqueos o latencias artificiales

Ejemplo de uso del modo más rápido:
```bash
export SPEED_MODE=1
export REDUCE_OUTPUT=1          # Opcional: menos archivos auxiliares
export PRE_CLEAN_OUTPUT=1       # Limpia antes la carpeta si quieres un directorio limpio
python3 api_downloader.py
```

En este modo, si necesitas MP3 específicamente (por compatibilidad) puedes descargar `bestaudio` y luego convertir localmente donde tengas más CPU/RAM disponibles.

### Ejemplos rápidos

Descargas rápidas de playlist limitada a 10 elementos, sin metadata extra y evitando duplicados:
```bash
export REDUCE_OUTPUT=1
export PLAYLIST_LIMIT=10
export DOWNLOAD_ARCHIVE=1
export PRE_CLEAN_OUTPUT=1   # Borra antes el contenido del directorio destino
python3 api_downloader.py
```

Modo turbo (máxima velocidad, mejor audio directo sin conversión):
```bash
export SPEED_MODE=1
export REDUCE_OUTPUT=1
python3 api_downloader.py
```

Descargar y luego eliminar automáticamente los archivos (solo flujo de streaming directo):
```bash
export POST_CLEAN_OUTPUT=1
export REMOVE_EMPTY_DIR=1
python3 api_downloader.py
```

Forzar modo single (solo primer item de cualquier playlist) y prefetch deshabilitado:
```bash
export SINGLE_ITEM=1
export PREFETCH_MODE=off
python3 api_downloader.py
```

Prefetch completo (para diagnosticar) con timeout 20s:
```bash
export PREFETCH_MODE=full
export PREFETCH_TIMEOUT=20
python3 api_downloader.py
```

Reintentos ampliados (desactivar STRICT_TWO_ATTEMPTS) y usar lista de proxies:
```bash
export STRICT_TWO_ATTEMPTS=0
export PROXY_LIST="socks5://1.2.3.4:1080,https://5.6.7.8:3128"
python3 api_downloader.py
```

### Métricas
Endpoint: `GET /metrics`
Devuelve JSON como:
```json
{
	"global": {
		"status_requests": 42,
		"download_requests": 3,
		"active_jobs_peak": 2
	},
	"states": {"descargando":1,"completado":1},
	"jobs_total": 2,
	"timestamp": "2025-09-12T12:34:56Z"
}
```
Cada `/status/<job_id>` incluye `status_polls` para saber cuántas veces se ha consultado ese trabajo.

### Polling Adaptativo (Frontend)
El frontend ahora reduce peticiones:
1. Empieza cada 2s
2. Si `attempt >=2` o >3 polls sin finalizar -> 4s
3. Tras >8 polls -> 6s
Detiene polling al completar/error/cancelar. El panel muestra: `📡 Polls: N (intervalo actual: Xs)`.

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -m 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.

## ⚠️ Aviso Legal

Este proyecto es solo para uso educativo. Asegúrate de cumplir con los términos de servicio de YouTube y las leyes de derechos de autor de tu país.

---

Creado con ❤️ por [buhitoRamos](https://github.com/buhitoRamos)
