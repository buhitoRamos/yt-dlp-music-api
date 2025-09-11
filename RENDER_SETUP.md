# 🚀 Guía de Despliegue en Render

## Configuración para resolver errores 429 en Render

### Paso 1: Exportar cookies de YouTube

1. **Instala la extensión "Get cookies.txt LOCALLY"** en Chrome/Firefox
2. **Ve a youtube.com e inicia sesión** con tu cuenta de Google
3. **Exporta las cookies**:
   - Haz clic en la extensión
   - Selecciona "Export"
   - Guarda como `cookies.txt`

### Paso 2: Configurar variable de entorno en Render

1. **Ve a tu dashboard de Render**
2. **Selecciona tu servicio**
3. **Ve a "Environment"**
4. **Agrega una nueva variable**:
   - **Key**: `YOUTUBE_COOKIES`
   - **Value**: (contenido completo del archivo cookies.txt)

#### Cómo copiar el contenido de cookies.txt:

```bash
# En tu computadora local:
cat cookies.txt
```

Copia todo el contenido y pégalo en el valor de la variable de entorno.

### Paso 3: Redeploy del servicio

1. **Ve a "Deploys" en Render**
2. **Haz clic en "Deploy latest commit"**
3. **Espera a que termine el despliegue**

## ✅ Verificación

Una vez configurado, tu aplicación en Render:
- ✅ Usará las cookies automáticamente
- ✅ Evitará errores 429
- ✅ Podrá descargar sin problemas

## 🔒 Seguridad

- ✅ Las cookies se almacenan como variables de entorno (seguro)
- ✅ No se exponen en el código fuente
- ✅ Se crean archivos temporales que se eliminan automáticamente

## 🔄 Mantenimiento

- **Renueva las cookies** cada 1-2 meses
- **Actualiza la variable de entorno** cuando expiren
- **Monitorea los logs** para detectar errores 429

## 📝 Ejemplo de cookies.txt válido

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1640995200	CONSENT	YES+cb
.youtube.com	TRUE	/	FALSE	1640995200	VISITOR_INFO1_LIVE	abcdef123456
.youtube.com	TRUE	/	TRUE	1640995200	YSC	xyz789
```

## 🆘 Solución de problemas

### Si sigues teniendo errores 429:
1. Verifica que la variable `YOUTUBE_COOKIES` existe
2. Asegúrate de que el contenido sea válido
3. Exporta cookies nuevas (pueden haber expirado)
4. Redespliega el servicio

### Si no aparece la variable de entorno:
1. Ve a Render Dashboard → Tu servicio → Environment
2. Verifica que `YOUTUBE_COOKIES` esté listada
3. Haz un nuevo deploy después de agregar la variable
