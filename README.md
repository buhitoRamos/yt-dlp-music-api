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
- 📊 **Monitoreo de Progreso**: Status en tiempo real de las descargas
- 🧪 **Métricas en Vivo**: Endpoint `/metrics` con contadores globales y por estado
- 🎵 **Múltiples Formatos**: MP3, MP4, y mejor calidad disponible
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
```bash
python3 api_downloader.py
```

4. **Abrir en el navegador**:
```
http://localhost:8080
```

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
├── api_downloader.py      # API Flask principal
├── frontend/
│   ├── index.html        # Interfaz web
│   ├── css/
│   │   └── styles.css    # Estilos responsivos
│   └── js/
│       └── app.js        # Lógica del frontend
├── requirements.txt       # Dependencias Python
└── README.md             # Documentación
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

### Ejemplos rápidos

Descargas rápidas de playlist limitada a 10 elementos, sin metadata extra y evitando duplicados:
```bash
export REDUCE_OUTPUT=1
export PLAYLIST_LIMIT=10
export DOWNLOAD_ARCHIVE=1
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
