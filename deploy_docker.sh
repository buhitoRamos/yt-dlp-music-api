#!/usr/bin/env bash
# Desplegar localmente con Docker (construir imagen y correr en el puerto 8080)
set -e
IMAGE_NAME=yt-dlp-music-api:latest

docker build -t $IMAGE_NAME .

docker run -it --rm -p 8080:8080 \
  -e PORT=8080 \
  -v "$PWD/downloads":/app/downloads \
  $IMAGE_NAME
