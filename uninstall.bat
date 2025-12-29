@echo off
echo ========================================
echo HP Monitor - Odinstalace
echo ========================================
echo.

set /p confirm="Opravdu chces odinstalovat HP Monitor? (A/N): "
if /i not "%confirm%"=="A" (
    echo Odinstalace zrusena.
    pause
    exit /b
)

echo Mazani aplikace...
if exist HPMonitor.exe del /f /q HPMonitor.exe
if exist config.json del /f /q config.json
if exist .venv rmdir /s /q .venv
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo HP Monitor byl odinstalovan.
echo Muzete smazat celou slozku.
echo.
pause
