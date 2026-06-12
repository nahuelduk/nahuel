"""
Risk manager — position sizing, stop-loss, take-profit enforcement.
"""
import logging
import config

log = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, broker):
        self.broker = broker

    def position_size(self, price: float, capital: float) -> float:
        """Kelly-lite: risk N% of capital, capped by max open trades."""
        risk_usd  = capital * config.RISK_PER_TRADE
        size = risk_usd / (price * config.STOP_LOSS_PCT)
        return round(size, 6)

    def open_trades_count(self) -> int:
        if hasattr(self.broker, "portfolio"):
            return len(self.broker.portfolio.positions)
        return 0

    def can_open(self) -> bool:
        return self.open_trades_count() < config.MAX_OPEN_TRADES

    def stop_loss_price(self, entry: float, side: str) -> float:
        return entry * (1 - config.STOP_LOSS_PCT) if side == "buy" else entry * (1 + config.STOP_LOSS_PCT)

    def take_profit_price(self, entry: float, side: str) -> float:
        return entry * (1 + config.TAKE_PROFIT_PCT) if side == "buy" else entry * (1 - config.TAKE_PROFIT_PCT)

    def check_exits(self, positions: dict, prices: dict) -> list[dict]:
        """Return list of {symbol, reason} that should be closed."""
        exits = []
        for symbol, pos in positions.items():
            price = prices.get(symbol, 0)
            if not price:
                continue
            sl = self.stop_loss_price(pos["avg_price"], "buy")
            tp = self.take_profit_price(pos["avg_price"], "buy")
            if price <= sl:
                exits.append({"symbol": symbol, "reason": "stop_loss"})
            elif price >= tp:
                exits.append({"symbol": symbol, "reason": "take_profit"})
        return exits
