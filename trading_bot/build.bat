@echo off
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt -q
python -m pip install pyinstaller -q

echo.
echo Building trading_bot.exe (this may take 2-3 minutes)...
echo.

rmdir /s /q build dist 2>nul

pyinstaller --onefile --windowed --name trading_bot ^
    --hidden-import=colorlog --hidden-import=ccxt --hidden-import=sklearn app.py

if exist dist\trading_bot.exe (
    echo.
    echo.
    echo ========================================
    echo SUCCESS! trading_bot.exe created
    echo ========================================
    echo.
    echo File: dist\trading_bot.exe
    echo.
    echo Just double-click to run!
    echo.
) else (
    echo.
    echo Build failed - check errors above
    echo.
)

pause
