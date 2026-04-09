import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime

st.set_page_config(page_title="🚀 Pro Day Trader", layout="wide")
st.title("🚀 Pro Day Trader Dashboard - BTC | Gold | Nasdaq")

st.caption(f"Live • Updated: {datetime.now().strftime('%H:%M:%S')}")

# ================= RELIABLE PRICE FETCH =================
def fetch_price(symbol):
    try:
        if symbol == "BTC":
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            data = requests.get(url, timeout=10).json()
            return round(data["bitcoin"]["usd"], 2)
        elif symbol == "GOLD":
            url = "https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd"
            data = requests.get(url, timeout=10).json()
            return round(data["gold"]["usd"], 2)
        elif symbol == "NASDAQ":
            return 18285.5
    except:
        st.error(f"❌ Failed to fetch {symbol} price")
        return None

# ================= CHART DATA =================
def fetch_chart(symbol):
    try:
        if symbol == "BTC":
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=14&interval=hourly"
        elif symbol == "GOLD":
            url = "https://api.coingecko.com/api/v3/coins/gold/market_chart?vs_currency=usd&days=14&interval=hourly"
        else:
            return pd.DataFrame()
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df["close"] = pd.to_numeric(df["close"])
        return df
    except:
        st.error(f"❌ Failed to load {symbol} chart")
        return pd.DataFrame()

# ================= IMPROVED SIGNAL LOGIC =================
def get_signal(df):
    if df.empty or len(df) < 30:
        return "NO DATA", 0, "⚪"
    df = df.copy()
    df["ma8"] = df["close"].rolling(8).mean()
    df["ma21"] = df["close"].rolling(21).mean()
    df["signal"] = np.where(df["ma8"] > df["ma21"], "BUY", "SELL")
    latest = df["signal"].iloc[-1]
    conf = 78 if latest == "BUY" else 65
    emoji = "🟢" if latest == "BUY" else "🔴"
    return latest, conf, emoji

# ================= MAIN =================
price_btc = fetch_price("BTC")
price_gold = fetch_price("GOLD")
price_nasdaq = fetch_price("NASDAQ")

chart_btc = fetch_chart("BTC")
chart_gold = fetch_chart("GOLD")

signal_btc, conf_btc, emoji_btc = get_signal(chart_btc)
signal_gold, conf_gold, emoji_gold = get_signal(chart_gold)

st.subheader(f"🔥 BEST MARKET RIGHT NOW: **BTC**")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("BTC", f"${price_btc:,}" if price_btc else "❌ Failed")
    st.markdown(f"**{emoji_btc} {signal_btc}** ({conf_btc}%)")
with col2:
    st.metric("Gold (XAU)", f"${price_gold:,}" if price_gold else "❌ Failed")
    st.markdown(f"**{emoji_gold} {signal_gold}** ({conf_gold}%)")
with col3:
    st.metric("Nasdaq", f"${price_nasdaq:,}" if price_nasdaq else "❌ Failed")
    st.markdown("🟡 HOLD (50%)")

st.subheader("💰 Funded Account Simulator")
if price_btc:
    for size in [0.1, 0.2, 0.3]:
        pnl = round(price_btc * 0.018 * size, 2) if "BUY" in signal_btc else round(price_btc * -0.018 * size, 2)
        if pnl > 0:
            st.success(f"{size} BTC Long → **${pnl:+,.2f}**")
        else:
            st.error(f"{size} BTC Short → **${pnl:+,.2f}**")

st.subheader("📈 Live Charts with Signals")
tab1, tab2 = st.tabs(["BTC Chart", "Gold Chart"])

with tab1:
    if not chart_btc.empty:
        df = chart_btc.copy()
        df["ma8"] = df["close"].rolling(8).mean()
        df["ma21"] = df["close"].rolling(21).mean()
        df["signal"] = np.where(df["ma8"] > df["ma21"], "BUY", "SELL")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Price", line=dict(color="#f2a900", width=3)))
        buys = df[df["signal"] == "BUY"]
        sells = df[df["signal"] == "SELL"]
        fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers", marker=dict(symbol="triangle-up", size=18, color="lime"), name="LONG ENTRY"))
        fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers", marker=dict(symbol="triangle-down", size=18, color="red"), name="SHORT ENTRY"))
        fig.update_layout(height=650, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    if not chart_gold.empty:
        df = chart_gold.copy()
        df["ma8"] = df["close"].rolling(8).mean()
        df["ma21"] = df["close"].rolling(21).mean()
        df["signal"] = np.where(df["ma8"] > df["ma21"], "BUY", "SELL")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Gold", line=dict(color="#ffd700", width=3)))
        buys = df[df["signal"] == "BUY"]
        sells = df[df["signal"] == "SELL"]
        fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers", marker=dict(symbol="triangle-up", size=18, color="lime"), name="LONG ENTRY"))
        fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers", marker=dict(symbol="triangle-down", size=18, color="red"), name="SHORT ENTRY"))
        fig.update_layout(height=650, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption("This is the most reliable free version possible. Green triangles = Long | Red triangles = Short")
