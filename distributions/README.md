# 🎵 YT-DLP Music API - Sistema de Distribuciones Standalone

## ✅ **Problemas Resueltos**

1. ✅ **Error `max_workers referenced before assignment`** - Corregido
2. ✅ **Puerto fijo en 8080** - Configurado automáticamente 
3. ✅ **Distribuciones para Windows desde Mac** - Cross-compilation implementada
4. ✅ **Versioning sin sobrescribir** - Sistema incremental con timestamps

## 📦 **Estructura de Distribuciones**

```
distributions/
├── darwin/                    # ← Latest macOS (usar este)
│   ├── YT-DLP-Music-API.app  
│   ├── launch.sh             
│   ├── check_port.sh         
│   ├── lsof_8080.sh          
│   └── README.md             
├── windows/                   # ← Latest Windows (usar este)
│   ├── YT-DLP-Music-API.exe  
│   ├── launch.bat            
│   ├── check_port.bat        
│   └── README.md             
├── darwin_YYYYMMDD_HHMMSS/    # Versiones archivadas con timestamp
└── windows_YYYYMMDD_HHMMSS/   # Versiones archivadas con timestamp
```

## 🚀 **Uso Rápido**

### **Mac:**
```bash
cd distributions/darwin/
./launch.sh
```

### **Windows:**
```cmd
cd distributions\\windows\\
launch.bat
```

## 🔧 **Scripts de Construcción**

### **Script Original** (`build_standalone.py`)
- Sobrescribe distribuciones existentes
- Básico, funcional

### **Script Incremental** (`build_incremental.py`) ⭐ **RECOMENDADO**
- **NO borra** distribuciones existentes
- Crea versiones con timestamp + latest
- Manejo inteligente de binarios (no descarga si existen)
- Cross-compilation Mac → Windows
- READMEs automáticos

#### **Opciones de uso:**
```bash
# Solo sistema actual
python3 build_incremental.py

# Sistema específico
python3 build_incremental.py --target darwin
python3 build_incremental.py --target windows

# Ambos sistemas
python3 build_incremental.py --target both
```

## 📋 **Características Implementadas**

### ✅ **Backend (API)**
- **Detección automática de playlists** - Extrae URLs individuales
- **Descargas paralelas** - Múltiples archivos simultáneamente  
- **Progreso en tiempo real** - Feedback por archivo y global
- **Puerto fijo 8080** - Sin conflictos automáticos
- **Múltiples modos de descarga**:
  - Single command (clásico)
  - Sequential individual
  - Parallel individual
- **Error handling robusto**

### ✅ **Frontend (Web UI)**
- **Interfaz intuitiva** - Drag & drop URLs
- **Progreso visual** - Barras de progreso por archivo
- **Debug logs** - Información detallada de errores
- **Responsive design** - Funciona en móviles

### ✅ **Distribuciones Standalone**
- **Sin dependencias** - Python, yt-dlp, ffmpeg incluidos
- **Binarios nativos** - .app para Mac, .exe para Windows
- **Scripts de utilidad** - Verificación de puertos, inicio automático
- **Cross-platform** - Generar Windows desde Mac

## 🎯 **URLs Soportadas**

- ✅ Videos individuales de YouTube
- ✅ Playlists de YouTube  
- ✅ Albums de YouTube Music
- ✅ Canales de YouTube
- ✅ Otros sitios compatibles con yt-dlp

## 🔍 **Diagnóstico y Utilidades**

### **Scripts disponibles:**
- `check_port.sh` (Mac) / `check_port.bat` (Windows) - Verificar puerto 8080
- `lsof_8080.sh` (Mac) - Comando directo lsof
- `launch.sh` / `launch.bat` - Inicio automático con navegador

### **Endpoints de API:**
```
GET  /                     # Frontend web
POST /download             # Iniciar descarga
GET  /status/<job_id>      # Ver progreso
GET  /download/<job_id>/<index>  # Descargar archivo
GET  /jobs                 # Listar trabajos
GET  /formats              # Formatos disponibles
```

## 🐛 **Troubleshooting**

### **Error: max_workers referenced before assignment**
✅ **CORREGIDO** en versiones actuales

### **Puerto 8080 ocupado**
```bash
# Mac
./check_port.sh

# Windows  
check_port.bat
```

### **La aplicación no inicia**
```bash
# Mac - Verificar permisos
chmod +x launch.sh
chmod +x YT-DLP-Music-API.app/Contents/MacOS/YT-DLP-Music-API

# Mac - Permitir aplicaciones no firmadas
sudo spctl --master-disable
```

### **Cross-compilation Windows no funciona en runtime**
- La versión generada desde Mac puede tener limitaciones
- Para mayor compatibilidad, construir en Windows nativo

## 📊 **Ambiente de Variables**

```bash
# Configuración de puerto
PORT=8080                    # Puerto del servidor

# Modos de descarga
USE_SINGLE_COMMAND=0         # 0=individual, 1=comando único
FORCE_SEQUENTIAL=0           # 0=paralelo, 1=secuencial

# Limpieza automática
AUTO_WIPE_DIR=0              # 0=conservar, 1=borrar automático
PRE_CLEAN_OUTPUT=1           # 1=limpiar antes de iniciar
KEEP_INFO_JSON=0             # 0=borrar .info.json, 1=conservar
```

## 🎉 **Estado del Proyecto**

### **Completado:**
- [x] Detección de playlists y extracción de URLs
- [x] Implementación de descargas paralelas  
- [x] Error `max_workers` corregido
- [x] Puerto fijo en 8080
- [x] Distribuciones para Mac y Windows
- [x] Sistema incremental de builds
- [x] Scripts de utilidad y diagnóstico

### **En progreso:**
- [ ] Optimización del progreso en tiempo real
- [ ] Mejoras en la interfaz de usuario

---

**🚀 ¡Listo para usar!** Escoge la distribución de tu plataforma y ejecuta el script de inicio.