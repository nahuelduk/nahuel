@echo off
REM Build script for Trading Bot — creates trading_bot.exe and dashboard.exe

echo.
echo ========================================
echo Building Trading Bot Executables
echo ========================================
echo.

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

echo.
echo [1/2] Building Bot executable...
pyinstaller --onefile ^
    --name trading_bot ^
    --icon=trading_bot.ico ^
    --add-data "config.py:." ^
    --add-data ".env:." ^
    --hidden-import=colorlog ^
    --hidden-import=ccxt ^
    --hidden-import=pandas_ta ^
    --collect-all=streamlit ^
    main.py

echo.
echo [2/2] Building Dashboard executable...
pyinstaller --onefile ^
    --name dashboard ^
    --icon=dashboard.ico ^
    --windowed ^
    --hidden-import=streamlit ^
    --hidden-import=plotly ^
    dashboard.py

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Executables are in: .\dist\
echo.
echo To run:
echo   1. trading_bot.exe        (Terminal window - bot process)
echo   2. dashboard.exe          (Browser dashboard)
echo.
pause
