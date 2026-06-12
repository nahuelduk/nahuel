"""
Technical indicators computed with pandas-ta — all on a single DataFrame.
"""
import pandas as pd
import pandas_ta as ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 50:
        return df

    df = df.copy()

    # Trend
    df.ta.ema(length=20,  append=True)
    df.ta.ema(length=50,  append=True)
    df.ta.ema(length=200, append=True)

    # Momentum
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)

    # Volatility
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)

    # Volume
    df.ta.obv(append=True)
    df.ta.vwap(append=True)

    df.dropna(inplace=True)
    return df


def compute_signal(df: pd.DataFrame) -> float:
    """
    Returns a score in [-1, 1]:
      > 0.5  → strong buy
      < -0.5 → strong sell
      else   → hold
    """
    if df.empty:
        return 0.0

    last = df.iloc[-1]
    score = 0.0
    weight = 0.0

    # EMA trend
    if "EMA_20" in last.index and "EMA_50" in last.index:
        score  += 0.3 if last["EMA_20"] > last["EMA_50"] else -0.3
        weight += 0.3

    # RSI
    if "RSI_14" in last.index:
        rsi = last["RSI_14"]
        if rsi < 30:
            score += 0.4
        elif rsi > 70:
            score -= 0.4
        else:
            score += (50 - rsi) / 50 * 0.2
        weight += 0.4

    # MACD histogram
    if "MACDh_12_26_9" in last.index:
        hist = last["MACDh_12_26_9"]
        prev_hist = df.iloc[-2]["MACDh_12_26_9"] if len(df) > 1 else hist
        if hist > 0 and hist > prev_hist:
            score += 0.2
        elif hist < 0 and hist < prev_hist:
            score -= 0.2
        weight += 0.2

    # Bollinger Bands
    if all(k in last.index for k in ["BBL_20_2.0", "BBU_20_2.0"]):
        close = last["close"]
        if close < last["BBL_20_2.0"]:
            score += 0.1
        elif close > last["BBU_20_2.0"]:
            score -= 0.1
        weight += 0.1

    return round(score / weight if weight else 0.0, 4)
