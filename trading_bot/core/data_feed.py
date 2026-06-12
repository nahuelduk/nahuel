"""
Market data fetcher — OHLCV candles + live ticker via CCXT.
"""
import ccxt
import pandas as pd
import logging
import config

log = logging.getLogger(__name__)


class DataFeed:
    def __init__(self):
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange = exchange_class({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        if config.SANDBOX and hasattr(self.exchange, "set_sandbox_mode"):
            self.exchange.set_sandbox_mode(True)

    def fetch_ohlcv(self, symbol: str, timeframe: str = config.TIMEFRAME,
                    limit: int = config.CANDLES_BACK) -> pd.DataFrame:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df.astype(float)
        except ccxt.BaseError as e:
            log.error("fetch_ohlcv %s: %s", symbol, e)
            return pd.DataFrame()

    def fetch_ticker(self, symbol: str) -> dict:
        try:
            return self.exchange.fetch_ticker(symbol)
        except ccxt.BaseError as e:
            log.error("fetch_ticker %s: %s", symbol, e)
            return {}

    def fetch_prices(self, symbols: list[str]) -> dict:
        prices = {}
        for s in symbols:
            t = self.fetch_ticker(s)
            if t:
                prices[s] = t.get("last", 0)
        return prices
