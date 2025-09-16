#!/bin/bash
echo "Iniciando YT-DLP Music API..."
open -a "YT-DLP-Music-API.app"
sleep 3
echo "Detectando puerto..."
for port in 8080 5000 8000 8888; do
    if lsof -i :$port | grep -q "YT-DLP"; then
        echo "Aplicación encontrada en puerto $port"
        open "http://localhost:$port"
        break
    fi
done
