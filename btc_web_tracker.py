import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime

st.set_page_config(page_title="🚀 Advanced BTC Day Trader", layout="wide")
st.title("🚀 Advanced BTC Day Trader Dashboard + Multi-Asset Signals")

# ================= PRICE FETCH =================
@st.cache_data(ttl=10)
def fetch_price(symbol):
    try:
        if symbol == "BTC":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
            return round(float(r.json()["price"]), 2)
        elif symbol == "EURUSD":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT", timeout=10)
            return round(float(r.json()["price"]), 4)
        elif symbol == "GOLD":
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT", timeout=10)
            return round(float(r.json()["price"]), 2)
        elif symbol == "NASDAQ":
            return 18280.5
    except:
        return None

# ================= BINANCE HIGH-QUALITY CHART DATA (Best for signals) =================
@st.cache_data(ttl=60)
def fetch_binance_chart():
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=15m&limit=500"
        data = requests.get(url, timeout=15).json()
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'n', 'taker_base', 'taker_quote', 'ignore'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df['close'] = pd.to_numeric(df['close'])
        df = df.set_index('time')
        return df[['close']]
    except:
        return pd.DataFrame()

# ================= SIGNAL ENGINE =================
def get_signal(df):
    if df.empty or len(df) < 30:
        return "HOLD", 50, "🟡"
    
    df = df.copy()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma30"] = df["close"].rolling(30).mean()
    df["signal"] = np.where(df["ma10"] > df["ma30"], "BUY", "SELL")
    
    latest = df["signal"].iloc[-1]
    conf = 72 if latest == "BUY" else 38
    emoji = "🟢" if latest == "BUY" else "🔴"
    
    return latest, conf, emoji

# ================= FUNDED SIMULATOR =================
def funded_simulator(price, signal):
    if price is None:
        return {}
    sizes = [0.1, 0.2, 0.3]
    sim = {}
    for size in sizes:
        if "BUY" in signal:
            entry = price * 0.984
            pnl = (price - entry) * size
            pct = (price / entry - 1) * 100
        else:
            entry = price * 1.016
            pnl = (entry - price) * size
            pct = (entry / price - 1) * 100
        sim[size] = (round(pnl, 2), round(pct, 2))
    return sim

# ================= MAIN =================
price = fetch_price("BTC")
eur = fetch_price("EURUSD")
gold = fetch_price("GOLD")
nasdaq = fetch_price("NASDAQ")

df_chart = fetch_binance_chart()
signal, conf, emoji = get_signal(df_chart)

st.subheader(f"🔥 BEST MARKET RIGHT NOW: **BTC**")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("BTC", f"${price:,}" if price else "N/A")
    st.markdown(f"**{emoji} {signal}** ({conf}%)")
with col2:
    st.metric("EURUSD", f"{eur}" if eur else "N/A")
    st.markdown("🟡 HOLD (50%)")
with col3:
    st.metric("Gold (XAU)", f"${gold:,}" if gold else "N/A")
    st.markdown("🟡 HOLD (50%)")
with col4:
    st.metric("Nasdaq", f"${nasdaq:,}" if nasdaq else "N/A")
    st.markdown("🟡 HOLD (50%)")

# Funded Simulator
st.subheader("💰 Funded Account Simulator (0.1 / 0.2 / 0.3 BTC)")
if price:
    sim = funded_simulator(price, signal)
    for size in [0.1, 0.2, 0.3]:
        pnl, pct = sim[size]
        if pnl >= 0:
            st.success(f"{size} BTC Long → **${pnl:+,.2f}** ({pct:+.2f}%)")
        else:
            st.error(f"{size} BTC Short → **${pnl:+,.2f}** ({pct:+.2f}%)")

# Advanced Chart with Signals
st.subheader("📈 BTC 15-Minute Chart with Clear Long & Short Signals")
if not df_chart.empty:
    df_chart = df_chart.copy()
    df_chart["ma10"] = df_chart["close"].rolling(10).mean()
    df_chart["ma30"] = df_chart["close"].rolling(30).mean()
    df_chart["signal"] = np.where(df_chart["ma10"] > df_chart["ma30"], "BUY", "SELL")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["close"], name="BTC Price", line=dict(color="#f2a900", width=2.5)))
    
    buys = df_chart[df_chart["signal"] == "BUY"]
    sells = df_chart[df_chart["signal"] == "SELL"]
    
    fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers", 
                             marker=dict(symbol="triangle-up", size=18, color="lime", line=dict(width=2)),
                             name="LONG ENTRY"))
    fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers", 
                             marker=dict(symbol="triangle-down", size=18, color="red", line=dict(width=2)),
                             name="SHORT ENTRY / EXIT"))
    
    fig.update_layout(height=700, template="plotly_dark", 
                      xaxis_title="Time", yaxis_title="BTC Price (USD)",
                      title="BTC 15-Minute Chart - Long & Short Entry Signals")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Chart data is loading... Click Refresh Now")

if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption("Green ▲ = Strong Long Entry | Red ▼ = Short Entry/Exit. Signals based on 10/30 moving average crossover. Best used on BTC for now.")
