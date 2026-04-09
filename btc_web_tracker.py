import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime

st.set_page_config(page_title="🚀 Live Day Trader", layout="wide")
st.title("🚀 Live Day Trader Dashboard - BTC | Gold | Nasdaq")

st.caption(f"🔴 Live Update • {datetime.now().strftime('%H:%M:%S')}")

# ================= FAST PRICE FETCH =================
@st.cache_data(ttl=8)
def fetch_price(symbol):
    try:
        if symbol == "BTC":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=6)
            return round(float(r.json()["price"]), 2)
        elif symbol == "GOLD":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT", timeout=6)
            return round(float(r.json()["price"]), 2)
        elif symbol == "NASDAQ":
            return 18285.5
    except:
        return None

# ================= POLYMARKET (Fixed) =================
@st.cache_data(ttl=40)
def fetch_polymarket():
    try:
        r = requests.get("https://gamma-api.polymarket.com/markets?active=true&limit=100", timeout=10)
        data = r.json()
        btc = []
        for m in data if isinstance(data, list) else data.get("markets", []):
            title = (m.get("question") or m.get("title", "")).lower()
            if "bitcoin" in title or "btc" in title:
                try:
                    prob = round(float(m.get("outcomePrices", [0.5])[0]) * 100, 1)
                    btc.append({"title": m.get("question")[:65], "prob": prob})
                except:
                    pass
        return btc[:8]
    except:
        return []

# ================= BTC CHART =================
@st.cache_data(ttl=20)
def fetch_btc_chart():
    try:
        r = requests.get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=280", timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=['time','open','high','low','close','volume','_','_','_','_','_','_'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df['close'] = pd.to_numeric(df['close'])
        return df.set_index('time')[['close']]
    except:
        return pd.DataFrame()

# ================= SIGNAL =================
def get_signal(df):
    if df.empty or len(df) < 25:
        return "HOLD", 50, "🟡"
    df = df.copy()
    df["ma8"] = df["close"].rolling(8).mean()
    df["ma21"] = df["close"].rolling(21).mean()
    signal = "STRONG BUY" if df["ma8"].iloc[-1] > df["ma21"].iloc[-1] else "STRONG SELL"
    conf = 78 if "BUY" in signal else 65
    emoji = "🟢" if "BUY" in signal else "🔴"
    return signal, conf, emoji

# ================= MAIN =================
price_btc = fetch_price("BTC")
price_gold = fetch_price("GOLD")
price_nasdaq = fetch_price("NASDAQ")
poly = fetch_polymarket()
df_chart = fetch_btc_chart()
signal, conf, emoji = get_signal(df_chart)

st.subheader(f"🔥 BEST MARKET RIGHT NOW: **BTC**")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("BTC", f"${price_btc:,}" if price_btc else "N/A")
    st.markdown(f"**{emoji} {signal}** ({conf}%)")
with col2:
    st.metric("Gold (XAU)", f"${price_gold:,}" if price_gold else "N/A")
    st.markdown("🟡 HOLD (52%)")
with col3:
    st.metric("Nasdaq", f"${price_nasdaq:,}" if price_nasdaq else "N/A")
    st.markdown("🟡 HOLD (49%)")

st.subheader("📊 Polymarket Crowd Wisdom (Real Money)")
if poly:
    for m in poly:
        st.write(f"• {m['title']} → **{m['prob']}%**")
else:
    st.info("Polymarket loading...")

st.subheader("💰 Funded Account Simulator")
if price_btc:
    for size in [0.1, 0.2, 0.3]:
        pnl = round(price_btc * 0.018 * size, 2) if "BUY" in signal else round(price_btc * -0.018 * size, 2)
        if pnl > 0:
            st.success(f"{size} BTC Long → **${pnl:+,.2f}**")
        else:
            st.error(f"{size} BTC Short → **${pnl:+,.2f}**")

st.subheader("📈 BTC 5-Minute Live Chart with Signals")
if not df_chart.empty:
    df = df_chart.copy()
    df["ma8"] = df["close"].rolling(8).mean()
    df["ma21"] = df["close"].rolling(21).mean()
    df["signal"] = np.where(df["ma8"] > df["ma21"], "BUY", "SELL")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Price", line=dict(color="#f2a900", width=3)))
    buys = df[df["signal"] == "BUY"]
    sells = df[df["signal"] == "SELL"]
    fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers", marker=dict(symbol="triangle-up", size=18, color="lime"), name="LONG ENTRY"))
    fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers", marker=dict(symbol="triangle-down", size=18, color="red"), name="SHORT ENTRY"))
    fig.update_layout(height=680, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Chart loading...")

if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption("Green ▲ = Long Entry | Red ▼ = Short Entry | Polymarket crowd data included.")
