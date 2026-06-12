"""
Broker abstraction: same interface for paper trading and live exchanges (CCXT).
"""
import ccxt
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
import config

log = logging.getLogger(__name__)


@dataclass
class Order:
    symbol: str
    side: str       # 'buy' | 'sell'
    amount: float
    price: float
    order_type: str = "market"
    id: str = ""
    status: str = "open"


@dataclass
class Portfolio:
    cash: float = config.PAPER_CAPITAL
    positions: dict = field(default_factory=dict)   # symbol → {amount, avg_price}

    @property
    def total_value(self) -> float:
        return self.cash + sum(
            v["amount"] * v["last_price"] for v in self.positions.values()
        )


class PaperBroker:
    """Simulated broker — no network calls, instant fills at market price."""

    def __init__(self):
        self.portfolio = Portfolio()
        self.orders: list[Order] = []
        log.info("Paper broker initialised — capital: $%.2f", self.portfolio.cash)

    def get_balance(self) -> Portfolio:
        return self.portfolio

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Order:
        order = Order(symbol=symbol, side=side, amount=amount, price=price,
                      id=f"paper-{int(time.time()*1000)}", status="filled")
        cost = amount * price
        if side == "buy":
            if cost > self.portfolio.cash:
                log.warning("Insufficient funds: need $%.2f, have $%.2f", cost, self.portfolio.cash)
                order.status = "rejected"
                return order
            self.portfolio.cash -= cost
            pos = self.portfolio.positions.get(symbol, {"amount": 0, "avg_price": 0, "last_price": price})
            total = pos["amount"] + amount
            pos["avg_price"] = (pos["amount"] * pos["avg_price"] + cost) / total
            pos["amount"] = total
            pos["last_price"] = price
            self.portfolio.positions[symbol] = pos
        else:
            pos = self.portfolio.positions.get(symbol)
            if not pos or pos["amount"] < amount:
                log.warning("Not enough %s to sell", symbol)
                order.status = "rejected"
                return order
            self.portfolio.cash += amount * price
            pos["amount"] -= amount
            if pos["amount"] < 1e-8:
                del self.portfolio.positions[symbol]
        self.orders.append(order)
        log.info("[PAPER] %s %s %.6f @ $%.4f", side.upper(), symbol, amount, price)
        return order

    def update_prices(self, prices: dict):
        for symbol, price in prices.items():
            if symbol in self.portfolio.positions:
                self.portfolio.positions[symbol]["last_price"] = price


class LiveBroker:
    """Live broker via CCXT — supports 100+ exchanges."""

    def __init__(self):
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange = exchange_class({
            "apiKey": config.API_KEY,
            "secret": config.API_SECRET,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
        if config.SANDBOX and hasattr(self.exchange, "set_sandbox_mode"):
            self.exchange.set_sandbox_mode(True)
        log.info("Live broker: %s (sandbox=%s)", config.EXCHANGE_ID, config.SANDBOX)

    def get_balance(self):
        return self.exchange.fetch_balance()

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Order:
        try:
            raw = self.exchange.create_order(symbol, "market", side, amount)
            return Order(symbol=symbol, side=side, amount=amount, price=price,
                         id=raw["id"], status=raw.get("status", "open"))
        except ccxt.BaseError as e:
            log.error("Order failed: %s", e)
            return Order(symbol=symbol, side=side, amount=amount, price=price, status="error")


def get_broker():
    return PaperBroker() if config.PAPER_TRADING else LiveBroker()
