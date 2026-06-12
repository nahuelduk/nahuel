"""
Technical indicators — pure pandas implementation.
"""
import pandas as pd
import numpy as np


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 50:
        return df

    df = df.copy()

    # EMA
    df["EMA_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["close"].ewm(span=200, adjust=False).mean()

    # RSI
    df["RSI_14"] = compute_rsi(df["close"], 14)

    # MACD
    macd_line, signal_line = compute_macd(df["close"], 12, 26, 9)
    df["MACD"] = macd_line
    df["MACD_signal"] = signal_line
    df["MACDh_12_26_9"] = macd_line - signal_line

    # Bollinger Bands
    bb_middle = df["close"].rolling(window=20).mean()
    bb_std = df["close"].rolling(window=20).std()
    df["BBM_20_2.0"] = bb_middle
    df["BBU_20_2.0"] = bb_middle + (bb_std * 2)
    df["BBL_20_2.0"] = bb_middle - (bb_std * 2)

    # ATR
    df["ATR_14"] = compute_atr(df["high"], df["low"], df["close"], 14)
    df["ATRr_14"] = df["ATR_14"] / df["close"]

    # OBV
    df["OBV"] = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()

    # VWAP
    df["VWAP"] = (df["close"] * df["volume"]).rolling(window=20).sum() / df["volume"].rolling(window=20).sum()

    df.dropna(inplace=True)
    return df


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


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
