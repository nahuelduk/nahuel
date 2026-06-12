@echo off
setlocal enabledelayedexpansion

echo Installing PyInstaller...
python -m pip install pyinstaller -q

echo.
echo Building trading_bot.exe...
echo.

pyinstaller --onefile ^
    --windowed ^
    --name trading_bot ^
    --distpath dist ^
    --specpath build ^
    --workpath build\work ^
    --add-data "config.py;." ^
    --add-data "core;core" ^
    --add-data "analysis;analysis" ^
    --add-data "utils;utils" ^
    --hidden-import=colorlog ^
    --hidden-import=ccxt ^
    --hidden-import=sklearn ^
    --collect-all=streamlit ^
    --collect-all=plotly ^
    app.py

if exist dist\trading_bot.exe (
    echo.
    echo ✓ SUCCESS! trading_bot.exe created
    echo.
    echo Location: dist\trading_bot.exe
    echo.
    echo Double-click to run!
    echo.
) else (
    echo.
    echo ✗ Build failed
    echo.
)

pause
