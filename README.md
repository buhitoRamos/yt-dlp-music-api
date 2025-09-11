# 🎵 YouTube Music Downloader API

Una API web moderna para descargar música de YouTube y YouTube Music con interfaz web intuitiva.

![Demo](https://img.shields.io/badge/Status-Funcionando-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-API-green)

## ✨ Características

- 🎯 **Interfaz Web Moderna**: Frontend responsive con CSS3 y JavaScript ES6+
- 🚀 **API RESTful**: Endpoints completos para descarga y monitoreo
- 🛡️ **Sistema Anti-Bloqueo Inteligente**: Detecta automáticamente el entorno y aplica estrategias específicas
- ❌ **Cancelación en Tiempo Real**: Botón para cancelar descargas en progreso
- 📁 **Selector de Carpetas**: Integración con File System Access API
- 📊 **Monitoreo de Progreso**: Status en tiempo real de las descargas
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
- `GET /status/<job_id>` - Ver progreso
- `POST /cancel/<job_id>` - Cancelar descarga
- `GET /formats` - Formatos disponibles
- `GET /environment` - Información del entorno y estrategias aplicadas
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

### Variables de entorno útiles (hosting / anti-bloqueo)
| Variable | Valor | Propósito |
|----------|-------|-----------|
| `FORCE_LOCAL_MODE` | 1 | Emula estrategias locales (incluye intento de cookies sintéticas) en un servidor remoto |
| `FORCE_REMOTE_MODE` | 1 | Fuerza estrategias de entorno remoto aun estando en local |
| `USE_FAKE_CONSENT_COOKIE` | 1 (default) | Crea cookie CONSENT/PREF sintética si no hay cookies reales |
| `YOUTUBE_COOKIES` | (texto) | Cookies exportadas reales para alta tasa de éxito |

Ejemplo rápido (Render / Railway sin cookies reales):
```bash
FORCE_LOCAL_MODE=1
USE_FAKE_CONSENT_COOKIE=1
```
Esto activa: user-agents rotativos + cliente web local + cookie sintética mínima para evitar algunos bloqueos.

Para máxima efectividad añade también:
```bash
YOUTUBE_COOKIES="(contenido de tu cookies.txt)"
```

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
