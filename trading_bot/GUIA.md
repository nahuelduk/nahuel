# Trading Bot con IA — Guía Completa

## Qué hace

Bot de trading automatizado que analiza mercados continuamente y opera solo.
Combina análisis técnico (indicadores clásicos) con Machine Learning (Random Forest).

---

## Cómo funciona

Cada 60 segundos ejecuta este ciclo:

1. Descarga precios en tiempo real via CCXT
2. Calcula indicadores: EMA, RSI, MACD, Bollinger Bands, ATR
3. Predice dirección con ML (Random Forest entrenado con histórico)
4. Combina: score técnico (60%) + predicción ML (40%)
5. Si score > 0.5 → compra | revisa stop-loss y take-profit de posiciones abiertas
6. Ejecuta orden (simulada o real)

### Gestión de riesgo automática
- Máximo 3 trades abiertos al mismo tiempo
- Stop-loss: −2% por trade
- Take-profit: +4% por trade
- Tamaño de posición: 1% del capital por operación
- El modelo ML se reentrena cada 24 ciclos automáticamente

---

## Instalación

```bash
cd trading_bot
pip install -r requirements.txt
cp .env.example .env
```

---

## Configuración rápida (`config.py`)

```python
PAPER_TRADING = True          # True = simulado | False = dinero real
EXCHANGE_ID   = "binance"     # ver lista de brokers abajo
SYMBOLS       = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TIMEFRAME     = "1h"          # 1m 5m 15m 1h 4h 1d
PAPER_CAPITAL = 10_000.0      # capital inicial simulado en USD
```

---

## Ejecutar

```bash
python main.py
```

---

## Brokers soportados y cómo vincularlos

### CRIPTO

#### Binance (el más popular, recomendado para empezar)
1. Crear cuenta: https://testnet.binance.vision  ← testnet gratuita
2. Generar API Key en la testnet
3. En `.env`:
```
EXCHANGE_ID=binance
API_KEY=tu_key
API_SECRET=tu_secret
```
4. En `config.py`: `SANDBOX = True`

#### Bybit
1. Testnet: https://testnet.bybit.com
2. Registrarse → API Management → crear key con permiso "Trade"
3. En `.env`: `EXCHANGE_ID=bybit`

#### Kraken
1. Cuenta demo: https://demo-futures.kraken.com
2. En `.env`: `EXCHANGE_ID=kraken`

#### OKX
1. Demo: https://www.okx.com/demo-trading
2. En `.env`: `EXCHANGE_ID=okx`

#### Coinbase Advanced
1. Sandbox: https://public.sandbox.exchange.coinbase.com
2. En `.env`: `EXCHANGE_ID=coinbase`

---

### ACCIONES (stocks)

#### Alpaca (recomendado para acciones USA)
1. Crear cuenta gratis: https://alpaca.markets
2. Ir a Paper Trading → generar API keys
3. En `.env`:
```
EXCHANGE_ID=alpaca
API_KEY=tu_key
API_SECRET=tu_secret
```
4. En `config.py`: `SYMBOLS = ["AAPL", "TSLA", "NVDA"]`
5. `SANDBOX = True` usa automáticamente el entorno paper de Alpaca

#### Interactive Brokers
1. Instalar TWS o IB Gateway
2. Activar paper account en: https://www.interactivebrokers.com
3. En `.env`: `EXCHANGE_ID=ibkr`

---

### FOREX

#### OANDA
1. Demo gratuita: https://www.oanda.com/forex-trading/demo
2. En `.env`:
```
EXCHANGE_ID=oanda
API_KEY=tu_token
```
3. `SYMBOLS = ["EUR/USD", "GBP/USD"]`

---

## Compilar a Ejecutable Windows (.exe)

### Un solo .exe (incluye todo)

```bash
cd trading_bot
.\build_single.bat
```

Esto crea: `dist\trading_bot.exe` (~200 MB)

### Usar el ejecutable

1. Ejecutá `trading_bot.exe`
2. Interfaz gráfica con 3 botones:
   - **▶ Start Bot** — inicia el bot de trading
   - **⏹ Stop Bot** — detiene el bot
   - **📊 Open Dashboard** — abre navegador con dashboard
3. Los logs aparecen en la ventana del launcher

---

## Pasar de simulado a dinero real

En `config.py` cambiar solo estas 2 líneas:

```python
PAPER_TRADING = False   # ← era True
SANDBOX       = False   # ← era True
```

> ⚠️ Probá al menos 2 semanas en paper trading antes de pasar a real.

---

## Estructura de archivos

```
trading_bot/
├── main.py              ← punto de entrada, ejecutar esto
├── config.py            ← toda la configuración
├── .env                 ← API keys (no subir a git)
├── .env.example         ← plantilla de .env
├── requirements.txt     ← dependencias Python
├── GUIA.md              ← este archivo
├── core/
│   ├── bot.py           ← loop principal, orquesta todo
│   ├── broker.py        ← PaperBroker (simulado) + LiveBroker (CCXT)
│   ├── data_feed.py     ← descarga OHLCV y precios en tiempo real
│   └── risk_manager.py  ← SL/TP, tamaño de posición, límite de trades
└── analysis/
    ├── technical.py     ← indicadores técnicos → score [-1, 1]
    └── ml_model.py      ← Random Forest: predice dirección + confianza
```

---

## Exchanges compatibles (100+)

binance, bybit, kraken, okx, coinbase, bitfinex, huobi, kucoin, gate,
alpaca, bitmex, deribit, phemex, mexc, bitget, oanda, ibkr, y más.

Ver lista completa: https://github.com/ccxt/ccxt#supported-exchanges

---

## Preguntas frecuentes

**¿Necesito dinero real para probarlo?**
No. Con `PAPER_TRADING = True` opera con $10,000 simulados sin tocar ninguna cuenta.

**¿Funciona 24/7?**
Sí, mientras el proceso esté corriendo. Para dejarlo corriendo en un servidor usar `nohup python main.py &` o un servicio systemd.

**¿Puedo agregar mis propias estrategias?**
Sí, en `analysis/technical.py` modificá la función `compute_signal()`.

**¿Qué pasa si se cae internet?**
El loop captura el error, lo loguea y reintenta en el siguiente ciclo.
