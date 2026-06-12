# Compilar Trading Bot a Ejecutables Windows

## Opción 1: Script automático (RECOMENDADO)

```powershell
cd C:\Users\pc01\nahuel\trading_bot
.\build.bat
```

Esto crea:
- `dist\trading_bot.exe` — el bot
- `dist\dashboard.exe` — el dashboard

---

## Opción 2: Compilación manual con PyInstaller

### Instalar PyInstaller
```powershell
python -m pip install pyinstaller
```

### Compilar Bot
```powershell
pyinstaller --onefile --name trading_bot --hidden-import=colorlog --hidden-import=ccxt main.py
```

### Compilar Dashboard
```powershell
pyinstaller --onefile --windowed --name dashboard --hidden-import=streamlit --hidden-import=plotly dashboard.py
```

Los ejecutables estarán en `dist\`

---

## Usar los ejecutables

### 1. Preparar antes de compilar
Asegúrate de que `.env` esté en la carpeta `trading_bot/`:
```
EXCHANGE_ID=binance
API_KEY=tu_api_key
API_SECRET=tu_api_secret
```

### 2. Copiar `config.py` y `.env` a `dist/`
Los ejecutables necesitan estos archivos en la misma carpeta.

### 3. Ejecutar
```powershell
cd dist
.\trading_bot.exe    # en una terminal
.\dashboard.exe      # en otra terminal
```

El dashboard se abre automáticamente en http://localhost:8501

---

## Alternativa: Instalador (.msi)

Para crear un instalador profesional:
1. Instala NSIS: https://nsis.sourceforge.io/Download
2. Crea un script .nsi con PyInstaller
3. El usuario solo descarga 1 .msi y listo

(Podemos hacerlo si lo necesitas)

---

## Problemas comunes

**Error: "ModuleNotFoundError"**
→ Agrega `--hidden-import=nombre_modulo` al comando pyinstaller

**El .exe no encuentra config.py**
→ Copia `config.py` y `.env` a la misma carpeta que el .exe

**El dashboard no se abre**
→ Ejecuta en CMD/PowerShell, no desde el explorador de archivos

---

## Tamaño de los ejecutables

Esperado: ~150-200 MB cada uno (Streamlit + todas las dependencias)

Para reducir:
```powershell
pyinstaller --onefile --nozipfile main.py
```

Pero toma más tiempo en ejecutarse.
