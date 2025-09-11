# 🚀 Configuración de Cookies para Render (Opcional)

## ⚡ ¿Cuándo necesitas esto?

El sistema ahora funciona **automáticamente** en la mayoría de casos, pero si sigues teniendo problemas en Render, puedes agregar cookies como respaldo.

## 🍪 Configurar cookies en Render (Solo si es necesario)

### Paso 1: Exportar cookies de YouTube

1. **Instala "Get cookies.txt LOCALLY"** en Chrome/Firefox
2. **Ve a youtube.com e inicia sesión**
3. **Exporta las cookies** y copia el contenido

### Paso 2: Configurar en Render

1. **Ve a tu dashboard de Render**: https://dashboard.render.com/web/srv-d31es3fdiees73arpf7g
2. **Click en "Environment"** en la barra lateral
3. **Agregar nueva variable**:
   - **Key**: `YOUTUBE_COOKIES`
   - **Value**: (pega aquí el contenido completo del archivo cookies.txt)
4. **Guardar y redesplegar**

### Paso 3: Verificar

Una vez configurado, puedes verificar el estado en:
```
GET https://tu-app.onrender.com/environment
```

Debería mostrar:
```json
{
  "environment": "remote_server",
  "platform_detected": ["Render"],
  "cookies_available": true,
  "anti_blocking_strategies": {
    "max_attempts": 5,
    "sleep_intervals": "3-8s",
    "throttling": "50K-10K"
  }
}
```

## 🎯 Sistema Inteligente

El sistema ahora:

✅ **Detecta automáticamente** si está en Render/Heroku/Railway  
✅ **Aplica estrategias específicas** para cada entorno  
✅ **Usa 5 intentos** en servidores remotos vs 3 en local  
✅ **Throttling automático** para evitar detección  
✅ **Timeouts más largos** en producción  
✅ **Cookies como último recurso** (intento 5/5)  

## 🔍 Solución de problemas

### Si sigue fallando después de configurar cookies:

1. **Verifica las cookies**:
   ```bash
   curl https://tu-app.onrender.com/environment
   ```

2. **Asegúrate de que Render use la rama correcta**:
   - Dashboard → Settings → Build & Deploy
   - Branch: `release/25.90`

3. **Redespliega después de cambios**:
   - Dashboard → Deploys → Deploy latest commit

## 📊 Monitoreo

El endpoint `/status/<job_id>` ahora incluye:
- `environment`: local_dev o remote_server
- `attempt`: intento actual (ej: "3/5")
- `user_agent`: User-Agent usado
- `cookies_used`: si se usaron cookies

## 💡 Recomendación

**Primero** intenta sin cookies - el sistema debería funcionar automáticamente.  
**Solo si falla** agrega las cookies como respaldo.
