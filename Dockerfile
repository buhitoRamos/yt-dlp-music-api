FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para descargas
RUN mkdir -p /app/downloads

# Exponer puerto
EXPOSE 8080

# Variables de entorno
ENV FLASK_APP=api_downloader.py
ENV FLASK_ENV=production
ENV PORT=8080

# Comando para ejecutar la aplicación
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 api_downloader:app