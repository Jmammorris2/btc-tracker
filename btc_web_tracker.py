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

st.set_page_config(page_title="🚀 BTC Tracker", layout="wide")
st.title("🚀 Bitcoin Live Tracker + Polymarket + Self-Fixing AI")

LOG_FILE = "btc_polymarket_log.csv"
MODEL_FILE = "btc_predictor_model.pkl"

# ================= PRICE & HISTORY =================
@st.cache_data(ttl=30)
def fetch_btc_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        data = requests.get(url, timeout=10).json()
        price = data["bitcoin"]["usd"]
        change = data["bitcoin"].get("usd_24h_change", 0)
        return round(price, 2), round(change, 2)
    except:
        return None, None

@st.cache_data(ttl=300)
def fetch_historical_bars(days=40):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=minute"
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df["return_5min"] = df["close"].pct_change(5)
        return df.dropna()
    except:
        return pd.DataFrame()

# ================= POLYMARKET =================
@st.cache_data(ttl=60)
def fetch_polymarket_btc_markets():
    markets = []
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "closed": "false", "limit": 200, "order": "volume", "ascending": "false"},
            timeout=15
        )
        data = resp.json()
        for m in data if isinstance(data, list) else data.get("markets", []):
            q = (m.get("question") or m.get("title", "")).lower()
            if "bitcoin" in q or "btc" in q:
                try:
                    prob = round(float(m.get("outcomePrices", [0.5])[0]) * 100, 1)
                except:
                    prob = 50.0
                markets.append({
                    "title": m.get("question") or m.get("title", "BTC Market"),
                    "implied_prob_%": prob,
                    "volume": int(float(m.get("volume", 0) or 0))
                })
        return sorted(markets, key=lambda x: x["volume"], reverse=True)[:15]
    except:
        return []

# ================= AI FUNCTIONS =================
def prepare_features(df, avg_prob=50):
    df = df.copy()
    for i in range(1, 11):
        df[f"lag_{i}"] = df["close"].pct_change(i)
    df["vol_5"] = df["close"].rolling(5).std()
    df["crowd_sentiment"] = avg_prob / 100
    df["target_5min"] = (df["close"].shift(-5) > df["close"]).astype(int)
    return df.dropna()

def train_or_load_model(bars_df, markets):
    if bars_df.empty or len(bars_df) < 80:
        return None, None
    avg_prob = np.mean([m["implied_prob_%"] for m in markets]) if markets else 50
    feats = prepare_features(bars_df, avg_prob)
    X = feats[[f"lag_{i}" for i in range(1,11)] + ["vol_5", "crowd_sentiment"]]
    y = feats["target_5min"]
    
    model = RandomForestClassifier(n_estimators=150, random_state=42)
    model.fit(X, y)
    acc = accuracy_score(y, model.predict(X))
    joblib.dump(model, MODEL_FILE)
    return model, round(acc * 100, 1)

def predict_future(model, bars_df, markets):
    if not model or bars_df.empty: 
        return None
    avg_prob = np.mean([m["implied_prob_%"] for m in markets]) if markets else 50
    latest = prepare_features(bars_df, avg_prob).iloc[-1:]
    X = latest[[f"lag_{i}" for i in range(1,11)] + ["vol_5", "crowd_sentiment"]]
    prob = model.predict_proba(X)[0][1]
    return {
        "5min_up_%": round(prob * 100, 1), 
        "direction": "🟢 UP" if prob > 0.5 else "🔴 DOWN"
    }

def log_data(price, change, markets, pred):
    row = {"timestamp": datetime.now().isoformat(), "btc_price": price, "change_pct": change}
    if pred:
        row["ai_5min"] = pred["5min_up_%"]
    pd.DataFrame([row]).to_csv(LOG_FILE, mode="a", header=not os.path.exists(LOG_FILE), index=False)

# ================= MAIN DASHBOARD =================
price, change = fetch_btc_price()
col1, col2, col3 = st.columns([2, 1.4, 1])

with col1:
    if price:
        st.metric("Current BTC Price", f"${price:,}", f"{change:+.2f}% 24h")
    else:
        st.error("Price fetch failed - try Refresh")

polymarket_markets = fetch_polymarket_btc_markets()
bars_df = fetch_historical_bars()
model, accuracy = train_or_load_model(bars_df, polymarket_markets)

with col2:
    st.subheader("📊 Polymarket Crowd")
    if polymarket_markets:
        for m in polymarket_markets:
            st.write(f"• {m['title'][:68]:68} → **{m['implied_prob_%']}%**")
    else:
        st.write("No active BTC markets right now")

with col3:
    st.subheader("🤖 AI 5-min Prediction")
    if model:
        pred = predict_future(model, bars_df, polymarket_markets)
        if pred:
            st.success(f"**Next 5 min: {pred['direction']}** ({pred['5min_up_%']}%)")
            st.caption(f"Model Accuracy: **{accuracy}%**")
    else:
        st.info("Collecting more data...")

st.subheader("📈 BTC Price Chart")
if not bars_df.empty:
    fig = go.Figure(go.Scatter(x=bars_df.index[-500:], y=bars_df["close"][-500:], line=dict(color="#f2a900")))
    fig.update_layout(height=500, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

if st.button("🔄 Refresh Now (Live Data + Retrain AI)"):
    pred = predict_future(model, bars_df, polymarket_markets) if model else None
    log_data(price, change, polymarket_markets, pred)
    st.rerun()

st.caption("✅ No API key needed • Data updates on Refresh")
