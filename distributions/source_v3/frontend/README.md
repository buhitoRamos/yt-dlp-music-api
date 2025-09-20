# Frontend - Music Downloader

Estructura organizada del frontend de la aplicación Music Downloader.

## 📁 Estructura de archivos

```
frontend/
├── index.html          # Página principal (HTML limpio)
├── css/
│   └── styles.css      # Todos los estilos CSS
└── js/
    └── app.js          # Toda la lógica JavaScript
```

## 🎨 Características del frontend

### HTML (`index.html`)
- ✅ Estructura semántica limpia
- ✅ Formulario responsivo
- ✅ Selector de carpetas nativo
- ✅ Rutas rápidas (Downloads, Music, Desktop)
- ✅ Indicadores de progreso en tiempo real

### CSS (`css/styles.css`)
- ✅ Diseño moderno con gradientes
- ✅ Responsive design (móvil y desktop)
- ✅ Animaciones suaves
- ✅ Componentes reutilizables
- ✅ Colores y tipografía consistentes

### JavaScript (`js/app.js`)
- ✅ Comunicación con API REST
- ✅ Manejo de formularios
- ✅ Selector de carpetas avanzado
- ✅ Monitoreo de progreso en tiempo real
- ✅ Gestión de estados de descarga

## 🚀 Cómo usar

### En desarrollo local:
```bash
# Desde la raíz del proyecto
python3 api_downloader.py

# Abrir en navegador:
http://localhost:8080
```

### En producción:
El servidor Flask sirve automáticamente los archivos desde la carpeta `frontend/`.

## 🛠️ Personalización

### Cambiar colores:
Edita las variables CSS en `css/styles.css`:
```css
/* Colores principales */
--primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--accent-color: #ff6b6b;
--success-color: #28a745;
```

### Agregar funcionalidades:
Extiende `js/app.js` agregando nuevas funciones.

### Modificar layout:
Ajusta la estructura en `index.html` y los estilos correspondientes.

## 📱 Compatibilidad

- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## 🔧 APIs utilizadas

- **File System Access API** - Para selector de carpetas (Chrome/Edge)
- **webkitdirectory** - Fallback para otros navegadores
- **Fetch API** - Comunicación con el backend
- **FormData API** - Manejo de formularios
