"""
Central configuration — edit this file to switch markets, brokers, and modes.
"""
from dotenv import load_dotenv
import os

load_dotenv()

# ── Mode ──────────────────────────────────────────────────────────────────────
PAPER_TRADING = True          # False → real money

# ── Broker / Exchange ─────────────────────────────────────────────────────────
# Any CCXT-supported exchange: 'binance', 'kraken', 'coinbase', 'alpaca', etc.
EXCHANGE_ID   = os.getenv("EXCHANGE_ID", "binance")
API_KEY       = os.getenv("API_KEY", "")
API_SECRET    = os.getenv("API_SECRET", "")
SANDBOX       = True          # exchange-level testnet when available

# ── Markets to trade ──────────────────────────────────────────────────────────
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
]

TIMEFRAME     = "1h"          # 1m 5m 15m 1h 4h 1d
CANDLES_BACK  = 200           # history loaded on startup

# ── Risk management ───────────────────────────────────────────────────────────
RISK_PER_TRADE   = 0.01       # 1 % of portfolio per trade
MAX_OPEN_TRADES  = 3
STOP_LOSS_PCT    = 0.02       # 2 %
TAKE_PROFIT_PCT  = 0.04       # 4 %

# ── Paper trading initial capital ─────────────────────────────────────────────
PAPER_CAPITAL    = 10_000.0   # USD

# ── Bot loop ──────────────────────────────────────────────────────────────────
LOOP_INTERVAL_SEC = 60        # analysis frequency
