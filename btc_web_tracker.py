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
st.title("🚀 BTC Day Trader Dashboard - Long & Short Mock Swings + Funded Account Simulator")

LOG_FILE = "btc_daytrader_log.csv"
MODEL_FILE = "btc_daytrader_model.pkl"

# ================= ROBUST PRICE FETCH =================
@st.cache_data(ttl=20)
def fetch_btc_price():
    try:
        data = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=8).json()
        return round(float(data["price"]), 2), None
    except:
        try:
            data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true", timeout=8).json()
            price = data["bitcoin"]["usd"]
            change = data["bitcoin"].get("usd_24h_change", 0)
            return round(price, 2), round(change, 2)
        except:
            return 0, 0

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

# ================= POLYMARKET & AI =================
@st.cache_data(ttl=60)
def fetch_polymarket_btc_markets():
    markets = []
    try:
        resp = requests.get("https://gamma-api.polymarket.com/markets", 
                           params={"active":"true","closed":"false","limit":200,"order":"volume","ascending":"false"}, timeout=15)
        data = resp.json()
        for m in data if isinstance(data, list) else data.get("markets", []):
            q = (m.get("question") or m.get("title", "")).lower()
            if "bitcoin" in q or "btc" in q:
                try:
                    prob = round(float(m.get("outcomePrices", [0.5])[0]) * 100, 1)
                except:
                    prob = 50.0
                markets.append({"title": m.get("question") or "BTC Market", "implied_prob_%": prob})
        return sorted(markets, key=lambda x: x["implied_prob_%"], reverse=True)[:10]
    except:
        return []

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
    
    if prob > 0.68: return "STRONG BUY", round(prob*100, 1), "🟢"
    elif prob > 0.58: return "BUY", round(prob*100, 1), "🟢"
    elif prob < 0.32: return "STRONG SELL", round((1-prob)*100, 1), "🔴"
    elif prob < 0.42: return "SELL", round((1-prob)*100, 1), "🔴"
    else: return "HOLD", round(prob*100, 1), "🟡"

# ================= FUNDED ACCOUNT SIMULATOR (0.1 / 0.2 / 0.3 BTC) =================
def funded_simulator(current_price):
    sizes = [0.1, 0.2, 0.3]
    results = {}
    for size in sizes:
        # Long
        long_entry = current_price * 0.985
        long_pnl = (current_price - long_entry) * size
        long_pnl_pct = (current_price / long_entry - 1) * 100
        
        # Short
        short_entry = current_price * 1.015
        short_pnl = (short_entry - current_price) * size
        short_pnl_pct = (short_entry / current_price - 1) * 100
        
        results[size] = {
            "long_pnl": round(long_pnl, 2),
            "long_pnl_pct": round(long_pnl_pct, 2),
            "short_pnl": round(short_pnl, 2),
            "short_pnl_pct": round(short_pnl_pct, 2)
        }
    return results

# ================= MAIN DASHBOARD =================
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

signal, confidence, emoji = get_signal(model, bars_df, polymarket_markets)

st.subheader("📢 CURRENT SIGNAL")
st.markdown(f"### {emoji} **{signal}** — Confidence **{confidence}%**")

# ================= FUNDED ACCOUNT SIMULATOR =================
if price > 0:
    sim = funded_simulator(price)
    
    st.subheader("💰 Funded Account Simulator (Clear Long & Short)")
    st.caption("Shows exact $ profit/loss if you placed 0.1 / 0.2 / 0.3 BTC right now")

    for size in [0.1, 0.2, 0.3]:
        col_l, col_s = st.columns(2)
        with col_l:
            st.markdown(f"**Long {size} BTC**")
            st.success(f"P&L: **${sim[size]['long_pnl']:+,.2f}**  ({sim[size]['long_pnl_pct']:+.2f}%)")
        with col_s:
            st.markdown(f"**Short {size} BTC**")
            st.error(f"P&L: **${sim[size]['short_pnl']:+,.2f}**  ({sim[size]['short_pnl_pct']:+.2f}%)")
        st.divider()

# Polymarket + Outlook
st.subheader("📊 Polymarket Crowd Wisdom")
if polymarket_markets:
    for m in polymarket_markets:
        st.write(f"• {m['title'][:65]:65} → **{m['implied_prob_%']}%**")

if st.button("🔄 Refresh Now (New Signal + Live P&L Simulator)"):
    st.rerun()

st.caption("This simulator assumes you entered at a realistic slippage (1.5%). Use the 0.1–0.3 BTC sizes to match your funded account risk.")
