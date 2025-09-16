#!/bin/bash

# Script para verificar el estado del puerto 8080
# Autor: YT-DLP Music API
# Fecha: $(date)

echo "🔍 Verificando estado del puerto 8080..."
echo "=========================================="

# Verificar si el puerto está en uso
if lsof -i :8080 >/dev/null 2>&1; then
    echo "✅ Puerto 8080 está EN USO:"
    echo ""
    lsof -i :8080 | head -10
    echo ""
    
    # Obtener PID del proceso
    PID=$(lsof -t -i:8080 | head -1)
    if [ ! -z "$PID" ]; then
        echo "📋 Detalles del proceso:"
        ps -p $PID -o pid,ppid,command
        echo ""
        
        # Verificar si es nuestra aplicación
        if ps -p $PID -o command | grep -q "YT-DLP\|api_downloader"; then
            echo "🎵 Es nuestra aplicación YT-DLP Music API"
            echo ""
            echo "🌐 Puedes acceder en: http://localhost:8080"
            echo ""
            echo "Para cerrar la aplicación:"
            echo "   kill $PID"
            echo "   # o"
            echo "   killall \"YT-DLP-Music-API\""
        else
            echo "⚠️  Es otra aplicación usando el puerto"
            echo ""
            echo "Para liberar el puerto:"
            echo "   kill $PID"
            echo "   # o forzar:"
            echo "   kill -9 $PID"
        fi
    fi
else
    echo "❌ Puerto 8080 está LIBRE"
    echo ""
    echo "✅ Puedes iniciar YT-DLP Music API con:"
    echo "   PORT=8080 python3 api_downloader.py"
    echo "   # o"
    echo "   ./launch.sh"
fi

echo ""
echo "🔧 Comandos útiles:"
echo "   lsof -i :8080           # Ver qué usa el puerto"
echo "   lsof -t -i:8080         # Solo PID"
echo "   ps aux | grep YT-DLP    # Ver procesos YT-DLP"
echo "   killall YT-DLP-Music-API # Cerrar aplicación"
echo ""

# Verificar otros puertos relacionados
echo "🔍 Verificando puertos alternativos:"
for port in 5000 8000 8888 3000; do
    if lsof -i :$port >/dev/null 2>&1; then
        echo "   Puerto $port: EN USO"
    else
        echo "   Puerto $port: libre"
    fi
done