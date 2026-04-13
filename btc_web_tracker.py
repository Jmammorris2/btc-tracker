import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json, math

st.set_page_config(
    page_title="Alpha Trader Pro",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-title { font-family: 'Space Mono', monospace; font-size: 2rem; font-weight: 700;
              background: linear-gradient(90deg, #00ff88, #00d4ff); -webkit-background-clip: text;
              -webkit-text-fill-color: transparent; margin-bottom: 0; }
.signal-badge { display:inline-block; border-radius:4px; padding:2px 10px; font-size:11px; font-weight:700; letter-spacing:.05em; }
.sig-buy  { background:#00ff8822; color:#00ff88; border:1px solid #00ff8855; }
.sig-sell { background:#ff444422; color:#ff4444; border:1px solid #ff444455; }
.sig-hold { background:#88888822; color:#aaa; border:1px solid #88888855; }
.note-card { border-radius:8px; padding:12px 16px; margin-bottom:8px; font-size:13px; line-height:1.6; }
.note-watch { background:#1a1400; border-left:3px solid #f0a500; color:#ffd166; }
.note-buy   { background:#001a0a; border-left:3px solid #00ff88; color:#88ffcc; }
.note-sell  { background:#1a0000; border-left:3px solid #ff4444; color:#ff9999; }
.note-info  { background:#001020; border-left:3px solid #00d4ff; color:#88ddff; }
.trader-box { background:#0d0d1a; border:1px solid #1a1a3a; border-radius:12px; padding:16px; margin-bottom:12px; }
.metric-box { background:#111127; border:1px solid #1e1e3a; border-radius:8px; padding:12px; text-align:center; }
.metric-val { font-family:'Space Mono',monospace; font-size:1.3rem; font-weight:700; }
.metric-lbl { font-size:10px; color:#666; text-transform:uppercase; letter-spacing:.08em; margin-top:2px; }
.pos-long  { background:#001a0a; border-left:3px solid #00ff88; border-radius:8px; padding:10px 14px; font-size:12px; }
.pos-short { background:#1a0000; border-left:3px solid #ff4444; border-radius:8px; padding:10px 14px; font-size:12px; }
.pos-none  { background:#111; border-radius:8px; padding:10px 14px; font-size:12px; color:#555; }
.bt-stat   { background:#0a0a1a; border:1px solid #1a1a2e; border-radius:8px; padding:10px; text-align:center; }
.bt-val    { font-family:'Space Mono',monospace; font-size:1.1rem; font-weight:700; }
.bt-lbl    { font-size:10px; color:#555; margin-top:2px; }
.stTabs [data-baseweb="tab-list"] { background:#080818; border-radius:10px; padding:4px; }
.stTabs [data-baseweb="tab"] { border-radius:8px; color:#666; font-size:13px; }
.stTabs [aria-selected="true"] { background:#1a1a3a; color:#fff; }
</style>
""", unsafe_allow_html=True)

# ─── KEY GATE ───────────────────────────────────────────────────────────────
def get_keys():
    p = st.secrets.get("POLYGON_KEY","") if hasattr(st,"secrets") else ""
    a = st.secrets.get("ANTHROPIC_KEY","") if hasattr(st,"secrets") else ""
    return st.session_state.get("POLYGON_KEY",p), st.session_state.get("ANTHROPIC_KEY",a)

POLYGON_KEY, ANTHROPIC_KEY = get_keys()

if not POLYGON_KEY:
    st.markdown('<div class="main-title">⚡ Alpha Trader Pro</div>', unsafe_allow_html=True)
    st.markdown("### Setup — Enter your API keys")
    with st.form("keys"):
        pk = st.text_input("Polygon.io API Key (free at polygon.io)", type="password")
        ak = st.text_input("Anthropic API Key (for AI notes — optional)", type="password")
        if st.form_submit_button("Launch App"):
            if pk:
                st.session_state["POLYGON_KEY"] = pk
                st.session_state["ANTHROPIC_KEY"] = ak
                st.rerun()
            else:
                st.error("Polygon key required.")
    st.info("Add keys to `.streamlit/secrets.toml` to skip this screen. See README.")
    st.stop()

# ─── SESSION STATE ────────────────────────────────────────────────────────────
def make_trader(name, emoji, style, desc, risk, rr, filters, sources):
    return dict(name=name, emoji=emoji, style=style, desc=desc,
                risk_pct=risk, rr=rr, signal_filters=filters, data_sources=sources,
                balance=25000.0, peak=25000.0, trades=[], open_pos=None,
                history=[25000.0], win_streak=0, loss_streak=0)

if "traders" not in st.session_state:
    st.session_state["traders"] = [
        make_trader("Macro Maya", "🌍", "Multi-source macro + technicals",
            "Waits for RSI, MACD, MA, Bollinger AND volume all aligned. Also checks fear/greed index and on-chain data for BTC.",
            0.008, 2.5,
            {"rsi_range":(35,65), "need_macd":True, "need_ma":True, "need_vol":True, "strong_only":True},
            ["price","volume","rsi","macd","bb","fear_greed","on_chain"]),
        make_trader("Momentum Mike", "🚀", "Momentum + breakout specialist",
            "Trades breakouts above Bollinger upper band or below lower. Uses ATR for stop sizing. Loves volatility.",
            0.015, 2.0,
            {"rsi_range":(20,80), "need_macd":False, "need_ma":True, "need_vol":False, "strong_only":False, "bb_break":True},
            ["price","rsi","macd","bb","atr","volume"]),
        make_trader("Scalp Sam", "⚡", "Fast RSI + VWAP scalper",
            "Uses tight stops, high frequency. Enters on RSI extremes confirmed by VWAP position. Small risk, many trades.",
            0.005, 1.5,
            {"rsi_range":(25,75), "need_macd":False, "need_ma":False, "need_vol":False, "strong_only":False, "rsi_extreme":True},
            ["price","rsi","vwap","stoch","cci"]),
    ]

if "notes" not in st.session_state:
    st.session_state["notes"] = []
if "last_ai" not in st.session_state:
    st.session_state["last_ai"] = 0.0
if "bt_results" not in st.session_state:
    st.session_state["bt_results"] = {}

TRADERS = st.session_state["traders"]

MARKETS = {
    "BTC":  {"label":"BTC / USD",    "poly_ticker":"X:BTCUSD", "cg_id":"bitcoin",    "stop_mult":0.025, "crypto":True,  "lot":1.0,   "color":"#f0a500"},
    "ETH":  {"label":"ETH / USD",    "poly_ticker":"X:ETHUSD", "cg_id":"ethereum",   "stop_mult":0.030, "crypto":True,  "lot":1.0,   "color":"#627eea"},
    "NQ":   {"label":"NASDAQ (QQQ)", "poly_ticker":"QQQ",      "cg_id":None,         "stop_mult":0.010, "crypto":False, "lot":100.0, "color":"#378add"},
    "GOLD": {"label":"Gold (GLD)",   "poly_ticker":"GLD",      "cg_id":None,         "stop_mult":0.008, "crypto":False, "lot":100.0, "color":"#ba7517"},
    "SPY":  {"label":"S&P 500 (SPY)","poly_ticker":"SPY",      "cg_id":None,         "stop_mult":0.008, "crypto":False, "lot":100.0, "color":"#22c55e"},
}

# ─── DATA FETCHERS ────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_cg_chart(cg_id, days=90):
    try:
        d = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily", timeout=15).json()
        prices  = [p[1] for p in d["prices"]]
        volumes = [v[1] for v in d.get("total_volumes", [])]
        dates   = [pd.Timestamp(p[0], unit="ms") for p in d["prices"]]
        return pd.DataFrame({"close": prices, "volume": volumes}, index=dates)
    except Exception as e:
        st.warning(f"CoinGecko error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_polygon_ohlcv(ticker, poly_key, days=90):
    try:
        to_d  = datetime.today().strftime("%Y-%m-%d")
        fr_d  = (datetime.today()-timedelta(days=days)).strftime("%Y-%m-%d")
        url   = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
                 f"{fr_d}/{to_d}?adjusted=true&sort=asc&limit={days}&apiKey={poly_key}")
        d = requests.get(url, timeout=15).json()
        if "results" not in d or len(d["results"]) < 5:
            return pd.DataFrame()
        rows = d["results"]
        df = pd.DataFrame(rows)
        df.index = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})
        return df[["open","high","low","close","volume"]]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d = requests.get("https://api.alternative.me/fng/?limit=10", timeout=10).json()
        data = d.get("data", [])
        return {
            "value": int(data[0]["value"]),
            "label": data[0]["value_classification"],
            "history": [int(x["value"]) for x in data[:10]],
        }
    except:
        return {"value": 50, "label": "Neutral", "history": [50]*10}

@st.cache_data(ttl=600)
def fetch_on_chain():
    """Fetch BTC on-chain metrics from public APIs."""
    result = {}
    try:
        r = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin", timeout=10).json()
        md = r.get("market_data", {})
        result["market_cap"]       = md.get("market_cap", {}).get("usd", 0)
        result["volume_24h"]       = md.get("total_volume", {}).get("usd", 0)
        result["price_change_7d"]  = md.get("price_change_percentage_7d", 0)
        result["price_change_30d"] = md.get("price_change_percentage_30d", 0)
        result["ath"]              = md.get("ath", {}).get("usd", 0)
        result["ath_change_pct"]   = md.get("ath_change_percentage", {}).get("usd", 0)
        result["circulating"]      = md.get("circulating_supply", 0)
        result["dev_score"]        = r.get("developer_score", 0)
        result["community_score"]  = r.get("community_score", 0)
    except:
        pass
    return result

@st.cache_data(ttl=120)
def fetch_polygon_snapshot(ticker, poly_key):
    try:
        url = (f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
               f"/{ticker}?apiKey={poly_key}")
        return requests.get(url, timeout=10).json().get("ticker", {})
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_polygon_rsi(ticker, poly_key):
    try:
        url = (f"https://api.polygon.io/v1/indicators/rsi/{ticker}"
               f"?timespan=hour&window=14&series_type=close&order=desc&limit=5&apiKey={poly_key}")
        d = requests.get(url, timeout=10).json()
        vals = d.get("results", {}).get("values", [])
        return [v["value"] for v in vals] if vals else []
    except:
        return []

@st.cache_data(ttl=60)
def fetch_polygon_macd(ticker, poly_key):
    try:
        url = (f"https://api.polygon.io/v1/indicators/macd/{ticker}"
               f"?timespan=day&short_window=12&long_window=26&signal_window=9"
               f"&series_type=close&order=desc&limit=5&apiKey={poly_key}")
        d = requests.get(url, timeout=10).json()
        vals = d.get("results", {}).get("values", [])
        return vals if vals else []
    except:
        return []

@st.cache_data(ttl=60)
def fetch_polygon_ema(ticker, poly_key, window=20):
    try:
        url = (f"https://api.polygon.io/v1/indicators/ema/{ticker}"
               f"?timespan=day&window={window}&series_type=close&order=desc&limit=5&apiKey={poly_key}")
        d = requests.get(url, timeout=10).json()
        vals = d.get("results", {}).get("values", [])
        return [v["value"] for v in vals] if vals else []
    except:
        return []

# ─── INDICATORS ───────────────────────────────────────────────────────────────
def add_indicators(df):
    if df.empty or len(df) < 26:
        return df
    df = df.copy()
    closes = df["close"].values

    # MAs
    df["ema8"]  = df["close"].ewm(span=8,  adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["sma200"]= df["close"].rolling(200).mean()

    # MACD
    e12 = df["close"].ewm(span=12, adjust=False).mean()
    e26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]        = e12 - e26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # RSI
    delta = df["close"].diff()
    gain  = delta.where(delta>0, 0.0).rolling(14).mean()
    loss  = (-delta.where(delta<0, 0.0)).rolling(14).mean().replace(0, 1e-10)
    df["rsi"] = 100 - (100/(1+gain/loss))

    # Bollinger
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2*df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2*df["bb_std"]
    df["bb_pct"]   = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # ATR
    if "high" in df.columns and "low" in df.columns:
        hl   = df["high"] - df["low"]
        hc   = (df["high"] - df["close"].shift()).abs()
        lc   = (df["low"]  - df["close"].shift()).abs()
        df["atr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    else:
        df["atr"] = df["close"] * 0.02

    # Stochastic
    lo14 = df["close"].rolling(14).min()
    hi14 = df["close"].rolling(14).max()
    df["stoch_k"] = 100 * (df["close"] - lo14) / (hi14 - lo14 + 1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # CCI
    if "high" in df.columns and "low" in df.columns:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        df["cci"] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std() + 1e-10)
    else:
        df["cci"] = (df["close"] - df["close"].rolling(20).mean()) / (df["close"].rolling(20).std() + 1e-10)

    # VWAP (rolling 20-day)
    if "volume" in df.columns:
        df["vwap"] = (df["close"] * df["volume"]).rolling(20).sum() / df["volume"].rolling(20).sum()

    # Volume MA
    if "volume" in df.columns:
        df["vol_ma"] = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / df["vol_ma"]

    # Signals
    bull_ema   = df["ema8"] > df["ema21"]
    bull_macd  = df["macd"] > df["macd_signal"]
    macd_cross_up = bull_macd & ~bull_macd.shift(1).fillna(False)
    macd_cross_dn = ~bull_macd & bull_macd.shift(1).fillna(False)
    rsi_ok_buy    = df["rsi"].between(35, 68)
    rsi_ok_sell   = (df["rsi"] > 32)
    bb_squeeze    = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"] < 0.04

    df["signal"] = np.where(
        bull_ema & macd_cross_up & rsi_ok_buy,  "STRONG BUY",
        np.where(bull_ema & bull_macd & df["rsi"].between(38,65), "BUY",
        np.where(~bull_ema & macd_cross_dn & rsi_ok_sell, "STRONG SELL",
        np.where(~bull_ema & ~bull_macd & (df["rsi"]>38), "SELL",
        np.where(df["rsi"]<28, "OVERSOLD",
        np.where(df["rsi"]>74, "OVERBOUGHT", "HOLD"))))))

    return df

# ─── BACKTESTING ENGINE ────────────────────────────────────────────────────────
def run_backtest(df, trader_config, label="Strategy"):
    if df.empty or "signal" not in df.columns or len(df) < 30:
        return {"error": "Not enough data"}
    df = df.dropna(subset=["close","signal","rsi"]).copy()
    capital    = 10000.0
    cash       = capital
    position   = 0.0
    entry_px   = 0.0
    trades     = []
    equity     = []
    filters    = trader_config.get("signal_filters", {})
    stop_pct   = 0.025
    target_mult= trader_config.get("rr", 2.0)

    def check_entry(row):
        s = row["signal"]
        r = row.get("rsi", 50)
        rng = filters.get("rsi_range", (20,80))
        if not (rng[0] <= r <= rng[1]):
            return None
        if filters.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"):
            return None
        if filters.get("bb_break") and "bb_pct" in row:
            bp = row["bb_pct"]
            if s in ("BUY","STRONG BUY") and bp > 0.8:
                return "long"
            if s in ("SELL","STRONG SELL") and bp < 0.2:
                return "short"
        if filters.get("rsi_extreme"):
            if r < 32 and s != "OVERBOUGHT":
                return "long"
            if r > 68 and s != "OVERSOLD":
                return "short"
        if s in ("BUY","STRONG BUY","OVERSOLD"):
            return "long"
        if s in ("SELL","STRONG SELL","OVERBOUGHT"):
            return "short"
        return None

    for i in range(1, len(df)):
        row   = df.iloc[i]
        price = row["close"]
        val   = cash + position * price
        equity.append({"date": df.index[i], "equity": val})

        # stop loss & take profit
        if position > 0 and entry_px > 0:
            sl = entry_px * (1 - stop_pct)
            tp = entry_px * (1 + stop_pct * target_mult)
            if price <= sl or price >= tp:
                pnl  = (price - entry_px) * position
                cash += position * price
                trades.append({"type":"Long","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"TP" if price>=tp else "SL"})
                position = 0; entry_px = 0
                continue
        if position < 0 and entry_px > 0:
            sl = entry_px * (1 + stop_pct)
            tp = entry_px * (1 - stop_pct * target_mult)
            if price >= sl or price <= tp:
                pnl  = (entry_px - price) * abs(position)
                cash += abs(position) * price
                trades.append({"type":"Short","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"TP" if price<=tp else "SL"})
                position = 0; entry_px = 0
                continue

        prev_row = df.iloc[i-1]
        if position == 0:
            direction = check_entry(prev_row)
            if direction == "long":
                units    = (cash * 0.95) / price
                position = units; cash -= units*price; entry_px = price
            elif direction == "short":
                units    = (cash * 0.95) / price
                position = -units; cash += units*price; entry_px = price
        else:
            cur_dir = check_entry(prev_row)
            if position > 0 and cur_dir == "short":
                pnl = (price - entry_px) * position
                cash += position * price
                trades.append({"type":"Long","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"Signal flip"})
                position = 0; entry_px = 0
            elif position < 0 and cur_dir == "long":
                pnl = (entry_px - price) * abs(position)
                cash += abs(position) * price
                trades.append({"type":"Short","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"Signal flip"})
                position = 0; entry_px = 0

    if position != 0:
        fp  = df.iloc[-1]["close"]
        pnl = (fp-entry_px)*position if position>0 else (entry_px-fp)*abs(position)
        cash += abs(position)*fp
        trades.append({"type":"Open@end","entry":entry_px,"exit":fp,"pnl":pnl,
                       "date":df.index[-1],"reason":"End"})

    if not trades:
        return {"error": "No trades generated"}

    eq_df  = pd.DataFrame(equity)
    tdf    = pd.DataFrame(trades)
    wins   = tdf[tdf["pnl"]>0]
    losses = tdf[tdf["pnl"]<=0]
    total_ret    = (cash - capital) / capital * 100
    bh_ret       = (df.iloc[-1]["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"] * 100
    win_rate     = len(wins)/len(tdf)*100 if len(tdf) else 0
    profit_factor= abs(wins["pnl"].sum() / losses["pnl"].sum()) if not losses.empty and losses["pnl"].sum()!=0 else 99.0
    avg_win      = wins["pnl"].mean()   if not wins.empty   else 0
    avg_loss     = losses["pnl"].mean() if not losses.empty else 0
    sharpe       = 0.0
    if len(eq_df) > 1:
        eq_df["ret"] = eq_df["equity"].pct_change()
        mu  = eq_df["ret"].mean()
        sig = eq_df["ret"].std()
        sharpe = (mu / sig * np.sqrt(252)) if sig > 0 else 0.0
    roll_max = eq_df["equity"].cummax()
    max_dd   = ((eq_df["equity"] - roll_max) / roll_max * 100).min()
    calmar   = total_ret / abs(max_dd) if max_dd != 0 else 0

    # consecutive win/loss streaks
    streaks = []
    cur = 0
    for p in tdf["pnl"]:
        if p > 0:
            cur = max(1, cur+1)
        else:
            cur = min(-1, cur-1)
        streaks.append(cur)
    max_win_streak  = max(streaks) if streaks else 0
    max_loss_streak = abs(min(streaks)) if streaks else 0

    return {
        "total_return":   round(total_ret, 2),
        "bh_return":      round(bh_ret, 2),
        "win_rate":       round(win_rate, 1),
        "total_trades":   len(tdf),
        "wins":           len(wins),
        "losses":         len(losses),
        "avg_win":        round(avg_win, 2),
        "avg_loss":       round(avg_loss, 2),
        "profit_factor":  round(min(profit_factor, 99.0), 2),
        "max_drawdown":   round(max_dd, 2),
        "sharpe":         round(sharpe, 2),
        "calmar":         round(calmar, 2),
        "max_win_streak": max_win_streak,
        "max_loss_streak":max_loss_streak,
        "equity_curve":   eq_df,
        "trade_list":     tdf,
        "final_equity":   round(cash, 2),
        "label":          label,
    }

# ─── CHART BUILDERS ──────────────────────────────────────────────────────────
def build_advanced_chart(df, title, color="#00ff88", show_signals=True, bt=None):
    if df.empty:
        return None
    rows = 4
    heights = [0.5, 0.18, 0.18, 0.14]
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        row_heights=heights, vertical_spacing=0.03,
        subplot_titles=["", "MACD", "RSI", "Volume"],
    )

    # BB bands
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"],
            line=dict(color="rgba(100,100,200,0.3)", width=1), showlegend=False, name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"],
            line=dict(color="rgba(100,100,200,0.3)", width=1),
            fill="tonexty", fillcolor="rgba(100,100,200,0.05)",
            showlegend=False, name="BB Lower"), row=1, col=1)

    # Price
    if "open" in df.columns and "high" in df.columns:
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["open"], high=df["high"],
            low=df["low"], close=df["close"], name="Price",
            increasing_line_color="#00ff88", decreasing_line_color="#ff4444",
            increasing_fillcolor="#00ff8833", decreasing_fillcolor="#ff444433",
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=df["close"],
            name="Price", line=dict(color=color, width=2)), row=1, col=1)

    # MAs
    for col_name, mc, lbl in [("ema8","#5DCAA5","EMA8"),("ema21","#ED93B1","EMA21"),("ema50","#F59E0B","EMA50")]:
        if col_name in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col_name],
                name=lbl, line=dict(color=mc, width=1.2, dash="dot")), row=1, col=1)

    # Signals
    if show_signals and "signal" in df.columns:
        buys   = df[df["signal"].isin(["BUY","STRONG BUY","OVERSOLD"])]
        sells  = df[df["signal"].isin(["SELL","STRONG SELL","OVERBOUGHT"])]
        sb     = df[df["signal"]=="STRONG BUY"]
        ss     = df[df["signal"]=="STRONG SELL"]
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers",
                marker=dict(symbol="triangle-up", size=10, color="#00ff88"),
                name="Buy"), row=1, col=1)
        if not sb.empty:
            fig.add_trace(go.Scatter(x=sb.index, y=sb["close"], mode="markers",
                marker=dict(symbol="star", size=15, color="#00ffcc"),
                name="Strong Buy"), row=1, col=1)
        if not sells.empty:
            fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers",
                marker=dict(symbol="triangle-down", size=10, color="#ff4444"),
                name="Sell"), row=1, col=1)
        if not ss.empty:
            fig.add_trace(go.Scatter(x=ss.index, y=ss["close"], mode="markers",
                marker=dict(symbol="x", size=12, color="#ff0000"),
                name="Strong Sell"), row=1, col=1)

    # Backtest trade overlays
    if bt and "trade_list" in bt and not bt["trade_list"].empty:
        tdf = bt["trade_list"]
        for _, tr in tdf.iterrows():
            col_t = "#00ff88" if tr["pnl"] > 0 else "#ff4444"
            try:
                entry_y = df.loc[df.index <= tr["date"], "close"].iloc[-1] if tr["date"] in df.index else tr["entry"]
                fig.add_trace(go.Scatter(
                    x=[tr["date"]], y=[tr["entry"]],
                    mode="markers",
                    marker=dict(symbol="circle", size=8, color=col_t, opacity=0.7),
                    showlegend=False, name="Trade"), row=1, col=1)
            except:
                pass

    # MACD
    if "macd" in df.columns:
        bar_cols = ["#00ff88" if v>=0 else "#ff4444" for v in df["macd_hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"],
            marker_color=bar_cols, name="MACD Hist", showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd"],
            line=dict(color=color, width=1.5), name="MACD"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"],
            line=dict(color="#ED93B1", width=1.5), name="Signal"), row=2, col=1)

    # RSI
    if "rsi" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["rsi"],
            line=dict(color="#7C3AED", width=2), name="RSI"), row=3, col=1)
        fig.add_hline(y=70, line=dict(color="#ff4444", width=1, dash="dash"), row=3, col=1)
        fig.add_hline(y=30, line=dict(color="#00ff88", width=1, dash="dash"), row=3, col=1)
        fig.add_hline(y=50, line=dict(color="#555",    width=1, dash="dot"),  row=3, col=1)

    # Volume
    if "volume" in df.columns:
        vol_colors = ["#00ff8866" if c>=o else "#ff444466"
                      for c,o in zip(df["close"], df.get("open", df["close"]))]
        fig.add_trace(go.Bar(x=df.index, y=df["volume"],
            marker_color=vol_colors, name="Volume", showlegend=False), row=4, col=1)
        if "vol_ma" in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df["vol_ma"],
                line=dict(color="#F59E0B", width=1), name="Vol MA"), row=4, col=1)

    fig.update_layout(
        height=800, template="plotly_dark",
        title=dict(text=title, font=dict(size=14, color="#ccc")),
        paper_bgcolor="#080818", plot_bgcolor="#0d0d1a",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
        margin=dict(l=0, r=0, t=50, b=0),
    )
    fig.update_xaxes(gridcolor="#1a1a2e", zerolinecolor="#1a1a2e")
    fig.update_yaxes(gridcolor="#1a1a2e", zerolinecolor="#1a1a2e")
    return fig

def build_equity_chart(bt_results):
    fig = go.Figure()
    colors = {"Macro Maya":"#00ff88","Momentum Mike":"#00d4ff","Scalp Sam":"#f0a500"}
    for name, bt in bt_results.items():
        if bt and "equity_curve" in bt:
            eq = bt["equity_curve"]
            c  = colors.get(name, "#fff")
            final_val = eq["equity"].iloc[-1] if not eq.empty else 10000
            ret = (final_val - 10000) / 10000 * 100
            fig.add_trace(go.Scatter(
                x=eq["date"], y=eq["equity"],
                name=f"{name} ({ret:+.1f}%)",
                line=dict(color=c, width=2),
                fill="tozeroy",
                fillcolor=c.replace("#","rgba(") + ",0.05)".replace("rgba(","rgba(").replace("(","(")
                    if False else "rgba(0,0,0,0)",
            ))
    fig.add_hline(y=10000, line=dict(color="#555", width=1, dash="dot"), annotation_text="$10k start")
    fig.update_layout(
        height=350, template="plotly_dark",
        title="Equity curves — all traders vs $10k start",
        paper_bgcolor="#080818", plot_bgcolor="#0d0d1a",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="Date", yaxis_title="Portfolio ($)",
        margin=dict(l=0,r=0,t=50,b=0),
    )
    return fig

def build_monthly_returns(bt):
    if not bt or "equity_curve" not in bt:
        return None
    eq = bt["equity_curve"].copy()
    if eq.empty:
        return None
    eq["month"] = pd.to_datetime(eq["date"]).dt.to_period("M")
    monthly = eq.groupby("month")["equity"].last()
    monthly_ret = monthly.pct_change() * 100
    colors = ["#00ff88" if v >= 0 else "#ff4444" for v in monthly_ret.fillna(0)]
    fig = go.Figure(go.Bar(
        x=[str(m) for m in monthly_ret.index],
        y=monthly_ret.fillna(0),
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in monthly_ret.fillna(0)],
        textposition="outside", textfont=dict(size=9, color="#aaa"),
    ))
    fig.add_hline(y=0, line=dict(color="#555", width=1))
    fig.update_layout(
        height=220, template="plotly_dark",
        title="Monthly returns",
        paper_bgcolor="#080818", plot_bgcolor="#0d0d1a",
        yaxis_title="Return %",
        margin=dict(l=0,r=0,t=40,b=0),
    )
    return fig

def build_drawdown_chart(bt):
    if not bt or "equity_curve" not in bt:
        return None
    eq = bt["equity_curve"].copy()
    if eq.empty:
        return None
    roll_max = eq["equity"].cummax()
    dd = (eq["equity"] - roll_max) / roll_max * 100
    fig = go.Figure(go.Scatter(
        x=eq["date"], y=dd, fill="tozeroy",
        fillcolor="rgba(255,68,68,0.15)",
        line=dict(color="#ff4444", width=1.5),
        name="Drawdown %",
    ))
    fig.update_layout(
        height=180, template="plotly_dark",
        title="Drawdown %",
        paper_bgcolor="#080818", plot_bgcolor="#0d0d1a",
        yaxis_title="%",
        margin=dict(l=0,r=0,t=40,b=0),
    )
    return fig

# ─── SIGNAL ENGINE ────────────────────────────────────────────────────────────
def get_market_signal(df, fg=None, on_chain=None):
    if df.empty or "rsi" not in df.columns:
        return {"signal":"HOLD","conf":50,"rsi":50,"ma_bull":False,"macd_bull":False,"price":0}
    row   = df.iloc[-1]
    price = float(row["close"])
    rsi_v = float(row.get("rsi", 50))
    sig_v = str(row.get("signal", "HOLD"))
    ma_b  = bool(row.get("ema8",0) > row.get("ema21",0))
    macd_b= bool(row.get("macd",0) > row.get("macd_signal",0))
    conf  = 50
    if sig_v == "STRONG BUY":   conf = 82
    elif sig_v == "BUY":         conf = 66
    elif sig_v == "STRONG SELL": conf = 80
    elif sig_v == "SELL":        conf = 64
    elif sig_v == "OVERSOLD":    conf = 74
    elif sig_v == "OVERBOUGHT":  conf = 72

    # boost/reduce from fear & greed
    if fg:
        fg_val = fg.get("value", 50)
        if sig_v in ("BUY","STRONG BUY","OVERSOLD") and fg_val < 30:
            conf = min(95, conf + 8)   # extreme fear = better buy
        if sig_v in ("SELL","STRONG SELL","OVERBOUGHT") and fg_val > 75:
            conf = min(95, conf + 8)   # extreme greed = better sell

    return {"signal":sig_v, "conf":conf, "rsi":rsi_v, "ma_bull":ma_b,
            "macd_bull":macd_b, "price":price,
            "bb_pct": float(row.get("bb_pct", 0.5)),
            "atr":    float(row.get("atr", price*0.02)),
            "stoch_k":float(row.get("stoch_k", 50)),
            "cci":    float(row.get("cci", 0)),
    }

# ─── TRADER SIMULATION ────────────────────────────────────────────────────────
def simulate_all_traders(market_signals):
    for tr in TRADERS:
        if tr["open_pos"]:
            pos = tr["open_pos"]
            mk  = pos["market"]
            sig = market_signals.get(mk)
            if not sig:
                continue
            p      = sig["price"]
            is_long= pos["dir"] == "long"
            hit_sl = (is_long and p <= pos["stop"]) or (not is_long and p >= pos["stop"])
            hit_tp = (is_long and p >= pos["tp"])   or (not is_long and p <= pos["tp"])
            if hit_sl or hit_tp:
                pnl = (p - pos["entry"]) * pos["units"] if is_long else (pos["entry"] - p) * pos["units"]
                tr["balance"] = max(0, tr["balance"] + pnl)
                tr["peak"]    = max(tr["peak"], tr["balance"])
                result = "win" if pnl > 0 else "loss"
                tr["trades"].append(dict(market=mk, dir=pos["dir"],
                    entry=pos["entry"], exit=p, pnl=round(pnl,2),
                    result=result, reason="TP" if (hit_tp) else "SL",
                    time=datetime.now().strftime("%H:%M:%S")))
                tr["history"].append(round(tr["balance"],2))
                if result == "win":
                    tr["win_streak"]  = tr.get("win_streak",0)+1
                    tr["loss_streak"] = 0
                else:
                    tr["loss_streak"] = tr.get("loss_streak",0)+1
                    tr["win_streak"]  = 0
                tr["open_pos"] = None

        if not tr["open_pos"]:
            for mk, sig in market_signals.items():
                if sig["conf"] < 50:
                    continue
                f      = tr["signal_filters"]
                rng    = f.get("rsi_range",(20,80))
                rsi_v  = sig["rsi"]
                s      = sig["signal"]
                if not (rng[0] <= rsi_v <= rng[1]):
                    continue
                if f.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"):
                    continue
                is_buy = s in ("BUY","STRONG BUY","OVERSOLD")
                is_sell= s in ("SELL","STRONG SELL","OVERBOUGHT")
                if f.get("bb_break"):
                    bp = sig.get("bb_pct",0.5)
                    if is_buy and bp < 0.8:
                        continue
                    if is_sell and bp > 0.2:
                        continue
                if f.get("rsi_extreme"):
                    is_buy  = rsi_v < 32
                    is_sell = rsi_v > 68
                if not is_buy and not is_sell:
                    continue
                direction  = "long" if is_buy else "short"
                p          = sig["price"]
                atr        = sig.get("atr", p*0.02)
                stop_dist  = atr * 1.5
                stop  = p - stop_dist if is_buy else p + stop_dist
                tp    = p + stop_dist * tr["rr"] if is_buy else p - stop_dist * tr["rr"]
                risk  = tr["balance"] * tr["risk_pct"]
                units = risk / stop_dist
                tr["open_pos"] = dict(market=mk, dir=direction,
                    entry=round(p,2), stop=round(stop,2), tp=round(tp,2),
                    units=units, risk_amt=round(risk,2), time=datetime.now().strftime("%H:%M:%S"))
                break

# ─── AI NOTES ─────────────────────────────────────────────────────────────────
def push_note(ntype, market, text):
    st.session_state["notes"].insert(0,
        {"type":ntype,"market":market,"text":text,"time":datetime.now().strftime("%H:%M:%S")})
    if len(st.session_state["notes"]) > 50:
        st.session_state["notes"].pop()

def generate_notes(market_signals, fg, on_chain, sessions, anthropic_key):
    cooldown = 90
    if time.time() - st.session_state["last_ai"] < cooldown:
        return
    st.session_state["last_ai"] = time.time()
    labels = {mk: v["label"] for mk, v in MARKETS.items()}
    summaries = ". ".join(
        f"{labels.get(mk,mk)}: RSI {v['rsi']:.0f}, signal {v['signal']}, "
        f"BB at {v.get('bb_pct',0.5)*100:.0f}%, Stoch {v.get('stoch_k',50):.0f}"
        for mk, v in market_signals.items()
    )
    fg_str = f"Fear & Greed index: {fg['value']} ({fg['label']})" if fg else ""
    oc_str = ""
    if on_chain:
        oc_str = (f"BTC 7d change: {on_chain.get('price_change_7d',0):.1f}%, "
                  f"30d change: {on_chain.get('price_change_30d',0):.1f}%, "
                  f"ATH distance: {on_chain.get('ath_change_pct',0):.1f}%")
    sess = ", ".join(sessions)

    if not anthropic_key:
        # fallback
        for mk, sig in market_signals.items():
            r, s, bp = sig["rsi"], sig["signal"], sig.get("bb_pct",0.5)
            label = labels.get(mk,mk)
            if r > 72 or s == "OVERBOUGHT":
                push_note("watch", mk, f"**{label}** is really high right now — watch out for a pullback soon. Don't buy here, wait for it to cool down first.")
            elif r < 30 or s == "OVERSOLD":
                push_note("buy", mk, f"**{label}** got beaten down pretty low. Look for a green candle to close, then it might be a decent spot to sneak in small.")
            elif s == "STRONG BUY":
                push_note("buy", mk, f"**{label}** is looking good — both the short and long averages are going up together. Look for half a green candle then buy.")
            elif s == "STRONG SELL":
                push_note("sell", mk, f"**{label}** flipped to downtrend. Stay out of new buys. If you're in, think about your stop-loss.")
        return

    try:
        prompt = (
            f"You are a friendly trading coach texting a beginner who loves trading ideas but hates jargon. "
            f"Markets right now: {summaries}. {fg_str}. {oc_str}. Session: {sess}. "
            f"Write 4-5 short plain-English notes — like texting a mate. "
            f"Examples: 'BTC is dropping like it forgot its keys — stay out for now', "
            f"'Gold looks like it wants to bounce — wait for one green candle then sneak in small', "
            f"'Fear index is extreme fear — historically good time to think about buying crypto'. "
            f"NO jargon. Say things like 'the candle turned green' not 'bullish engulfing'. "
            f"Say 'price is near the top of its range' not 'upper Bollinger band'. "
            f"Format as JSON array only: "
            f'[{{"type":"watch|buy|sell|info","market":"BTC|ETH|NQ|GOLD|SPY","text":"..."}}]. '
            f"Return ONLY the JSON array."
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key":anthropic_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-sonnet-4-5","max_tokens":800,
                  "messages":[{"role":"user","content":prompt}]},
            timeout=25,
        )
        raw    = resp.json()["content"][0]["text"].strip()
        parsed = json.loads(raw.replace("```json","").replace("```","").strip())
        for n in parsed:
            push_note(n.get("type","info"), n.get("market","BTC"), n.get("text",""))
    except:
        for mk, sig in market_signals.items():
            r, s = sig["rsi"], sig["signal"]
            label = labels.get(mk, mk)
            if r > 70:
                push_note("watch", mk, f"**{label}** is running hot — RSI at {r:.0f}. Watch for a drop, don't chase.")
            elif r < 30:
                push_note("buy", mk, f"**{label}** looks oversold at RSI {r:.0f}. Watch for a green candle bounce.")
            elif "BUY" in s:
                push_note("buy", mk, f"**{label}** signal is pointing up. Check for a green candle close before entering.")
            elif "SELL" in s:
                push_note("sell", mk, f"**{label}** signal pointing down. Stay out or tighten stops.")

# ─── SESSION BANNER ────────────────────────────────────────────────────────────
SESSION_TIPS = {
    "Tokyo":    "Quiet session. BTC/ETH can drift or spike randomly. Gold and stocks are mostly flat.",
    "London":   "Things picking up! Gold and BTC usually make moves at the London open.",
    "New York": "Prime time — all markets active. US stock market open, sharpest signals.",
    "Overlap":  "🔥 Peak time — London + NY both open. This is when the biggest moves happen.",
    "Off-hours":"Slow and thin. Wider spreads. Better to watch than trade.",
}

def session_banner():
    utc = datetime.now(ZoneInfo("UTC"))
    hf  = utc.hour + utc.minute/60
    sessions = []
    if 0  <= hf < 9:  sessions.append(("Tokyo","#7C3AED"))
    if 8  <= hf < 17: sessions.append(("London","#2563EB"))
    if 13 <= hf < 22: sessions.append(("New York","#059669"))
    if 13 <= hf < 17: sessions.append(("Overlap","#D97706"))
    if not sessions:   sessions.append(("Off-hours","#555"))
    badges = " ".join(
        f'<span style="background:{c};color:#fff;border-radius:6px;padding:3px 12px;font-size:12px;font-weight:700;margin-right:6px">{n}</span>'
        for n,c in sessions)
    tip = SESSION_TIPS.get(sessions[0][0],"")
    ny  = utc.astimezone(ZoneInfo("America/New_York"))
    lon = utc.astimezone(ZoneInfo("Europe/London"))
    st.markdown(
        f'<div style="background:#0d0d1a;border:1px solid #1a1a3a;border-radius:10px;padding:12px 18px;margin-bottom:16px">'
        f'<div style="margin-bottom:6px">{badges}</div>'
        f'<div style="font-size:13px;color:#aaa;margin-bottom:4px">{tip}</div>'
        f'<div style="font-size:11px;color:#555">UTC {utc.strftime("%H:%M")} | ET {ny.strftime("%H:%M")} | LDN {lon.strftime("%H:%M")}</div>'
        f'</div>', unsafe_allow_html=True)
    return [n for n,_ in sessions]

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:Space Mono,monospace;font-size:1.1rem;font-weight:700;color:#00ff88">⚡ Alpha Trader Pro</div>', unsafe_allow_html=True)
    st.divider()
    with st.expander("🔑 API Keys", expanded=False):
        np_ = st.text_input("Polygon.io Key", value=POLYGON_KEY, type="password")
        na_ = st.text_input("Anthropic Key",  value=ANTHROPIC_KEY, type="password")
        if st.button("Save"):
            st.session_state["POLYGON_KEY"]   = np_
            st.session_state["ANTHROPIC_KEY"] = na_
            st.cache_data.clear(); st.rerun()
    st.divider()
    auto_refresh = st.toggle("Auto-refresh (90s)", value=False)
    selected_markets = st.multiselect(
        "Markets to watch",
        ["BTC","ETH","NQ","GOLD","SPY"],
        default=["BTC","NQ","GOLD"],
    )
    bt_days = st.slider("Backtest period (days)", 30, 365, 90)
    note_filter = st.selectbox("Filter alerts", ["ALL"]+["BTC","ETH","NQ","GOLD","SPY"])
    st.divider()
    if st.button("🔄 Refresh data"):
        st.cache_data.clear(); st.rerun()
    if st.button("🗑 Clear alerts"):
        st.session_state["notes"] = []; st.rerun()
    if st.button("♻️ Reset traders"):
        st.session_state["traders"] = [
            make_trader("Macro Maya","🌍","Multi-source macro + technicals",
                "Waits for RSI, MACD, MA, Bollinger AND volume all aligned.",
                0.008,2.5,{"rsi_range":(35,65),"need_macd":True,"need_ma":True,"need_vol":True,"strong_only":True},
                ["price","volume","rsi","macd","bb","fear_greed","on_chain"]),
            make_trader("Momentum Mike","🚀","Momentum + breakout specialist",
                "Trades breakouts above Bollinger bands. Uses ATR for stops.",
                0.015,2.0,{"rsi_range":(20,80),"need_macd":False,"need_ma":True,"need_vol":False,"strong_only":False,"bb_break":True},
                ["price","rsi","macd","bb","atr","volume"]),
            make_trader("Scalp Sam","⚡","Fast RSI + VWAP scalper",
                "Enters on RSI extremes. Small risk, high frequency.",
                0.005,1.5,{"rsi_range":(25,75),"need_macd":False,"need_ma":False,"need_vol":False,"strong_only":False,"rsi_extreme":True},
                ["price","rsi","vwap","stoch","cci"]),
        ]
        st.rerun()
    st.divider()
    st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

# ─── FETCH ALL DATA ────────────────────────────────────────────────────────────
if not selected_markets:
    selected_markets = ["BTC","NQ","GOLD"]

with st.spinner("Loading live data from all sources..."):
    all_dfs = {}
    for mk in selected_markets:
        info = MARKETS[mk]
        if info["crypto"]:
            raw = fetch_cg_chart(info["cg_id"], days=max(bt_days+10, 100))
        else:
            raw = fetch_polygon_ohlcv(info["poly_ticker"], POLYGON_KEY, days=max(bt_days+10, 100))
        all_dfs[mk] = add_indicators(raw)

    fg       = fetch_fear_greed()
    on_chain = fetch_on_chain() if "BTC" in selected_markets else {}

market_signals = {}
for mk in selected_markets:
    df = all_dfs.get(mk, pd.DataFrame())
    market_signals[mk] = get_market_signal(df, fg, on_chain)

active_sessions = session_banner()
simulate_all_traders(market_signals)
generate_notes(market_signals, fg, on_chain, active_sessions, ANTHROPIC_KEY)

# ─── PAGE ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">⚡ Alpha Trader Pro</div>', unsafe_allow_html=True)
st.markdown('<div style="color:#555;font-size:13px;margin-bottom:16px">Multi-source signals · Advanced backtesting · 3 competing AI traders · Plain-English alerts</div>', unsafe_allow_html=True)

# ── Fear & Greed ──────────────────────────────────────────────────────────────
if fg:
    fv  = fg["value"]
    fc  = "#ff4444" if fv < 25 else "#ff9900" if fv < 45 else "#ffff00" if fv < 55 else "#99ff44" if fv < 75 else "#00ff88"
    fl  = fg["label"]
    st.markdown(
        f'<div style="display:inline-block;background:#0d0d1a;border:1px solid #1a1a3a;'
        f'border-radius:8px;padding:8px 18px;font-size:13px;margin-bottom:16px">'
        f'Market Fear & Greed: <span style="color:{fc};font-weight:700;font-size:16px">{fv}</span> '
        f'<span style="color:{fc}">{fl}</span>'
        f'<span style="color:#555;font-size:11px;margin-left:12px">'
        f'{"Extreme fear = potential buy zone" if fv<25 else "Extreme greed = be careful" if fv>75 else ""}'
        f'</span></div>',
        unsafe_allow_html=True)

# ── Price cards ───────────────────────────────────────────────────────────────
st.subheader("Live signals")
cols = st.columns(len(selected_markets))
for col, mk in zip(cols, selected_markets):
    with col:
        info = MARKETS[mk]
        sig  = market_signals.get(mk, {})
        p    = sig.get("price", 0)
        df   = all_dfs.get(mk, pd.DataFrame())
        chg  = 0
        if not df.empty and len(df) > 1:
            chg = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2] * 100
        s   = sig.get("signal","HOLD")
        c   = sig.get("conf", 50)
        r   = sig.get("rsi",  50)
        isBuy  = "BUY"  in s or s == "OVERSOLD"
        isSell = "SELL" in s or s == "OVERBOUGHT"
        border  = "#00ff88" if isBuy else "#ff4444" if isSell else "#1a1a3a"
        chg_col = "#00ff88" if chg >= 0 else "#ff4444"
        px_fmt  = f"${p:,.0f}" if mk in ("BTC","ETH") else f"${p:,.2f}"
        sig_cls = "sig-buy" if isBuy else "sig-sell" if isSell else "sig-hold"
        st.markdown(
            f'<div style="border:2px solid {border};border-radius:12px;padding:14px;'
            f'background:#0d0d1a;margin-bottom:4px">'
            f'<div style="font-size:11px;color:#555;margin-bottom:4px">{info["label"]}</div>'
            f'<div style="font-size:22px;font-weight:700;color:{info["color"]};font-family:Space Mono,monospace">{px_fmt}</div>'
            f'<div style="font-size:12px;color:{chg_col};margin-bottom:8px">{chg:+.2f}% today</div>'
            f'<span class="signal-badge {sig_cls}">{s}</span><br>'
            f'<div style="font-size:11px;color:#555;margin-top:4px">'
            f'Conf: {c}% | RSI: {r:.0f} | BB: {sig.get("bb_pct",0.5)*100:.0f}%</div>'
            f'</div>', unsafe_allow_html=True)

st.divider()

# ── Main tabs ──────────────────────────────────────────────────────────────────
tab_alerts, tab_traders, tab_backtest, tab_sessions = st.tabs([
    "📝 Alerts", "🤖 AI Traders", "📊 Backtesting", "🕐 Sessions"
])

# ── ALERTS ────────────────────────────────────────────────────────────────────
with tab_alerts:
    st.subheader("Plain-English market alerts")
    st.caption("No jargon — written like a text from a mate who's been watching the charts.")
    notes = st.session_state["notes"]
    if note_filter != "ALL":
        notes = [n for n in notes if n["market"] == note_filter]
    if not notes:
        st.info("Notes will appear here. Hit Refresh to generate them.")
    icons = {"watch":"👀 Watch out","buy":"🟢 Possible buy","sell":"🔴 Consider selling","info":"💡 Heads up"}
    for n in notes[:12]:
        cls = {"watch":"note-watch","buy":"note-buy","sell":"note-sell","info":"note-info"}.get(n["type"],"note-info")
        label = MARKETS.get(n["market"],{}).get("label", n["market"])
        st.markdown(
            f'<div class="note-card {cls}">'
            f'<div style="font-size:10px;color:#555;margin-bottom:2px">{n["time"]}</div>'
            f'<div style="font-weight:600;font-size:12px;margin-bottom:4px">{icons.get(n["type"],"💡")} — {label}</div>'
            f'{n["text"]}</div>', unsafe_allow_html=True)
    if fg:
        st.divider()
        st.markdown("**Fear & Greed history (last 10 days)**")
        fig_fg = go.Figure(go.Bar(
            x=list(range(len(fg["history"]))), y=fg["history"],
            marker_color=["#ff4444" if v<25 else "#ff9900" if v<45 else "#ffff44" if v<55 else "#00ff88" for v in fg["history"]],
            text=[str(v) for v in fg["history"]], textposition="outside",
        ))
        fig_fg.update_layout(height=180, template="plotly_dark", paper_bgcolor="#080818", plot_bgcolor="#0d0d1a",
                             margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Days ago", yaxis=dict(range=[0,120]))
        st.plotly_chart(fig_fg, use_container_width=True)
    if on_chain:
        st.divider()
        st.markdown("**BTC on-chain snapshot**")
        oc1, oc2, oc3, oc4 = st.columns(4)
        oc1.metric("Market cap",      f"${on_chain.get('market_cap',0)/1e9:.1f}B")
        oc2.metric("24h volume",      f"${on_chain.get('volume_24h',0)/1e9:.1f}B")
        oc3.metric("7d change",       f"{on_chain.get('price_change_7d',0):+.1f}%")
        oc4.metric("Distance from ATH", f"{on_chain.get('ath_change_pct',0):.1f}%")

# ── AI TRADERS ─────────────────────────────────────────────────────────────────
with tab_traders:
    st.subheader("3 AI traders — different strategies, same markets")
    st.caption("Each uses different data sources and risk rules. The scoreboard shows which approach works best right now.")

    # scoreboard
    rows = []
    for tr in TRADERS:
        pnl  = tr["balance"] - 25000
        wins = sum(1 for t in tr["trades"] if t["result"]=="win")
        tot  = len(tr["trades"])
        wr   = round(wins/tot*100) if tot else 0
        dd   = round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
        rows.append({"Trader":f"{tr['emoji']} {tr['name']}","Strategy":tr["style"],
                     "Balance":tr["balance"],"P&L":pnl,"Win%":wr,"Trades":tot,"DD%":dd,
                     "W-Streak":tr.get("win_streak",0),"L-Streak":tr.get("loss_streak",0)})
    df_score = pd.DataFrame(rows).sort_values("P&L",ascending=False).reset_index(drop=True)
    df_score.index += 1
    st.dataframe(
        df_score.style
            .format({"Balance":"${:,.0f}","P&L":"${:+,.0f}","Win%":"{}%","DD%":"{}%"})
            .map(lambda v:"color:#00ff88;font-weight:700" if v>0 else "color:#ff4444;font-weight:700", subset=["P&L"]),
        use_container_width=True)

    # equity chart
    hist_fig = go.Figure()
    hc = {"Macro Maya":"#00ff88","Momentum Mike":"#00d4ff","Scalp Sam":"#f0a500"}
    for tr in TRADERS:
        if len(tr["history"]) > 1:
            pnl_pct = (tr["balance"]-25000)/25000*100
            hist_fig.add_trace(go.Scatter(
                y=tr["history"], name=f"{tr['emoji']} {tr['name']} ({pnl_pct:+.1f}%)",
                line=dict(color=hc.get(tr["name"],"#fff"), width=2)))
    hist_fig.add_hline(y=25000, line=dict(color="#555",width=1,dash="dot"), annotation_text="$25k start")
    hist_fig.update_layout(height=280, template="plotly_dark", paper_bgcolor="#080818",
                           plot_bgcolor="#0d0d1a", margin=dict(l=0,r=0,t=30,b=0),
                           legend=dict(orientation="h",y=1.05))
    st.plotly_chart(hist_fig, use_container_width=True)

    # individual cards
    tr_tabs = st.tabs([f"{tr['emoji']} {tr['name']}" for tr in TRADERS])
    for ttab, tr in zip(tr_tabs, TRADERS):
        with ttab:
            pnl = tr["balance"] - 25000
            col_p = "#00ff88" if pnl >= 0 else "#ff4444"
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            m1.metric("Balance", f"${tr['balance']:,.0f}", delta=f"{pnl:+,.0f}")
            m2.metric("Net P&L",  f"${pnl:+,.0f}")
            wins = sum(1 for t in tr["trades"] if t["result"]=="win")
            tot  = len(tr["trades"])
            m3.metric("Win rate", f"{round(wins/tot*100) if tot else 0}%")
            m4.metric("Trades",   tot)
            m5.metric("Risk/trade", f"{tr['risk_pct']*100:.1f}%")
            m6.metric("R:R",      f"1:{tr['rr']}")

            st.caption(f"**Data sources:** {', '.join(tr['data_sources'])} | **Strategy:** {tr['desc']}")

            # open position
            pos = tr["open_pos"]
            if pos:
                mk     = pos["market"]
                info   = MARKETS.get(mk,{})
                sig    = market_signals.get(mk,{})
                cur_p  = sig.get("price", pos["entry"])
                unreal = (cur_p-pos["entry"])*pos["units"] if pos["dir"]=="long" else (pos["entry"]-cur_p)*pos["units"]
                uc = "#00ff88" if unreal>=0 else "#ff4444"
                fmt = "0f" if info.get("crypto") else ".2f"
                st.markdown(
                    f'<div class="{"pos-long" if pos["dir"]=="long" else "pos-short"}">'
                    f'<b>{info.get("label",mk)} — {pos["dir"].upper()}</b> | '
                    f'Entered ${pos["entry"]:{fmt}} | Now ${cur_p:{fmt}}<br>'
                    f'Stop: <span style="color:#ff4444">${pos["stop"]:{fmt}}</span> | '
                    f'Target: <span style="color:#00ff88">${pos["tp"]:{fmt}}</span> | '
                    f'Unrealized: <span style="color:{uc}"><b>${unreal:+,.0f}</b></span>'
                    f'</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="pos-none">No open position right now</div>', unsafe_allow_html=True)

            # trade log
            if tr["trades"]:
                st.markdown("**Recent trades**")
                tdf = pd.DataFrame(tr["trades"][-10:][::-1])
                show = [c for c in ["time","market","dir","entry","exit","pnl","result","reason"] if c in tdf.columns]
                st.dataframe(
                    tdf[show].style
                        .format({c:"${:,.2f}" for c in ["entry","exit","pnl"] if c in tdf.columns})
                        .map(lambda v:"color:#00ff88" if v=="win" else "color:#ff4444", subset=["result"] if "result" in tdf.columns else []),
                    use_container_width=True, hide_index=True)

# ── BACKTESTING ────────────────────────────────────────────────────────────────
with tab_backtest:
    st.subheader(f"Advanced backtesting — last {bt_days} days")
    st.caption("Full signal chart with entries/exits, equity curves, monthly returns, drawdown analysis, and trade log.")

    bt_market = st.selectbox("Choose market to backtest", selected_markets)
    bt_trader  = st.selectbox("Choose trader strategy", [tr["name"] for tr in TRADERS])
    show_sigs  = st.toggle("Show buy/sell signals on chart", value=True)
    show_bb    = st.toggle("Show Bollinger Bands", value=True)
    run_bt     = st.button("▶ Run backtest", type="primary")

    df_bt = all_dfs.get(bt_market, pd.DataFrame())
    trader_cfg = next((tr for tr in TRADERS if tr["name"] == bt_trader), TRADERS[0])

    if run_bt or st.session_state["bt_results"]:
        if run_bt:
            with st.spinner("Running backtest..."):
                bt = run_backtest(df_bt, trader_cfg, label=f"{bt_trader} on {bt_market}")
                if "equity_curve" in bt:
                    # run all 3 for comparison
                    all_bts = {}
                    for tr in TRADERS:
                        all_bts[tr["name"]] = run_backtest(df_bt, tr, label=tr["name"])
                    st.session_state["bt_results"] = {"main": bt, "all": all_bts, "market": bt_market}
                else:
                    st.error(bt.get("error","Backtest failed"))

        saved = st.session_state.get("bt_results", {})
        bt    = saved.get("main")
        all_bts = saved.get("all", {})

        if bt and "equity_curve" in bt:
            # stat grid
            s1,s2,s3,s4,s5,s6,s7,s8 = st.columns(8)
            color_ret = "#00ff88" if bt["total_return"]>0 else "#ff4444"
            s1.markdown(f'<div class="bt-stat"><div class="bt-val" style="color:{color_ret}">{bt["total_return"]:+.1f}%</div><div class="bt-lbl">Strategy return</div></div>', unsafe_allow_html=True)
            s2.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["bh_return"]:+.1f}%</div><div class="bt-lbl">Buy & hold</div></div>', unsafe_allow_html=True)
            s3.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["win_rate"]:.0f}%</div><div class="bt-lbl">Win rate</div></div>', unsafe_allow_html=True)
            s4.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["total_trades"]}</div><div class="bt-lbl">Total trades</div></div>', unsafe_allow_html=True)
            s5.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["profit_factor"]:.2f}</div><div class="bt-lbl">Profit factor</div></div>', unsafe_allow_html=True)
            s6.markdown(f'<div class="bt-stat"><div class="bt-val" style="color:#ff4444">{bt["max_drawdown"]:.1f}%</div><div class="bt-lbl">Max drawdown</div></div>', unsafe_allow_html=True)
            s7.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["sharpe"]:.2f}</div><div class="bt-lbl">Sharpe ratio</div></div>', unsafe_allow_html=True)
            s8.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["calmar"]:.2f}</div><div class="bt-lbl">Calmar ratio</div></div>', unsafe_allow_html=True)

            # additional stats
            st.markdown("")
            a1,a2,a3,a4 = st.columns(4)
            a1.metric("Avg win",          f"${bt['avg_win']:+,.2f}")
            a2.metric("Avg loss",         f"${bt['avg_loss']:+,.2f}")
            a3.metric("Max win streak",   bt["max_win_streak"])
            a4.metric("Max loss streak",  bt["max_loss_streak"])

            # main chart
            fig_main = build_advanced_chart(df_bt, f"{bt_market} — {bt_trader}", MARKETS[bt_market]["color"], show_sigs, bt)
            if fig_main:
                st.plotly_chart(fig_main, use_container_width=True)

            # equity + monthly + drawdown
            c_eq, c_mo = st.columns([2,1])
            with c_eq:
                fig_eq = build_equity_chart(all_bts)
                if fig_eq: st.plotly_chart(fig_eq, use_container_width=True)
            with c_mo:
                fig_mo = build_monthly_returns(bt)
                if fig_mo: st.plotly_chart(fig_mo, use_container_width=True)

            fig_dd = build_drawdown_chart(bt)
            if fig_dd: st.plotly_chart(fig_dd, use_container_width=True)

            # comparison table
            if all_bts:
                st.markdown("### All 3 strategies compared on this market")
                comp_rows = []
                for tname, tbt in all_bts.items():
                    if tbt and "total_return" in tbt:
                        comp_rows.append({
                            "Trader": tname,
                            "Return %": tbt["total_return"],
                            "B&H %":   tbt["bh_return"],
                            "Win rate": tbt["win_rate"],
                            "Trades":  tbt["total_trades"],
                            "Max DD %":tbt["max_drawdown"],
                            "Sharpe":  tbt["sharpe"],
                            "Calmar":  tbt["calmar"],
                            "PF":      tbt["profit_factor"],
                        })
                if comp_rows:
                    df_comp = pd.DataFrame(comp_rows)
                    st.dataframe(
                        df_comp.style
                            .format({"Return %":"{:+.1f}%","B&H %":"{:+.1f}%","Win rate":"{:.0f}%",
                                     "Max DD %":"{:.1f}%","Sharpe":"{:.2f}","Calmar":"{:.2f}","PF":"{:.2f}"})
                            .highlight_max(subset=["Return %","Win rate","Sharpe"], color="#1a3a1a")
                            .highlight_min(subset=["Max DD %"], color="#1a3a1a"),
                        use_container_width=True, hide_index=True)

            # trade log
            with st.expander("📋 Full trade log"):
                tdf = bt["trade_list"].copy()
                tdf["pnl_pct"] = tdf["pnl"] / 10000 * 100
                st.dataframe(
                    tdf.style
                        .format({"entry":"${:,.2f}","exit":"${:,.2f}","pnl":"${:+,.2f}","pnl_pct":"{:+.2f}%"})
                        .map(lambda v:"color:#00ff88" if v>0 else "color:#ff4444", subset=["pnl"]),
                    use_container_width=True, hide_index=True)

            with st.expander("⚠️ Backtest disclaimer"):
                st.caption("Past performance does not guarantee future results. No slippage, commissions, or fees are modelled. Signals are computed on historical daily closes, which introduces look-ahead bias risk. Do not trade based solely on backtest results.")
        else:
            st.info("Click **▶ Run backtest** to start.")

# ── SESSIONS ──────────────────────────────────────────────────────────────────
with tab_sessions:
    st.subheader("Trading session guide")
    st.markdown("All times **UTC**. The best signals usually come at session opens and the London/NY overlap.")
    utc_now = datetime.now(ZoneInfo("UTC"))
    hf_now  = utc_now.hour + utc_now.minute/60
    session_rows = [
        ("Tokyo",   "00:00–09:00","03:00–08:00","BTC, ETH","Low volume. BTC drifts or spikes randomly. Avoid stocks and gold.","#7C3AED"),
        ("London",  "08:00–17:00","08:00–10:00","Gold, BTC","Strong breakout potential at open. Gold reacts to EU data. BTC picks up.","#2563EB"),
        ("New York","13:00–22:00","13:30–16:00","NQ, SPY, Gold, BTC","Highest volume. US open at 13:30 UTC spikes all markets.","#059669"),
        ("Overlap", "13:00–17:00","13:00–15:00","All","PRIME TIME — tightest spreads, sharpest signals, biggest moves.","#D97706"),
        ("Off-hours","22:00–00:00","Avoid","None","Very thin. Random BTC gaps. Stay out unless you know why.","#555"),
    ]
    for sname, hours, best, mkts, desc, sc in session_rows:
        starts = {"Tokyo":0,"London":8,"New York":13,"Overlap":13,"Off-hours":22}
        ends   = {"Tokyo":9,"London":17,"New York":22,"Overlap":17,"Off-hours":24}
        is_now = starts.get(sname,0) <= hf_now < ends.get(sname,99)
        border = sc if is_now else "#1a1a2e"
        badge  = f' <span style="background:{sc};color:#fff;border-radius:4px;padding:1px 8px;font-size:11px">ACTIVE NOW</span>' if is_now else ""
        st.markdown(
            f'<div style="border:1.5px solid {border};border-radius:10px;padding:14px 18px;margin-bottom:10px;background:#0d0d1a">'
            f'<div style="font-size:15px;font-weight:600;color:{sc}">{sname}{badge}</div>'
            f'<div style="font-size:12px;color:#666;margin-top:4px">Hours: {hours} | Best entry: {best} | Markets: {mkts}</div>'
            f'<div style="font-size:13px;color:#aaa;margin-top:6px">{desc}</div>'
            f'</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### Best entry windows by market")
    st.markdown("""
| Market | Best session | Ideal entry (UTC) | Why |
|---|---|---|---|
| BTC / USD | London open or NY overlap | 08:00–10:00 or 13:00–16:00 | Highest momentum |
| ETH / USD | Same as BTC | 08:00–10:00 or 13:00–16:00 | Follows BTC closely |
| NASDAQ (QQQ) | New York | 13:30–16:00 | After US open, peak volume |
| Gold (GLD) | London + NY overlap | 08:00–10:00 or 13:30–15:00 | EU/US data at these times |
| S&P 500 (SPY) | New York | 13:30–15:30 | US open liquidity |
""")

if auto_refresh:
    time.sleep(90)
    st.cache_data.clear()
    st.rerun()
