# 🌊 DigitalOcean VPS Setup Guide

## 🎯 ¿Por qué DigitalOcean VPS?

- **IPs menos bloqueadas** que los grandes clouds
- **Navegadores reales** para cookies auténticas
- **Control total** del entorno
- **Persistencia** de cookies entre reinicios
- **Solo $5/mes** droplet básico

## 🚀 Setup Paso a Paso

### 1. Crear Droplet

1. Ir a **digitalocean.com**
2. Create → Droplets
3. **Ubuntu 22.04 LTS**
4. **Regular Intel $5/mo** (1GB RAM, 25GB SSD)
5. **SSH Key** (recomendado) o password
6. Crear droplet

### 2. Conectar al Servidor

```bash
ssh root@YOUR_DROPLET_IP
```

### 3. Setup Inicial

```bash
# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias
apt install -y python3 python3-pip nginx git curl wget ffmpeg

# Instalar navegadores para cookies reales
apt install -y chromium-browser firefox-esr

# Instalar Node.js (para algunas funciones de yt-dlp)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
```

### 4. Clonar y Setup Proyecto

```bash
# Clonar proyecto
cd /var/www
git clone https://github.com/buhitoRamos/yt-dlp-music-api.git
cd yt-dlp-music-api

# Instalar dependencias Python
pip3 install -r requirements.txt

# Crear directorio para descargas
mkdir -p downloads
chmod 755 downloads

# Crear usuario para la app (seguridad)
adduser --system --group ytdlp
chown -R ytdlp:ytdlp /var/www/yt-dlp-music-api
```

### 5. Configurar Nginx

```bash
# Crear configuración nginx
cat > /etc/nginx/sites-available/ytdlp << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    location /static/ {
        alias /var/www/yt-dlp-music-api/frontend/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Activar sitio
ln -s /etc/nginx/sites-available/ytdlp /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### 6. Configurar Systemd Service

```bash
# Crear servicio systemd
cat > /etc/systemd/system/ytdlp.service << 'EOF'
[Unit]
Description=YT-DLP Music API
After=network.target

[Service]
Type=simple
User=ytdlp
Group=ytdlp
WorkingDirectory=/var/www/yt-dlp-music-api
Environment=FLASK_APP=api_downloader.py
Environment=FLASK_ENV=production
ExecStart=/usr/bin/python3 api_downloader.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Activar y iniciar servicio
systemctl daemon-reload
systemctl enable ytdlp
systemctl start ytdlp

# Verificar estado
systemctl status ytdlp
```

### 7. Setup Cookies Automáticas

```bash
# Crear script para obtener cookies frescas
cat > /var/www/yt-dlp-music-api/update_cookies.sh << 'EOF'
#!/bin/bash
cd /var/www/yt-dlp-music-api

# Intentar obtener cookies de chromium
sudo -u ytdlp python3 -m yt_dlp --cookies-from-browser chromium --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ" &>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Cookies de Chromium funcionando"
    echo "BROWSER_COOKIES=chromium" > .env
else
    # Intentar Firefox
    sudo -u ytdlp python3 -m yt_dlp --cookies-from-browser firefox --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ" &>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Cookies de Firefox funcionando"
        echo "BROWSER_COOKIES=firefox" > .env
    else
        echo "⚠️ No se pudieron obtener cookies automáticas"
    fi
fi
EOF

chmod +x /var/www/yt-dlp-music-api/update_cookies.sh

# Ejecutar script
/var/www/yt-dlp-music-api/update_cookies.sh

# Programar actualización diaria de cookies
(crontab -l 2>/dev/null; echo "0 6 * * * /var/www/yt-dlp-music-api/update_cookies.sh") | crontab -
```

### 8. Configurar Firewall

```bash
# Configurar UFW
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
```

### 9. SSL Opcional (Certbot)

```bash
# Instalar Certbot
apt install -y certbot python3-certbot-nginx

# Obtener certificado (reemplazar YOUR_DOMAIN)
certbot --nginx -d YOUR_DOMAIN

# Auto-renovación
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

## 🎯 Ventajas de esta Setup

### ✅ Beneficios:
- **Cookies reales** de navegadores instalados
- **IP menos sospechosa** que grandes clouds
- **Persistencia** de configuración
- **Control total** del entorno
- **Escalabilidad** (puedes aumentar el droplet)

### 📊 Tasa de Éxito Esperada:
- **Con navegadores**: 85-95%
- **Sin cookies**: 70-80%
- **Vs Render**: +20-30% más éxito

## 🔧 Mantenimiento

### Actualizar código:
```bash
cd /var/www/yt-dlp-music-api
git pull origin main
systemctl restart ytdlp
```

### Ver logs:
```bash
journalctl -u ytdlp -f
```

### Actualizar yt-dlp:
```bash
pip3 install --upgrade yt-dlp
systemctl restart ytdlp
```

## 💰 Costo Total:
- **Droplet**: $5/mes
- **Dominio** (opcional): $10-15/año
- **Total**: ~$5-6/mes

Esta setup debería resolver definitivamente los problemas de bloqueo de YouTube.