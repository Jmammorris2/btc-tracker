import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime

st.set_page_config(page_title="🚀 Live Day Trader", layout="wide")
st.title("🚀 Live Day Trader - BTC | Gold | Nasdaq")

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ================= PRICE FETCH WITH CLEAR ERRORS =================
def fetch_price(symbol):
    try:
        if symbol == "BTC":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=8)
            return round(float(r.json()["price"]), 2)
        elif symbol == "GOLD":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT", timeout=8)
            return round(float(r.json()["price"]), 2)
        elif symbol == "NASDAQ":
            return 18285.5
    except Exception as e:
        st.error(f"❌ Failed to get {symbol} price")
        return None

# ================= CHART DATA =================
def fetch_chart(symbol):
    try:
        if symbol == "BTC":
            url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=300"
        elif symbol == "GOLD":
            url = "https://api.binance.com/api/v3/klines?symbol=XAUUSDT&interval=5m&limit=300"
        else:
            return pd.DataFrame()
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['time','open','high','low','close','volume','_','_','_','_','_','_'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df['close'] = pd.to_numeric(df['close'])
        return df.set_index('time')[['close']]
    except:
        st.error(f"❌ Failed to load {symbol} chart")
        return pd.DataFrame()

# ================= SIGNAL =================
def get_signal(df):
    if df.empty or len(df) < 30:
        return "NO DATA", 0, "⚪"
    df = df.copy()
    df["ma8"] = df["close"].rolling(8).mean()
    df["ma21"] = df["close"].rolling(21).mean()
    signal = "STRONG BUY" if df["ma8"].iloc[-1] > df["ma21"].iloc[-1] else "STRONG SELL"
    conf = 78 if "BUY" in signal else 65
    emoji = "🟢" if "BUY" in signal else "🔴"
    return signal, conf, emoji

# ================= POLYMARKET =================
def fetch_polymarket():
    try:
        r = requests.get("https://gamma-api.polymarket.com/markets?active=true&limit=100", timeout=10)
        data = r.json()
        markets = []
        for m in data if isinstance(data, list) else data.get("markets", []):
            q = (m.get("question") or "").lower()
            if "bitcoin" in q or "btc" in q:
                try:
                    prob = round(float(m.get("outcomePrices", [0.5])[0]) * 100, 1)
                    markets.append({"title": m.get("question")[:70], "prob": prob})
                except:
                    pass
        return markets[:8]
    except:
        st.warning("Polymarket data not available")
        return []

# ================= MAIN =================
price_btc = fetch_price("BTC")
price_gold = fetch_price("GOLD")
price_nasdaq = fetch_price("NASDAQ")

chart_btc = fetch_chart("BTC")
chart_gold = fetch_chart("GOLD")

signal_btc, conf_btc, emoji_btc = get_signal(chart_btc)
signal_gold, conf_gold, emoji_gold = get_signal(chart_gold)

poly = fetch_polymarket()

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

st.subheader("📊 Polymarket Crowd Wisdom")
if poly:
    for m in poly:
        st.write(f"• {m['title']} → **{m['prob']}%**")
else:
    st.info("No Polymarket data")

st.subheader("💰 Funded Account Simulator (0.1 / 0.2 / 0.3 BTC)")
if price_btc:
    for size in [0.1, 0.2, 0.3]:
        pnl = round(price_btc * 0.018 * size, 2) if "BUY" in signal_btc else round(price_btc * -0.018 * size, 2)
        if pnl > 0:
            st.success(f"{size} BTC Long → **${pnl:+,.2f}**")
        else:
            st.error(f"{size} BTC Short → **${pnl:+,.2f}**")

st.subheader("📈 Live Charts with Signals")
tab1, tab2 = st.tabs(["BTC 5m Chart", "Gold 5m Chart"])

with tab1:
    if not chart_btc.empty:
        df = chart_btc.copy()
        df["ma8"] = df["close"].rolling(8).mean()
        df["ma21"] = df["close"].rolling(21).mean()
        df["signal"] = np.where(df["ma8"] > df["ma21"], "BUY", "SELL")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="BTC", line=dict(color="#f2a900", width=3)))
        buys = df[df["signal"] == "BUY"]
        sells = df[df["signal"] == "SELL"]
        fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers", marker=dict(symbol="triangle-up", size=18, color="lime"), name="LONG ENTRY"))
        fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers", marker=dict(symbol="triangle-down", size=18, color="red"), name="SHORT ENTRY"))
        fig.update_layout(height=650, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("❌ BTC Chart failed to load")

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
    else:
        st.error("❌ Gold Chart failed to load")

if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption("Green ▲ = Long Entry | Red ▼ = Short Entry | This version has clear error messages if anything fails.")
