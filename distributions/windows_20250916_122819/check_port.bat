@echo off
echo Verificando puerto 8080...
netstat -an | find ":8080"
if %errorlevel% == 0 (
    echo Puerto 8080 está en uso
) else (
    echo Puerto 8080 está libre
)
pause
