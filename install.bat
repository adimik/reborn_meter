@echo off
echo ========================================
echo HP Monitor - Instalace
echo ========================================
echo.

REM Kontrola Pythonu
python --version >nul 2>&1
if errorlevel 1 (
    echo [CHYBA] Python neni nainstalovan!
    echo Stahni Python z: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Vytvareni virtualniho prostredi...
python -m venv .venv

echo [2/3] Instalace zavislosti...
.venv\Scripts\pip.exe install -r requirements.txt

echo [3/3] Hotovo!
echo.
echo ========================================
echo Instalace dokoncena!
echo ========================================
echo.
echo Spust aplikaci: start.bat
echo.
pause
