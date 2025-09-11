#!/usr/bin/env bash
# Script rápido para desplegar en Railway usando su CLI
# Requisitos: instalar railway CLI y estar logueado (`npm i -g railway` y `railway login`)
set -e

# Inicializar proyecto en railway si es la primera vez
if ! railway init &>/dev/null; then
  echo "railway init failed or already initialized"
fi

# Crear o usar un proyecto existente
railway up --detach

echo "Despliegue Railway iniciado. Usa 'railway logs' para ver logs y 'railway status' para ver estado." 
