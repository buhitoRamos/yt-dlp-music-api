# YT-DLP Music API - Darwin Distribution

**Versión:** 20250916_122728  
**Generado:** 2025-09-16 12:27:28  
**Plataforma:** Darwin

## 🚀 Inicio Rápido

### Darwin:
```bash
./launch.sh
```

## 📁 Contenido

- **YT-DLP-Music-API.app** - Aplicación principal
- **launch.sh** - Script de inicio
- **check_port.sh** - Verificar puerto 8080
- **README.md** - Esta documentación

## ✅ Características

- ✅ Puerto fijo: 8080
- ✅ Sin dependencias externas
- ✅ Detección automática de playlists  
- ✅ Descargas paralelas
- ✅ Progreso en tiempo real
- ✅ Compatible con YouTube, YouTube Music

## 🔧 Solución de problemas

### Error: max_workers referenced before assignment
Este error ha sido corregido en esta versión.

### Puerto ocupado
Usar `check_port.sh` para diagnosticar.

### La aplicación no inicia
- Verificar permisos: `chmod +x *.sh`
- Verificar que el puerto 8080 esté libre

---
*Construido con PyInstaller desde Darwin*
