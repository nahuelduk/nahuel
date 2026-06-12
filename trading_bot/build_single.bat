@echo off
REM Build single Trading Bot executable with launcher
REM Run this in the trading_bot folder

echo.
echo ========================================
echo Building Trading Bot (Single .exe)
echo ========================================
echo.

REM Install PyInstaller if not present
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

echo.
echo Building trading_bot.exe (this may take 2-3 minutes)...
echo.

pyinstaller --onefile ^
    --windowed ^
    --name trading_bot ^
    --add-data "config.py;." ^
    --add-data ".env;." ^
    --add-data "core;core" ^
    --add-data "analysis;analysis" ^
    --add-data "utils;utils" ^
    --hidden-import=colorlog ^
    --hidden-import=ccxt ^
    --hidden-import=sklearn ^
    --collect-all=streamlit ^
    --collect-all=plotly ^
    launcher.py

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Executable: .\dist\trading_bot.exe
echo.
echo Run it and click:
echo   1. "Start Bot" - inicia el bot de trading
echo   2. "Open Dashboard" - abre el dashboard en navegador
echo.
pause
