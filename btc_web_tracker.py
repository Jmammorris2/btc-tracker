import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
from sklearn.ensemble import RandomForestClassifier
import numpy as np

st.set_page_config(page_title="🚀 Multi-Asset Day Trader", layout="wide")
st.title("🚀 Multi-Asset Day Trader Dashboard - BTC | EURUSD | Gold")

# ================= PRICE FETCH WITH SAFE FALLBACK =================
@st.cache_data(ttl=20)
def fetch_price(symbol):
    try:
        if symbol == "BTC":
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
            return round(float(data["price"]), 2)
        elif symbol == "EURUSD":
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT", timeout=10).json()
            return round(float(data["price"]), 4)
        elif symbol == "GOLD":
            data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT", timeout=10).json()
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
            url = f"https://api.coingecko.com/api/v3/coins/gold/market_chart?vs_currency=usd&days={days}"
        else:
            return pd.DataFrame()
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df["close"] = pd.to_numeric(df["close"])
        return df
    except:
        return pd.DataFrame()

# ================= SIGNAL ENGINE =================
def get_signal_for_asset(asset, price, bars_df):
    if price is None or bars_df.empty or len(bars_df) < 25:
        return "HOLD", 50, "🟡"
    
    df = bars_df.copy()
    for i in range(1, 12):
        df[f"lag_{i}"] = df["close"].pct_change(i)
    df["vol_8"] = df["close"].rolling(8).std()
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df = df.dropna()
    
    if len(df) < 15:
        return "HOLD", 50, "🟡"
    
    X = df[[f"lag_{i}" for i in range(1,12)] + ["vol_8"]]
    y = df["target"]
    
    model = RandomForestClassifier(n_estimators=150, random_state=42)
    model.fit(X, y)
    prob = model.predict_proba(X.iloc[-1:].values.reshape(1, -1))[0][1]
    
    if prob > 0.67: return "STRONG BUY", round(prob*100, 1), "🟢"
    elif prob > 0.57: return "BUY", round(prob*100, 1), "🟢"
    elif prob < 0.33: return "STRONG SELL", round((1-prob)*100, 1), "🔴"
    elif prob < 0.43: return "SELL", round((1-prob)*100, 1), "🔴"
    else: return "HOLD", round(prob*100, 1), "🟡"

# ================= FUNDED SIMULATOR =================
def funded_simulator(price, signal):
    if price is None:
        return {}
    sizes = [0.1, 0.2, 0.3]
    sims = {}
    for size in sizes:
        if "BUY" in signal:
            entry = price * 0.985
            pnl = (price - entry) * size
            pct = (price / entry - 1) * 100
        else:
            entry = price * 1.015
            pnl = (entry - price) * size
            pct = (entry / price - 1) * 100
        sims[size] = (round(pnl, 2), round(pct, 2))
    return sims

# ================= MAIN DASHBOARD =================
assets = ["BTC", "EURUSD", "GOLD"]
prices = {asset: fetch_price(asset) for asset in assets}
bars = {asset: fetch_historical(asset) for asset in assets}

signals = {}
for asset in assets:
    signals[asset] = get_signal_for_asset(asset, prices[asset], bars[asset])

# Best asset
valid_signals = {a: signals[a] for a in assets if signals[a][1] > 50}
best_asset = max(valid_signals, key=lambda a: valid_signals[a][1]) if valid_signals else "BTC"

st.subheader(f"🔥 BEST MARKET RIGHT NOW: **{best_asset}**")

col1, col2, col3 = st.columns(3)

for col, asset in zip([col1, col2, col3], assets):
    with col:
        price = prices[asset]
        signal, conf, emoji = signals[asset]
        price_display = f"${price:,}" if price and asset != "EURUSD" else f"{price}" if price else "N/A"
        st.metric(f"{asset}", price_display)
        st.markdown(f"**{emoji} {signal}** ({conf}%)")

# Funded Simulator for Best Asset
st.subheader("💰 Funded Account Simulator - Best Signal")
if prices[best_asset]:
    sim = funded_simulator(prices[best_asset], signals[best_asset][0])
    for size in [0.1, 0.2, 0.3]:
        pnl, pct = sim[size]
        if pnl >= 0:
            st.success(f"{best_asset} {size} lot → **${pnl:+.2f}** ({pct:+.2f}%)")
        else:
            st.error(f"{best_asset} {size} lot → **${pnl:+.2f}** ({pct:+.2f}%)")
else:
    st.warning("Waiting for price data...")

st.divider()

st.subheader("📊 All Assets")
for asset in assets:
    signal, conf, emoji = signals[asset]
    price = prices[asset]
    st.write(f"**{asset}** | {price if price else 'N/A'} → {emoji} **{signal}** ({conf}%)")

if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption("Signals combine momentum + volatility. Use the strongest signal for your Alpha Trader funded account.")
