"""
Main trading bot — orchestrates data → analysis → decision → execution loop.
"""
import time
import logging
import colorlog
import config
from core.broker      import get_broker
from core.data_feed   import DataFeed
from core.risk_manager import RiskManager
from analysis.technical import add_indicators, compute_signal
from analysis.ml_model  import MLPredictor


def setup_logging():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        log_colors={"DEBUG": "cyan", "INFO": "green", "WARNING": "yellow",
                    "ERROR": "red", "CRITICAL": "bold_red"},
    ))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


class TradingBot:
    def __init__(self):
        self.broker  = get_broker()
        self.feed    = DataFeed()
        self.risk    = RiskManager(self.broker)
        self.models  = {s: MLPredictor() for s in config.SYMBOLS}
        self.log     = logging.getLogger(__name__)
        self._initial_train()

    def _initial_train(self):
        self.log.info("Downloading historical data and training models…")
        for symbol in config.SYMBOLS:
            df = self.feed.fetch_ohlcv(symbol)
            if not df.empty:
                df = add_indicators(df)
                self.models[symbol].train(df)

    # ── Core loop ─────────────────────────────────────────────────────────────

    def tick(self):
        prices = self.feed.fetch_prices(config.SYMBOLS)
        if not prices:
            self.log.warning("No price data received — skipping tick")
            return

        # Update paper portfolio prices
        if hasattr(self.broker, "update_prices"):
            self.broker.update_prices(prices)

        # Check exits first
        if hasattr(self.broker, "portfolio"):
            exits = self.risk.check_exits(self.broker.portfolio.positions, prices)
            for ex in exits:
                symbol = ex["symbol"]
                pos    = self.broker.portfolio.positions[symbol]
                self.broker.place_order(symbol, "sell", pos["amount"], prices[symbol])
                self.log.info("EXIT %s — reason: %s", symbol, ex["reason"])

        # Analyse each symbol
        for symbol in config.SYMBOLS:
            if symbol in (self.broker.portfolio.positions if hasattr(self.broker, "portfolio") else {}):
                continue  # already holding, wait for exit signal

            df = self.feed.fetch_ohlcv(symbol, limit=config.CANDLES_BACK)
            if df.empty:
                continue
            df = add_indicators(df)

            tech_score = compute_signal(df)
            ml_dir     = self.models[symbol].predict(df)
            ml_conf    = self.models[symbol].confidence(df)

            # Combine: tech_score weighted 60%, ML 40%
            combined = tech_score * 0.6 + (ml_dir * ml_conf) * 0.4
            price    = prices.get(symbol, 0)

            self.log.info(
                "%s | price=%.4f | tech=%.3f | ml=%+d(%.0f%%) | combined=%.3f",
                symbol, price, tech_score, ml_dir, ml_conf * 100, combined,
            )

            if combined > 0.5 and self.risk.can_open() and price > 0:
                capital = (self.broker.portfolio.cash
                           if hasattr(self.broker, "portfolio")
                           else 10_000)
                size = self.risk.position_size(price, capital)
                if size > 0:
                    self.broker.place_order(symbol, "buy", size, price)
                    self.log.info("ENTRY BUY %s  size=%.6f @ $%.4f", symbol, size, price)

        # Retrain ML model every 24 ticks (~24 h on 1h TF)
        if not hasattr(self, "_tick_count"):
            self._tick_count = 0
        self._tick_count += 1
        if self._tick_count % 24 == 0:
            self._initial_train()

        # Portfolio summary
        if hasattr(self.broker, "portfolio"):
            p = self.broker.portfolio
            self.log.info("Portfolio — cash: $%.2f | total: $%.2f | positions: %d",
                          p.cash, p.total_value, len(p.positions))

    def run(self):
        mode = "PAPER" if config.PAPER_TRADING else "LIVE"
        self.log.info("=" * 60)
        self.log.info("Trading Bot started — mode: %s | symbols: %s", mode, config.SYMBOLS)
        self.log.info("Loop interval: %ds | timeframe: %s", config.LOOP_INTERVAL_SEC, config.TIMEFRAME)
        self.log.info("=" * 60)
        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                self.log.info("Bot stopped by user.")
                break
            except Exception as e:
                self.log.error("Tick error: %s", e, exc_info=True)
            time.sleep(config.LOOP_INTERVAL_SEC)
