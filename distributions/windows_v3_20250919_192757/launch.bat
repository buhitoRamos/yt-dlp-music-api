@echo off
echo 🎵 Iniciando YT-DLP Music API v3.0...
echo 🔧 Verificando dependencias...

if exist "binaries\ffmpeg.exe" (
    echo ✅ FFmpeg incluido
) else (
    echo ⚠️ FFmpeg no encontrado
)

echo 🚀 Lanzando aplicación v3.0...
echo 📱 Si no se abre automáticamente el navegador, ve a: http://localhost:8080

start "" "YT-DLP-Music-API-v3.exe"
timeout /t 3 /nobreak >nul
echo 🌐 Abriendo navegador en puerto 8080...
start "" "http://localhost:8080"

echo.
echo 🎵 YT-DLP Music API v3.0 está ejecutándose!
echo 📱 Navegador: http://localhost:8080
echo 🛑 Para cerrar: usa el botón "🔌 Cerrar App" en la interfaz
echo.
pause
