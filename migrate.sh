#!/bin/bash

echo "🚀 Script de Migración - YT-DLP Music API"
echo "========================================"

echo "📋 Opciones de despliegue disponibles:"
echo "1. 🚄 Railway (Rápido - 2 minutos)"
echo "2. ✈️  Fly.io (Medio - 5 minutos)"
echo "3. 🌊 DigitalOcean VPS (Completo - 30 minutos)"
echo "4. 📊 Ver comparación completa"

read -p "Selecciona una opción (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚄 RAILWAY DEPLOYMENT"
        echo "===================="
        echo "✅ Archivos ya preparados:"
        echo "   - requirements.txt"
        echo "   - Procfile"
        echo "   - runtime.txt"
        echo ""
        echo "📋 Pasos manuales:"
        echo "1. Ir a railway.app"
        echo "2. Conectar GitHub"
        echo "3. Seleccionar este repositorio"
        echo "4. Deploy automático"
        echo ""
        echo "🔧 Variables de entorno opcionales:"
        echo "   YOUTUBE_COOKIES=tu_cookie_aqui"
        echo ""
        echo "⏱️  Tiempo estimado: 2-3 minutos"
        echo "📊 Éxito esperado: 60-75% (mejor que Render)"
        ;;
    
    2)
        echo ""
        echo "✈️  FLY.IO DEPLOYMENT"
        echo "==================="
        echo "✅ Archivos ya preparados:"
        echo "   - Dockerfile"
        echo "   - fly.toml"
        echo "   - requirements.txt (con gunicorn)"
        echo ""
        echo "📋 Comandos para ejecutar:"
        echo "1. Instalar flyctl:"
        echo "   curl -L https://fly.io/install.sh | sh"
        echo ""
        echo "2. Login:"
        echo "   flyctl auth login"
        echo ""
        echo "3. Deploy:"
        echo "   flyctl deploy"
        echo ""
        echo "⏱️  Tiempo estimado: 5-10 minutos"
        echo "📊 Éxito esperado: 70-80%"
        ;;
    
    3)
        echo ""
        echo "🌊 DIGITALOCEAN VPS (RECOMENDADO)"
        echo "================================="
        echo "✅ Setup completo con navegadores reales"
        echo ""
        echo "📖 Ver guía completa en:"
        echo "   DIGITALOCEAN_VPS_SETUP.md"
        echo ""
        echo "🎯 Ventajas:"
        echo "   - Navegadores reales (Chrome, Firefox)"
        echo "   - IPs menos bloqueadas"
        echo "   - Control total"
        echo "   - Cookies persistentes"
        echo ""
        echo "💰 Costo: $5/mes"
        echo "⏱️  Setup inicial: 30-60 minutos"
        echo "📊 Éxito esperado: 85-95%"
        ;;
    
    4)
        echo ""
        echo "📊 COMPARACIÓN DE PLATAFORMAS"
        echo "============================"
        echo ""
        printf "%-12s %-10s %-12s %-10s %-10s %-15s\n" "Plataforma" "Precio" "Setup" "Navegador" "IP Quality" "Éxito"
        echo "------------------------------------------------------------------------"
        printf "%-12s %-10s %-12s %-10s %-10s %-15s\n" "Render" "Gratis" "Auto" "❌" "⭐⭐" "40-60%"
        printf "%-12s %-10s %-12s %-10s %-10s %-15s\n" "Railway" "Gratis" "Auto" "❌" "⭐⭐⭐" "60-75%"
        printf "%-12s %-10s %-12s %-10s %-10s %-15s\n" "Fly.io" "\$5/mes" "5 min" "⭐" "⭐⭐⭐" "70-80%"
        printf "%-12s %-10s %-12s %-10s %-10s %-15s\n" "DO VPS" "\$5/mes" "30 min" "✅" "⭐⭐⭐⭐" "85-95%"
        printf "%-12s %-10s %-12s %-10s %-10s %-15s\n" "Heroku" "\$7/mes" "Auto" "❌" "⭐⭐⭐" "65-75%"
        echo ""
        echo "🎯 Recomendación: DigitalOcean VPS para máximo éxito"
        echo "⚡ Alternativa rápida: Railway para probar inmediatamente"
        ;;
    
    *)
        echo "❌ Opción no válida"
        exit 1
        ;;
esac

echo ""
echo "📚 Documentación disponible:"
echo "   - RAILWAY_SETUP.md"
echo "   - DIGITALOCEAN_VPS_SETUP.md"
echo "   - DEPLOYMENT_ALTERNATIVES.md"
echo ""
echo "🔧 Sistema anti-bot ya optimizado para todas las plataformas"
echo ""

# Verificar si hay cambios sin commitear
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Hay cambios sin commitear. ¿Quieres hacer commit y push?"
    read -p "Hacer commit y push? (y/n): " commit_choice
    
    if [ "$commit_choice" = "y" ] || [ "$commit_choice" = "Y" ]; then
        git add .
        git commit -m "Add deployment alternatives and optimization for multiple platforms"
        git push origin main
        echo "✅ Cambios enviados a GitHub"
    fi
else
    echo "✅ Repositorio actualizado en GitHub"
fi

echo ""
echo "🎉 ¡Listo para migrar! Elige la plataforma que prefieras."