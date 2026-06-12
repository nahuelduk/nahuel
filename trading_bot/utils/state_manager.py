"""
Persistent state — bot saves portfolio, trades, signals to JSON.
Dashboard reads this to display in real-time.
"""
import json
import os
from pathlib import Path
from datetime import datetime

STATE_FILE = Path(__file__).parent.parent / "bot_state.json"


def init_state():
    if not STATE_FILE.exists():
        save_state({
            "portfolio": {"cash": 10000, "positions": {}, "total_value": 10000},
            "trades": [],
            "signals": [],
            "last_update": datetime.now().isoformat(),
        })


def save_state(state: dict):
    state["last_update"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def load_state() -> dict:
    if not STATE_FILE.exists():
        init_state()
    with open(STATE_FILE) as f:
        return json.load(f)


def update_portfolio(cash: float, positions: dict, prices: dict):
    state = load_state()
    total = cash + sum(pos["amount"] * prices.get(sym, pos.get("last_price", 0))
                       for sym, pos in positions.items())
    state["portfolio"] = {
        "cash": round(cash, 2),
        "positions": {k: {**v, "last_price": prices.get(k, v.get("last_price", 0))}
                      for k, v in positions.items()},
        "total_value": round(total, 2),
    }
    save_state(state)


def add_trade(symbol: str, side: str, amount: float, price: float, reason: str = ""):
    state = load_state()
    state["trades"].append({
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "side": side,
        "amount": round(amount, 6),
        "price": round(price, 4),
        "reason": reason,
    })
    state["trades"] = state["trades"][-100:]  # keep last 100
    save_state(state)


def add_signal(symbol: str, tech_score: float, ml_dir: int, ml_conf: float, combined: float):
    state = load_state()
    state["signals"].append({
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "tech_score": round(tech_score, 4),
        "ml_direction": ml_dir,
        "ml_confidence": round(ml_conf, 4),
        "combined_score": round(combined, 4),
    })
    state["signals"] = state["signals"][-1000:]  # keep last 1000
    save_state(state)
