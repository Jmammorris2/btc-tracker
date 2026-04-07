import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import numpy as np

st.set_page_config(page_title="🚀 BTC Tracker", layout="wide")
st.title("🚀 Bitcoin Live Tracker + Polymarket + Self-Fixing AI")

LOG_FILE = "btc_polymarket_log.csv"
MODEL_FILE = "btc_predictor_model.pkl"

# ================= PRICE & HISTORY (No API Key) =================
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

# ================= AI MODEL =================
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
    X = feats[[f"lag_{i}" for i in range(
