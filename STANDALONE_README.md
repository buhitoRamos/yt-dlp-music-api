# YT-DLP Music API - Distribución Standalone

Este directorio contiene las herramientas para crear versiones standalone (sin necesidad de hosting) de YT-DLP Music API para Mac y Windows.

## 🚀 Uso Rápido

### Para crear la distribución:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar el constructor
python build_standalone.py
```

### Para usar la aplicación:

**Mac:**
```bash
cd distribution/darwin/
./launch.sh
```

**Windows:**
```cmd
cd distribution\windows\
launch.bat
```

## 📦 Contenido de la distribución

```
distribution/
├── darwin/                    # Versión para macOS
│   ├── YT-DLP-Music-API.app  # Aplicación nativa de Mac
│   └── launch.sh             # Script de inicio automático
└── windows/                   # Versión para Windows
    ├── YT-DLP-Music-API.exe  # Ejecutable de Windows
    └── launch.bat            # Script de inicio automático
```

## ⚙️ Configuración

### Variables de entorno incluidas:
- `AUTO_WIPE_DIR=0` - Conservar archivos descargados
- `PRE_CLEAN_OUTPUT=1` - Limpiar antes de iniciar
- `USE_SINGLE_COMMAND=0` - Usar modo paralelo por defecto

### Directorios de salida:
- **Mac**: `~/Downloads/YT-DLP-Music/`
- **Windows**: `%USERPROFILE%\Downloads\YT-DLP-Music\`

## 🔧 Personalización

### Modificar configuración por defecto:

Edita `api_downloader.py` antes de construir:

```python
# Cambiar puerto por defecto
DEFAULT_PORT = 8080  # En lugar de 5000

# Cambiar directorio de salida
DEFAULT_OUTPUT_DIR = "~/Music/Downloads"
```

### Incluir archivos adicionales:

Modifica `build_standalone.py` en la sección `added_files`:

```python
added_files = [
    ('mi_config.json', '.'),
    ('mis_scripts/', 'scripts/'),
    # ... otros archivos
]
```

## 🛠️ Construcción Manual

### Para Mac (.app):

```bash
pyinstaller --onedir --windowed \
  --add-data "frontend:frontend" \
  --add-binary "binaries/darwin/yt-dlp:binaries" \
  --name "YT-DLP-Music-API" \
  api_downloader.py
```

### Para Windows (.exe):

```cmd
pyinstaller --onefile --console ^
  --add-data "frontend;frontend" ^
  --add-binary "binaries/windows/yt-dlp.exe;binaries" ^
  --add-binary "binaries/windows/ffmpeg.exe;binaries" ^
  --name "YT-DLP-Music-API" ^
  api_downloader.py
```

## 📋 Requisitos del sistema

### Mac:
- macOS 10.12 o superior
- 100MB de espacio libre
- Conexión a internet para descargas

### Windows:
- Windows 10 o superior
- 200MB de espacio libre
- Conexión a internet para descargas

## 🚨 Solución de problemas

### Error: "No se puede abrir la aplicación"
**Mac**: Permitir aplicaciones de desarrolladores no identificados:
```bash
sudo spctl --master-disable
```

### Error: "Windows Defender bloquea el archivo"
**Windows**: Agregar excepción en Windows Defender para el directorio de la aplicación.

### Error: "yt-dlp no encontrado"
Verificar que los binarios estén incluidos:
```bash
# Mac
ls -la distribution/darwin/YT-DLP-Music-API.app/Contents/MacOS/binaries/

# Windows
dir distribution\windows\binaries\
```

## 🔄 Actualización

Para actualizar a una nueva versión:

1. Hacer pull de los cambios del repositorio
2. Ejecutar nuevamente `python build_standalone.py`
3. Reemplazar los archivos de distribución

## 📞 Soporte

- **Errores de construcción**: Verificar que todas las dependencias estén instaladas
- **Problemas de ejecución**: Revisar los logs en la consola
- **Descargas fallidas**: Verificar conexión a internet y URLs válidas

## 🎯 Ventajas de la versión standalone

✅ **Sin hosting**: Funciona completamente offline (excepto para descargas)  
✅ **Sin Python**: No requiere Python instalado en el sistema  
✅ **Portable**: Se puede copiar a cualquier computadora  
✅ **Privado**: Todas las descargas son locales  
✅ **Rápido**: Sin latencia de red al servidor  

---

*Construido con ❤️ usando PyInstaller y yt-dlp*