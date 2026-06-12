"""
Technical indicators computed with ta library — all on a single DataFrame.
"""
import pandas as pd
import ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 50:
        return df

    df = df.copy()

    # Trend
    df["EMA_20"] = ta.trend.ema_indicator(df["close"], window=20)
    df["EMA_50"] = ta.trend.ema_indicator(df["close"], window=50)
    df["EMA_200"] = ta.trend.ema_indicator(df["close"], window=200)

    # Momentum
    df["RSI_14"] = ta.momentum.rsi(df["close"], window=14)
    macd = ta.trend.macd(df["close"], window_fast=12, window_slow=26, window_sign=9)
    df["MACD"] = macd
    df["MACD_signal"] = ta.trend.macd_signal(df["close"], window_fast=12, window_slow=26, window_sign=9)
    df["MACDh_12_26_9"] = macd - df["MACD_signal"]

    # Volatility
    bb = ta.volatility.bollinger_bands(df["close"], window=20, window_dev=2)
    df["BBU_20_2.0"] = bb.iloc[:, 0]
    df["BBM_20_2.0"] = bb.iloc[:, 1]
    df["BBL_20_2.0"] = bb.iloc[:, 2]
    df["ATR_14"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    df["ATRr_14"] = df["ATR_14"] / df["close"]

    # Volume
    df["OBV"] = ta.volume.on_balance_volume(df["close"], df["volume"])
    df["VWAP"] = ta.volume.volume_weighted_average_price(df["high"], df["low"], df["close"], df["volume"])

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
