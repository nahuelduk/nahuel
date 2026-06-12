"""
Lightweight ML layer — Random Forest trained on rolling window, predicts
next-candle direction (1=up, -1=down, 0=neutral).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import logging

log = logging.getLogger(__name__)

FEATURES = [
    "RSI_14", "MACDh_12_26_9", "ATRr_14",
    "EMA_20", "EMA_50",
    "close_pct", "volume_pct",
]


class MLPredictor:
    def __init__(self):
        self.model  = RandomForestClassifier(n_estimators=100, max_depth=6,
                                              random_state=42, n_jobs=-1)
        self.scaler = StandardScaler()
        self.trained = False

    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame | None:
        df = df.copy()
        df["close_pct"]  = df["close"].pct_change()
        df["volume_pct"] = df["volume"].pct_change()
        df["ATRr_14"] = df.get("ATRr_14", df["ATR_14"] if "ATR_14" in df.columns else 0)
        available = [f for f in FEATURES if f in df.columns]
        if len(available) < 3:
            return None
        return df[available].dropna()

    def train(self, df: pd.DataFrame) -> bool:
        feat = self._build_features(df)
        if feat is None or len(feat) < 60:
            return False
        X = feat.iloc[:-1].values
        y = np.sign(df["close"].pct_change().shift(-1).loc[feat.index].iloc[:-1].values)
        y = np.where(np.abs(y) < 0.001, 0, y).astype(int)
        try:
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.trained = True
            log.info("ML model trained on %d samples", len(X))
            return True
        except Exception as e:
            log.error("ML training failed: %s", e)
            return False

    def predict(self, df: pd.DataFrame) -> int:
        if not self.trained:
            return 0
        feat = self._build_features(df)
        if feat is None or feat.empty:
            return 0
        try:
            X = self.scaler.transform(feat.iloc[[-1]].values)
            return int(self.model.predict(X)[0])
        except Exception:
            return 0

    def confidence(self, df: pd.DataFrame) -> float:
        if not self.trained:
            return 0.0
        feat = self._build_features(df)
        if feat is None or feat.empty:
            return 0.0
        try:
            X = self.scaler.transform(feat.iloc[[-1]].values)
            proba = self.model.predict_proba(X)[0]
            return float(max(proba))
        except Exception:
            return 0.0
