@echo off
setlocal enabledelayedexpansion

echo Installing PyInstaller...
python -m pip install pyinstaller -q

echo.
echo Building trading_bot.exe...
echo.

rmdir /s /q build dist 2>nul

pyinstaller --onefile --windowed --name trading_bot --hidden-import=colorlog --hidden-import=ccxt --hidden-import=sklearn --collect-all=streamlit --collect-all=plotly app.py

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
