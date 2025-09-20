@echo off
REM YT-DLP Music API - Launcher de Doble Clic para Windows
REM Este archivo puede ejecutarse haciendo doble clic desde el Explorador de Windows

title YT-DLP Music API v3.0 - Launcher Windows

REM Cambiar al directorio donde está el script
cd /d "%~dp0"

REM Mostrar información inicial
echo.
echo ===============================================
echo  🎵 YT-DLP Music API v3.0 - Windows Launcher
echo ===============================================
echo  📁 Directorio: %CD%
echo  🖥️ Sistema: Windows
echo  ⏰ Fecha/Hora: %DATE% %TIME%
echo ===============================================
echo.

REM Verificar si Python está instalado
echo 🔍 Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Python no está instalado o no está en PATH
    echo.
    echo 💡 SOLUCIÓN:
    echo    1. Descargar Python desde: https://python.org
    echo    2. Durante la instalación, marcar "Add Python to PATH"
    echo    3. Reiniciar y ejecutar este archivo nuevamente
    echo.
    echo 📱 Presiona cualquier tecla para abrir la página de descarga...
    pause >nul
    start https://python.org/downloads/
    goto :error_exit
)

REM Mostrar versión de Python encontrada
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python encontrado: %PYTHON_VERSION%
echo.

REM Verificar si existe el launcher universal
if not exist "launch_universal.py" (
    echo ❌ ERROR: No se encontró el archivo launch_universal.py
    echo 📁 Asegúrate de que este archivo esté en el mismo directorio
    goto :error_exit
)

echo 🚀 Iniciando YT-DLP Music API...
echo 💡 Se abrirá automáticamente en tu navegador
echo ⏹️ Para cerrar: Presiona Ctrl+C en esta ventana o usa el botón "Cerrar App" en la web
echo.

REM Ejecutar el launcher universal
python launch_universal.py

REM Si llegamos aquí, el programa terminó normalmente
echo.
echo 🛑 YT-DLP Music API se ha cerrado
echo 📱 Presiona cualquier tecla para salir...
pause >nul
exit /b 0

:error_exit
echo.
echo ❌ No se pudo iniciar la aplicación
echo 📱 Presiona cualquier tecla para salir...
pause >nul
exit /b 1