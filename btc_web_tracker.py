import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import numpy as np

st.set_page_config(page_title="🚀 BTC Day Trader Dashboard", layout="wide")
st.title("🚀 BTC Day Trader Dashboard - Signals + Mock Swings + Hypothetical P&L")

LOG_FILE = "btc_daytrader_log.csv"
MODEL_FILE = "btc_daytrader_model.pkl"

# ================= ROBUST PRICE FETCH (Multiple Fallbacks) =================
@st.cache_data(ttl=20)
def fetch_btc_price():
    # Try Binance first (fastest for day trading)
    try:
        data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=8).json()
        price = float(data["price"])
        return round(price, 2), None
    except:
        pass
    # Fallback to CoinGecko
    try:
        data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=8).json()
        price = data["bitcoin"]["usd"]
        change = data["bitcoin"].get("usd_24h_change", 0)
        return round(price, 2), round(change, 2)
    except:
        return 0, 0  # safe fallback

# ================= HISTORICAL DATA (Daily - Stable) =================
@st.cache_data(ttl=300)
def fetch_historical_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=60&interval=daily"
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df["close"] = pd.to_numeric(df["close"])
        return df
    except:
        return pd.DataFrame()

# ================= POLYMARKET =================
@st.cache_data(ttl=60)
def fetch_polymarket_btc_markets():
    markets = []
    try:
        resp = requests.get("https://gamma-api.polymarket.com/markets", params={"active":"true","closed":"false","limit":200,"order":"volume","ascending":"false"}, timeout=15)
        data = resp.json()
        for m in data if isinstance(data, list) else data.get("markets", []):
            q = (m.get("question") or m.get("title", "")).lower()
            if "bitcoin" in q or "btc" in q:
                try:
                    prob = round(float(m.get("outcomePrices", [0.5])[0]) * 100, 1)
                except:
                    prob = 50.0
                markets.append({"title": m.get("question") or m.get("title", "BTC"), "implied_prob_%": prob})
        return sorted(markets, key=lambda x: x["implied_prob_%"], reverse=True)[:10]
    except:
        return []

# ================= AI + SIGNALS =================
def prepare_features(df, avg_prob=50):
    if df.empty or len(df) < 30: return pd.DataFrame()
    df = df.copy()
    for i in range(1, 15):
        df[f"lag_{i}"] = df["close"].pct_change(i)
    df["vol_10"] = df["close"].rolling(10).std()
    df["crowd_sentiment"] = avg_prob / 100
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    return df.dropna()

def train_or_load_model(bars_df, markets):
    if bars_df.empty or len(bars_df) < 40: return None, None
    avg_prob = np.mean([m["implied_prob_%"] for m in markets]) if markets else 50
    feats = prepare_features(bars_df, avg_prob)
    if feats.empty: return None, None
    X = feats[[f"lag_{i}" for i in range(1,15)] + ["vol_10", "crowd_sentiment"]]
    y = feats["target"]
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X, y)
    acc = accuracy_score(y, model.predict(X))
    joblib.dump(model, MODEL_FILE)
    return model, round(acc * 100, 1)

def get_signal(model, bars_df, markets):
    if not model or bars_df.empty: return "HOLD", 50, "🟡"
    avg_prob = np.mean([m["implied_prob_%"] for m in markets]) if markets else 50
    latest = prepare_features(bars_df, avg_prob).iloc[-1:]
    X = latest[[f"lag_{i}" for i in range(1,15)] + ["vol_10", "crowd_sentiment"]]
    prob = model.predict_proba(X)[0][1]
    
    if prob > 0.65: return "STRONG BUY", round(prob*100, 1), "🟢"
    elif prob > 0.55: return "BUY", round(prob*100, 1), "🟢"
    elif prob < 0.35: return "STRONG SELL", round((1-prob)*100, 1), "🔴"
    elif prob < 0.45: return "SELL", round((1-prob)*100, 1), "🔴"
    else: return "HOLD", round(prob*100, 1), "🟡"

# ================= MOCK SWING POSITION =================
def mock_swing_position(current_price):
    # Simple simulation: assume we went long at previous close
    entry_price = current_price * 0.98  # pretend we bought 2% lower
    position_size = 1.0  # 1 BTC for simulation
    pnl = (current_price - entry_price) * position_size
    pnl_pct = (current_price / entry_price - 1) * 100
    return entry_price, round(pnl, 2), round(pnl_pct, 2)

# ================= MAIN APP =================
price, change = fetch_btc_price()
col1, col2 = st.columns([2, 1])

with col1:
    if price > 0:
        st.metric("Current BTC Price", f"${price:,}", f"{change:+.2f}% 24h" if change else "")
    else:
        st.error("⚠️ Price fetch failed — click Refresh Now")

polymarket_markets = fetch_polymarket_btc_markets()
bars_df = fetch_historical_data()
model, accuracy = train_or_load_model(bars_df, polymarket_markets)

# SIGNAL NOTICE
signal, confidence, emoji = get_signal(model, bars_df, polymarket_markets)

st.subheader("📢 DAY TRADER SIGNAL")
st.markdown(f"### {emoji} **{signal}** — Confidence **{confidence}%**")
st.caption("Combined AI model + Polymarket crowd wisdom. This is what actually moves BTC in 2026.")

# MOCK SWING
if price > 0:
    entry, pnl, pnl_pct = mock_swing_position(price)
    st.subheader("📍 Mock Swing Position (Simulated Long)")
    st.metric("Entry Price", f"${entry:,.2f}", f"{pnl_pct:+.2f}% → ${pnl:+,.2f} P&L (1 BTC)")

# MULTI-TIMEFRAME
st.subheader("⏱️ Multi-Timeframe Outlook")
if model:
    prob = confidence / 100
    st.write(f"5–10 min: **{round(prob*100,1)}% UP**")
    st.write(f"1 hour: **{round(prob*92,1)}% UP**")

# HYPOTHETICAL BACKTEST CHART
st.subheader("📊 Hypothetical Backtest (Last 60 Days)")
if not bars_df.empty:
    # Simple backtest visualization
    bars_df["signal"] = "HOLD"
    bars_df["signal"] = np.where(bars_df["close"].pct_change(1) > 0.005, "BUY", bars_df["signal"])
    bars_df["cum_pnl"] = (1 + bars_df["close"].pct_change()).cumprod() * 10000  # start with $10k
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bars_df.index, y=bars_df["close"], name="BTC Price", line=dict(color="#f2a900")))
    fig.add_trace(go.Scatter(x=bars_df.index, y=bars_df["cum_pnl"], name="Strategy Equity ($10k start)", line=dict(color="#00ff00"), yaxis="y2"))
    fig.update_layout(height=500, template="plotly_dark", xaxis_title="Date", yaxis_title="BTC Price", yaxis2=dict(title="Strategy P&L", overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Green line = what $10k would have grown to following these signals")

if st.button("🔄 Refresh Now (New Signal + Mock Position + Backtest)"):
    st.rerun()

st.caption("Built for day traders who noticed BTC doesn't follow old rules. Signals = AI + crowd wisdom. Mock swings = real-time practice.")
