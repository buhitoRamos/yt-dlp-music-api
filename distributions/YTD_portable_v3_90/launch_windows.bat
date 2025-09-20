@echo off
REM YT-DLP Music API - Windows Portable Launcher v3.0
echo 🎵 === YT-DLP Music API v3.0 Universal Portable ===
echo 🚀 Iniciando aplicación portable para Windows...
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Verificar si Python está disponible
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python no encontrado
    echo 💡 Por favor instala Python desde https://python.org
    echo 💡 Asegúrate de marcar "Add Python to PATH" durante la instalación
    pause
    exit /b 1
)

echo ✅ Python encontrado
echo.

REM Usar el launcher universal de Python
python launch_universal.py

REM Si algo sale mal, pausar para ver el error
if %errorlevel% neq 0 (
    echo.
    echo ❌ Error ejecutando la aplicación
    pause
)