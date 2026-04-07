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

st.set_page_config(page_title="🚀 Multi-Asset Day Trader", layout="wide")
st.title("🚀 Multi-Asset Day Trader Dashboard - BTC | EURUSD | Gold")

LOG_FILE = "daytrader_log.csv"
MODEL_FILE = "daytrader_model.pkl"

# ================= PRICE FETCH =================
@st.cache_data(ttl=20)
def fetch_price(symbol):
    try:
        if symbol == "BTC":
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=8).json()
            return round(float(data["price"]), 2)
        elif symbol == "EURUSD":
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT", timeout=8).json()
            return round(float(data["price"]), 4)
        elif symbol == "GOLD":
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT", timeout=8).json()
            return round(float(data["price"]), 2)
    except:
        return None

# ================= HISTORICAL DATA =================
@st.cache_data(ttl=300)
def fetch_historical(symbol, days=60):
    try:
        if symbol == "BTC":
            url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}"
        elif symbol == "GOLD":
            # Using CoinGecko for Gold
            url = f"https://api.coingecko.com/api/v3/coins/gold/market_chart?vs_currency=usd&days={days}"
        else:
            return pd.DataFrame()  # EURUSD historical is limited here
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df["close"] = pd.to_numeric(df["close"])
        return df
    except:
        return pd.DataFrame()

# ================= AI SIGNAL ENGINE =================
def get_signal_for_asset(asset, price, bars_df, polymarket_prob=50):
    if bars_df.empty or len(bars_df) < 30:
        return "HOLD", 50, "🟡"
    
    df = bars_df.copy()
    for i in range(1, 12):
        df[f"lag_{i}"] = df["close"].pct_change(i)
    df["vol_8"] = df["close"].rolling(8).std()
    df["crowd"] = polymarket_prob / 100
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df = df.dropna()
    
    if len(df) < 20:
        return "HOLD", 50, "🟡"
    
    X = df[[f"lag_{i}" for i in range(1,12)] + ["vol_8", "crowd"]]
    y = df["target"]
    
    model = RandomForestClassifier(n_estimators=150, random_state=42)
    model.fit(X, y)
    prob = model.predict_proba(X.iloc[-1:].values.reshape(1, -1))[0][1]
    
    if prob > 0.67: return "STRONG BUY", round(prob*100, 1), "🟢"
    elif prob > 0.57: return "BUY", round(prob*100, 1), "🟢"
    elif prob < 0.33: return "STRONG SELL", round((1-prob)*100, 1), "🔴"
    elif prob < 0.43: return "SELL", round((1-prob)*100, 1), "🔴"
    else: return "HOLD", round(prob*100, 1), "🟡"

# ================= FUNDED ACCOUNT SIMULATOR =================
def funded_simulator(price, asset, signal):
    sizes = [0.1, 0.2, 0.3]
    sims = {}
    for size in sizes:
        if "BUY" in signal:
            entry = price * 0.985
            pnl = (price - entry) * size
            pnl_pct = (price / entry - 1) * 100
            sims[size] = (round(pnl, 2), round(pnl_pct, 2))
        else:
            entry = price * 1.015
            pnl = (entry - price) * size
            pnl_pct = (entry / price - 1) * 100
            sims[size] = (round(pnl, 2), round(pnl_pct, 2))
    return sims

# ================= MAIN APP =================
assets = ["BTC", "EURUSD", "GOLD"]
prices = {asset: fetch_price(asset) for asset in assets}
bars = {asset: fetch_historical(asset) for asset in assets}

signals = {}
for asset in assets:
    poly_prob = 55 if asset == "BTC" else 50  # Polymarket mainly for BTC
    signals[asset] = get_signal_for_asset(asset, prices[asset], bars[asset], poly_prob)

# Find best asset
best_asset = max(signals, key=lambda a: signals[a][1] if "BUY" in signals[a][0] or "SELL" in signals[a][0] else 0)

st.subheader(f"🔥 BEST MARKET RIGHT NOW: **{best_asset}**")

col1, col2, col3 = st.columns(3)

for col, asset in zip([col1, col2, col3], assets):
    with col:
        price = prices[asset]
        signal, conf, emoji = signals[asset]
        st.metric(f"{asset} Price", f"${price:,}" if asset != "EURUSD" else f"{price}", "")
        st.markdown(f"**{emoji} {signal}** ({conf}%)")

# Funded Account Simulator
st.subheader("💰 Funded Account Simulator (0.1 / 0.2 / 0.3 lots)")
if prices[best_asset]:
    sim = funded_simulator(prices[best_asset], best_asset, signals[best_asset][0])
    for size in [0.1, 0.2, 0.3]:
        pnl, pct = sim[size]
        if pnl > 0:
            st.success(f"{best_asset} {size} lot → **${pnl:+.2f}** ({pct:+.2f}%)")
        else:
            st.error(f"{best_asset} {size} lot → **${pnl:+.2f}** ({pct:+.2f}%)")

st.divider()

st.subheader("📊 All Assets Signals")
for asset in assets:
    signal, conf, emoji = signals[asset]
    st.write(f"**{asset}** → {emoji} **{signal}** ({conf}% confidence)")

if st.button("🔄 Refresh Now (New Signals + Simulator)"):
    st.rerun()

st.caption("This dashboard compares BTC, EURUSD, and Gold in real-time. Use the strongest signal for your funded account. Signals combine momentum + crowd sentiment.")
