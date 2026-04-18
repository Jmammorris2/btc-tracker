"""
Nigel v4 — Alpha Futures Intelligence
REBUILT: Real P&L math, honest signals, Monte Carlo eval probability,
genuine paper trading loop, no fake "100 AI" theater.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json, pathlib, random

st.set_page_config(
    page_title="Nigel v4 — Alpha Futures",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;600&display=swap');

*, html, body { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background: #05050f; }

.nigel-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 3.8rem;
  letter-spacing: 0.12em;
  color: #fff;
  line-height: 1;
  margin: 0;
}
.nigel-title span { color: #ff4d00; }

.mono { font-family: 'Space Mono', monospace; }

.pill {
  display: inline-block;
  border-radius: 2px;
  padding: 2px 10px;
  font-family: 'Space Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .08em;
}
.pill-buy  { background: rgba(0,230,100,0.12); color: #00e664; border: 1px solid rgba(0,230,100,0.3); }
.pill-sell { background: rgba(255,60,60,0.12);  color: #ff3c3c; border: 1px solid rgba(255,60,60,0.3); }
.pill-hold { background: rgba(120,120,140,0.12); color: #7878a0; border: 1px solid rgba(120,120,140,0.25); }
.pill-scalp{ background: rgba(255,180,0,0.12); color: #ffb400; border: 1px solid rgba(255,180,0,0.3); }

.card {
  background: #0c0c1e;
  border: 1px solid #1a1a35;
  border-radius: 6px;
  padding: 16px;
}
.card-accent-green { border-left: 3px solid #00e664; }
.card-accent-red   { border-left: 3px solid #ff3c3c; }
.card-accent-gold  { border-left: 3px solid #ffb400; }
.card-accent-blue  { border-left: 3px solid #00aaff; }

.stat-val {
  font-family: 'Space Mono', monospace;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1;
}
.stat-lbl {
  font-size: 10px;
  color: #44445a;
  letter-spacing: .06em;
  margin-top: 3px;
  text-transform: uppercase;
}

.mc-bar-wrap {
  background: #111128;
  border-radius: 3px;
  height: 8px;
  margin: 4px 0;
  overflow: hidden;
}
.mc-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.signal-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #111128;
}
.signal-row:last-child { border-bottom: none; }

.live-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #00e664;
  animation: pulse 2s infinite;
  margin-right: 5px;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.warn-box {
  background: #1a0a00;
  border: 1px solid #ff4d0044;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 12px;
  color: #ff9955;
  margin-bottom: 10px;
}
.info-box {
  background: #001020;
  border: 1px solid #00aaff33;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 12px;
  color: #66ccff;
  margin-bottom: 10px;
}

div[data-testid="stMetricValue"] { font-family: 'Space Mono', monospace; }
.stTabs [data-baseweb="tab-list"] { background: #0c0c1e; border-radius: 6px; gap: 2px; padding: 4px; }
.stTabs [data-baseweb="tab"] { border-radius: 4px; color: #44445a; font-size: 13px; }
.stTabs [aria-selected="true"] { background: #1a1a35 !important; color: #fff !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# CONSTANTS — REAL CME CONTRACT SPECS
# ─────────────────────────────────────────────────────────────
MARKETS = {
    "ES":  {"label": "E-mini S&P 500",   "proxy": "SPY",      "color": "#00e664", "crypto": False,
            "tick": 0.25,  "tick_usd": 12.50, "multiplier": 50,   "margin_est": 13200,
            "desc": "Most liquid CME future. Tracks S&P 500. $12.50/tick, $50/point."},
    "NQ":  {"label": "E-mini Nasdaq 100","proxy": "QQQ",      "color": "#00aaff", "crypto": False,
            "tick": 0.25,  "tick_usd": 5.00,  "multiplier": 20,   "margin_est": 17600,
            "desc": "Higher beta than ES. Tech-driven. $5/tick, $20/point."},
    "GC":  {"label": "Gold Futures",     "proxy": "GLD",      "color": "#ffb400", "crypto": False,
            "tick": 0.10,  "tick_usd": 10.00, "multiplier": 100,  "margin_est": 8800,
            "desc": "100 troy oz. Safe haven. $10/tick. Moves on USD & Fed policy."},
    "CL":  {"label": "Crude Oil WTI",    "proxy": "USO",      "color": "#ff6655", "crypto": False,
            "tick": 0.01,  "tick_usd": 10.00, "multiplier": 1000, "margin_est": 6600,
            "desc": "1000 barrels. $10/tick. High vol. EIA Wednesdays move it hard."},
    "YM":  {"label": "Dow Jones Fut.",   "proxy": "DIA",      "color": "#cc88ff", "crypto": False,
            "tick": 1.0,   "tick_usd": 5.00,  "multiplier": 5,    "margin_est": 10000,
            "desc": "Slower than ES. $5/tick. Value stock driven. Less algo whipsaw."},
    "BTC": {"label": "Micro BTC Futures","proxy": "X:BTCUSD", "color": "#f7931a", "crypto": True,
            "tick": 5.0,   "tick_usd": 25.00, "multiplier": 0.1,  "margin_est": 4000,
            "desc": "0.1 BTC per contract. $25/tick. 24/7. Gap risk overnight."},
    "ETH": {"label": "Micro ETH Futures","proxy": "X:ETHUSD", "color": "#627eea", "crypto": True,
            "tick": 0.01,  "tick_usd": 0.10,  "multiplier": 0.1,  "margin_est": 1200,
            "desc": "0.1 ETH per contract. High beta crypto. DeFi news sensitive."},
}

ALPHA_ACCOUNTS = {
    "10k":  {"size": 10_000,  "target": 1_000,  "max_loss": 400,   "eod_dd_pct": 0.04, "max_contracts": {"ES":6,  "NQ":3,  "GC":2,  "CL":2,  "YM":3,  "BTC":1, "ETH":1}},
    "25k":  {"size": 25_000,  "target": 2_500,  "max_loss": 1_000, "eod_dd_pct": 0.04, "max_contracts": {"ES":10, "NQ":6,  "GC":4,  "CL":4,  "YM":6,  "BTC":2, "ETH":2}},
    "50k":  {"size": 50_000,  "target": 5_000,  "max_loss": 2_000, "eod_dd_pct": 0.04, "max_contracts": {"ES":15, "NQ":10, "GC":8,  "CL":6,  "YM":10, "BTC":3, "ETH":3}},
    "100k": {"size": 100_000, "target": 10_000, "max_loss": 4_000, "eod_dd_pct": 0.04, "max_contracts": {"ES":20, "NQ":15, "GC":12, "CL":10, "YM":15, "BTC":5, "ETH":5}},
}

PERSIST = pathlib.Path("nigel_v4_state.json")

def _load():
    if PERSIST.exists():
        try:
            with open(PERSIST) as f: return json.load(f)
        except: return {}
    return {}

def _save(key, val):
    d = _load(); d[key] = val
    with open(PERSIST, "w") as f: json.dump(d, f, default=str)

def _get(key, default=None):
    return _load().get(key, default)

# ─────────────────────────────────────────────────────────────
# API KEY GATE
# ─────────────────────────────────────────────────────────────
def get_key():
    sk = st.secrets.get("POLYGON_KEY", "") if hasattr(st, "secrets") else ""
    return st.session_state.get("POLYGON_KEY", sk or _get("POLYGON_KEY", ""))

POLYGON_KEY = get_key()

if not POLYGON_KEY:
    st.markdown('<div class="nigel-title">NIGEL <span>v4</span></div>', unsafe_allow_html=True)
    st.markdown("#### Alpha Futures Intelligence — Setup")
    st.markdown('<div class="info-box">Polygon.io free tier covers SPY/QQQ/GLD/USO/DIA as CME proxies + BTC/ETH crypto. Paid tier unlocks native futures. Get your free key at polygon.io</div>', unsafe_allow_html=True)
    with st.form("setup"):
        pk = st.text_input("Polygon.io API Key", type="password")
        if st.form_submit_button("Launch Nigel", type="primary"):
            if pk:
                st.session_state["POLYGON_KEY"] = pk
                _save("POLYGON_KEY", pk)
                st.rerun()
            else:
                st.error("Key required.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_daily(ticker, key, days=120):
    try:
        to = datetime.today().strftime("%Y-%m-%d")
        fr = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        r = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{fr}/{to}"
            f"?adjusted=true&sort=asc&limit={days}&apiKey={key}", timeout=15
        ).json()
        if "results" not in r or len(r["results"]) < 10: return pd.DataFrame()
        df = pd.DataFrame(r["results"])
        df.index = pd.to_datetime(df["t"], unit="ms")
        return df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})[["open","high","low","close","volume"]]
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_intraday(ticker, key, minutes=300):
    try:
        to = datetime.today().strftime("%Y-%m-%d")
        fr = (datetime.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        r = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{fr}/{to}"
            f"?adjusted=true&sort=asc&limit={minutes}&apiKey={key}", timeout=15
        ).json()
        if "results" not in r or len(r["results"]) < 10: return pd.DataFrame()
        df = pd.DataFrame(r["results"])
        df.index = pd.to_datetime(df["t"], unit="ms")
        return df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})[["open","high","low","close","volume"]]
    except: return pd.DataFrame()

@st.cache_data(ttl=120)
def fetch_crypto_daily(cg_id, days=120):
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily", timeout=15
        ).json()
        prices  = [p[1] for p in r["prices"]]
        volumes = [v[1] for v in r.get("total_volumes", [])]
        dates   = [pd.Timestamp(p[0], unit="ms") for p in r["prices"]]
        df = pd.DataFrame({"close": prices, "volume": volumes}, index=dates)
        df["open"] = df["close"].shift(1).fillna(df["close"])
        df["high"] = df["close"] * 1.01
        df["low"]  = df["close"] * 0.99
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_crypto_hourly(cg_id):
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days=3&interval=hourly", timeout=15
        ).json()
        prices = [p[1] for p in r["prices"]]
        dates  = [pd.Timestamp(p[0], unit="ms") for p in r["prices"]]
        df = pd.DataFrame({"close": prices}, index=dates)
        df["open"] = df["close"].shift(1).fillna(df["close"])
        df["high"] = df["close"] * 1.005
        df["low"]  = df["close"] * 0.995
        df["volume"] = 1000
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d = requests.get("https://api.alternative.me/fng/?limit=30", timeout=10).json()["data"]
        return {"value": int(d[0]["value"]), "label": d[0]["value_classification"],
                "history": [int(x["value"]) for x in d]}
    except: return {"value": 50, "label": "Neutral", "history": [50]*30}

# ─────────────────────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────────────────────
def add_indicators(df):
    if df.empty or len(df) < 26: return df
    df = df.copy()
    # EMAs
    for span, col in [(8,"ema8"),(21,"ema21"),(50,"ema50")]:
        df[col] = df["close"].ewm(span=span, adjust=False).mean()
    # MACD
    e12 = df["close"].ewm(span=12, adjust=False).mean()
    e26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]   = e12 - e26
    df["macd_s"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_h"] = df["macd"] - df["macd_s"]
    # RSI-14
    delta = df["close"].diff()
    gain  = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(14).mean().replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + gain / loss))
    # Bollinger
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    df["bb_pct"]   = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
    # ATR
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"]  - df["close"].shift()).abs()
    df["atr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    df["atr_pct"] = df["atr"] / df["close"] * 100
    # Stochastic
    lo14 = df["low"].rolling(14).min()
    hi14 = df["high"].rolling(14).max()
    df["stoch_k"] = 100 * (df["close"] - lo14) / (hi14 - lo14 + 1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    # VWAP (rolling 20-bar)
    if "volume" in df.columns:
        df["vwap"]    = (df["close"] * df["volume"]).rolling(20).sum() / (df["volume"].rolling(20).sum() + 1e-10)
        df["vol_ma"]  = df["volume"].rolling(20).mean()
        df["vol_rat"] = df["volume"] / (df["vol_ma"] + 1e-10)
    # Signal — strict, no inflate
    bull_ema  = (df["ema8"] > df["ema21"]) & (df["ema21"] > df["ema50"])
    bear_ema  = (df["ema8"] < df["ema21"]) & (df["ema21"] < df["ema50"])
    macd_bull = df["macd"] > df["macd_s"]
    macd_bear = df["macd"] < df["macd_s"]
    macd_xup  = macd_bull & ~macd_bull.shift(1).fillna(False)
    macd_xdn  = macd_bear & ~macd_bear.shift(1).fillna(False)
    rsi = df["rsi"]
    df["signal"] = np.where(
        bull_ema & macd_xup & rsi.between(38, 65),      "STRONG BUY",
        np.where(bull_ema & macd_bull & rsi.between(40, 60), "BUY",
        np.where(rsi < 28,                               "OVERSOLD",
        np.where(bear_ema & macd_xdn & rsi.between(35, 62), "STRONG SELL",
        np.where(bear_ema & macd_bear & rsi.between(40, 62), "SELL",
        np.where(rsi > 74,                               "OVERBOUGHT",
        "HOLD"))))))
    return df

def add_scalp_indicators(df):
    if df.empty or len(df) < 14: return df
    df = df.copy()
    for span, col in [(3,"ema3"),(8,"ema8"),(13,"ema13")]:
        df[col] = df["close"].ewm(span=span, adjust=False).mean()
    delta = df["close"].diff()
    gain  = delta.where(delta > 0, 0.0).rolling(7).mean()
    loss  = (-delta.where(delta < 0, 0.0)).rolling(7).mean().replace(0, 1e-10)
    df["rsi7"]    = 100 - (100 / (1 + gain / loss))
    lo9 = df["low"].rolling(9).min()   if "low"  in df.columns else df["close"].rolling(9).min()
    hi9 = df["high"].rolling(9).max()  if "high" in df.columns else df["close"].rolling(9).max()
    df["stoch_k"] = 100 * (df["close"] - lo9) / (hi9 - lo9 + 1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    df["bb_mid"]   = df["close"].rolling(10).mean()
    df["bb_std"]   = df["close"].rolling(10).std()
    df["bb_upper"] = df["bb_mid"] + 1.8 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 1.8 * df["bb_std"]
    df["bb_pct"]   = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
    if "volume" in df.columns:
        df["vwap"]     = (df["close"] * df["volume"]).rolling(20).sum() / (df["volume"].rolling(20).sum() + 1e-10)
        df["vwap_dev"] = (df["close"] - df["vwap"]) / (df["vwap"] + 1e-10) * 100
    else:
        df["vwap_dev"] = 0.0
    hl = (df["high"] - df["low"]) if "high" in df.columns else df["close"] * 0
    hc = (df["high"] - df["close"].shift()).abs() if "high" in df.columns else df["close"] * 0
    lc = (df["low"]  - df["close"].shift()).abs()  if "low"  in df.columns else df["close"] * 0
    df["atr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(7).mean()
    df["mom3"] = df["close"].pct_change(3) * 100
    return df

# ─────────────────────────────────────────────────────────────
# REAL P&L MATH
# ─────────────────────────────────────────────────────────────
def calc_real_pnl(mk, direction, entry, exit_price, contracts):
    """True futures P&L using real contract specs."""
    info = MARKETS[mk]
    tick     = info["tick"]
    tick_usd = info["tick_usd"]
    ticks    = (exit_price - entry) / tick
    if direction == "short": ticks = -ticks
    return round(ticks * tick_usd * contracts, 2)

def calc_ticks(mk, price_diff):
    return abs(price_diff) / MARKETS[mk]["tick"]

def calc_dollar_risk(mk, stop_ticks, contracts):
    return stop_ticks * MARKETS[mk]["tick_usd"] * contracts

# ─────────────────────────────────────────────────────────────
# HONEST BACKTEST — REAL FUTURES P&L
# ─────────────────────────────────────────────────────────────
def run_real_backtest(df, mk, account_size, risk_pct=0.005, rr=2.0, signal_filter="aligned"):
    """
    Backtest with REAL futures dollar P&L.
    risk_pct = fraction of account to risk per trade (e.g. 0.005 = 0.5%)
    rr = reward:risk ratio
    signal_filter: 'aligned'=all 3 EMAs + MACD, 'loose'=any buy/sell signal
    """
    if df.empty or "signal" not in df.columns or len(df) < 40:
        return {"error": "insufficient data"}
    info    = MARKETS[mk]
    tick    = info["tick"]
    tv      = info["tick_usd"]
    max_c   = ALPHA_ACCOUNTS[account_size]["max_contracts"].get(mk, 5)
    capital = ALPHA_ACCOUNTS[account_size]["size"]
    target  = ALPHA_ACCOUNTS[account_size]["target"]
    max_loss= ALPHA_ACCOUNTS[account_size]["max_loss"]
    eod_dd  = ALPHA_ACCOUNTS[account_size]["eod_dd_pct"]

    df = df.dropna(subset=["close", "signal", "rsi", "atr"]).copy()

    balance = float(capital)
    peak    = float(capital)
    trades  = []
    equity  = []
    pos     = None  # {dir, entry, stop, tp, contracts}
    blown   = False
    passed  = False

    for i in range(1, len(df)):
        row   = df.iloc[i]
        prev  = df.iloc[i - 1]
        price = float(row["close"])
        atr   = float(row["atr"])
        sig   = str(prev["signal"])

        # Check open position
        if pos:
            is_long = pos["dir"] == "long"
            pnl = calc_real_pnl(mk, pos["dir"], pos["entry"], price, pos["contracts"])
            hit_sl = (is_long and price <= pos["stop"]) or (not is_long and price >= pos["stop"])
            hit_tp = (is_long and price >= pos["tp"])   or (not is_long and price <= pos["tp"])
            if hit_sl or hit_tp:
                real_pnl = calc_real_pnl(mk, pos["dir"],
                    pos["entry"],
                    pos["tp"] if hit_tp else pos["stop"],
                    pos["contracts"])
                balance += real_pnl
                peak = max(peak, balance)
                dd_pct = (peak - balance) / peak
                result = "win" if real_pnl > 0 else "loss"
                trades.append({
                    "date": df.index[i], "mk": mk,
                    "dir": pos["dir"], "entry": pos["entry"],
                    "exit": pos["tp"] if hit_tp else pos["stop"],
                    "contracts": pos["contracts"],
                    "pnl": real_pnl, "result": result,
                    "reason": "TP" if hit_tp else "SL",
                    "balance_after": round(balance, 2),
                })
                pos = None
                # Check blown / passed
                if balance <= capital - max_loss or dd_pct >= eod_dd:
                    blown = True; break
                if balance >= capital + target:
                    passed = True

        # Look for entry
        if not pos and not blown:
            is_b = sig in ("BUY", "STRONG BUY", "OVERSOLD")
            is_s = sig in ("SELL", "STRONG SELL", "OVERBOUGHT")
            if signal_filter == "aligned":
                # Require all EMAs aligned
                ema_ok_b = float(prev.get("ema8", 0)) > float(prev.get("ema21", 0)) > float(prev.get("ema50", 0))
                ema_ok_s = float(prev.get("ema8", 0)) < float(prev.get("ema21", 0)) < float(prev.get("ema50", 0))
                is_b = is_b and ema_ok_b
                is_s = is_s and ema_ok_s

            direction = "long" if is_b else "short" if is_s else None
            if direction:
                stop_dist = max(atr * 1.2, tick * 4)  # at least 4 ticks
                tp_dist   = stop_dist * rr
                stop  = round(price - stop_dist if direction == "long" else price + stop_dist, 4)
                tp    = round(price + tp_dist   if direction == "long" else price - tp_dist,   4)
                # Size: risk X% of account, max N contracts
                dollar_risk_per_contract = calc_dollar_risk(mk, calc_ticks(mk, stop_dist), 1)
                if dollar_risk_per_contract > 0:
                    contracts = min(
                        max_c,
                        max(1, int((balance * risk_pct) / dollar_risk_per_contract))
                    )
                else:
                    contracts = 1
                pos = {"dir": direction, "entry": price, "stop": stop,
                       "tp": tp, "contracts": contracts}

        equity.append({"date": df.index[i], "equity": balance})

    if not trades:
        return {"error": "no trades generated"}

    tdf   = pd.DataFrame(trades)
    wins  = tdf[tdf["pnl"] > 0]
    losses= tdf[tdf["pnl"] <= 0]
    eq    = pd.DataFrame(equity)
    bh    = (float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / float(df["close"].iloc[0]) * 100

    # Real P&L metrics
    total_pnl   = tdf["pnl"].sum()
    avg_win     = wins["pnl"].mean()   if not wins.empty   else 0
    avg_loss    = losses["pnl"].mean() if not losses.empty else 0
    win_rate    = len(wins) / len(tdf) * 100
    pf          = abs(avg_win / avg_loss) if avg_loss != 0 else 99
    max_dd      = 0.0
    if len(eq) > 1:
        rm   = eq["equity"].cummax()
        dds  = (eq["equity"] - rm) / rm * 100
        max_dd = float(dds.min())
    sharpe = 0.0
    if len(eq) > 2:
        r2 = eq["equity"].pct_change().dropna()
        if r2.std() > 0: sharpe = float(r2.mean() / r2.std() * np.sqrt(252))

    return {
        "mk": mk, "account_size": account_size,
        "capital": capital, "target": target, "max_loss": max_loss,
        "total_pnl": round(total_pnl, 2),
        "final_balance": round(balance, 2),
        "total_return_pct": round((balance - capital) / capital * 100, 2),
        "bh_return": round(bh, 2),
        "win_rate": round(win_rate, 1),
        "total_trades": len(tdf),
        "wins": len(wins), "losses": len(losses),
        "avg_win_usd": round(avg_win, 2),
        "avg_loss_usd": round(avg_loss, 2),
        "profit_factor": round(min(pf, 99.0), 2),
        "max_drawdown": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "equity_curve": eq,
        "trade_list": tdf,
        "blown": blown,
        "passed": passed,
        "signal_filter": signal_filter,
        "risk_pct": risk_pct,
        "rr": rr,
    }

# ─────────────────────────────────────────────────────────────
# MONTE CARLO — ALPHA FUTURES EVAL PROBABILITY
# ─────────────────────────────────────────────────────────────
def monte_carlo_eval(win_rate, avg_win_usd, avg_loss_usd, account_size_key,
                     n_sims=3000, trades_per_day=3, max_days=30):
    """
    Simulate N paths of the Alpha Futures evaluation.
    Returns: probability of passing, probability of blowing, expected days to pass.
    Uses REAL dollar figures from the backtest, not %s.
    """
    acct  = ALPHA_ACCOUNTS[account_size_key]
    start = acct["size"]
    target_profit = acct["target"]
    max_loss      = acct["max_loss"]
    eod_dd_frac   = acct["eod_dd_pct"]

    wr   = win_rate / 100
    avg_w = abs(avg_win_usd)  if avg_win_usd  != 0 else abs(avg_loss_usd) * 2
    avg_l = abs(avg_loss_usd) if avg_loss_usd != 0 else avg_w / 2
    # Add realistic variance
    w_std = avg_w * 0.5
    l_std = avg_l * 0.4

    paths_pass   = 0
    paths_blow   = 0
    days_to_pass = []
    daily_pnls   = []

    for _ in range(n_sims):
        balance  = float(start)
        peak_bal = float(start)
        day_open = float(start)
        passed = blown = False

        for day in range(max_days):
            day_open   = balance
            day_trades = trades_per_day + random.randint(-1, 1)
            day_pnl    = 0.0

            for _ in range(max(1, day_trades)):
                if random.random() < wr:
                    trade_pnl = max(0, np.random.normal(avg_w, w_std))
                else:
                    trade_pnl = -max(0, np.random.normal(avg_l, l_std))
                day_pnl += trade_pnl
                balance += trade_pnl
                peak_bal = max(peak_bal, balance)

                # Intraday blow check
                if (balance <= start - max_loss) or ((peak_bal - balance) / peak_bal >= eod_dd_frac):
                    blown = True; break
                if balance >= start + target_profit:
                    passed = True; break
            if blown or passed: break
            # EOD drawdown check (vs day open)
            eod_dd = (peak_bal - balance) / peak_bal
            if eod_dd >= eod_dd_frac:
                blown = True; break

        daily_pnls.append(balance - start)
        if passed: paths_pass += 1; days_to_pass.append(day + 1)
        if blown:  paths_blow += 1

    pass_pct  = paths_pass / n_sims * 100
    blow_pct  = paths_blow / n_sims * 100
    avg_days  = np.mean(days_to_pass) if days_to_pass else None
    med_final = float(np.median(daily_pnls))
    p10_final = float(np.percentile(daily_pnls, 10))
    p90_final = float(np.percentile(daily_pnls, 90))

    return {
        "pass_prob":  round(pass_pct,  1),
        "blow_prob":  round(blow_pct,  1),
        "neither":    round(100 - pass_pct - blow_pct, 1),
        "avg_days_to_pass": round(avg_days, 1) if avg_days else None,
        "median_pnl": round(med_final, 0),
        "p10_pnl":    round(p10_final, 0),
        "p90_pnl":    round(p90_final, 0),
        "n_sims":     n_sims,
        "sample_paths": min(200, n_sims),
    }

# ─────────────────────────────────────────────────────────────
# SCALP SIGNAL GENERATOR — HONEST CONFIDENCE
# ─────────────────────────────────────────────────────────────
def gen_scalp_signals(intraday_map, daily_signals, selected):
    out = []
    now = datetime.now().strftime("%H:%M")
    for mk in selected:
        df = intraday_map.get(mk, pd.DataFrame())
        if df.empty or len(df) < 15: continue
        df  = add_scalp_indicators(df)
        row = df.iloc[-1]
        prv = df.iloc[-2] if len(df) > 2 else row

        price   = float(row["close"])
        rsi     = float(row.get("rsi7",  50))
        stk     = float(row.get("stoch_k", 50))
        bb_pct  = float(row.get("bb_pct",  0.5))
        vdev    = float(row.get("vwap_dev", 0))
        mom     = float(row.get("mom3",     0))
        atr     = float(row.get("atr",      price * 0.003))
        ema3    = float(row.get("ema3",     price))
        ema8    = float(row.get("ema8",     price))
        prev_stk= float(prv.get("stoch_k",  stk))

        long_sc = short_sc = 0
        reasons = []

        # Long signals
        if rsi < 28:           long_sc += 3; reasons.append(f"RSI {rsi:.0f} ← deeply oversold")
        elif rsi < 35:         long_sc += 1; reasons.append(f"RSI {rsi:.0f} ← low")
        if stk < 15 and stk > prev_stk: long_sc += 2; reasons.append("Stoch %K crossed up <15")
        if bb_pct < 0.08:      long_sc += 2; reasons.append("Lower BB squeeze touch")
        if vdev < -0.7:        long_sc += 1; reasons.append(f"Below VWAP {vdev:.1f}%")
        if ema3 > ema8 and float(prv.get("ema3", ema3)) <= float(prv.get("ema8", ema8)):
                               long_sc += 2; reasons.append("EMA3×EMA8 bullish cross")
        if mom > 0.15:         long_sc += 1; reasons.append(f"Momentum +{mom:.2f}%")

        # Short signals
        if rsi > 72:           short_sc += 3; reasons.append(f"RSI {rsi:.0f} ← deeply overbought")
        elif rsi > 65:         short_sc += 1; reasons.append(f"RSI {rsi:.0f} ← high")
        if stk > 85 and stk < prev_stk: short_sc += 2; reasons.append("Stoch %K crossed down >85")
        if bb_pct > 0.92:      short_sc += 2; reasons.append("Upper BB squeeze touch")
        if vdev > 0.7:         short_sc += 1; reasons.append(f"Above VWAP +{vdev:.1f}%")
        if ema3 < ema8 and float(prv.get("ema3", ema3)) >= float(prv.get("ema8", ema8)):
                               short_sc += 2; reasons.append("EMA3×EMA8 bearish cross")
        if mom < -0.15:        short_sc += 1; reasons.append(f"Momentum {mom:.2f}%")

        # Daily bias alignment bonus
        dsig = daily_signals.get(mk, {}).get("signal", "HOLD")
        if long_sc > short_sc  and ("BUY"  in dsig or dsig == "OVERSOLD"):   long_sc  = int(long_sc  * 1.25)
        if short_sc > long_sc  and ("SELL" in dsig or dsig == "OVERBOUGHT"): short_sc = int(short_sc * 1.25)

        if long_sc >= 4 and long_sc > short_sc:
            direction = "LONG";  score = long_sc
        elif short_sc >= 4 and short_sc > long_sc:
            direction = "SHORT"; score = short_sc
        else:
            continue

        # Honest confidence — max 88%, needs score >= 9 for that
        conf = min(88, 42 + score * 5)
        # Real stop/target using ATR and actual tick sizes
        info     = MARKETS[mk]
        tick     = info["tick"]
        stop_tks = max(4, round(atr / tick))        # ticks of stop
        tp_tks   = round(stop_tks * 1.5)            # 1:1.5 R:R (conservative for scalps)
        stop_dist= stop_tks * tick
        tp_dist  = tp_tks   * tick
        stop  = round(price - stop_dist if direction == "LONG" else price + stop_dist, 4)
        tp    = round(price + tp_dist   if direction == "LONG" else price - tp_dist,   4)
        usd_risk_1c = stop_tks * info["tick_usd"]

        out.append({
            "mk": mk, "label": info["label"], "color": info["color"],
            "direction": direction, "price": price,
            "stop": stop, "tp": tp,
            "stop_ticks": stop_tks, "tp_ticks": tp_tks,
            "usd_risk_1c": round(usd_risk_1c, 2),
            "conf": conf,
            "rsi": round(rsi, 1), "stoch_k": round(stk, 1),
            "bb_pct": round(bb_pct * 100, 1), "vwap_dev": round(vdev, 2),
            "reasons": [r for r in reasons if ("long" in r.lower() or "LONG" not in r) or direction == "LONG"][:4],
            "daily_bias": dsig, "time": now,
        })
    out.sort(key=lambda x: x["conf"], reverse=True)
    return out

# ─────────────────────────────────────────────────────────────
# GET LIVE SIGNAL FROM INDICATORS
# ─────────────────────────────────────────────────────────────
def get_live_signal(df):
    if df.empty or "signal" not in df.columns:
        return {"signal": "HOLD", "conf": 0, "rsi": 50, "price": 0,
                "bb_pct": 0.5, "atr": 0, "atr_pct": 0, "stoch_k": 50, "chg": 0}
    row = df.iloc[-1]
    prv = df.iloc[-2] if len(df) > 1 else row
    sig = str(row.get("signal", "HOLD"))
    rsi = float(row.get("rsi", 50))
    # Honest confidence — tied to signal strength, no inflation
    conf_map = {"STRONG BUY": 75, "BUY": 58, "OVERSOLD": 65,
                "STRONG SELL": 73, "SELL": 56, "OVERBOUGHT": 63, "HOLD": 30}
    conf = conf_map.get(sig, 30)
    chg  = (float(row["close"]) - float(prv["close"])) / float(prv["close"]) * 100
    return {
        "signal": sig, "conf": conf,
        "rsi":     round(float(row.get("rsi",    50)),  1),
        "price":   float(row["close"]),
        "bb_pct":  float(row.get("bb_pct",  0.5)),
        "atr":     float(row.get("atr",     0)),
        "atr_pct": float(row.get("atr_pct", 0)),
        "stoch_k": float(row.get("stoch_k", 50)),
        "chg":     round(chg, 2),
    }

# ─────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────
if "bt_cache"       not in st.session_state: st.session_state["bt_cache"]       = {}
if "mc_cache"       not in st.session_state: st.session_state["mc_cache"]       = {}
if "scalp_sigs"     not in st.session_state: st.session_state["scalp_sigs"]     = []
if "last_scalp"     not in st.session_state: st.session_state["last_scalp"]     = 0.0
if "paper_trades"   not in st.session_state: st.session_state["paper_trades"]   = _get("paper_trades", [])
if "paper_balance"  not in st.session_state: st.session_state["paper_balance"]  = _get("paper_balance", None)

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:Bebas Neue,sans-serif;font-size:1.6rem;color:#ff4d00;letter-spacing:.1em">NIGEL v4</div>', unsafe_allow_html=True)
    st.caption("Alpha Futures Intelligence")
    st.divider()

    with st.expander("🔑 API Key"):
        nk = st.text_input("Polygon.io", value=POLYGON_KEY, type="password")
        if st.button("Save"):
            st.session_state["POLYGON_KEY"] = nk
            _save("POLYGON_KEY", nk)
            st.cache_data.clear(); st.rerun()

    selected_markets = st.multiselect(
        "Instruments", ["ES","NQ","GC","CL","YM","BTC","ETH"],
        default=["ES","NQ","GC","CL"]
    )
    account_key = st.selectbox("Account Size", list(ALPHA_ACCOUNTS.keys()),
                               format_func=lambda x: f"${int(x.replace('k',''))},000", index=1)
    bt_days = st.slider("Lookback (days)", 30, 365, 90)

    st.divider()
    st.markdown("**Backtest Settings**")
    risk_pct = st.slider("Risk per trade (%)", 0.2, 2.0, 0.5, 0.1) / 100
    rr_ratio = st.slider("Reward:Risk", 1.0, 4.0, 2.0, 0.25)
    sig_filter = st.radio("Signal filter", ["aligned", "loose"],
                          help="Aligned = all 3 EMAs + MACD must agree. Loose = any signal.")

    st.divider()
    auto_refresh = st.toggle("Auto-refresh (90s)")
    if st.button("🔄 Refresh data"):     st.cache_data.clear(); st.rerun()
    if st.button("🗑 Clear paper trades"):
        st.session_state["paper_trades"] = []; st.session_state["paper_balance"] = None
        _save("paper_trades", []); _save("paper_balance", None); st.rerun()

    st.divider()
    if PERSIST.exists():
        st.caption(f"💾 {PERSIST.name} ({PERSIST.stat().st_size/1024:.1f} KB)")

if not selected_markets: selected_markets = ["ES", "NQ"]

# ─────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────
CG = {"BTC": "bitcoin", "ETH": "ethereum"}

with st.spinner("Loading market data…"):
    daily_dfs    = {}
    intraday_dfs = {}
    for mk in selected_markets:
        info = MARKETS[mk]
        if info["crypto"]:
            daily_dfs[mk]    = add_indicators(fetch_crypto_daily(CG[mk], days=max(bt_days+15, 120)))
            intraday_dfs[mk] = add_scalp_indicators(fetch_crypto_hourly(CG[mk]))
        else:
            daily_dfs[mk]    = add_indicators(fetch_daily(info["proxy"], POLYGON_KEY, days=max(bt_days+15, 120)))
            intraday_dfs[mk] = add_scalp_indicators(fetch_intraday(info["proxy"], POLYGON_KEY))
    fg = fetch_fear_greed()

live_signals = {mk: get_live_signal(daily_dfs.get(mk, pd.DataFrame())) for mk in selected_markets}

# Scalp signals — refresh every 60s
if time.time() - st.session_state["last_scalp"] > 60:
    st.session_state["scalp_sigs"] = gen_scalp_signals(intraday_dfs, live_signals, selected_markets)
    st.session_state["last_scalp"] = time.time()
scalp_sigs = st.session_state["scalp_sigs"]

# ─────────────────────────────────────────────────────────────
# SESSION CLOCK
# ─────────────────────────────────────────────────────────────
utc  = datetime.now(ZoneInfo("UTC"))
hf   = utc.hour + utc.minute / 60
ny   = utc.astimezone(ZoneInfo("America/New_York"))
chi  = utc.astimezone(ZoneInfo("America/Chicago"))
sessions = []
if 0   <= hf < 9:  sessions.append(("Tokyo", "#7C3AED"))
if 8   <= hf < 17: sessions.append(("London", "#2563EB"))
if 13  <= hf < 22: sessions.append(("New York", "#059669"))
if 13  <= hf < 17: sessions.append(("NY×London Overlap", "#D97706"))
if not sessions:   sessions.append(("Off-hours", "#555"))
cme_live = 13 <= hf < 22

sess_html = " ".join(
    f'<span style="background:{c};color:#fff;border-radius:3px;padding:2px 9px;font-size:11px;font-weight:700">{n}</span>'
    for n, c in sessions
)
cme_html = ('<span style="background:#059669;color:#fff;border-radius:3px;padding:2px 9px;font-size:11px;font-weight:700;margin-left:5px">🔔 CME LIVE</span>'
            if cme_live else
            '<span style="background:#1a1a30;color:#555;border-radius:3px;padding:2px 9px;font-size:11px;margin-left:5px">CME closed</span>')

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="nigel-title">NIGEL <span>v4</span></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-family:Space Mono,monospace;font-size:10px;color:#33334a;letter-spacing:.1em;margin-bottom:4px">'
        f'ALPHA FUTURES INTELLIGENCE · REAL P&L MATH · MONTE CARLO EVAL PROBABILITY</div>',
        unsafe_allow_html=True
    )
with col_h2:
    acct = ALPHA_ACCOUNTS[account_key]
    st.markdown(
        f'<div class="card" style="margin-top:4px">'
        f'<div style="font-size:10px;color:#44445a;font-family:Space Mono,monospace">ACCOUNT</div>'
        f'<div style="font-size:1.1rem;font-weight:600;color:#fff">${acct["size"]:,}</div>'
        f'<div style="font-size:11px;color:#33334a">Target <span style="color:#00e664">${acct["target"]:,}</span> · Max loss <span style="color:#ff3c3c">${acct["max_loss"]:,}</span></div>'
        f'</div>',
        unsafe_allow_html=True
    )

st.markdown(
    f'<div style="margin:10px 0 14px">{sess_html}{cme_html}'
    f'<span style="color:#33334a;font-size:11px;font-family:Space Mono,monospace;margin-left:10px">'
    f'UTC {utc.strftime("%H:%M")} · ET {ny.strftime("%H:%M")} · CT {chi.strftime("%H:%M")}'
    f'</span></div>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────
# LIVE SIGNAL CARDS
# ─────────────────────────────────────────────────────────────
st.markdown('<div style="font-size:11px;color:#33334a;font-family:Space Mono,monospace;margin-bottom:8px">'
            '<span class="live-dot"></span>LIVE · Updates every 5 min</div>', unsafe_allow_html=True)

sig_cols = st.columns(len(selected_markets))
for col, mk in zip(sig_cols, selected_markets):
    with col:
        sig   = live_signals[mk]
        info  = MARKETS[mk]
        s     = sig["signal"]
        is_b  = "BUY" in s or s == "OVERSOLD"
        is_s  = "SELL" in s or s == "OVERBOUGHT"
        bc    = "#00e664" if is_b else "#ff3c3c" if is_s else "#1a1a35"
        cc    = "#00e664" if sig["chg"] >= 0 else "#ff3c3c"
        pc    = "pill-buy" if is_b else "pill-sell" if is_s else "pill-hold"
        scalp = next((sc for sc in scalp_sigs if sc["mk"] == mk), None)
        scalp_bit = (f'<div style="margin-top:5px"><span class="pill pill-scalp">⚡ {scalp["direction"]} {scalp["conf"]}%</span></div>'
                     if scalp else "")
        price_display = f'${sig["price"]:,.1f}' if sig["price"] else ""
        st.markdown(
            f'<div style="border:1.5px solid {bc};border-radius:6px;padding:13px;background:#0c0c1e">'
            f'<div style="font-size:9px;color:#33334a;font-family:Space Mono,monospace">{mk} · {info["label"]}</div>'
            f'<div style="font-size:1.35rem;font-weight:700;color:#fff;font-family:Space Mono,monospace">'
            f'{price_display}</div>'
            f'<div style="font-size:11px;color:{cc};font-family:Space Mono,monospace">{sig["chg"]:+.2f}%</div>'
            f'<div style="margin:5px 0"><span class="pill {pc}">{s}</span></div>'
            f'<div style="font-size:10px;color:#33334a">Conf <b style="color:#fff">{sig["conf"]}%</b> · RSI <b style="color:#fff">{sig["rsi"]}</b></div>'
            f'<div style="font-size:10px;color:#33334a">ATR {sig["atr_pct"]:.2f}%/day</div>'
            f'{scalp_bit}</div>',
            unsafe_allow_html=True
        )

st.divider()

# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────
tab_mc, tab_bt, tab_scalp, tab_chart, tab_ref = st.tabs([
    "🎯 Eval Probability",
    "📊 Real Backtest",
    "⚡ Scalp Signals",
    "📈 Charts",
    "📚 Reference",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — MONTE CARLO EVAL PROBABILITY
# ══════════════════════════════════════════════════════════════
with tab_mc:
    st.subheader("🎯 Alpha Futures Eval Pass Probability")
    st.markdown(
        '<div class="info-box">Runs 3,000 simulated evaluations using your real backtest stats. '
        'Each simulation trades day-by-day respecting the 4% EOD drawdown rule and max loss limit. '
        'This tells you honestly: <b>will you pass or blow the account?</b></div>',
        unsafe_allow_html=True
    )

    mc_mk = st.selectbox("Instrument to simulate", selected_markets, key="mc_mk")
    mc_tpd = st.slider("Avg trades per day", 1, 8, 3)
    mc_days = st.slider("Max eval days", 10, 60, 30)

    run_mc = st.button("▶ Run Monte Carlo (3,000 simulations)", type="primary")

    # Check if we have backtest results for this market
    bt_key = f"{mc_mk}_{account_key}_{bt_days}_{risk_pct}_{rr_ratio}_{sig_filter}"
    cached_bt = st.session_state["bt_cache"].get(bt_key)

    if run_mc:
        # Run backtest first if not cached
        if not cached_bt:
            with st.spinner(f"Running backtest for {mc_mk}…"):
                df_bt = daily_dfs.get(mc_mk, pd.DataFrame())
                bt_res = run_real_backtest(df_bt, mc_mk, account_key, risk_pct, rr_ratio, sig_filter)
                if "error" not in bt_res:
                    st.session_state["bt_cache"][bt_key] = bt_res
                    cached_bt = bt_res

        if cached_bt and "error" not in cached_bt:
            with st.spinner("Simulating 3,000 evaluation paths…"):
                mc = monte_carlo_eval(
                    win_rate=cached_bt["win_rate"],
                    avg_win_usd=cached_bt["avg_win_usd"],
                    avg_loss_usd=cached_bt["avg_loss_usd"],
                    account_size_key=account_key,
                    n_sims=3000,
                    trades_per_day=mc_tpd,
                    max_days=mc_days,
                )
                st.session_state["mc_cache"][mc_mk] = mc
        else:
            st.error("Run a backtest first (or not enough data). Check the Backtest tab.")

    mc_res = st.session_state["mc_cache"].get(mc_mk)

    if mc_res:
        pass_p = mc_res["pass_prob"]
        blow_p = mc_res["blow_prob"]
        neit_p = mc_res["neither"]

        # Big probability display
        pc = "#00e664" if pass_p >= 60 else "#ffb400" if pass_p >= 40 else "#ff3c3c"
        bc2= "#ff3c3c" if blow_p >= 40 else "#ffb400" if blow_p >= 20 else "#33334a"

        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:20px">
          <div class="card" style="text-align:center;border-top:3px solid {pc}">
            <div class="stat-lbl">PASS PROBABILITY</div>
            <div class="stat-val" style="font-size:3rem;color:{pc}">{pass_p}%</div>
            <div style="font-size:11px;color:#44445a">of {mc_res["n_sims"]:,} simulations</div>
          </div>
          <div class="card" style="text-align:center;border-top:3px solid {bc2}">
            <div class="stat-lbl">BLOW PROBABILITY</div>
            <div class="stat-val" style="font-size:3rem;color:{bc2}">{blow_p}%</div>
            <div style="font-size:11px;color:#44445a">hit max loss / EOD 4% limit</div>
          </div>
          <div class="card" style="text-align:center;border-top:3px solid #33334a">
            <div class="stat-lbl">STILL IN EVAL</div>
            <div class="stat-val" style="font-size:3rem;color:#7878a0">{neit_p}%</div>
            <div style="font-size:11px;color:#44445a">incomplete at day {mc_days}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Probability bar
        st.markdown(f"""
        <div style="margin-bottom:16px">
          <div style="font-size:10px;color:#44445a;font-family:Space Mono,monospace;margin-bottom:6px">OUTCOME DISTRIBUTION</div>
          <div style="display:flex;height:24px;border-radius:4px;overflow:hidden">
            <div style="background:#00e664;width:{pass_p}%;display:flex;align-items:center;justify-content:center;font-size:10px;font-family:Space Mono,monospace;color:#000;font-weight:700">{"PASS " + str(pass_p) + "%" if pass_p > 8 else ""}</div>
            <div style="background:#1a1a35;width:{neit_p}%;display:flex;align-items:center;justify-content:center;font-size:10px;color:#555">{"..." if neit_p > 5 else ""}</div>
            <div style="background:#ff3c3c;width:{blow_p}%;display:flex;align-items:center;justify-content:center;font-size:10px;font-family:Space Mono,monospace;color:#fff;font-weight:700">{"BLOW " + str(blow_p) + "%" if blow_p > 8 else ""}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Stats
        avg_d = mc_res.get("avg_days_to_pass")
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px">
          <div class="card">
            <div class="stat-lbl">Avg days to pass</div>
            <div class="stat-val" style="color:#00e664">{avg_d if avg_d else "N/A"}</div>
          </div>
          <div class="card">
            <div class="stat-lbl">Median P&L at end</div>
            <div class="stat-val" style="color:{"#00e664" if mc_res["median_pnl"]>=0 else "#ff3c3c"}">${mc_res["median_pnl"]:+,}</div>
          </div>
          <div class="card">
            <div class="stat-lbl">10th percentile</div>
            <div class="stat-val" style="color:#ff3c3c">${mc_res["p10_pnl"]:+,}</div>
          </div>
          <div class="card">
            <div class="stat-lbl">90th percentile</div>
            <div class="stat-val" style="color:#00e664">${mc_res["p90_pnl"]:+,}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Verdict
        if pass_p >= 65:
            verdict = f'<div class="card card-accent-green"><b style="color:#00e664">✅ Strong edge.</b> Your backtest stats give you a real shot at passing. Keep risk at {risk_pct*100:.1f}% per trade and don\'t deviate from your system.</div>'
        elif pass_p >= 45:
            verdict = f'<div class="card card-accent-gold"><b style="color:#ffb400">⚠️ Marginal edge.</b> Coin-flip territory. Consider cutting risk per trade to 0.3–0.4% and only trading the highest-confidence signals.</div>'
        elif pass_p >= 25:
            verdict = f'<div class="card card-accent-red"><b style="color:#ff3c3c">❌ Low probability.</b> The current strategy doesn\'t have enough edge to reliably pass. Improve win rate or R:R before trying the eval.</div>'
        else:
            verdict = f'<div class="card card-accent-red"><b style="color:#ff3c3c">🚨 Do not attempt eval yet.</b> Less than 25% pass probability. The strategy is losing money in backtests — fix this first.</div>'
        st.markdown(verdict, unsafe_allow_html=True)

        # What needs to improve
        if cached_bt:
            st.markdown("#### What would improve your odds?")
            imp_cols = st.columns(3)
            # Scenario A: better RR
            mc_a = monte_carlo_eval(cached_bt["win_rate"], cached_bt["avg_win_usd"] * 1.5,
                                    cached_bt["avg_loss_usd"], account_key,
                                    n_sims=1000, trades_per_day=mc_tpd, max_days=mc_days)
            # Scenario B: better win rate
            mc_b = monte_carlo_eval(min(75, cached_bt["win_rate"] + 10), cached_bt["avg_win_usd"],
                                    cached_bt["avg_loss_usd"], account_key,
                                    n_sims=1000, trades_per_day=mc_tpd, max_days=mc_days)
            # Scenario C: fewer trades
            mc_c = monte_carlo_eval(cached_bt["win_rate"], cached_bt["avg_win_usd"],
                                    cached_bt["avg_loss_usd"], account_key,
                                    n_sims=1000, trades_per_day=max(1, mc_tpd - 1), max_days=mc_days)
            for col2, (lbl2, res2, desc2) in zip(imp_cols, [
                (f"If avg win = ${abs(cached_bt['avg_win_usd'])*1.5:.0f}", mc_a, "Improve RR to 1:3"),
                (f"If win rate = {min(75,cached_bt['win_rate']+10):.0f}%", mc_b, "Better entry timing"),
                (f"If {max(1,mc_tpd-1)} trades/day", mc_c, "Be more selective"),
            ]):
                delta = res2["pass_prob"] - pass_p
                dc = "#00e664" if delta > 0 else "#ff3c3c"
                col2.markdown(
                    f'<div class="card"><div style="font-size:11px;color:#fff;font-weight:600">{desc2}</div>'
                    f'<div style="font-size:10px;color:#44445a">{lbl2}</div>'
                    f'<div style="margin-top:8px;font-size:1.2rem;font-family:Space Mono,monospace;color:{dc}">'
                    f'{res2["pass_prob"]}% <span style="font-size:12px">({delta:+.0f}%)</span></div></div>',
                    unsafe_allow_html=True
                )
    else:
        st.info("Configure your settings above and click **Run Monte Carlo** to see your eval pass probability.")

# ══════════════════════════════════════════════════════════════
# TAB 2 — REAL BACKTEST
# ══════════════════════════════════════════════════════════════
with tab_bt:
    st.subheader("📊 Real Futures Backtest")
    st.markdown(
        '<div class="info-box">P&L is in <b>real futures dollars</b> using actual tick sizes and values. '
        'SPY/QQQ/GLD are used as proxies for ES/NQ/GC — price levels differ but % moves are representative. '
        'Max contracts per Alpha Futures rules enforced.</div>',
        unsafe_allow_html=True
    )

    bt_mk_sel = st.selectbox("Instrument", selected_markets, key="bt_mk_sel")
    run_bt = st.button("▶ Run Backtest", type="primary", key="run_bt_btn")

    bt_key2 = f"{bt_mk_sel}_{account_key}_{bt_days}_{risk_pct}_{rr_ratio}_{sig_filter}"
    if run_bt:
        with st.spinner("Running real P&L backtest…"):
            df_bt2 = daily_dfs.get(bt_mk_sel, pd.DataFrame())
            bt2 = run_real_backtest(df_bt2, bt_mk_sel, account_key, risk_pct, rr_ratio, sig_filter)
            st.session_state["bt_cache"][bt_key2] = bt2

    bt2 = st.session_state["bt_cache"].get(bt_key2)

    if bt2 and "error" not in bt2:
        info2 = MARKETS[bt_mk_sel]
        acct2 = ALPHA_ACCOUNTS[account_key]

        # Status flags
        if bt2["blown"]:
            st.markdown('<div class="warn-box">🚨 This strategy would have <b>BLOWN the account</b> in the backtest period — hit the max loss or 4% EOD drawdown limit.</div>', unsafe_allow_html=True)
        elif bt2["passed"]:
            st.markdown('<div class="card card-accent-green" style="margin-bottom:10px">✅ This strategy <b>would have PASSED the Alpha Futures evaluation</b> in the backtest period.</div>', unsafe_allow_html=True)

        # Proxy disclaimer
        proxy = info2["proxy"]
        st.markdown(f'<div style="font-size:11px;color:#33334a;margin-bottom:12px;font-family:Space Mono,monospace">⚠ Using {proxy} as proxy for {bt_mk_sel} · Tick={info2["tick"]} · ${info2["tick_usd"]}/tick · Max {acct2["max_contracts"].get(bt_mk_sel,5)} contracts</div>', unsafe_allow_html=True)

        # Key metrics
        pnl_c    = "#00e664" if bt2["total_pnl"] >= 0 else "#ff3c3c"
        ret_c    = "#00e664" if bt2["total_return_pct"] >= 0 else "#ff3c3c"
        metrics  = [
            ("Total P&L",     f'${bt2["total_pnl"]:+,.0f}',   pnl_c),
            ("Return %",      f'{bt2["total_return_pct"]:+.1f}%', ret_c),
            ("vs Buy&Hold",   f'{bt2["bh_return"]:+.1f}%',    "#7878a0"),
            ("Win Rate",      f'{bt2["win_rate"]:.0f}%',       "#fff"),
            ("Trades",        str(bt2["total_trades"]),         "#fff"),
            ("Avg Win",       f'${bt2["avg_win_usd"]:+,.0f}',  "#00e664"),
            ("Avg Loss",      f'${bt2["avg_loss_usd"]:+,.0f}', "#ff3c3c"),
            ("Profit Factor", f'{bt2["profit_factor"]:.2f}',   "#ffb400" if bt2["profit_factor"] >= 1.5 else "#ff3c3c"),
            ("Max Drawdown",  f'{bt2["max_drawdown"]:.1f}%',   "#ff3c3c"),
            ("Sharpe",        f'{bt2["sharpe"]:.2f}',           "#00aaff"),
        ]
        mc2 = st.columns(5)
        for i, (lbl2, val2, vc2) in enumerate(metrics):
            mc2[i % 5].markdown(
                f'<div class="card" style="margin-bottom:8px;text-align:center">'
                f'<div class="stat-val" style="color:{vc2}">{val2}</div>'
                f'<div class="stat-lbl">{lbl2}</div></div>',
                unsafe_allow_html=True
            )

        # Alpha Futures progress toward target
        progress_pct = min(100, max(0, bt2["total_pnl"] / acct2["target"] * 100))
        p_col = "#00e664" if progress_pct >= 50 else "#ffb400" if progress_pct >= 25 else "#ff3c3c"
        st.markdown(f"""
        <div style="margin:16px 0">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:#44445a;font-family:Space Mono,monospace;margin-bottom:5px">
            <span>PROFIT TARGET PROGRESS</span>
            <span>${bt2["total_pnl"]:+,.0f} / ${acct2["target"]:,}</span>
          </div>
          <div class="mc-bar-wrap" style="height:12px">
            <div class="mc-bar-fill" style="width:{progress_pct}%;background:{p_col}"></div>
          </div>
          <div style="font-size:10px;color:#33334a;text-align:right">{progress_pct:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

        # Equity curve
        eq = bt2["equity_curve"]
        if not eq.empty:
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                x=eq["date"], y=eq["equity"],
                fill="tozeroy",
                fillcolor=f"rgba(0,230,100,0.06)" if bt2["total_pnl"] >= 0 else "rgba(255,60,60,0.06)",
                line=dict(color="#00e664" if bt2["total_pnl"] >= 0 else "#ff3c3c", width=2),
                name="Balance"
            ))
            fig_eq.add_hline(y=float(acct2["size"]), line=dict(color="#333355", width=1, dash="dot"))
            fig_eq.add_hline(y=float(acct2["size"] + acct2["target"]),
                             line=dict(color="#00e66455", width=1, dash="dot"),
                             annotation_text="Target", annotation_font_color="#00e664")
            fig_eq.add_hline(y=float(acct2["size"] - acct2["max_loss"]),
                             line=dict(color="#ff3c3c55", width=1, dash="dot"),
                             annotation_text="Max Loss", annotation_font_color="#ff3c3c")
            fig_eq.update_layout(
                height=280, template="plotly_dark",
                paper_bgcolor="#05050f", plot_bgcolor="#0c0c1e",
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis=dict(gridcolor="#0f0f20"), yaxis=dict(gridcolor="#0f0f20"),
                showlegend=False, title=dict(text="Account Equity (Real $ P&L)", font=dict(color="#44445a", size=12))
            )
            st.plotly_chart(fig_eq, width="stretch", key="bt_eq")

        # Trade log
        with st.expander(f"📋 Trade log ({bt2['total_trades']} trades)"):
            tlog = bt2["trade_list"].copy()
            tlog["date"] = pd.to_datetime(tlog["date"]).dt.strftime("%Y-%m-%d")
            st.dataframe(
                tlog[["date","dir","entry","exit","contracts","pnl","result","reason","balance_after"]].style
                    .format({"entry": "${:,.2f}", "exit": "${:,.2f}",
                             "pnl": "${:+,.0f}", "balance_after": "${:,.0f}"})
                    .map(lambda v: "color:#00e664" if isinstance(v, (int,float)) and v > 0
                         else "color:#ff3c3c" if isinstance(v, (int,float)) and v < 0 else "",
                         subset=["pnl"]),
                width="stretch", hide_index=True
            )

    elif bt2 and "error" in bt2:
        st.warning(f"Backtest failed: {bt2['error']}. Try a longer lookback window or different instrument.")
    else:
        st.info("Select an instrument and click **▶ Run Backtest**.")

# ══════════════════════════════════════════════════════════════
# TAB 3 — SCALP SIGNALS
# ══════════════════════════════════════════════════════════════
with tab_scalp:
    st.subheader("⚡ Scalp Signals — 5-min / Hourly")
    st.markdown(
        '<div class="info-box">Signals based on EMA3/8/13 crosses, RSI-7, Stochastic extremes, '
        'VWAP deviation, BB squeezes. Max confidence capped at 88%. Entry/stop/target in <b>real ticks</b>. '
        'Crypto uses hourly bars (5-min not available free).</div>',
        unsafe_allow_html=True
    )

    if st.button("🔄 Refresh scalp signals"):
        st.session_state["last_scalp"] = 0; st.rerun()

    min_conf_s = st.slider("Min confidence", 50, 85, 60, key="sc_conf")
    filtered_s = [s for s in scalp_sigs if s["conf"] >= min_conf_s]

    if not filtered_s:
        st.info(f"No scalp signals above {min_conf_s}% confidence right now.")
    else:
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Signals", len(filtered_s))
        sc2.metric("🟢 Long",  sum(1 for s in filtered_s if s["direction"] == "LONG"))
        sc3.metric("🔴 Short", sum(1 for s in filtered_s if s["direction"] == "SHORT"))

        for s in filtered_s:
            is_long = s["direction"] == "LONG"
            dc = "#00e664" if is_long else "#ff3c3c"
            bc_card = "#001a08" if is_long else "#1a0005"
            reasons_html = " · ".join(
                f'<span style="color:#44445a;font-size:11px">{r}</span>'
                for r in s["reasons"]
            )
            dsig_c = "#00e664" if "BUY" in s["daily_bias"] else "#ff3c3c" if "SELL" in s["daily_bias"] else "#555"
            max_c_here = ALPHA_ACCOUNTS[account_key]["max_contracts"].get(s["mk"], 5)

            st.markdown(f"""
            <div style="border:1.5px solid {dc};border-radius:6px;padding:16px;background:{bc_card};margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">
                <div>
                  <span style="color:{dc};font-size:1.1rem;font-weight:700;font-family:Space Mono,monospace">
                    {"▲ LONG" if is_long else "▼ SHORT"}
                  </span>
                  <span style="color:#aaa;margin-left:8px;font-size:13px">{s["label"]}</span>
                  <span style="background:{dc}22;color:{dc};border-radius:3px;padding:1px 8px;font-size:10px;margin-left:6px;font-family:Space Mono,monospace">{s["conf"]}% CONF</span>
                </div>
                <div style="font-size:10px;color:#33334a;font-family:Space Mono,monospace">{s["time"]}</div>
              </div>

              <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px">
                <div style="background:#0c0c1e;border-radius:4px;padding:8px;text-align:center">
                  <div style="font-size:9px;color:#33334a">ENTRY</div>
                  <div style="color:#ffb400;font-family:Space Mono,monospace;font-size:13px;font-weight:700">{s["price"]:,.1f}</div>
                </div>
                <div style="background:#0c0c1e;border-radius:4px;padding:8px;text-align:center">
                  <div style="font-size:9px;color:#33334a">STOP</div>
                  <div style="color:#ff3c3c;font-family:Space Mono,monospace;font-size:13px;font-weight:700">{s["stop"]:,.1f}</div>
                  <div style="font-size:9px;color:#33334a">{s["stop_ticks"]:.0f} ticks</div>
                </div>
                <div style="background:#0c0c1e;border-radius:4px;padding:8px;text-align:center">
                  <div style="font-size:9px;color:#33334a">TARGET</div>
                  <div style="color:#00e664;font-family:Space Mono,monospace;font-size:13px;font-weight:700">{s["tp"]:,.1f}</div>
                  <div style="font-size:9px;color:#33334a">{s["tp_ticks"]:.0f} ticks</div>
                </div>
                <div style="background:#0c0c1e;border-radius:4px;padding:8px;text-align:center">
                  <div style="font-size:9px;color:#33334a">$/contract</div>
                  <div style="color:#fff;font-family:Space Mono,monospace;font-size:13px;font-weight:700">${s["usd_risk_1c"]:,.0f}</div>
                  <div style="font-size:9px;color:#33334a">risk</div>
                </div>
                <div style="background:#0c0c1e;border-radius:4px;padding:8px;text-align:center">
                  <div style="font-size:9px;color:#33334a">MAX LOTS</div>
                  <div style="color:#cc88ff;font-family:Space Mono,monospace;font-size:13px;font-weight:700">{max_c_here}</div>
                  <div style="font-size:9px;color:#33334a">Alpha limit</div>
                </div>
              </div>

              <div style="margin-bottom:6px">{reasons_html}</div>
              <div style="font-size:10px;color:#33334a;font-family:Space Mono,monospace">
                RSI-7:{s["rsi"]} · Stoch:{s["stoch_k"]} · BB%:{s["bb_pct"]} · VWAP:{s["vwap_dev"]:+.2f}%
                · Daily: <span style="color:{dsig_c}">{s["daily_bias"]}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 4 — CHARTS
# ══════════════════════════════════════════════════════════════
with tab_chart:
    st.subheader("📈 Charts")
    chart_mk = st.selectbox("Instrument", selected_markets, key="ch_mk")
    show_sig = st.toggle("Show signals", value=True)

    df_ch = daily_dfs.get(chart_mk, pd.DataFrame())
    if df_ch.empty:
        st.warning("No data available.")
    else:
        info_ch = MARKETS[chart_mk]
        fig_ch = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.50, 0.18, 0.18, 0.14],
            vertical_spacing=0.025,
        )
        # BB
        if "bb_upper" in df_ch.columns:
            fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch["bb_upper"],
                line=dict(color="rgba(100,100,200,0.2)", width=1), showlegend=False), row=1, col=1)
            fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch["bb_lower"],
                line=dict(color="rgba(100,100,200,0.2)", width=1),
                fill="tonexty", fillcolor="rgba(80,80,180,0.04)", showlegend=False), row=1, col=1)
        # Candles or line
        if "open" in df_ch.columns:
            fig_ch.add_trace(go.Candlestick(
                x=df_ch.index, open=df_ch["open"], high=df_ch["high"],
                low=df_ch["low"], close=df_ch["close"],
                increasing_line_color="#00e664", decreasing_line_color="#ff3c3c",
                name="Price"), row=1, col=1)
        else:
            fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch["close"],
                line=dict(color=info_ch["color"], width=2), name="Price"), row=1, col=1)
        # EMAs
        for col2, c2, n2 in [("ema8","#5DCAA5","EMA8"),("ema21","#ED93B1","EMA21"),("ema50","#F59E0B","EMA50")]:
            if col2 in df_ch.columns:
                fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch[col2],
                    line=dict(color=c2, width=1.2, dash="dot"), name=n2), row=1, col=1)
        # Signals
        if show_sig and "signal" in df_ch.columns:
            for sigs2, sym2, sz2, sc3 in [
                (["BUY","STRONG BUY","OVERSOLD"],    "triangle-up",   9,  "#00e664"),
                (["STRONG BUY"],                      "star",         14,  "#00ffcc"),
                (["SELL","STRONG SELL","OVERBOUGHT"], "triangle-down", 9,  "#ff3c3c"),
                (["STRONG SELL"],                     "x",            12,  "#ff0000"),
            ]:
                sub2 = df_ch[df_ch["signal"].isin(sigs2)]
                if not sub2.empty:
                    fig_ch.add_trace(go.Scatter(x=sub2.index, y=sub2["close"],
                        mode="markers", marker=dict(symbol=sym2, size=sz2, color=sc3),
                        name=sigs2[0]), row=1, col=1)
        # MACD
        if "macd" in df_ch.columns:
            mh = df_ch["macd_h"].fillna(0).tolist()
            mc3 = ["rgba(0,230,100,0.8)" if v >= 0 else "rgba(255,60,60,0.8)" for v in mh]
            fig_ch.add_trace(go.Bar(x=df_ch.index, y=df_ch["macd_h"],
                marker_color=mc3, showlegend=False), row=2, col=1)
            fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch["macd"],
                line=dict(color=info_ch["color"], width=1.5), name="MACD"), row=2, col=1)
            fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch["macd_s"],
                line=dict(color="#ED93B1", width=1.5), name="Signal"), row=2, col=1)
        # RSI
        if "rsi" in df_ch.columns:
            fig_ch.add_trace(go.Scatter(x=df_ch.index, y=df_ch["rsi"],
                line=dict(color="#cc88ff", width=2), name="RSI"), row=3, col=1)
            for lvl2, lc2 in [(70, "rgba(255,60,60,0.5)"), (30, "rgba(0,230,100,0.5)"), (50, "rgba(60,60,80,0.5)")]:
                fig_ch.add_hline(y=lvl2, line=dict(color=lc2, width=1, dash="dash"), row=3, col=1)
        # Volume
        if "volume" in df_ch.columns:
            vc3 = ["rgba(0,230,100,0.6)" if float(df_ch["close"].iloc[i2]) >= float(df_ch["open"].iloc[i2])
                   else "rgba(255,60,60,0.6)" for i2 in range(len(df_ch))]
            fig_ch.add_trace(go.Bar(x=df_ch.index, y=df_ch["volume"],
                marker_color=vc3, showlegend=False), row=4, col=1)

        fig_ch.update_layout(
            height=820, template="plotly_dark",
            paper_bgcolor="#05050f", plot_bgcolor="#0c0c1e",
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.02, font=dict(size=10)),
            margin=dict(l=0, r=0, t=30, b=0),
            title=dict(text=f"{chart_mk} — {info_ch['label']} (proxy: {info_ch['proxy']})",
                       font=dict(color="#44445a", size=12))
        )
        fig_ch.update_xaxes(gridcolor="#0f0f20", zerolinecolor="#0f0f20")
        fig_ch.update_yaxes(gridcolor="#0f0f20", zerolinecolor="#0f0f20")
        st.plotly_chart(fig_ch, width="stretch", key="main_chart")

# ══════════════════════════════════════════════════════════════
# TAB 5 — REFERENCE
# ══════════════════════════════════════════════════════════════
with tab_ref:
    st.subheader("📚 Alpha Futures Reference")

    st.markdown("""
### What Changed in Nigel v4

| Feature | v3 (old) | v4 (now) |
|---|---|---|
| P&L calculation | % of capital, fake | Real $ using tick×tick_value×contracts |
| "100 AI" ensemble | 10 configs × 10 noise = theater | Removed. One honest backtest per strategy |
| Confidence scores | Inflated to 80–95% | Capped at 88%, tied to actual indicator strength |
| Eval probability | Not modeled | Monte Carlo 3,000 paths using your real stats |
| Contract limits | Ignored | Alpha Futures limits enforced in backtest & sizing |
| Proxy disclosure | Hidden | Shown everywhere |

---
### Contract Specs
""")

    spec_rows = []
    for mk, info in MARKETS.items():
        acct2 = ALPHA_ACCOUNTS[account_key]
        spec_rows.append({
            "Contract": f"{mk} — {info['label']}",
            "Tick Size": info["tick"],
            "$/Tick": f"${info['tick_usd']}",
            "Proxy (free tier)": info["proxy"],
            f"Max lots ({account_key})": acct2["max_contracts"].get(mk, "—"),
            "Notes": info["desc"][:70],
        })
    st.dataframe(pd.DataFrame(spec_rows), width="stretch", hide_index=True)

    st.markdown("""
---
### Alpha Futures Eval Rules
| Rule | Detail |
|---|---|
| Profit target | 10% of account (e.g. $2,500 on 25k) |
| Max loss limit | 4% EOD (end-of-day balance, NOT intraday high) |
| Daily loss limit | None during eval |
| No consistency rule | Trade any size within limits |
| No news restrictions | Can trade through events |
| Scaling | Available post-eval |

### Sizing Formula (used in backtest)
```
Dollar risk per contract = stop_ticks × tick_usd
Contracts = min(max_allowed, floor(account × risk_pct / dollar_risk_per_contract))
```

### Prime Trading Windows (CME)
- **9:30–11:00 ET** — highest volatility, best ES/NQ signals
- **14:00–15:00 ET** — afternoon trend continuation
- **London open 3:00–5:00 ET** — GC/CL best opportunity
- Avoid: 12:00–13:30 ET (lunch lull), last 10 min before close

### Honest Disclaimer
Nigel uses ETF proxies (SPY→ES, QQQ→NQ, etc.) because real CME tick data requires
a Polygon.io paid tier. The **% price moves are representative**, but **dollar P&L
will differ** because ES trades at ~5,500 while SPY trades at ~550.
The Monte Carlo uses your actual win rate and average trade dollar amounts from the
backtest to project probability — this is the most honest forward estimate possible
with the available data.
""")

# ─────────────────────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(90)
    st.cache_data.clear()
    st.rerun()
