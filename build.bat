@echo off
echo ========================================
echo HP Monitor - Build EXE
echo ========================================
echo.

echo [1/4] Instalace PyInstaller...
.venv\Scripts\pip.exe install pyinstaller

echo [2/4] Building Updater.exe...
.venv\Scripts\pyinstaller.exe --onefile --console --name="updater" updater.py

echo [3/4] Building HPMonitor.exe...
.venv\Scripts\pyinstaller.exe --onefile --windowed --name="HPMonitor" --add-data "105937-OMRBGM-772.jpg;." hp_monitor.py

echo [4/4] Kopirovani updater.exe...
copy dist\updater.exe dist\updater.exe

echo.
echo ========================================
echo Hotovo!
echo ========================================
echo.
echo Soubory v dist\:
echo - HPMonitor.exe (hlavni aplikace)
echo - updater.exe (auto-updater)
echo.
echo Pro distribuci zabal:
echo - HPMonitor.exe
echo - updater.exe  
echo - 105937-OMRBGM-772.jpg
echo - uninstall.bat
echo.
pause
