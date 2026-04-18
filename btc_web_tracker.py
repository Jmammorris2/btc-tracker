"""
Nigel v3 — Alpha Futures Edition
CME Futures: ES, NQ, CL, GC, YM + crypto futures (BTC, ETH)
Data: Polygon.io (CME + crypto) | Persistent state | Hyper-short scalp signals
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json, pathlib

st.set_page_config(
    page_title="Nigel — Alpha Futures Intelligence",
    layout="wide", page_icon="⚡",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Syne:wght@400;700;800&display=swap');
html,body,[class*="css"]{font-family:'Syne',sans-serif;}
.main-title{font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:800;
  background:linear-gradient(90deg,#ff6b00,#ffd700,#00d4ff);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;letter-spacing:-0.03em;margin-bottom:0;}
.subtitle{color:#445566;font-size:12px;font-family:'JetBrains Mono',monospace;margin-bottom:18px;letter-spacing:.05em;}
.sig-badge{display:inline-block;border-radius:4px;padding:3px 12px;font-size:11px;font-weight:700;
  letter-spacing:.06em;font-family:'JetBrains Mono',monospace;}
.sig-buy{background:rgba(0,255,136,0.1);color:#00ff88;border:1px solid rgba(0,255,136,0.3);}
.sig-sell{background:rgba(255,68,68,0.1);color:#ff4444;border:1px solid rgba(255,68,68,0.3);}
.sig-hold{background:rgba(136,136,136,0.1);color:#888;border:1px solid rgba(136,136,136,0.3);}
.sig-scalp{background:rgba(255,200,0,0.15);color:#ffd700;border:1px solid rgba(255,200,0,0.4);}
.note-card{border-radius:10px;padding:13px 17px;margin-bottom:9px;font-size:13px;line-height:1.65;}
.note-watch{background:#1a1400;border-left:3px solid #f0a500;color:#ffd166;}
.note-buy{background:#001a0a;border-left:3px solid #00ff88;color:#88ffcc;}
.note-sell{background:#1a0000;border-left:3px solid #ff4444;color:#ff9999;}
.note-info{background:#001020;border-left:3px solid #00d4ff;color:#88ddff;}
.bt-stat{background:#0a0a1a;border:1px solid #1a1a2e;border-radius:8px;padding:10px;text-align:center;}
.bt-val{font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;}
.bt-lbl{font-size:10px;color:#555;margin-top:2px;}
.scalp-card{background:#0d0d00;border:2px solid #ffd700;border-radius:10px;padding:14px 18px;margin-bottom:10px;}
.scalp-urgent{background:#1a0d00;border:2px solid #ff6600;border-radius:10px;padding:14px 18px;margin-bottom:10px;}
.profit-best{background:#001a0a;border:2px solid #00ff88;border-radius:12px;padding:18px;margin-bottom:10px;}
.profit-good{background:#0a0a1a;border:1px solid #00d4ff44;border-radius:12px;padding:14px;margin-bottom:8px;}
.stTabs [data-baseweb="tab-list"]{background:#080818;border-radius:10px;padding:4px;}
.stTabs [data-baseweb="tab"]{border-radius:8px;color:#666;font-size:13px;}
.stTabs [aria-selected="true"]{background:#1a1a3a;color:#fff;}
</style>
""", unsafe_allow_html=True)

# ── PERSISTENCE ───────────────────────────────────────────────────────────────
PERSIST_FILE = pathlib.Path("nigel_af_state.json")

def load_persist():
    if PERSIST_FILE.exists():
        try:
            with open(PERSIST_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def persist_set(key, value):
    try:
        d = load_persist(); d[key] = value
        with open(PERSIST_FILE, "w") as f: json.dump(d, f, default=str)
    except: pass

def persist_get(key, default=None):
    return load_persist().get(key, default)

# ── CME FUTURES INSTRUMENTS ───────────────────────────────────────────────────
# Alpha Futures trades these CME products. Polygon tickers for equities/ETFs
# are used as proxies where direct futures data needs a paid tier.
# SPY=ES proxy, QQQ=NQ proxy, GLD=GC proxy, USO=CL proxy, DIA=YM proxy
MARKETS = {
    "ES":  {"label":"E-mini S&P 500 (ES)",     "poly_ticker":"SPY",       "color":"#22c55e", "crypto":False,
            "tick":0.25, "tick_val":12.50, "contract_val":"$50×price",
            "alpha_limits":{"10k":6,"25k":10,"50k":15,"100k":20},
            "desc":"Most liquid futures. NY session king. Reacts to every economic print."},
    "NQ":  {"label":"E-mini Nasdaq 100 (NQ)",  "poly_ticker":"QQQ",       "color":"#378add", "crypto":False,
            "tick":0.25, "tick_val":5.00, "contract_val":"$20×price",
            "alpha_limits":{"10k":3,"25k":6,"50k":10,"100k":15},
            "desc":"Higher beta than ES. Tech sector driven. Best momentum instrument."},
    "GC":  {"label":"Gold Futures (GC)",       "poly_ticker":"GLD",       "color":"#f0a500", "crypto":False,
            "tick":0.10, "tick_val":10.00, "contract_val":"100 troy oz",
            "alpha_limits":{"10k":2,"25k":4,"50k":8,"100k":12},
            "desc":"Safe haven. Moves on USD strength, Fed policy, geopolitics."},
    "CL":  {"label":"Crude Oil (CL)",          "poly_ticker":"USO",       "color":"#f87171", "crypto":False,
            "tick":0.01, "tick_val":10.00, "contract_val":"1000 barrels",
            "alpha_limits":{"10k":2,"25k":4,"50k":6,"100k":10},
            "desc":"High volatility. EIA Wednesday data moves it 1-2%. Trending instrument."},
    "YM":  {"label":"Dow Jones (YM)",          "poly_ticker":"DIA",       "color":"#a78bfa", "crypto":False,
            "tick":1.0,  "tick_val":5.00,  "contract_val":"$5×price",
            "alpha_limits":{"10k":3,"25k":6,"50k":10,"100k":15},
            "desc":"Slower than ES/NQ. Value stocks driven. Less prone to algo spikes."},
    "BTC": {"label":"Bitcoin (Micro BTC Fut)", "poly_ticker":"X:BTCUSD",  "color":"#f0a500", "crypto":True,
            "tick":5.0,  "tick_val":25.00, "contract_val":"0.1 BTC",
            "alpha_limits":{"10k":1,"25k":2,"50k":3,"100k":5},
            "desc":"Crypto futures on CME. High overnight gap risk. 24/7 market."},
    "ETH": {"label":"Ether (Micro ETH Fut)",   "poly_ticker":"X:ETHUSD",  "color":"#627eea", "crypto":True,
            "tick":0.01, "tick_val":0.10,  "contract_val":"0.1 ETH",
            "alpha_limits":{"10k":1,"25k":2,"50k":3,"100k":5},
            "desc":"Follows BTC with higher beta. DeFi/protocol news sensitive."},
}

# Alpha Futures account sizes and rules
ALPHA_ACCOUNTS = {
    "10k Basic":  {"size":10000, "profit_target":1000,  "max_loss_limit":400,  "daily_loss":None, "contracts_es":6},
    "25k Basic":  {"size":25000, "profit_target":2500,  "max_loss_limit":1000, "daily_loss":None, "contracts_es":10},
    "50k Basic":  {"size":50000, "profit_target":5000,  "max_loss_limit":2000, "daily_loss":None, "contracts_es":15},
    "100k Basic": {"size":100000,"profit_target":10000, "max_loss_limit":4000, "daily_loss":None, "contracts_es":20},
}

# ── 100 TRADER CONFIGS ────────────────────────────────────────────────────────
def _make_100():
    base = [
        (0.008,2.5,(35,65),True,False,False),
        (0.015,2.0,(20,80),False,True,False),
        (0.005,1.5,(25,75),False,False,True),
        (0.010,3.0,(30,70),True,False,False),
        (0.012,2.0,(20,80),False,False,True),
        (0.018,2.5,(25,75),False,True,False),
        (0.006,4.0,(40,60),True,False,False),
        (0.020,1.8,(20,80),False,False,False),
        (0.004,3.0,(38,62),True,False,False),
        (0.014,2.2,(22,78),False,True,False),
    ]
    styles = ["Momentum","Reversal","Breakout","Scalp","Swing","Position","Day","Macro","Quant","Hybrid"]
    tags   = ["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta","Iota","Kappa"]
    out = []
    for i in range(100):
        b = base[i % 10]; noise = 1 + (i % 7 - 3) * 0.04
        risk = round(min(0.025, max(0.003, b[0]*noise)), 4)
        rr   = round(max(1.2, b[1] + (i%5-2)*0.15), 2)
        lo   = max(15, b[2][0] + (i%7-3)*2)
        hi   = min(85, b[2][1] + (i%7-3)*2)
        out.append({"name":f"{styles[i%10]}-{tags[i%10]}{i+1}","risk":risk,"rr":rr,
                    "rsi_range":(lo,hi),"strong_only":b[3],"bb_break":b[4],"rsi_extreme":b[5]})
    return out

ALL100 = _make_100()

# ── SESSION STATE ─────────────────────────────────────────────────────────────
def _make_trader(name, emoji, style, desc, risk, rr, filters, sources):
    return dict(name=name,emoji=emoji,style=style,desc=desc,risk_pct=risk,rr=rr,
                signal_filters=filters,data_sources=sources,balance=25000.0,peak=25000.0,
                trades=[],open_pos=None,history=[25000.0],win_streak=0,loss_streak=0)

if "traders" not in st.session_state:
    saved = persist_get("traders_state")
    st.session_state["traders"] = saved if saved else [
        _make_trader("ES Scalper","⚡","ES micro-scalp","Scalps ES 1-3 min. RSI extremes + VWAP dev. Tight 2-tick stops.",
            0.005,1.5,{"rsi_range":(25,75),"strong_only":False,"bb_break":False,"rsi_extreme":True},
            ["price","rsi","vwap","stoch","cci"]),
        _make_trader("NQ Momentum","🚀","NQ breakout","Rides NQ momentum post 9:30 open. BB breakouts, ATR stops.",
            0.015,2.0,{"rsi_range":(20,80),"strong_only":False,"bb_break":True,"rsi_extreme":False},
            ["price","rsi","macd","bb","atr","volume"]),
        _make_trader("GC Macro","🌍","Gold macro swing","Buys Gold on USD weakness. Full alignment required.",
            0.008,2.5,{"rsi_range":(35,65),"strong_only":True,"bb_break":False,"rsi_extreme":False},
            ["price","volume","rsi","macd","bb"]),
        _make_trader("CL Trend","🛢️","Crude trend follower","EMA50 + RSI 40-60 + MACD. Holds for bigger moves.",
            0.010,3.0,{"rsi_range":(30,70),"strong_only":True,"bb_break":False,"rsi_extreme":False},
            ["price","rsi","macd","ema50","volume"]),
        _make_trader("Multi Contrarian","🔄","Counter-trend reversal","Buys oversold, sells overbought across all instruments.",
            0.012,2.0,{"rsi_range":(20,80),"strong_only":False,"bb_break":False,"rsi_extreme":True},
            ["price","rsi","stoch","cci","bb"]),
    ]

for k, v in [("notes",[]),("bt_results",{}),("ensemble_results",{}),("grand_strategy",{}),
              ("profit_analysis",{})]:
    if k not in st.session_state:
        disk = persist_get(k)
        st.session_state[k] = disk if disk else v

if "last_ai"        not in st.session_state: st.session_state["last_ai"]        = 0.0
if "ensemble_ran"   not in st.session_state: st.session_state["ensemble_ran"]   = bool(persist_get("ensemble_ran", False))
if "scalp_signals"  not in st.session_state: st.session_state["scalp_signals"]  = []
if "last_scalp"     not in st.session_state: st.session_state["last_scalp"]     = 0.0
if "last_save"      not in st.session_state: st.session_state["last_save"]      = 0.0

TRADERS = st.session_state["traders"]

def autosave():
    if time.time() - st.session_state["last_save"] > 60:
        persist_set("traders_state", TRADERS)
        persist_set("notes", st.session_state.get("notes",[])[-40:])
        persist_set("ensemble_ran", st.session_state.get("ensemble_ran", False))
        st.session_state["last_save"] = time.time()

# ── KEY GATE ──────────────────────────────────────────────────────────────────
def get_keys():
    p = st.secrets.get("POLYGON_KEY","") if hasattr(st,"secrets") else ""
    pp = persist_get("POLYGON_KEY","")
    return st.session_state.get("POLYGON_KEY", p or pp)

POLYGON_KEY = get_keys()

if not POLYGON_KEY:
    st.markdown('<div class="main-title">⚡ Nigel — Alpha Futures</div>', unsafe_allow_html=True)
    st.markdown("### Setup")
    with st.form("keys"):
        pk = st.text_input("Polygon.io API Key (needed for CME futures data)", type="password")
        if st.form_submit_button("Launch"):
            if pk:
                st.session_state["POLYGON_KEY"] = pk
                persist_set("POLYGON_KEY", pk)
                st.rerun()
            else:
                st.error("Polygon key required.")
    st.info("Polygon.io free tier covers SPY/QQQ/GLD/USO/DIA as CME proxies, plus BTC/ETH crypto. Paid tier gets native futures contracts (ES, NQ etc).")
    st.stop()

# ── DATA FETCHERS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_poly_ohlcv(ticker, key, days=120):
    try:
        to = datetime.today().strftime("%Y-%m-%d")
        fr = (datetime.today()-timedelta(days=days)).strftime("%Y-%m-%d")
        d = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{fr}/{to}"
            f"?adjusted=true&sort=asc&limit={days}&apiKey={key}", timeout=15
        ).json()
        if "results" not in d or len(d["results"]) < 5: return pd.DataFrame()
        df = pd.DataFrame(d["results"])
        df.index = pd.to_datetime(df["t"], unit="ms")
        return df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})[["open","high","low","close","volume"]]
    except: return pd.DataFrame()

@st.cache_data(ttl=120)
def fetch_cg(cg_id, days=120):
    try:
        d = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily", timeout=15
        ).json()
        prices  = [p[1] for p in d["prices"]]
        volumes = [v[1] for v in d.get("total_volumes",[])]
        dates   = [pd.Timestamp(p[0],unit="ms") for p in d["prices"]]
        return pd.DataFrame({"close":prices,"volume":volumes},index=dates)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_poly_intraday(ticker, key, minutes=200):
    try:
        to = datetime.today().strftime("%Y-%m-%d")
        fr = (datetime.today()-timedelta(days=5)).strftime("%Y-%m-%d")
        d = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{fr}/{to}"
            f"?adjusted=true&sort=asc&limit={minutes}&apiKey={key}", timeout=15
        ).json()
        if "results" not in d or len(d["results"]) < 10: return pd.DataFrame()
        df = pd.DataFrame(d["results"])
        df.index = pd.to_datetime(df["t"], unit="ms")
        return df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})[["open","high","low","close","volume"]]
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_cg_hourly(cg_id):
    try:
        d = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days=2&interval=hourly", timeout=15
        ).json()
        prices = [p[1] for p in d["prices"]]
        dates  = [pd.Timestamp(p[0],unit="ms") for p in d["prices"]]
        return pd.DataFrame({"close":prices}, index=dates)
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d = requests.get("https://api.alternative.me/fng/?limit=14", timeout=10).json()["data"]
        return {"value":int(d[0]["value"]),"label":d[0]["value_classification"],
                "history":[int(x["value"]) for x in d]}
    except: return {"value":50,"label":"Neutral","history":[50]*14}

# ── INDICATORS ────────────────────────────────────────────────────────────────
def add_indicators(df):
    if df.empty or len(df) < 26: return df
    df = df.copy()
    df["ema8"]  = df["close"].ewm(span=8,  adjust=False).mean()
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    e12 = df["close"].ewm(span=12,adjust=False).mean()
    e26 = df["close"].ewm(span=26,adjust=False).mean()
    df["macd"]        = e12 - e26
    df["macd_signal"] = df["macd"].ewm(span=9,adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]
    delta = df["close"].diff()
    gain  = delta.where(delta>0,0.0).rolling(14).mean()
    loss  = (-delta.where(delta<0,0.0)).rolling(14).mean().replace(0,1e-10)
    df["rsi"] = 100 - (100 / (1 + gain/loss))
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2*df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2*df["bb_std"]
    df["bb_pct"]   = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)
    if "high" in df.columns:
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"]  - df["close"].shift()).abs()
        df["atr"] = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(14).mean()
    else:
        df["atr"] = df["close"] * 0.01
    lo14 = df["close"].rolling(14).min()
    hi14 = df["close"].rolling(14).max()
    df["stoch_k"] = 100*(df["close"]-lo14)/(hi14-lo14+1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    if "volume" in df.columns:
        df["vwap"]      = (df["close"]*df["volume"]).rolling(20).sum() / (df["volume"].rolling(20).sum()+1e-10)
        df["vol_ma"]    = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / (df["vol_ma"]+1e-10)
    bull_ema  = df["ema8"] > df["ema21"]
    bull_macd = df["macd"] > df["macd_signal"]
    mcu = bull_macd & ~bull_macd.shift(1).fillna(False)
    mcd = ~bull_macd & bull_macd.shift(1).fillna(False)
    df["signal"] = np.where(
        bull_ema & mcu & df["rsi"].between(35,68),      "STRONG BUY",
        np.where(bull_ema & bull_macd & df["rsi"].between(38,65), "BUY",
        np.where(~bull_ema & mcd & (df["rsi"]>32),    "STRONG SELL",
        np.where(~bull_ema & ~bull_macd & (df["rsi"]>38), "SELL",
        np.where(df["rsi"]<28, "OVERSOLD",
        np.where(df["rsi"]>74, "OVERBOUGHT","HOLD"))))))
    return df

def add_scalp_indicators(df):
    if df.empty or len(df) < 14: return df
    df = df.copy()
    df["ema3"]  = df["close"].ewm(span=3,  adjust=False).mean()
    df["ema8"]  = df["close"].ewm(span=8,  adjust=False).mean()
    df["ema13"] = df["close"].ewm(span=13, adjust=False).mean()
    delta = df["close"].diff()
    gain  = delta.where(delta>0,0.0).rolling(7).mean()
    loss  = (-delta.where(delta<0,0.0)).rolling(7).mean().replace(0,1e-10)
    df["rsi7"] = 100 - (100/(1+gain/loss))
    lo9 = df["close"].rolling(9).min()
    hi9 = df["close"].rolling(9).max()
    df["stoch_k"] = 100*(df["close"]-lo9)/(hi9-lo9+1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    df["bb_mid"]   = df["close"].rolling(10).mean()
    df["bb_std"]   = df["close"].rolling(10).std()
    df["bb_upper"] = df["bb_mid"] + 1.8*df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 1.8*df["bb_std"]
    df["bb_pct"]   = (df["close"]-df["bb_lower"])/(df["bb_upper"]-df["bb_lower"]+1e-10)
    if "volume" in df.columns:
        df["vwap"]     = (df["close"]*df["volume"]).rolling(20).sum()/(df["volume"].rolling(20).sum()+1e-10)
        df["vwap_dev"] = (df["close"]-df["vwap"])/(df["vwap"]+1e-10)*100
    else:
        df["vwap_dev"] = 0.0
    if "high" in df.columns:
        hl = df["high"]-df["low"]
        hc = (df["high"]-df["close"].shift()).abs()
        lc = (df["low"]-df["close"].shift()).abs()
        df["atr"] = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(7).mean()
    else:
        df["atr"] = df["close"]*0.004
    df["mom"] = df["close"].pct_change(3)*100
    return df

# ── SCALP SIGNAL GENERATOR ────────────────────────────────────────────────────
def generate_scalp_signals(intraday_dfs, market_signals_daily, selected):
    signals = []
    now_str = datetime.now().strftime("%H:%M:%S")
    for mk in selected:
        df_raw = intraday_dfs.get(mk, pd.DataFrame())
        if df_raw.empty or len(df_raw) < 15: continue
        df   = add_scalp_indicators(df_raw)
        row  = df.iloc[-1]
        prev = df.iloc[-2] if len(df)>2 else row
        price    = float(row["close"])
        rsi      = float(row.get("rsi7",50))
        stoch_k  = float(row.get("stoch_k",50))
        bb_pct   = float(row.get("bb_pct",0.5))
        vwap_dev = float(row.get("vwap_dev",0))
        mom      = float(row.get("mom",0))
        atr      = float(row.get("atr",price*0.004))
        ema3     = float(row.get("ema3",price))
        ema8     = float(row.get("ema8",price))
        prev_k   = float(prev.get("stoch_k",stoch_k))
        mkt_info = MARKETS.get(mk,{})
        reasons=[]; long_score=0; short_score=0
        if rsi<28:            long_score+=3;  reasons.append(f"RSI7={rsi:.0f} oversold")
        elif rsi<35:          long_score+=1;  reasons.append(f"RSI7={rsi:.0f} low")
        if stoch_k<15 and stoch_k>prev_k: long_score+=2; reasons.append("Stoch crossed up <15")
        if bb_pct<0.1:        long_score+=2;  reasons.append("Lower BB touch")
        if vwap_dev<-0.6:     long_score+=1;  reasons.append(f"VWAP dev {vwap_dev:.1f}%")
        if ema3>ema8 and float(prev.get("ema3",ema3))<=float(prev.get("ema8",ema8)):
                              long_score+=2;  reasons.append("EMA3 crossed EMA8 up")
        if mom>0.1:           long_score+=1;  reasons.append(f"Mom +{mom:.2f}%")
        if rsi>72:            short_score+=3; reasons.append(f"RSI7={rsi:.0f} overbought")
        elif rsi>65:          short_score+=1; reasons.append(f"RSI7={rsi:.0f} high")
        if stoch_k>85 and stoch_k<prev_k: short_score+=2; reasons.append("Stoch crossed down >85")
        if bb_pct>0.9:        short_score+=2; reasons.append("Upper BB touch")
        if vwap_dev>0.6:      short_score+=1; reasons.append(f"VWAP dev +{vwap_dev:.1f}%")
        if ema3<ema8 and float(prev.get("ema3",ema3))>=float(prev.get("ema8",ema8)):
                              short_score+=2; reasons.append("EMA3 crossed EMA8 down")
        if mom<-0.1:          short_score+=1; reasons.append(f"Mom {mom:.2f}%")
        daily_sig = market_signals_daily.get(mk,{}).get("signal","HOLD")
        if "BUY"  in daily_sig or daily_sig=="OVERSOLD":   long_score  = int(long_score*1.2)
        if "SELL" in daily_sig or daily_sig=="OVERBOUGHT": short_score = int(short_score*1.2)
        if long_score>=4 and long_score>short_score:     direction="LONG"; conf=min(95,50+long_score*5)
        elif short_score>=4 and short_score>long_score:  direction="SHORT"; conf=min(95,50+short_score*5)
        else: continue
        urgency = "urgent" if conf>=80 else "hot" if conf>=65 else "normal"
        sd = max(atr*1.0, price*0.002)
        td = sd*1.5
        stop   = round(price-sd if direction=="LONG" else price+sd, 4)
        target = round(price+td if direction=="LONG" else price-td, 4)
        # Tick value for Alpha Futures sizing hint
        tick     = mkt_info.get("tick",0.25)
        tick_val = mkt_info.get("tick_val",12.50)
        ticks_risk = sd/tick if tick>0 else 0
        dollar_risk = ticks_risk*tick_val
        signals.append({
            "market":mk,"label":mkt_info.get("label",mk),"color":mkt_info.get("color","#fff"),
            "direction":direction,"price":price,"stop":stop,"target":target,
            "conf":conf,"urgency":urgency,"rsi":round(rsi,1),"stoch_k":round(stoch_k,1),
            "bb_pct":round(bb_pct*100,1),"vwap_dev":round(vwap_dev,2),"reasons":reasons[:4],
            "hold_est":"5–15 min","rr":"1:1.5","time":now_str,"daily_bias":daily_sig,
            "timeframe":"5-min scalp","tick_risk":round(ticks_risk,1),"dollar_risk":round(dollar_risk,2),
        })
    signals.sort(key=lambda x:x["conf"],reverse=True)
    return signals

# ── BACKTEST ENGINE ───────────────────────────────────────────────────────────
def run_backtest(df, cfg, label=""):
    if df.empty or "signal" not in df.columns or len(df)<30: return {"error":"insufficient data"}
    df  = df.dropna(subset=["close","signal","rsi"]).copy()
    capital=10000.0; cash=capital; pos=0.0; entry=0.0; trades=[]; equity=[]
    stop_pct=0.02; rr=float(cfg.get("rr",2.0))
    f = cfg.get("signal_filters", cfg)
    def direction(row):
        s=row["signal"]; r=float(row.get("rsi",50)); rng=f.get("rsi_range",(20,80))
        if not (rng[0]<=r<=rng[1]): return None
        if f.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"): return None
        if f.get("bb_break"):
            bp=float(row.get("bb_pct",0.5))
            if s in ("BUY","STRONG BUY") and bp>0.8: return "long"
            if s in ("SELL","STRONG SELL") and bp<0.2: return "short"
            return None
        if f.get("rsi_extreme"):
            if r<32: return "long"
            if r>68: return "short"
            return None
        if s in ("BUY","STRONG BUY","OVERSOLD"): return "long"
        if s in ("SELL","STRONG SELL","OVERBOUGHT"): return "short"
        return None
    for i in range(1,len(df)):
        row=df.iloc[i]; price=float(row["close"])
        equity.append({"date":df.index[i],"equity":cash+pos*price})
        if pos>0 and entry>0:
            if price<=entry*(1-stop_pct) or price>=entry*(1+stop_pct*rr):
                pnl=(price-entry)*pos; cash+=pos*price
                trades.append({"type":"Long","entry":entry,"exit":price,"pnl":pnl,"date":df.index[i],
                                "reason":"TP" if price>=entry*(1+stop_pct*rr) else "SL"})
                pos=0; entry=0; continue
        if pos<0 and entry>0:
            if price>=entry*(1+stop_pct) or price<=entry*(1-stop_pct*rr):
                pnl=(entry-price)*abs(pos); cash+=abs(pos)*price
                trades.append({"type":"Short","entry":entry,"exit":price,"pnl":pnl,"date":df.index[i],
                                "reason":"TP" if price<=entry*(1-stop_pct*rr) else "SL"})
                pos=0; entry=0; continue
        prev=df.iloc[i-1]; d=direction(prev)
        if pos==0:
            if d=="long":  u=cash*0.95/price; pos=u;  cash-=u*price;  entry=price
            elif d=="short": u=cash*0.95/price; pos=-u; cash+=u*price; entry=price
        else:
            if pos>0 and d=="short":
                pnl=(price-entry)*pos; cash+=pos*price
                trades.append({"type":"Long","entry":entry,"exit":price,"pnl":pnl,"date":df.index[i],"reason":"Flip"})
                pos=0; entry=0
            elif pos<0 and d=="long":
                pnl=(entry-price)*abs(pos); cash+=abs(pos)*price
                trades.append({"type":"Short","entry":entry,"exit":price,"pnl":pnl,"date":df.index[i],"reason":"Flip"})
                pos=0; entry=0
    if pos!=0:
        fp=float(df.iloc[-1]["close"]); pnl=(fp-entry)*pos if pos>0 else (entry-fp)*abs(pos)
        cash+=abs(pos)*fp; trades.append({"type":"Open","entry":entry,"exit":fp,"pnl":pnl,"date":df.index[-1],"reason":"End"})
    if not trades: return {"error":"no trades"}
    eq=pd.DataFrame(equity); tdf=pd.DataFrame(trades)
    wins=tdf[tdf["pnl"]>0]; losses=tdf[tdf["pnl"]<=0]
    tot_ret=(cash-capital)/capital*100
    bh=(float(df.iloc[-1]["close"])-float(df.iloc[0]["close"]))/float(df.iloc[0]["close"])*100
    wr=len(wins)/len(tdf)*100 if len(tdf) else 0
    pf=abs(wins["pnl"].sum()/losses["pnl"].sum()) if not losses.empty and losses["pnl"].sum()!=0 else 99.0
    sharpe=0.0
    if len(eq)>1:
        r2=eq["equity"].pct_change().dropna()
        if r2.std()>0: sharpe=r2.mean()/r2.std()*np.sqrt(252)
    rm=eq["equity"].cummax(); maxdd=((eq["equity"]-rm)/rm*100).min()
    streaks=[]; cur=0
    for p2 in tdf["pnl"]: cur=max(1,cur+1) if p2>0 else min(-1,cur-1); streaks.append(cur)
    return {"total_return":round(tot_ret,2),"bh_return":round(bh,2),"win_rate":round(wr,1),
            "total_trades":len(tdf),"wins":len(wins),"losses":len(losses),
            "avg_win":round(wins["pnl"].mean() if not wins.empty else 0,2),
            "avg_loss":round(losses["pnl"].mean() if not losses.empty else 0,2),
            "profit_factor":round(min(pf,99.0),2),"max_drawdown":round(maxdd,2),
            "sharpe":round(sharpe,2),"calmar":round(tot_ret/abs(maxdd) if maxdd!=0 else 0,2),
            "max_win_streak":max(streaks) if streaks else 0,
            "max_loss_streak":abs(min(streaks)) if streaks else 0,
            "equity_curve":eq,"trade_list":tdf,"final_equity":round(cash,2),"label":label}

# ── 100-AI ENSEMBLE ───────────────────────────────────────────────────────────
def run_ensemble(df_map):
    results_by_mkt = {}
    for mk,df in df_map.items():
        if df.empty: continue
        mkt_res = []
        for cfg in ALL100:
            bt = run_backtest(df, {"signal_filters":{k:cfg[k] for k in ("rsi_range","strong_only","bb_break","rsi_extreme")},"rr":cfg["rr"]}, cfg["name"])
            if "error" not in bt:
                score = bt["sharpe"]*(bt["win_rate"]/50)*max(0.1,1-abs(bt["max_drawdown"])/50)
                mkt_res.append({**bt,"name":cfg["name"],"score":round(score,4),
                                "rsi_range":cfg["rsi_range"],"rr":cfg["rr"],
                                "bb_break":cfg["bb_break"],"rsi_extreme":cfg["rsi_extreme"],"strong_only":cfg["strong_only"]})
        mkt_res.sort(key=lambda x:x["score"],reverse=True)
        results_by_mkt[mk] = mkt_res
    grand = {}
    for mk,res in results_by_mkt.items():
        if not res: continue
        top = res[:20]
        lo  = round(np.mean([r["rsi_range"][0] for r in top]))
        hi  = round(np.mean([r["rsi_range"][1] for r in top]))
        rr  = round(np.mean([r["rr"] for r in top]),2)
        df2 = df_map.get(mk,pd.DataFrame()); sig="HOLD"; conf=50; rsi_v=50
        if not df2.empty and "rsi" in df2.columns:
            row=df2.iloc[-1]; sig=str(row.get("signal","HOLD")); rsi_v=float(row.get("rsi",50))
            in_range=lo<=rsi_v<=hi; is_b="BUY" in sig or sig=="OVERSOLD"; is_s="SELL" in sig or sig=="OVERBOUGHT"
            conf=80 if (in_range and (is_b or is_s)) else 55 if (is_b or is_s) else 30
        grand[mk] = {"rsi_range":(lo,hi),"rr":rr,
                     "use_bb":sum(1 for r in top if r["bb_break"])>10,
                     "use_extreme":sum(1 for r in top if r["rsi_extreme"])>10,
                     "use_strong":sum(1 for r in top if r["strong_only"])>10,
                     "avg_ret":round(np.mean([r["total_return"] for r in top]),2),
                     "avg_sharpe":round(np.mean([r["sharpe"] for r in top]),2),
                     "avg_wr":round(np.mean([r["win_rate"] for r in top]),1),
                     "best":top[0]["name"],"signal":sig,"conf":conf,"rsi":round(rsi_v,1)}
    return results_by_mkt, grand

# ── PROFITABILITY ANALYSIS ────────────────────────────────────────────────────
def run_profit_analysis(all_dfs, grand, selected):
    """
    Cross-market profitability analysis tuned for Alpha Futures prop rules.
    Scores each instrument on: backtest returns, Sharpe, current signal strength,
    volatility (good for scalpers), Alpha Futures contract limits.
    """
    rows = []
    for mk in selected:
        if mk not in all_dfs or all_dfs[mk].empty: continue
        df    = all_dfs[mk]
        minfo = MARKETS.get(mk, {})
        gs    = grand.get(mk, {})
        # Run quick backtest with best strategy
        bt = run_backtest(df, {"signal_filters":{"rsi_range":(35,65),"strong_only":True,"bb_break":False,"rsi_extreme":False},"rr":2.5}, mk)
        if "error" in bt: continue
        # Volatility (normalized daily ATR as % of price)
        atr_pct = 0.0
        if "atr" in df.columns and not df["atr"].isna().all():
            atr_pct = float(df["atr"].iloc[-1] / df["close"].iloc[-1] * 100)
        # Signal strength score
        sig = gs.get("signal","HOLD")
        conf = gs.get("conf",50)
        sig_score = conf if ("BUY" in sig or "SELL" in sig) else 30
        # Win rate adjusted return
        wr_adj = bt["win_rate"] * bt["total_return"] / 100 if bt["total_return"] > 0 else bt["total_return"]
        # Alpha Futures contract limit (25k account)
        max_contracts = minfo.get("alpha_limits",{}).get("25k",5)
        # Overall score: sharpe×winrate×signal×volatility_bonus
        vol_bonus = min(2.0, atr_pct / 0.5)  # reward higher vol instruments for scalping
        score = (bt["sharpe"] * (bt["win_rate"]/50) * (sig_score/60) * max(0.5,vol_bonus))
        rows.append({
            "mk": mk,
            "label": minfo.get("label",mk),
            "signal": sig, "conf": conf,
            "rsi": gs.get("rsi",50),
            "bt_return": bt["total_return"],
            "bh_return": bt["bh_return"],
            "win_rate": bt["win_rate"],
            "sharpe": bt["sharpe"],
            "max_dd": bt["max_drawdown"],
            "profit_factor": bt["profit_factor"],
            "atr_pct": round(atr_pct,2),
            "max_contracts": max_contracts,
            "score": round(score,3),
            "wr_adj_ret": round(wr_adj,2),
            "desc": minfo.get("desc",""),
            "color": minfo.get("color","#fff"),
            "tick": minfo.get("tick",0.25),
            "tick_val": minfo.get("tick_val",12.50),
        })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows

# ── SIGNAL ENGINE ─────────────────────────────────────────────────────────────
def get_signal(df, fg=None):
    if df.empty or "rsi" not in df.columns:
        return {"signal":"HOLD","conf":50,"rsi":50,"price":0,"bb_pct":0.5,"atr":0,"stoch_k":50}
    row=df.iloc[-1]; price=float(row["close"]); rsi_v=float(row.get("rsi",50)); s=str(row.get("signal","HOLD"))
    conf={"STRONG BUY":82,"BUY":66,"STRONG SELL":80,"SELL":64,"OVERSOLD":74,"OVERBOUGHT":72}.get(s,50)
    if fg:
        fv=fg.get("value",50)
        if s in ("BUY","STRONG BUY","OVERSOLD")    and fv<30: conf=min(95,conf+8)
        if s in ("SELL","STRONG SELL","OVERBOUGHT") and fv>75: conf=min(95,conf+8)
    return {"signal":s,"conf":conf,"rsi":rsi_v,"price":price,
            "bb_pct":float(row.get("bb_pct",0.5)),"atr":float(row.get("atr",price*0.01)),"stoch_k":float(row.get("stoch_k",50))}

# ── TRADER SIMULATION ─────────────────────────────────────────────────────────
def simulate_traders(market_signals):
    for tr in TRADERS:
        if tr["open_pos"]:
            pos=tr["open_pos"]; mk=pos["market"]; sig=market_signals.get(mk)
            if not sig: continue
            p=sig["price"]; il=pos["dir"]=="long"
            hit_sl=(il and p<=pos["stop"]) or (not il and p>=pos["stop"])
            hit_tp=(il and p>=pos["tp"])   or (not il and p<=pos["tp"])
            if hit_sl or hit_tp:
                pnl=(p-pos["entry"])*pos["units"] if il else (pos["entry"]-p)*pos["units"]
                tr["balance"]=max(0,tr["balance"]+pnl); tr["peak"]=max(tr["peak"],tr["balance"])
                res="win" if pnl>0 else "loss"
                tr["trades"].append(dict(market=mk,dir=pos["dir"],entry=pos["entry"],exit=p,
                    pnl=round(pnl,2),result=res,reason="TP" if hit_tp else "SL",
                    time=datetime.now().strftime("%H:%M")))
                tr["history"].append(round(tr["balance"],2))
                if res=="win": tr["win_streak"]=tr.get("win_streak",0)+1; tr["loss_streak"]=0
                else:          tr["loss_streak"]=tr.get("loss_streak",0)+1; tr["win_streak"]=0
                tr["open_pos"]=None
        if not tr["open_pos"]:
            for mk,sig in market_signals.items():
                if sig["conf"]<52: continue
                f=tr["signal_filters"]; rng=f.get("rsi_range",(20,80)); r=sig["rsi"]; s=sig["signal"]
                if not (rng[0]<=r<=rng[1]): continue
                if f.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"): continue
                is_b=s in ("BUY","STRONG BUY","OVERSOLD"); is_s=s in ("SELL","STRONG SELL","OVERBOUGHT")
                if f.get("bb_break"):
                    bp=sig.get("bb_pct",0.5)
                    if is_b and bp<0.8: continue
                    if is_s and bp>0.2: continue
                if f.get("rsi_extreme"): is_b=r<32; is_s=r>68
                if not is_b and not is_s: continue
                direction="long" if is_b else "short"; p=sig["price"]; atr=sig.get("atr",p*0.01); sd=atr*1.5
                stop=p-sd if is_b else p+sd; tp=p+sd*tr["rr"] if is_b else p-sd*tr["rr"]
                risk=tr["balance"]*tr["risk_pct"]; units=risk/max(sd,0.001)
                tr["open_pos"]=dict(market=mk,dir=direction,entry=round(p,2),stop=round(stop,2),
                    tp=round(tp,2),units=units,risk_amt=round(risk,2),time=datetime.now().strftime("%H:%M"))
                break

# ── NOTES ─────────────────────────────────────────────────────────────────────
def push_note(t, mk, txt):
    st.session_state["notes"].insert(0,{"type":t,"market":mk,"text":txt,"time":datetime.now().strftime("%H:%M")})
    if len(st.session_state["notes"])>60: st.session_state["notes"].pop()

def generate_notes(market_signals, active_sessions):
    if time.time()-st.session_state["last_ai"]<90: return
    st.session_state["last_ai"]=time.time()
    for mk,sig in market_signals.items():
        r,s=sig["rsi"],sig["signal"]; lbl=MARKETS.get(mk,{}).get("label",mk)
        if r>72 or s=="OVERBOUGHT": push_note("watch",mk,f"**{lbl}** RSI {r:.0f} — overbought. Don't chase longs.")
        elif r<30 or s=="OVERSOLD": push_note("buy",mk,f"**{lbl}** RSI {r:.0f} — oversold. Watch for reversal candle.")
        elif s=="STRONG BUY":       push_note("buy",mk,f"**{lbl}** strong setup. EMA + MACD aligned. Wait for entry.")
        elif s=="STRONG SELL":      push_note("sell",mk,f"**{lbl}** bearish flip. Stay out of longs.")

# ── SESSION BANNER ────────────────────────────────────────────────────────────
def session_banner():
    utc=datetime.now(ZoneInfo("UTC")); hf=utc.hour+utc.minute/60
    sess=[]
    if 0<=hf<9:   sess.append(("Tokyo","#7C3AED"))
    if 8<=hf<17:  sess.append(("London","#2563EB"))
    if 13<=hf<22: sess.append(("New York","#059669"))
    if 13<=hf<17: sess.append(("NY+London Overlap","#D97706"))
    if not sess:  sess.append(("Off-hours","#555"))
    badges=" ".join(f'<span style="background:{c};color:#fff;border-radius:5px;padding:2px 10px;font-size:12px;font-weight:700">{n}</span>' for n,c in sess)
    ny=utc.astimezone(ZoneInfo("America/New_York")); chi=utc.astimezone(ZoneInfo("America/Chicago"))
    cme_open = 13<=hf<22  # CME equity futures hours (CT: 8:30am-3pm)
    cme_badge='<span style="background:#059669;color:#fff;border-radius:5px;padding:2px 10px;font-size:12px;font-weight:700;margin-left:6px">🔔 CME OPEN</span>' if cme_open else '<span style="background:#222;color:#666;border-radius:5px;padding:2px 10px;font-size:12px;margin-left:6px">CME closed</span>'
    saved_badge='<span style="background:#00d4ff22;border:1px solid #00d4ff44;color:#00d4ff;border-radius:4px;padding:2px 8px;font-size:10px;margin-left:6px">💾 STATE SAVED</span>' if PERSIST_FILE.exists() else ''
    st.markdown(f'<div style="background:#0a0a18;border:1px solid #1a1a30;border-radius:10px;padding:12px 18px;margin-bottom:16px">'
                f'<div style="margin-bottom:5px">{badges}{cme_badge}{saved_badge}</div>'
                f'<div style="font-size:11px;color:#444">UTC {utc.strftime("%H:%M")} | ET {ny.strftime("%H:%M")} | CT(CME) {chi.strftime("%H:%M")}</div>'
                f'</div>', unsafe_allow_html=True)
    return [n for n,_ in sess]

# ── CHARTS ────────────────────────────────────────────────────────────────────
def build_chart(df, title, color="#00ff88", show_sigs=True, bt=None):
    if df.empty: return None
    def vol_col(df2):
        c=df2["close"].tolist(); o=df2["open"].tolist() if "open" in df2.columns else c[:]
        n=min(len(c),len(o))
        return ["rgba(0,204,102,0.6)" if float(c[i])>=float(o[i]) else "rgba(204,51,51,0.6)" for i in range(n)]
    fig=make_subplots(rows=4,cols=1,shared_xaxes=True,row_heights=[0.50,0.18,0.18,0.14],
                      vertical_spacing=0.03,subplot_titles=["","MACD","RSI","Volume"])
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index,y=df["bb_upper"],line=dict(color="rgba(120,120,220,0.25)",width=1),showlegend=False),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["bb_lower"],line=dict(color="rgba(120,120,220,0.25)",width=1),fill="tonexty",fillcolor="rgba(100,100,200,0.05)",showlegend=False),row=1,col=1)
    if "open" in df.columns and "high" in df.columns:
        fig.add_trace(go.Candlestick(x=df.index,open=df["open"],high=df["high"],low=df["low"],close=df["close"],
            name="Price",increasing_line_color="#00ff88",decreasing_line_color="#ff4444",
            increasing_fillcolor="rgba(0,255,136,0.15)",decreasing_fillcolor="rgba(255,68,68,0.15)"),row=1,col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index,y=df["close"],name="Price",line=dict(color=color,width=2)),row=1,col=1)
    for cn,mc,lb in [("ema8","#5DCAA5","EMA8"),("ema21","#ED93B1","EMA21"),("ema50","#F59E0B","EMA50")]:
        if cn in df.columns: fig.add_trace(go.Scatter(x=df.index,y=df[cn],name=lb,line=dict(color=mc,width=1.2,dash="dot")),row=1,col=1)
    if show_sigs and "signal" in df.columns:
        for sigs,sym,sz,sc2 in [
            (["BUY","STRONG BUY","OVERSOLD"],"triangle-up",10,"#00ff88"),
            (["STRONG BUY"],"star",16,"#00ffcc"),
            (["SELL","STRONG SELL","OVERBOUGHT"],"triangle-down",10,"#ff4444"),
            (["STRONG SELL"],"x",13,"#ff0000"),
        ]:
            sub=df[df["signal"].isin(sigs)]
            if not sub.empty:
                fig.add_trace(go.Scatter(x=sub.index,y=sub["close"],mode="markers",
                    marker=dict(symbol=sym,size=sz,color=sc2),name=sigs[0]),row=1,col=1)
    if "macd" in df.columns:
        mhist=df["macd_hist"].fillna(0).tolist()
        mc2=["rgba(0,204,102,0.8)" if v>=0 else "rgba(204,51,51,0.8)" for v in mhist]
        fig.add_trace(go.Bar(x=df.index,y=df["macd_hist"],marker_color=mc2,showlegend=False),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["macd"],line=dict(color=color,width=1.5),name="MACD"),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["macd_signal"],line=dict(color="#ED93B1",width=1.5),name="Sig"),row=2,col=1)
    if "rsi" in df.columns:
        fig.add_trace(go.Scatter(x=df.index,y=df["rsi"],line=dict(color="#a78bfa",width=2),name="RSI"),row=3,col=1)
        for lvl,lc in [(70,"rgba(255,68,68,0.6)"),(30,"rgba(0,255,136,0.6)"),(50,"rgba(80,80,80,0.5)")]:
            fig.add_hline(y=lvl,line=dict(color=lc,width=1,dash="dash"),row=3,col=1)
    if "volume" in df.columns:
        vc=vol_col(df); n=min(len(df.index),len(df["volume"]),len(vc))
        fig.add_trace(go.Bar(x=df.index[:n],y=df["volume"].tolist()[:n],marker_color=vc[:n],showlegend=False),row=4,col=1)
    fig.update_layout(height=800,template="plotly_dark",title=dict(text=title,font=dict(size=14,color="#ccc")),
        paper_bgcolor="#080818",plot_bgcolor="#0a0a18",xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=10)),margin=dict(l=0,r=0,t=50,b=0))
    fig.update_xaxes(gridcolor="#111128",zerolinecolor="#111128")
    fig.update_yaxes(gridcolor="#111128",zerolinecolor="#111128")
    return fig

def build_equity_chart(bts, start=10000):
    fig=go.Figure()
    COLORS=["#00ff88","#00d4ff","#f0a500","#a78bfa","#ff6b6b"]
    for i,(name,bt) in enumerate(bts.items()):
        if bt and "equity_curve" in bt:
            eq=bt["equity_curve"]; ret=(eq["equity"].iloc[-1]-start)/start*100
            fig.add_trace(go.Scatter(x=eq["date"],y=eq["equity"],name=f"{name} ({ret:+.1f}%)",
                line=dict(color=COLORS[i%len(COLORS)],width=2)))
    fig.add_hline(y=start,line=dict(color="#444",width=1,dash="dot"))
    fig.update_layout(height=320,template="plotly_dark",title="Equity curves",paper_bgcolor="#080818",
        plot_bgcolor="#0a0a18",legend=dict(orientation="h",yanchor="bottom",y=1.02),margin=dict(l=0,r=0,t=50,b=0))
    return fig

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:800;color:#ff6b00">⚡ Nigel</div>', unsafe_allow_html=True)
    st.caption("Alpha Futures Intelligence")
    st.divider()
    with st.expander("🔑 API Keys"):
        np_ = st.text_input("Polygon.io Key", value=POLYGON_KEY, type="password")
        if st.button("Save Key"):
            st.session_state["POLYGON_KEY"] = np_
            persist_set("POLYGON_KEY", np_)
            st.cache_data.clear(); st.rerun()
    with st.expander("💾 Persistence"):
        if PERSIST_FILE.exists():
            sz = PERSIST_FILE.stat().st_size
            st.markdown(f'<div style="font-size:11px;color:#00d4ff">✅ {PERSIST_FILE.name} ({sz/1024:.1f} KB)</div>', unsafe_allow_html=True)
            if st.button("🗑 Reset state"): PERSIST_FILE.unlink(); st.rerun()
            if st.button("💾 Save now"):
                persist_set("traders_state", TRADERS)
                persist_set("notes", st.session_state.get("notes",[]))
                st.success("Saved!")
        else: st.caption("Auto-saves every 60s")
    st.divider()
    auto_refresh = st.toggle("Auto-refresh (90s)", value=False)
    selected_markets = st.multiselect(
        "Instruments (Alpha Futures)",
        ["ES","NQ","GC","CL","YM","BTC","ETH"],
        default=["ES","NQ","GC","CL"]
    )
    account_size = st.selectbox("Account size", list(ALPHA_ACCOUNTS.keys()), index=1)
    bt_days = st.slider("Backtest window (days)", 30, 365, 90)
    st.divider()
    if st.button("🔄 Refresh data"): st.cache_data.clear(); st.rerun()
    if st.button("🗑 Clear alerts"): st.session_state["notes"]=[]; st.rerun()
    if st.button("♻️ Reset traders"):
        del st.session_state["traders"]
        persist_set("traders_state", None); st.rerun()
    if st.button("🧠 Re-run Ensemble"): st.session_state["ensemble_ran"]=False
    if st.button("📊 Re-run Profit Analysis"): st.session_state["profit_analysis"]={}
    st.divider()
    st.caption(f"Alpha Futures · {datetime.now().strftime('%H:%M:%S')}")

# ── FETCH DATA ────────────────────────────────────────────────────────────────
if not selected_markets: selected_markets=["ES","NQ","GC","CL"]
CG_IDS = {"BTC":"bitcoin","ETH":"ethereum"}

with st.spinner("Loading CME futures data…"):
    all_dfs = {}
    for mk in selected_markets:
        info = MARKETS[mk]
        if info["crypto"] and mk in CG_IDS:
            raw = fetch_cg(CG_IDS[mk], days=max(bt_days+10,120))
        else:
            raw = fetch_poly_ohlcv(info["poly_ticker"], POLYGON_KEY, days=max(bt_days+10,120))
        all_dfs[mk] = add_indicators(raw)
    fg = fetch_fear_greed()

# Intraday for scalps
intraday_dfs = {}
for mk in selected_markets:
    info = MARKETS[mk]
    if info["crypto"] and mk in CG_IDS:
        raw_h = fetch_cg_hourly(CG_IDS[mk])
        intraday_dfs[mk] = add_scalp_indicators(raw_h) if not raw_h.empty else pd.DataFrame()
    else:
        raw_i = fetch_poly_intraday(info["poly_ticker"], POLYGON_KEY)
        intraday_dfs[mk] = add_scalp_indicators(raw_i) if not raw_i.empty else pd.DataFrame()

market_signals = {mk: get_signal(all_dfs.get(mk, pd.DataFrame()), fg) for mk in selected_markets}
active_sessions = session_banner()
simulate_traders(market_signals)
generate_notes(market_signals, active_sessions)
autosave()

# Scalp signals
if time.time()-st.session_state["last_scalp"]>60:
    st.session_state["scalp_signals"] = generate_scalp_signals(intraday_dfs, market_signals, selected_markets)
    st.session_state["last_scalp"] = time.time()
scalp_signals = st.session_state.get("scalp_signals",[])

# Ensemble
if not st.session_state["ensemble_ran"]:
    with st.spinner("🧠 Running 100-AI ensemble (~30s)…"):
        try:
            ens, grand = run_ensemble(all_dfs)
            st.session_state["ensemble_results"] = ens
            st.session_state["grand_strategy"]   = grand
            st.session_state["ensemble_ran"]      = True
            persist_set("ensemble_ran", True)
        except: st.session_state["ensemble_ran"] = True

grand = st.session_state.get("grand_strategy",{})

# Profit analysis (run once or on demand)
if not st.session_state.get("profit_analysis") and grand:
    with st.spinner("📊 Running profitability analysis…"):
        try:
            pa = run_profit_analysis(all_dfs, grand, selected_markets)
            st.session_state["profit_analysis"] = pa
            persist_set("profit_analysis_summary",
                [{k:v for k,v in r.items() if k not in ("desc","color")} for r in pa])
        except: pass

profit_analysis = st.session_state.get("profit_analysis",[])

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">⚡ Nigel — Alpha Futures</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">CME FUTURES INTELLIGENCE · ES · NQ · GC · CL · YM · 100-AI ENSEMBLE · ALPHA PROP RULES · HYPER-SHORT SCALPS</div>', unsafe_allow_html=True)

acct = ALPHA_ACCOUNTS[account_size]
st.markdown(
    f'<div style="background:#0a0a18;border:1px solid #ff6b0033;border-radius:8px;padding:8px 18px;font-size:12px;margin-bottom:12px;display:flex;gap:24px">'
    f'<span>📋 <b style="color:#ff6b00">{account_size}</b></span>'
    f'<span>🎯 Profit target: <b style="color:#00ff88">${acct["profit_target"]:,}</b></span>'
    f'<span>🛑 Max loss: <b style="color:#ff4444">${acct["max_loss_limit"]:,}</b></span>'
    f'<span>📉 Drawdown: <b style="color:#f0a500">4% EOD</b></span>'
    f'<span>🔔 CME futures: ES/NQ/GC/CL/YM via Tradovate/NinjaTrader</span>'
    f'</div>', unsafe_allow_html=True
)

# ── SCALP TICKER ──────────────────────────────────────────────────────────────
if scalp_signals:
    urgent = [s for s in scalp_signals if s["urgency"]=="urgent"]
    hot    = [s for s in scalp_signals if s["urgency"]=="hot"]
    if urgent or hot:
        items=[]
        for s in (urgent+hot)[:5]:
            c="#ff6600" if s["urgency"]=="urgent" else "#ffd700"
            items.append(f'<span style="color:{c};font-weight:700">{"🟢▲" if s["direction"]=="LONG" else "🔴▼"} {s["label"].split("(")[0].strip()} {s["conf"]}%</span>'
                         f'<span style="color:#666;font-size:11px"> @{s["price"]:,.1f} · {s["tick_risk"]:.0f} ticks</span>')
        st.markdown(f'<div style="background:#0d0d00;border:1px solid #ffd70033;border-radius:8px;padding:8px 16px;margin-bottom:12px;font-family:JetBrains Mono,monospace;font-size:12px">'
                    f'⚡ SCALP: {"&nbsp;&nbsp;|&nbsp;&nbsp;".join(items)}</div>', unsafe_allow_html=True)

# ── LIVE SIGNAL CARDS ─────────────────────────────────────────────────────────
if grand:
    st.markdown("### 🧠 100-AI Grand Strategy")
    gcols = st.columns(len([m for m in selected_markets if m in grand]))
    for col, mk in zip(gcols, [m for m in selected_markets if m in grand]):
        with col:
            gs = grand[mk]; sig = gs["signal"]; conf = gs["conf"]
            is_b="BUY" in sig or sig=="OVERSOLD"; is_s="SELL" in sig or sig=="OVERBOUGHT"
            bc="#00ff88" if is_b else "#ff4444" if is_s else "#555"
            minfo = MARKETS.get(mk,{})
            scalp_match = next((s for s in scalp_signals if s["market"]==mk), None)
            scalp_bit = f'<div style="font-size:10px;color:#ffd700;margin-top:3px">⚡ Scalp: {scalp_match["direction"]} {scalp_match["conf"]}%</div>' if scalp_match else ""
            st.markdown(f'<div style="border:2px solid {bc};border-radius:12px;padding:14px;background:#0a0a18">'
                        f'<div style="font-size:9px;color:#555;font-family:JetBrains Mono">{minfo.get("label",mk)}</div>'
                        f'<div style="font-size:1.1rem;font-weight:800;color:{bc}">{"🟢" if is_b else "🔴" if is_s else "⚪"} {sig}</div>'
                        f'<div style="font-size:11px;color:#888">Conf:{conf}% RSI:{gs["rsi"]}</div>'
                        f'<div style="font-size:10px;color:#555">Avg ret:{gs["avg_ret"]:+.1f}% Sharpe:{gs["avg_sharpe"]:.2f}</div>'
                        f'{scalp_bit}</div>', unsafe_allow_html=True)

st.markdown("### Live Signals")
pcols = st.columns(len(selected_markets))
for col, mk in zip(pcols, selected_markets):
    with col:
        info=MARKETS[mk]; sig=market_signals.get(mk,{}); p=sig.get("price",0)
        df=all_dfs.get(mk,pd.DataFrame()); chg=0
        if not df.empty and len(df)>1: chg=(float(df["close"].iloc[-1])-float(df["close"].iloc[-2]))/float(df["close"].iloc[-2])*100
        s=sig.get("signal","HOLD"); conf=sig.get("conf",50); r=sig.get("rsi",50)
        is_b="BUY" in s or s=="OVERSOLD"; is_s="SELL" in s or s=="OVERBOUGHT"
        bc="#00ff88" if is_b else "#ff4444" if is_s else "#1a1a30"; cc="#00ff88" if chg>=0 else "#ff4444"
        sc="sig-buy" if is_b else "sig-sell" if is_s else "sig-hold"
        scalp_here=next((ss for ss in scalp_signals if ss["market"]==mk), None)
        scalp_bit=f'<div style="margin-top:4px"><span class="sig-badge sig-scalp">⚡ {scalp_here["direction"]} {scalp_here["conf"]}%</span></div>' if scalp_here else ""
        contracts = info.get("alpha_limits",{}).get(account_size.replace(" Basic","").replace("k"," ").strip().replace(" ","k").lower()+"k",5)
        st.markdown(f'<div style="border:2px solid {bc};border-radius:12px;padding:12px;background:#0a0a18">'
                    f'<div style="font-size:9px;color:#555">{info["label"]}</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{info["color"]};font-family:JetBrains Mono">${p:,.1f}</div>'
                    f'<div style="font-size:11px;color:{cc}">{chg:+.2f}%</div>'
                    f'<span class="sig-badge {sc}">{s}</span>'
                    f'<div style="font-size:10px;color:#555;margin-top:3px">Conf:{conf}% RSI:{r:.0f}</div>'
                    f'{scalp_bit}'
                    f'</div>', unsafe_allow_html=True)

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────
t_profit, t_scalp, t_strategy, t_alerts, t_traders, t_bt, t_ensemble, t_ref = st.tabs([
    "💰 Profitability","⚡ Scalp Signals","🧠 Strategy","📝 Alerts","🤖 Traders","📊 Backtest","🔬 100-AI Lab","📚 Alpha Futures Ref"])

# ── PROFITABILITY ANALYSIS ────────────────────────────────────────────────────
with t_profit:
    st.subheader("💰 Profitability Analysis — Most Profitable Ideas for Alpha Futures")
    st.caption("Ranks each instrument by backtest returns, Sharpe, current signal strength and volatility. Tuned for Alpha Futures EOD drawdown rules.")

    if not profit_analysis:
        st.info("Run ensemble first (auto-runs on load), then this tab fills in.")
    else:
        # ── TOP PICK ──────────────────────────────────────────────────────────
        best = profit_analysis[0]
        bc = best["color"]
        sig = best["signal"]; is_b="BUY" in sig or sig=="OVERSOLD"; is_s="SELL" in sig or sig=="OVERBOUGHT"
        fc = "#00ff88" if is_b else "#ff4444" if is_s else "#888"
        st.markdown(f'<div class="profit-best">'
                    f'<div style="font-size:11px;color:#555;font-family:JetBrains Mono">🏆 NIGEL\'S TOP PICK — MOST PROFITABLE RIGHT NOW</div>'
                    f'<div style="font-size:2rem;font-weight:800;color:{fc};margin:6px 0">{best["label"]}</div>'
                    f'<div style="font-size:14px;color:#aaa;margin-bottom:8px">{best["desc"]}</div>'
                    f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px">'
                    f'<div style="background:#0a0a1a;border-radius:8px;padding:10px;text-align:center">'
                    f'<div style="font-size:10px;color:#555">Strategy Return</div><div style="color:#00ff88;font-size:1.2rem;font-weight:700">{best["bt_return"]:+.1f}%</div></div>'
                    f'<div style="background:#0a0a1a;border-radius:8px;padding:10px;text-align:center">'
                    f'<div style="font-size:10px;color:#555">Win Rate</div><div style="color:#00d4ff;font-size:1.2rem;font-weight:700">{best["win_rate"]:.0f}%</div></div>'
                    f'<div style="background:#0a0a1a;border-radius:8px;padding:10px;text-align:center">'
                    f'<div style="font-size:10px;color:#555">Sharpe</div><div style="color:#a78bfa;font-size:1.2rem;font-weight:700">{best["sharpe"]:.2f}</div></div>'
                    f'<div style="background:#0a0a1a;border-radius:8px;padding:10px;text-align:center">'
                    f'<div style="font-size:10px;color:#555">Daily Volatility</div><div style="color:#f0a500;font-size:1.2rem;font-weight:700">{best["atr_pct"]:.2f}%</div></div>'
                    f'<div style="background:#0a0a1a;border-radius:8px;padding:10px;text-align:center">'
                    f'<div style="font-size:10px;color:#555">Signal</div><div style="color:{fc};font-size:1.2rem;font-weight:700">{sig}</div></div>'
                    f'</div></div>', unsafe_allow_html=True)

        st.markdown("### 📊 Full Ranking")

        # Radar chart comparing top instruments
        if len(profit_analysis) >= 2:
            cats = ["Return","Win Rate","Sharpe","Volatility","Signal Conf"]
            fig_radar = go.Figure()
            for row2 in profit_analysis[:5]:
                vals = [
                    max(0,min(100,(row2["bt_return"]+20)/60*100)),
                    row2["win_rate"],
                    max(0,min(100,(row2["sharpe"]+1)/3*100)),
                    min(100,row2["atr_pct"]*20),
                    row2["conf"],
                ]
                vals_closed = vals + [vals[0]]
                cats_closed = cats + [cats[0]]
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals_closed, theta=cats_closed,
                    fill="toself", name=row2["mk"],
                    line_color=row2["color"],
                    fillcolor=row2["color"].replace("#","rgba(").rstrip(")") + ",0.08)" if "#" in row2["color"] else row2["color"],
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True,range=[0,100],gridcolor="#1a1a30"),
                           angularaxis=dict(gridcolor="#1a1a30")),
                template="plotly_dark", paper_bgcolor="#080818", height=380,
                legend=dict(orientation="h",y=-0.1), margin=dict(l=0,r=0,t=20,b=0)
            )
            st.plotly_chart(fig_radar, use_container_width=True, key="profit_radar")

        # Ranked cards
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣"]
        for i, row2 in enumerate(profit_analysis):
            sig2=row2["signal"]; is_b2="BUY" in sig2 or sig2=="OVERSOLD"; is_s2="SELL" in sig2 or sig2=="OVERBOUGHT"
            sc2="#00ff88" if is_b2 else "#ff4444" if is_s2 else "#555"
            border="#00ff88" if i==0 else "#00d4ff44" if i<3 else "#1a1a30"

            # What Nigel thinks
            if i==0:   verdict="🔥 BEST — Trade this first. Strongest edge right now."
            elif i==1: verdict="✅ GOOD — Solid second option. Diversifies well with #1."
            elif i==2: verdict="✅ DECENT — Worth watching. Enter on strong signal only."
            else:      verdict="⚠️ SKIP for now — Lower edge. Wait for better setup."

            # Alpha Futures P&L projection
            acct_sz = acct["size"]; risk_per = acct_sz * 0.004  # 0.4% risk per trade (conservative)
            contracts_here = row2["max_contracts"]
            ticks_per_trade = row2.get("tick_risk",8)  # from scalp or estimate
            dollar_per_contract = row2["tick_val"] * max(4, ticks_per_trade)
            proj_win = round(dollar_per_contract * contracts_here * (row2["win_rate"]/100), 0)

            st.markdown(f'<div class="profit-good" style="border-color:{border}">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                        f'  <div>'
                        f'    <span style="font-size:1.1rem">{medals[i]}</span>'
                        f'    <b style="font-size:1.1rem;color:{row2["color"]};margin-left:6px">{row2["label"]}</b>'
                        f'    <span style="background:{sc2}22;color:{sc2};border-radius:4px;padding:1px 8px;font-size:11px;margin-left:8px;font-family:JetBrains Mono">{sig2}</span>'
                        f'    <span style="color:#555;font-size:11px;margin-left:8px">Conf:{row2["conf"]}% RSI:{row2["rsi"]:.0f}</span>'
                        f'  </div>'
                        f'  <div style="font-size:11px;color:#555;text-align:right">Score: <b style="color:#00d4ff">{row2["score"]:.3f}</b></div>'
                        f'</div>'
                        f'<div style="font-size:12px;color:#888;margin:6px 0">{row2["desc"]}</div>'
                        f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin:8px 0">'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">Return</div><div style="color:{"#00ff88" if row2["bt_return"]>0 else "#ff4444"};font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["bt_return"]:+.1f}%</div></div>'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">Win%</div><div style="color:#00d4ff;font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["win_rate"]:.0f}%</div></div>'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">Sharpe</div><div style="color:#a78bfa;font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["sharpe"]:.2f}</div></div>'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">PF</div><div style="color:#f0a500;font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["profit_factor"]:.2f}</div></div>'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">Max DD</div><div style="color:#ff4444;font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["max_dd"]:.1f}%</div></div>'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">ATR/day</div><div style="color:#ffd700;font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["atr_pct"]:.2f}%</div></div>'
                        f'  <div style="text-align:center"><div style="font-size:9px;color:#555">Max Lots</div><div style="color:#888;font-size:12px;font-weight:700;font-family:JetBrains Mono">{row2["max_contracts"]}</div></div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'  <div style="font-size:12px;color:{"#00ff88" if i<3 else "#f0a500"}">{verdict}</div>'
                        f'  <div style="font-size:11px;color:#555">Alpha proj win/trade: <b style="color:#00d4ff">~${proj_win:,.0f}</b></div>'
                        f'</div></div>', unsafe_allow_html=True)

        # Summary table
        st.markdown("### 📋 Summary Table")
        tbl_rows = []
        for row2 in profit_analysis:
            sig2=row2["signal"]
            tbl_rows.append({
                "Instrument":row2["label"],"Signal":sig2,"Conf%":row2["conf"],"RSI":round(row2["rsi"],0),
                "Strategy Ret%":row2["bt_return"],"Win Rate%":row2["win_rate"],"Sharpe":row2["sharpe"],
                "PF":row2["profit_factor"],"Max DD%":row2["max_dd"],"ATR/day%":row2["atr_pct"],
                "Max Lots":row2["max_contracts"],"Score":row2["score"]
            })
        df_tbl = pd.DataFrame(tbl_rows)
        st.dataframe(df_tbl.style
            .format({"Strategy Ret%":"{:+.1f}%","Win Rate%":"{:.0f}%","Sharpe":"{:.2f}",
                     "PF":"{:.2f}","Max DD%":"{:.1f}%","ATR/day%":"{:.2f}%","Score":"{:.3f}"})
            .highlight_max(subset=["Strategy Ret%","Win Rate%","Sharpe","Score"],color="#1a3a1a")
            .highlight_min(subset=["Max DD%"],color="#1a3a1a"),
            use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("""<div style="background:#0a0a18;border:1px solid #1a1a30;border-radius:10px;padding:16px;font-size:13px;color:#aaa;line-height:1.9">
<b style="color:#ff6b00">⚡ Alpha Futures Profitability Tips:</b><br>
🥇 <b style="color:#00ff88">Top ranked = trade this first</b> — highest edge per the 100-AI ensemble<br>
📉 <b style="color:#f0a500">EOD 4% drawdown rule</b> = protect your account. Size so 1 bad trade ≠ end of day<br>
🎯 <b style="color:#00d4ff">Hit profit target fast</b> — once you're up 50% of target, scale back risk and protect<br>
⚡ <b style="color:#ffd700">High ATR% = more scalp opportunities</b> — volatile instruments move more ticks per bar<br>
📋 <b style="color:#888">Max lots = Alpha Futures contract limit for your account size</b> — never exceed this<br>
🕐 <b style="color:#888">9:30–11:00 ET</b> is the highest opportunity window for ES/NQ. GC trades best at London open.
</div>""", unsafe_allow_html=True)

# ── SCALP SIGNALS ─────────────────────────────────────────────────────────────
with t_scalp:
    st.subheader("⚡ Hyper Short — CME Scalp Signals (5-min)")
    st.caption("EMA3/8/13, RSI-7, Stochastic, VWAP deviation, Bollinger Band extremes. Best for 5–15 min holds. Use tight stops — 2–4 ticks on ES, 4–8 ticks on NQ.")
    min_conf = st.slider("Min confidence", 50, 90, 60, key="s_conf")
    if st.button("🔄 Refresh"):
        st.session_state["last_scalp"]=0; st.rerun()
    filtered = [s for s in scalp_signals if s["conf"]>=min_conf]
    if not filtered:
        st.info(f"No scalp signals above {min_conf}% right now. Lower threshold or wait.")
    else:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Signals", len(filtered))
        c2.metric("🟢 Long", sum(1 for s in filtered if s["direction"]=="LONG"))
        c3.metric("🔴 Short", sum(1 for s in filtered if s["direction"]=="SHORT"))
        c4.metric("🚨 Urgent", sum(1 for s in filtered if s["urgency"]=="urgent"))
        st.divider()
        for s in filtered:
            is_long = s["direction"]=="LONG"
            cls = "scalp-urgent" if s["urgency"]=="urgent" else "scalp-card"
            dc  = "#00ff88" if is_long else "#ff4444"
            urg = {"urgent":"🚨 URGENT","hot":"🔥 HOT","normal":"📊"}.get(s["urgency"],"")
            reasons_html=" · ".join(f'<span style="color:#888;font-size:11px">{r}</span>' for r in s["reasons"])
            bias_icon="↑" if "BUY" in s["daily_bias"] else "↓" if "SELL" in s["daily_bias"] else "→"
            st.markdown(f'<div class="{cls}">'
                        f'<div style="display:flex;justify-content:space-between;margin-bottom:8px">'
                        f'  <div><span style="color:{dc};font-size:1.2rem;font-weight:800">{"🟢 LONG" if is_long else "🔴 SHORT"}</span>'
                        f'  <span style="color:#aaa;margin-left:8px">{s["label"]}</span>'
                        f'  <span style="background:#1a1500;color:#ffd700;border-radius:4px;padding:1px 8px;font-size:10px;margin-left:8px">{urg}</span></div>'
                        f'  <div style="font-size:11px;color:#555">{s["timeframe"]} · {s["time"]}</div></div>'
                        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px">'
                        f'  <div style="background:#111;border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:#555">Entry</div><div style="color:#ffd700;font-family:JetBrains Mono;font-size:13px;font-weight:700">{s["price"]:,.1f}</div></div>'
                        f'  <div style="background:#111;border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:#555">Stop</div><div style="color:#ff4444;font-family:JetBrains Mono;font-size:13px;font-weight:700">{s["stop"]:,.1f}</div></div>'
                        f'  <div style="background:#111;border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:#555">Target</div><div style="color:#00ff88;font-family:JetBrains Mono;font-size:13px;font-weight:700">{s["target"]:,.1f}</div></div>'
                        f'  <div style="background:#111;border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:#555">Conf / R:R</div><div style="color:#a78bfa;font-family:JetBrains Mono;font-size:13px;font-weight:700">{s["conf"]}% · {s["rr"]}</div></div>'
                        f'  <div style="background:#111;border-radius:6px;padding:8px;text-align:center"><div style="font-size:9px;color:#555">Tick risk / $</div><div style="color:#f0a500;font-family:JetBrains Mono;font-size:13px;font-weight:700">{s["tick_risk"]:.0f}t · ${s["dollar_risk"]:,.0f}</div></div>'
                        f'</div>'
                        f'<div style="margin-bottom:5px">{reasons_html}</div>'
                        f'<div style="font-size:11px;color:#555">'
                        f'RSI7:{s["rsi"]} Stoch:{s["stoch_k"]} BB:{s["bb_pct"]}% VWAP:{s["vwap_dev"]:+.2f}%'
                        f'  Hold:{s["hold_est"]}  Daily:{bias_icon}{s["daily_bias"]}</div>'
                        f'</div>', unsafe_allow_html=True)

# ── GRAND STRATEGY ────────────────────────────────────────────────────────────
with t_strategy:
    st.subheader("🧠 Grand Strategy")
    if not grand:
        st.info("Ensemble running on first load…")
    else:
        sess_now=active_sessions[0] if active_sessions else "Off-hours"
        sw={"Tokyo":{"ES":0.4,"NQ":0.4,"GC":0.7,"CL":0.6,"YM":0.4,"BTC":1.3,"ETH":1.2},
            "London":{"ES":0.7,"NQ":0.6,"GC":1.4,"CL":1.1,"YM":0.6,"BTC":1.1,"ETH":1.0},
            "New York":{"ES":1.4,"NQ":1.4,"GC":1.1,"CL":1.2,"YM":1.3,"BTC":1.0,"ETH":0.9},
            "NY+London Overlap":{"ES":1.3,"NQ":1.2,"GC":1.2,"CL":1.1,"YM":1.2,"BTC":1.1,"ETH":1.0},
            "Off-hours":{"ES":0.3,"NQ":0.3,"GC":0.5,"CL":0.4,"YM":0.3,"BTC":0.7,"ETH":0.7}}.get(sess_now,{})
        scored={mk:{"score":grand[mk]["avg_sharpe"]*sw.get(mk,1.0),
                    "conf":min(99,round(grand[mk]["conf"]*sw.get(mk,1.0))),
                    "signal":grand[mk]["signal"],"rsi":grand[mk]["rsi"],"rr":grand[mk]["rr"],
                    "avg_ret":grand[mk]["avg_ret"]}
                for mk in grand if mk in selected_markets}
        if scored:
            best=max(scored,key=lambda x:scored[x]["score"]); bs=scored[best]; bsig=bs["signal"]
            is_bb="BUY" in bsig or bsig=="OVERSOLD"; is_bs="SELL" in bsig or bsig=="OVERBOUGHT"
            bc="#00ff88" if is_bb else "#ff4444" if is_bs else "#555"
            st.markdown(f'<div style="border:2px solid {bc};border-radius:14px;padding:20px 24px;'
                        f'background:{"#001a0a" if is_bb else "#1a0000" if is_bs else "#111"};margin-bottom:16px">'
                        f'<div style="font-size:11px;color:#555;font-family:JetBrains Mono">TOP PICK — {sess_now.upper()}</div>'
                        f'<div style="font-size:2rem;font-weight:800;color:{bc};margin:4px 0">{"🟢 BUY" if is_bb else "🔴 SELL" if is_bs else "⚪ HOLD"} — {MARKETS[best]["label"]}</div>'
                        f'<div style="font-size:13px;color:#aaa">Confidence: <b style="color:{bc}">{bs["conf"]}%</b> | R:R 1:{bs["rr"]} | Top-20 avg: {bs["avg_ret"]:+.1f}%</div>'
                        f'</div>', unsafe_allow_html=True)
        now_h = datetime.now(ZoneInfo("UTC")).hour
        plan = [(0,8,"00:00–08:00","Tokyo","BTC ETH","Crypto only. Avoid CME instruments — very thin pre-market.","#7C3AED"),
                (8,13,"08:00–13:00","London","GC CL","Gold + Crude wake up. London open breakouts. Avoid ES/NQ.","#2563EB"),
                (13,17,"13:00–17:00","NY Open + Overlap","ALL","🔥 PRIME TIME. ES/NQ explode at 9:30 ET. Sharpest CME signals.","#D97706"),
                (17,22,"17:00–22:00","New York Afternoon","ES NQ YM CL","US afternoon. Lower volume. Trail stops tighter.","#059669"),
                (22,24,"22:00–00:00","Off-hours","—","Very thin. Review plan for tomorrow.","#555")]
        st.markdown("### 📅 CME Trading Plan")
        for h0,h1,times,sname,mkts,tip,sc2 in plan:
            is_now=h0<=now_h<h1; border=sc2 if is_now else "#1a1a30"
            nb=f' <span style="background:{sc2};color:#fff;border-radius:3px;padding:1px 7px;font-size:10px">NOW</span>' if is_now else ""
            st.markdown(f'<div style="border:1.5px solid {border};border-radius:8px;padding:10px 16px;margin-bottom:6px;background:#0a0a18">'
                        f'<div style="font-size:12px;font-weight:700;color:{sc2};font-family:JetBrains Mono">{times} — {sname}{nb}</div>'
                        f'<div style="font-size:11px;color:#555">Instruments: {mkts}</div>'
                        f'<div style="font-size:12px;color:#aaa;margin-top:2px">{tip}</div>'
                        f'</div>', unsafe_allow_html=True)

# ── ALERTS ────────────────────────────────────────────────────────────────────
with t_alerts:
    st.subheader("📝 Alerts")
    notes = st.session_state["notes"]
    if not notes: st.info("Alerts appear here every 90 seconds.")
    icons={"watch":"👀 Watch","buy":"🟢 Possible buy","sell":"🔴 Consider sell","info":"💡 Info"}
    for n in notes[:15]:
        cls={"watch":"note-watch","buy":"note-buy","sell":"note-sell","info":"note-info"}.get(n["type"],"note-info")
        lbl=MARKETS.get(n["market"],{}).get("label",n["market"])
        st.markdown(f'<div class="note-card {cls}"><div style="font-size:10px;color:#555">{n["time"]}</div>'
                    f'<div style="font-weight:700;font-size:12px;margin-bottom:3px">{icons.get(n["type"],"💡")} — {lbl}</div>'
                    f'{n["text"]}</div>', unsafe_allow_html=True)
    if fg:
        st.divider(); st.markdown("**Fear & Greed (crypto sentiment)**")
        fig_fg = go.Figure(go.Bar(x=list(range(len(fg["history"]))),y=fg["history"],
            marker_color=["rgba(255,68,68,0.8)" if v<25 else "rgba(255,153,0,0.8)" if v<45 else "rgba(255,221,68,0.8)" if v<55 else "rgba(0,255,136,0.8)" for v in fg["history"]]))
        fig_fg.update_layout(height=160,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_fg, use_container_width=True, key="fg_chart")

# ── TRADERS ───────────────────────────────────────────────────────────────────
with t_traders:
    st.subheader("🤖 AI Trader Team")
    rows=[]
    for tr in TRADERS:
        pnl=tr["balance"]-25000; wins=sum(1 for t in tr["trades"] if t["result"]=="win"); tot=len(tr["trades"])
        dd=round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
        rows.append({"Trader":f"{tr['emoji']} {tr['name']}","Style":tr["style"],"Balance":tr["balance"],"P&L":pnl,
                     "Win%":round(wins/tot*100) if tot else 0,"Trades":tot,"DD%":dd})
    df_sc=pd.DataFrame(rows).sort_values("P&L",ascending=False).reset_index(drop=True); df_sc.index+=1
    st.dataframe(df_sc.style.format({"Balance":"${:,.0f}","P&L":"${:+,.0f}","Win%":"{}%","DD%":"{}%"})
        .map(lambda v:"color:#00ff88;font-weight:700" if isinstance(v,(int,float)) and v>0 else "color:#ff4444;font-weight:700" if isinstance(v,(int,float)) and v<0 else "",subset=["P&L"]),
        use_container_width=True)
    hfig=go.Figure()
    colors_t=["#00ff88","#00d4ff","#f0a500","#f87171","#a78bfa"]
    for i,tr in enumerate(TRADERS):
        if len(tr["history"])>1:
            hfig.add_trace(go.Scatter(y=tr["history"],name=f"{tr['emoji']} {tr['name']} ({(tr['balance']-25000)/25000*100:+.1f}%)",
                line=dict(color=colors_t[i%len(colors_t)],width=2)))
    hfig.add_hline(y=25000,line=dict(color="#444",width=1,dash="dot"))
    hfig.update_layout(height=240,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",
        margin=dict(l=0,r=0,t=30,b=0),legend=dict(orientation="h",y=1.05))
    st.plotly_chart(hfig,use_container_width=True,key="trader_history")

# ── BACKTEST ──────────────────────────────────────────────────────────────────
with t_bt:
    st.subheader(f"📊 Backtest — {bt_days} days")
    if st.session_state.get("bt_results"):
        st.markdown('<span style="background:#00d4ff22;border:1px solid #00d4ff44;border-radius:6px;padding:3px 10px;font-size:11px;color:#00d4ff">💾 Results preserved</span>', unsafe_allow_html=True)
    bt_mk=st.selectbox("Instrument",selected_markets,key="bt_mk")
    bt_mode=st.radio("Mode",["Single strategy","Compare all 5"],horizontal=True)
    bt_trader_name=st.selectbox("Strategy",[tr["name"] for tr in TRADERS]) if bt_mode=="Single strategy" else None
    show_sigs=st.toggle("Show signals on chart",value=True)
    if st.button("▶ Run Backtest",type="primary"):
        with st.spinner("Running backtest…"):
            df_bt=all_dfs.get(bt_mk,pd.DataFrame()); all_bts={}
            for tr in TRADERS:
                r=run_backtest(df_bt,tr,label=tr["name"])
                if "equity_curve" in r: all_bts[tr["name"]]=r
            if all_bts:
                mn=bt_trader_name if bt_trader_name and bt_trader_name in all_bts else list(all_bts.keys())[0]
                st.session_state["bt_results"]={"main":all_bts[mn],"all":all_bts,"market":bt_mk,"mode":bt_mode}
                try:
                    persist_set("bt_summary",{"market":bt_mk,"time":datetime.now().strftime("%H:%M %d/%m/%Y"),
                        "results":{n:{k:v for k,v in r.items() if k not in ("equity_curve","trade_list")} for n,r in all_bts.items()}})
                except: pass
            else: st.error("Not enough data.")
    saved=st.session_state.get("bt_results",{}); bt=saved.get("main"); all_bts=saved.get("all",{})
    if bt and "equity_curve" in bt:
        if bt_mode=="Compare all 5" and all_bts:
            comp=[{"Trader":n,"Return%":r["total_return"],"Win%":r["win_rate"],"Trades":r["total_trades"],
                   "MaxDD%":r["max_drawdown"],"Sharpe":r["sharpe"],"PF":r["profit_factor"]}
                  for n,r in all_bts.items() if "total_return" in r]
            if comp:
                df_c=pd.DataFrame(comp).sort_values("Sharpe",ascending=False)
                df_c.insert(0,"#",["🥇","🥈","🥉","4️⃣","5️⃣"][:len(df_c)])
                st.dataframe(df_c.style.format({"Return%":"{:+.1f}%","Win%":"{:.0f}%","MaxDD%":"{:.1f}%","Sharpe":"{:.2f}","PF":"{:.2f}"})
                    .highlight_max(subset=["Return%","Win%","Sharpe"],color="#1a3a1a")
                    .highlight_min(subset=["MaxDD%"],color="#1a3a1a"),use_container_width=True,hide_index=True)
            ef=build_equity_chart(all_bts)
            if ef: st.plotly_chart(ef,use_container_width=True,key="bt_eq_compare")
        cols8=st.columns(8)
        cr="#00ff88" if bt["total_return"]>0 else "#ff4444"
        for col2,(val,lbl2,vc) in zip(cols8,[
            (f"{bt['total_return']:+.1f}%","Strategy",cr),(f"{bt['bh_return']:+.1f}%","Buy&Hold","#aaa"),
            (f"{bt['win_rate']:.0f}%","Win Rate","#aaa"),(str(bt["total_trades"]),"Trades","#aaa"),
            (f"{bt['profit_factor']:.2f}","Prof Factor","#aaa"),(f"{bt['max_drawdown']:.1f}%","Max DD","#ff4444"),
            (f"{bt['sharpe']:.2f}","Sharpe","#aaa"),(f"{bt['calmar']:.2f}","Calmar","#aaa")]):
            col2.markdown(f'<div class="bt-stat"><div class="bt-val" style="color:{vc}">{val}</div><div class="bt-lbl">{lbl2}</div></div>',unsafe_allow_html=True)
        chart_mk=saved.get("market",bt_mk)
        fig_m=build_chart(all_dfs.get(chart_mk,pd.DataFrame()),f"{chart_mk} — {bt.get('label','')}",
            MARKETS.get(chart_mk,{}).get("color","#fff"),show_sigs,bt)
        if fig_m: st.plotly_chart(fig_m,use_container_width=True,key="bt_main_chart")
        with st.expander("📋 Trade log"):
            tdf3=bt["trade_list"].copy()
            st.dataframe(tdf3.style.format({"entry":"${:,.2f}","exit":"${:,.2f}","pnl":"${:+,.2f}"})
                .map(lambda v:"color:#00ff88" if isinstance(v,(int,float)) and v>0 else "color:#ff4444",subset=["pnl"]),
                use_container_width=True,hide_index=True)
    else:
        bt_sum=persist_get("bt_summary")
        if bt_sum:
            st.info(f"💾 Last backtest: **{bt_sum.get('market','?')}** at {bt_sum.get('time','?')}")
        else:
            st.info("Select an instrument and click ▶ Run Backtest.")

# ── 100-AI LAB ────────────────────────────────────────────────────────────────
with t_ensemble:
    st.subheader("🔬 100-AI Ensemble Lab")
    if st.button("🔄 Re-run Full Ensemble",type="primary"):
        with st.spinner("Testing 100 configs…"):
            try:
                ens,grand2=run_ensemble(all_dfs)
                st.session_state["ensemble_results"]=ens; st.session_state["grand_strategy"]=grand2
                st.session_state["ensemble_ran"]=True; st.session_state["profit_analysis"]={}
                persist_set("ensemble_ran",True); st.success("✅ Done!")
            except Exception as e: st.error(f"Error: {e}")
    ens=st.session_state.get("ensemble_results",{})
    if ens:
        e_mk=st.selectbox("Market",list(ens.keys()),key="emk")
        if e_mk and e_mk in ens:
            res=ens[e_mk]; rets=[r["total_return"] for r in res]
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("AIs",len(res)); c2.metric("Winners",len([r for r in res if r["total_return"]>0]))
            c3.metric("Avg ret",f"{np.mean(rets):+.1f}%"); c4.metric("Best",f"{max(rets):+.1f}%")
            c5.metric("Avg Sharpe",f"{np.mean([r['sharpe'] for r in res]):.2f}")
            top20=res[:20]
            fig_lb=make_subplots(rows=1,cols=2,subplot_titles=["Top-20 Returns","Top-20 Sharpe"])
            fig_lb.add_trace(go.Bar(x=[r["total_return"] for r in top20],y=[r["name"] for r in top20],orientation="h",
                marker_color=["rgba(0,204,102,0.8)" if r["total_return"]>=0 else "rgba(204,51,51,0.8)" for r in top20]),row=1,col=1)
            fig_lb.add_trace(go.Bar(x=[r["sharpe"] for r in top20],y=[r["name"] for r in top20],orientation="h",
                marker_color=["rgba(167,139,250,0.8)" if r["sharpe"]>=0 else "rgba(255,107,107,0.8)" for r in top20]),row=1,col=2)
            fig_lb.update_layout(height=480,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",showlegend=False,margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_lb,use_container_width=True,key="ens_lb")

# ── ALPHA FUTURES REFERENCE ───────────────────────────────────────────────────
with t_ref:
    st.subheader("📚 Alpha Futures Reference")
    st.markdown("""
### Alpha Futures — What You Need to Know

**Alpha Futures** is a prop firm (part of Alpha Capital Group) that funds traders on **real CME exchange-traded futures**.
Unlike forex prop firms — which simulate trades — Alpha Futures traders execute on actual CME/CBOT/NYMEX markets.

#### Platforms (all supported)
| Platform | Type | Best for |
|---|---|---|
| **Tradovate** | Cloud-based, browser | Fast execution, TradingView integration |
| **NinjaTrader** | Desktop | Algo strategies, advanced charts |
| **AlphaTicks (Quantower)** | Proprietary | Commission-free, integrated risk tools |
| **CQG / Rithmic** | Pro data feed | Sub-ms execution, institutional grade |

#### Account Rules
| Rule | Detail |
|---|---|
| Max Loss Limit | 4% of **end-of-day** balance (NOT intraday high — trader-friendly) |
| Profit Target | 10% of account size to get funded |
| Daily loss limit | None during evaluation |
| News trading | Permitted (with some restrictions) |
| Consistency rule | None — trade your style |
| Scaling | Available after proving consistency |

#### Instruments on Alpha Futures
| Contract | Tick | Tick Value | Notes |
|---|---|---|---|
| ES (E-mini S&P) | 0.25 pt | $12.50 | Most liquid. Best spreads. |
| NQ (E-mini Nasdaq) | 0.25 pt | $5.00 | Higher beta than ES |
| YM (Dow Jones) | 1 pt | $5.00 | Slower, value-driven |
| GC (Gold) | $0.10/oz | $10.00 | Safe haven, USD-driven |
| CL (Crude Oil) | $0.01/bbl | $10.00 | High vol, EIA data sensitive |
| MES (Micro ES) | 0.25 pt | $1.25 | Start here if sizing up |
| MNQ (Micro NQ) | 0.25 pt | $0.50 | Micro Nasdaq for smaller risk |

#### Best Strategy for Alpha Futures Evaluation
1. **Risk 0.3–0.5% per trade** (not the maximum — protect the 4% EOD limit)
2. **Target 1–3 trades/day** on highest-confidence signals only
3. **Scalp ES/NQ 9:30–11:00 ET** — this is the golden window
4. **Stop before 3% drawdown** on any day — gives you buffer
5. **Use micros (MES/MNQ)** to size precisely during evaluation phase
""")

    st.markdown("### Instrument Specs")
    specs_rows = []
    for mk,info in MARKETS.items():
        specs_rows.append({"Instrument":info["label"],"Tick Size":info["tick"],"Tick Value":f"${info['tick_val']}",
                           "Contract":info["contract_val"],"Max lots (25k)":info["alpha_limits"].get("25k",5),"Description":info["desc"][:60]+"…"})
    st.dataframe(pd.DataFrame(specs_rows),use_container_width=True,hide_index=True)

if auto_refresh:
    time.sleep(90)
    st.cache_data.clear()
    st.rerun()
