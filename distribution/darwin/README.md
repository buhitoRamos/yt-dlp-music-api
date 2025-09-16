# 🎵 YT-DLP Music API - Aplicación Standalone para Mac

## ✅ ¡Instalación Completada!

Tu aplicación standalone de YT-DLP Music API está lista para usar en macOS.

## 🚀 Cómo usar

### Opción 1: Script automático (Recomendado)
```bash
./launch.sh
```

### Opción 2: Manual
1. Abrir `YT-DLP-Music-API.app`
2. Esperar 3-5 segundos
3. Abrir navegador en: http://localhost:8080

## 📁 Contenido incluido

- ✅ **YT-DLP-Music-API.app** - Aplicación nativa de macOS
- ✅ **yt-dlp** - Descargador integrado
- ✅ **ffmpeg** - Procesador de audio/video
- ✅ **Frontend web** - Interfaz de usuario completa
- ✅ **launch.sh** - Script de inicio automático

## ⚙️ Características

- 🎯 **Sin internet requerido** para la aplicación (solo para descargas)
- 🎯 **Sin Python requerido** en el sistema
- 🎯 **Completamente portable** - se puede copiar a otras Macs
- 🎯 **Detección automática de playlists**
- 🎯 **Descargas paralelas** para mayor velocidad
- 🎯 **Progreso en tiempo real**

## 🛠️ Configuración por defecto

- **Puerto**: 8080 (automático si 5000 está ocupado)
- **Directorio de descargas**: `~/Downloads/yt-dlp/`
- **Limpieza automática**: Deshabilitada (archivos se conservan)
- **Modo de descarga**: Paralelo (más rápido)

## 🎮 Uso típico

1. **Ejecutar**: `./launch.sh`
2. **Abrir navegador**: Se abre automáticamente
3. **Pegar URL**: YouTube, YouTube Music, playlists
4. **Descargar**: Click en "Descargar"
5. **Monitorear**: Ver progreso en tiempo real
6. **Obtener archivos**: Click en "Descargar" cuando termine

## 🔧 Solución de problemas

### La aplicación no abre
```bash
# Verificar permisos
chmod +x launch.sh
chmod +x YT-DLP-Music-API.app/Contents/MacOS/YT-DLP-Music-API
```

### "No se puede abrir porque es de un desarrollador no identificado"
```bash
# Método 1: Clic derecho → Abrir → Abrir
# Método 2: Configuración del sistema
sudo spctl --master-disable
```

### El navegador no abre automáticamente
```bash
# Abrir manualmente
open http://localhost:8080
```

### Verificar que está ejecutándose
```bash
ps aux | grep "YT-DLP"
lsof -i :8080
```

## 📊 Estructura de archivos generados

```
~/Downloads/yt-dlp/
├── [título_video].mp3     # Audio extraído
├── [título_video].mp4     # Video completo  
└── playlist_[nombre]/     # Carpetas de playlists
    ├── 01 - [canción].mp3
    ├── 02 - [canción].mp3
    └── ...
```

## 🎯 URLs soportadas

- ✅ Videos individuales de YouTube
- ✅ Playlists de YouTube
- ✅ Albums de YouTube Music
- ✅ Canales completos
- ✅ URLs de música de otros sitios compatibles con yt-dlp

## 🚦 Estados de descarga

- 🟡 **En progreso** - Descargando archivos
- 🔵 **Procesando** - Extrayendo audio/video
- 🟢 **Completado** - Listo para descargar
- 🔴 **Error** - Revisar URL o conexión

## 💾 Espacio en disco

- **Aplicación**: ~100MB
- **Cada video**: 3-10MB (audio) / 20-100MB (video)
- **Playlists**: Variable según cantidad de elementos

## 🔄 Actualizar la aplicación

Para actualizar a una nueva versión:
1. Descargar nueva versión del repositorio
2. Ejecutar `python3 build_standalone.py` nuevamente
3. Reemplazar aplicación actual

---

**¡Disfruta descargando tu música favorita! 🎵**

*Aplicación construida el $(date) con yt-dlp y PyInstaller*