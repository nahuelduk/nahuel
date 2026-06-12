"""
Real-time trading dashboard with Streamlit.
Run: streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
from utils.state_manager import load_state

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide")
st.title("🤖 AI Trading Bot Dashboard")

col1, col2, col3 = st.columns(3)

try:
    state = load_state()
except FileNotFoundError:
    st.error("❌ Bot state not found. Start the bot first: `python main.py`")
    st.stop()

# ── Portfolio Stats ───────────────────────────────────────────────────────────

portfolio = state.get("portfolio", {})
with col1:
    st.metric("💰 Cash", f"${portfolio.get('cash', 0):.2f}")
with col2:
    st.metric("📊 Total Value", f"${portfolio.get('total_value', 0):.2f}")
with col3:
    positions = portfolio.get("positions", {})
    st.metric("📈 Open Positions", len(positions))

# ── Positions ─────────────────────────────────────────────────────────────────

if positions:
    st.subheader("Open Positions")
    pos_data = []
    for symbol, pos in positions.items():
        pos_data.append({
            "Symbol": symbol,
            "Amount": f"{pos['amount']:.6f}",
            "Avg Price": f"${pos['avg_price']:.4f}",
            "Last Price": f"${pos['last_price']:.4f}",
            "P&L %": f"{((pos['last_price'] - pos['avg_price']) / pos['avg_price'] * 100):.2f}%",
        })
    st.dataframe(pd.DataFrame(pos_data), use_container_width=True)

# ── Recent Trades ─────────────────────────────────────────────────────────────

trades = state.get("trades", [])
if trades:
    st.subheader("Recent Trades")
    trades_df = pd.DataFrame(trades[-20:])
    trades_df["timestamp"] = pd.to_datetime(trades_df["timestamp"]).dt.strftime("%H:%M:%S")
    trades_df["price"] = trades_df["price"].apply(lambda x: f"${x:.4f}")
    trades_df["amount"] = trades_df["amount"].apply(lambda x: f"{x:.6f}")
    st.dataframe(
        trades_df[["timestamp", "symbol", "side", "amount", "price", "reason"]],
        use_container_width=True,
    )

# ── Recent Signals ────────────────────────────────────────────────────────────

signals = state.get("signals", [])
if signals:
    st.subheader("Recent Signals")
    signals_df = pd.DataFrame(signals[-30:])
    signals_df["timestamp"] = pd.to_datetime(signals_df["timestamp"]).dt.strftime("%H:%M:%S")
    signals_df["tech_score"] = signals_df["tech_score"].round(3)
    signals_df["combined_score"] = signals_df["combined_score"].round(3)
    st.dataframe(
        signals_df[["timestamp", "symbol", "tech_score", "ml_direction", "combined_score"]],
        use_container_width=True,
    )

# ── Signal Chart ──────────────────────────────────────────────────────────────

if len(signals) > 10:
    st.subheader("Combined Score Over Time")
    signals_chart = pd.DataFrame(signals[-100:])
    signals_chart["timestamp"] = pd.to_datetime(signals_chart["timestamp"])

    fig = go.Figure()
    for symbol in signals_chart["symbol"].unique():
        symbol_data = signals_chart[signals_chart["symbol"] == symbol].sort_values("timestamp")
        fig.add_trace(go.Scatter(
            x=symbol_data["timestamp"],
            y=symbol_data["combined_score"],
            mode="lines+markers",
            name=symbol,
        ))

    fig.add_hline(y=0.5, line_dash="dash", line_color="green", annotation_text="Buy threshold")
    fig.add_hline(y=-0.5, line_dash="dash", line_color="red", annotation_text="Sell threshold")
    fig.update_layout(
        title="Combined Score (Tech 60% + ML 40%)",
        yaxis_title="Score",
        hovermode="x unified",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Last Update ───────────────────────────────────────────────────────────────

last_update = state.get("last_update", "Never")
st.divider()
st.caption(f"Last update: {last_update}")

# Auto-refresh
st.info("📡 Dashboard auto-refreshes every 5 seconds")
import time
time.sleep(5)
st.rerun()
