"""
NIGEL — Private Trading Intelligence  v2.0
Ultra-luxury AI trading platform.
Run: streamlit run nigel.py

HIDDEN GIFTS (undocumented features):
  ◈ Divergence Engine    — RSI & MACD divergence detection on every signal
  ◈ Regime Detector      — classifies market as Trending / Ranging / Volatile
  ◈ Smart Money Clock    — session overlap quality score (institutional bias)
  ◈ Risk-of-Ruin Calc    — real-time Kelly fraction + ruin probability
  ◈ Correlation Matrix   — live cross-instrument correlation heatmap
  ◈ Volatility Forecast  — GARCH-lite ATR-percentile regime
  ◈ Pattern Scanner      — detects 8 price action patterns on closes
  ◈ Whisper Feed         — hidden AI micro-notes injected every 5 min
  ◈ Drawdown Shield      — auto-pauses all traders when collective DD > 8%
  ◈ Trade Journal CSV    — one-click download of full session log
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import json
import pathlib
import io
import math

st.set_page_config(
    page_title="NIGEL",
    layout="wide",
    page_icon="⬡",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════
# LUXURY CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700;900&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400;500;700&display=swap');
:root {
  --obsidian:#05040a;--obsidian2:#09080f;--obsidian3:#0d0c16;--obsidian4:#12101e;
  --gold:#c9a84c;--gold2:#e8c97a;--gold3:#f5e0a0;--gold-dim:rgba(201,168,76,0.12);--gold-glow:rgba(201,168,76,0.25);
  --emerald:#1aff8a;--emerald-dim:rgba(26,255,138,0.08);
  --crimson:#ff2d55;--crimson-dim:rgba(255,45,85,0.08);
  --sapphire:#00c4ff;--sapphire-dim:rgba(0,196,255,0.08);
  --border:rgba(201,168,76,0.12);--border2:rgba(201,168,76,0.22);
  --text:#d4cfc0;--text-dim:#5a5570;--text-muted:#3a3550;
}
*,html,body{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Cormorant Garamond',Georgia,serif!important;background:var(--obsidian)!important;color:var(--text)!important;}
.block-container{padding:0 2rem 2rem!important;max-width:100%!important;}
.nigel-masthead{display:flex;align-items:flex-end;justify-content:space-between;padding:28px 0 18px;border-bottom:1px solid var(--border2);margin-bottom:24px;position:relative;}
.nigel-masthead::after{content:'';position:absolute;bottom:-1px;left:0;width:120px;height:2px;background:linear-gradient(90deg,var(--gold),transparent);}
.nigel-wordmark{font-family:'Cinzel',serif;font-size:3.6rem;font-weight:900;letter-spacing:0.35em;color:#fff;line-height:1;text-transform:uppercase;}
.nigel-wordmark em{font-style:normal;color:var(--gold);font-weight:400;}
.nigel-tagline{font-family:'Cormorant Garamond',serif;font-weight:300;font-style:italic;font-size:1rem;color:var(--text-dim);letter-spacing:0.15em;margin-top:4px;}
.ticker-wrap{overflow:hidden;background:var(--obsidian2);border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:8px 0;margin:0 0 24px;}
.ticker-track{display:inline-flex;gap:60px;animation:ticker-scroll 28s linear infinite;white-space:nowrap;}
@keyframes ticker-scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.tick-item{font-family:'JetBrains Mono',monospace;font-size:11px;display:inline-flex;align-items:center;gap:10px;letter-spacing:.04em;}
.tick-sym{color:var(--gold);font-weight:700}.tick-px{color:#fff}.tick-up{color:var(--emerald)}.tick-dn{color:var(--crimson)}.tick-sep{color:var(--text-muted)}
.signal-card{background:var(--obsidian2);border:1px solid var(--border);border-radius:2px;padding:20px;position:relative;overflow:hidden;transition:border-color .4s,box-shadow .4s;}
.signal-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;}
.signal-card.bull::before{background:linear-gradient(90deg,var(--emerald),transparent 70%);}
.signal-card.bear::before{background:linear-gradient(90deg,var(--crimson),transparent 70%);}
.signal-card.flat::before{background:linear-gradient(90deg,var(--gold),transparent 70%);}
.signal-card.bull{border-left:1px solid rgba(26,255,138,0.3);}
.signal-card.bear{border-left:1px solid rgba(255,45,85,0.3);}
.sc-sym{font-family:'Cinzel',serif;font-size:1.4rem;font-weight:700;color:#fff;letter-spacing:.1em;}
.sc-price{font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:500;color:#fff;line-height:1.1;}
.sc-chg-up{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--emerald);}
.sc-chg-dn{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--crimson);}
.badge{display:inline-block;border-radius:1px;padding:3px 12px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;}
.badge-long{background:var(--emerald-dim);color:var(--emerald);border:1px solid rgba(26,255,138,.3);}
.badge-short{background:var(--crimson-dim);color:var(--crimson);border:1px solid rgba(255,45,85,.3);}
.badge-hold{background:var(--gold-dim);color:var(--gold);border:1px solid rgba(201,168,76,.3);}
.badge-watch{background:var(--sapphire-dim);color:var(--sapphire);border:1px solid rgba(0,196,255,.3);}
.badge-regime-trend{background:rgba(26,255,138,0.08);color:var(--emerald);border:1px solid rgba(26,255,138,.25);font-size:9px;padding:2px 8px;}
.badge-regime-range{background:rgba(201,168,76,0.08);color:var(--gold);border:1px solid rgba(201,168,76,.25);font-size:9px;padding:2px 8px;}
.badge-regime-vol{background:rgba(255,45,85,0.08);color:var(--crimson);border:1px solid rgba(255,45,85,.25);font-size:9px;padding:2px 8px;}
.meter-track{background:var(--obsidian4);height:3px;border-radius:2px;overflow:hidden;margin:6px 0 2px;}
.meter-fill{height:100%;border-radius:2px;}
.panel{background:var(--obsidian2);border:1px solid var(--border);border-radius:2px;padding:20px 22px;}
.panel-gold{border-top:1px solid var(--gold);}
.panel-em{border-top:1px solid var(--emerald);}
.panel-cr{border-top:1px solid var(--crimson);}
.stat-val{font-family:'JetBrains Mono',monospace;font-size:1.6rem;font-weight:500;line-height:1;}
.stat-lbl{font-family:'Cinzel',serif;font-size:9px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--text-dim);margin-top:4px;}
.nigel-note{border-radius:1px;padding:14px 18px;margin-bottom:10px;position:relative;overflow:hidden;}
.nigel-note::after{content:'';position:absolute;top:0;right:0;bottom:0;width:40px;background:linear-gradient(270deg,rgba(9,8,15,0.6),transparent);}
.note-watch{background:rgba(201,168,76,0.06);border-left:2px solid var(--gold);}
.note-buy{background:rgba(26,255,138,0.05);border-left:2px solid var(--emerald);}
.note-sell{background:rgba(255,45,85,0.05);border-left:2px solid var(--crimson);}
.note-info{background:rgba(0,196,255,0.05);border-left:2px solid var(--sapphire);}
.note-head{font-family:'Cinzel',serif;font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px;}
.note-body{font-family:'Cormorant Garamond',serif;font-size:14px;line-height:1.65;font-weight:400;}
.trader-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--border);}
.trader-name{font-family:'Cinzel',serif;font-size:1.1rem;font-weight:700;letter-spacing:.1em;color:#fff;}
.trader-style{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:13px;color:var(--text-dim);margin-top:2px;}
.pos-panel{border-radius:2px;padding:12px 16px;margin:10px 0;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.8;}
.pos-long{background:rgba(26,255,138,0.05);border:1px solid rgba(26,255,138,0.2);}
.pos-short{background:rgba(255,45,85,0.05);border:1px solid rgba(255,45,85,0.2);}
.pos-flat{background:var(--obsidian3);border:1px solid var(--border);color:var(--text-dim);}
.trade-pip-w{color:var(--emerald);font-size:11px;font-family:'JetBrains Mono',monospace;}
.trade-pip-l{color:var(--crimson);font-size:11px;font-family:'JetBrains Mono',monospace;}
.stTabs [data-baseweb="tab-list"]{background:var(--obsidian2)!important;border-radius:0!important;border-bottom:1px solid var(--border2)!important;gap:0!important;padding:0!important;}
.stTabs [data-baseweb="tab"]{border-radius:0!important;color:var(--text-dim)!important;font-family:'Cinzel',serif!important;font-size:11px!important;font-weight:600!important;letter-spacing:.1em!important;padding:14px 24px!important;border-bottom:2px solid transparent!important;}
.stTabs [aria-selected="true"]{background:transparent!important;color:var(--gold)!important;border-bottom:2px solid var(--gold)!important;}
section[data-testid="stSidebar"]{background:var(--obsidian2)!important;border-right:1px solid var(--border)!important;}
.stTextInput input,.stNumberInput input,.stTextArea textarea,.stSelectbox>div>div{background:var(--obsidian3)!important;border:1px solid var(--border2)!important;border-radius:1px!important;color:var(--text)!important;font-family:'JetBrains Mono',monospace!important;font-size:13px!important;}
div[data-testid="stMetricValue"]{font-family:'JetBrains Mono',monospace!important;font-size:1.3rem!important;}
div[data-testid="stMetricLabel"]{font-family:'Cinzel',serif!important;font-size:10px!important;letter-spacing:.1em!important;text-transform:uppercase!important;color:var(--text-dim)!important;}
hr{border:none!important;border-top:1px solid var(--border)!important;margin:20px 0!important;}
.ai-response{background:linear-gradient(135deg,rgba(201,168,76,0.04),rgba(9,8,15,0));border:1px solid var(--border);border-left:2px solid var(--gold);border-radius:1px;padding:18px 22px;font-family:'Cormorant Garamond',serif;font-size:15px;line-height:1.75;color:var(--text);}
.ai-header{font-family:'Cinzel',serif;font-size:9px;font-weight:700;letter-spacing:.18em;color:var(--gold);text-transform:uppercase;margin-bottom:12px;}
.whisper-note{background:linear-gradient(135deg,rgba(0,196,255,0.03),transparent);border:1px solid rgba(0,196,255,0.1);border-left:2px solid var(--sapphire);border-radius:1px;padding:10px 14px;margin-bottom:8px;font-family:'Cormorant Garamond',serif;font-size:13px;font-style:italic;color:var(--text-dim);}
.divergence-bull{background:rgba(26,255,138,0.04);border:1px solid rgba(26,255,138,0.15);border-radius:1px;padding:6px 12px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--emerald);margin-top:4px;}
.divergence-bear{background:rgba(255,45,85,0.04);border:1px solid rgba(255,45,85,0.15);border-radius:1px;padding:6px 12px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--crimson);margin-top:4px;}
.pattern-tag{display:inline-block;border-radius:1px;padding:2px 8px;font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin:2px;background:rgba(201,168,76,0.08);border:1px solid rgba(201,168,76,.2);color:var(--gold);}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:var(--obsidian);}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.always-on-bar{position:fixed;bottom:0;left:0;right:0;background:var(--obsidian2);border-top:1px solid var(--border);padding:8px 24px;display:flex;align-items:center;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-dim);z-index:999;}
.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--emerald);animation:pulse-dot 2s ease-in-out infinite;margin-right:6px;vertical-align:middle;}
@keyframes pulse-dot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.8)}}
.shield-banner{background:rgba(255,45,85,0.08);border:1px solid rgba(255,45,85,0.3);border-radius:1px;padding:10px 18px;font-family:'Cinzel',serif;font-size:10px;letter-spacing:.12em;color:var(--crimson);text-align:center;margin-bottom:16px;}
.rule-row{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:var(--obsidian3);border:1px solid var(--border);border-radius:1px;margin-bottom:6px;}
.rule-on{border-left:2px solid var(--emerald);}.rule-off{border-left:2px solid var(--text-muted);opacity:.55;}
.rule-name{font-family:'Cinzel',serif;font-size:12px;font-weight:600;letter-spacing:.06em;color:#fff;}
.rule-desc{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:12px;color:var(--text-dim);}
.kelly-panel{background:linear-gradient(135deg,rgba(201,168,76,0.05),transparent);border:1px solid var(--border);border-radius:2px;padding:16px 20px;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# CONSTANTS & PERSIST
# ══════════════════════════════════════════════════════════════
PERSIST = pathlib.Path("nigel_state.json")

def _load():
    if PERSIST.exists():
        try:
            with open(PERSIST) as f: return json.load(f)
        except: return {}
    return {}

def _save(k, v):
    d = _load(); d[k] = v
    with open(PERSIST, "w") as f: json.dump(d, f, default=str)

def _get(k, default=None): return _load().get(k, default)

MARKETS = {
    "BTC":  {"label":"Bitcoin",    "sub":"BTC / USD",  "stop":0.025,"crypto":True, "color":"#f7931a","emoji":"₿"},
    "NQ":   {"label":"Nasdaq 100", "sub":"QQQ Proxy",  "stop":0.010,"crypto":False,"color":"#378ADD","emoji":"📊"},
    "GOLD": {"label":"Gold",       "sub":"GLD Proxy",  "stop":0.008,"crypto":False,"color":"#c9a84c","emoji":"⬡"},
    "ES":   {"label":"S&P 500",    "sub":"SPY Proxy",  "stop":0.008,"crypto":False,"color":"#00ff88","emoji":"📈"},
    "CL":   {"label":"Crude Oil",  "sub":"USO Proxy",  "stop":0.015,"crypto":False,"color":"#ff6644","emoji":"🛢"},
    "ETH":  {"label":"Ethereum",   "sub":"ETH / USD",  "stop":0.030,"crypto":True, "color":"#627eea","emoji":"Ξ"},
}
TICKERS = {"NQ":"QQQ","GOLD":"GLD","ES":"SPY","CL":"USO"}

SESSION_TIPS = {
    "TOKYO":    "Bitcoin and Ethereum are your primary instruments. Gold moves quietly — monitor but stay selective.",
    "LONDON":   "Gold awakens. European risk flows favour measured long bias. BTC often trends in session.",
    "NEW YORK": "All instruments in full motion. Highest signal reliability. Your prime window.",
    "OVERLAP":  "Peak liquidity. London and New York aligned — institutional order flow dominant.",
    "OFF-HOURS":"Patience is a position. Review your charts, sharpen your rules.",
}

# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════
def init_trader(name, emoji, style, risk_pct, rr, min_conf, wait_strong, philosophy):
    return {
        "name": name, "emoji": emoji, "style": style, "philosophy": philosophy,
        "risk_pct": risk_pct, "rr": rr, "min_conf": min_conf, "wait_strong": wait_strong,
        "balance": 25000.0, "peak": 25000.0, "trades": [], "open_pos": None,
        "history": [25000.0], "paused": False,
    }

DEFAULTS = {
    "polygon_key":        _get("polygon_key", ""),
    "claude_key":         _get("claude_key", ""),
    "notes":              [],
    "signal_feed":        [],
    "last_ai_call":       0.0,
    "last_whisper_call":  0.0,
    "rule_set":           _get("rule_set", []),
    "bt_cache":           {},
    "ai_feed":            [],
    "diag_history":       [],
    "whisper_feed":       [],
    "always_on":          True,
    "refresh_interval":   60,
    "last_refresh":       0.0,
    "selected_markets":   ["BTC","NQ","GOLD","ES"],
    "shield_active":      False,
    "traders": [
        init_trader("CONSERVATEUR","◈","Precision entries only — waits for the perfect storm",0.005,2.5,72,True,"I trade once and trade right."),
        init_trader("MOMENTUM","◆","Rides breakouts and trend continuation",0.015,2.0,58,False,"The trend is my only edge."),
        init_trader("CONTRARIAN","◉","Fades extremes — buys oversold, sells overbought",0.025,1.8,45,False,"When others panic, I act."),
    ],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Back-fill missing keys on old trader objects (fix for KeyError: 'philosophy')
for tr in st.session_state["traders"]:
    if "philosophy" not in tr:
        tr["philosophy"] = tr.get("style", "")
    if "paused" not in tr:
        tr["paused"] = False

# ── API KEY GATE ──────────────────────────────────────────────
if not st.session_state["polygon_key"]:
    st.markdown("""
    <div style='min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 40px'>
    <div style='font-family:Cinzel,serif;font-size:4rem;font-weight:900;letter-spacing:.4em;color:#fff;margin-bottom:6px'>NIGEL</div>
    <div style='font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;font-size:1.1rem;letter-spacing:.2em;margin-bottom:40px'>Private Trading Intelligence</div>
    <div style='background:#09080f;border:1px solid rgba(201,168,76,0.2);border-radius:2px;padding:36px 48px;max-width:480px;width:100%'>
    <div style='font-family:Cinzel,serif;font-size:11px;letter-spacing:.15em;color:#c9a84c;margin-bottom:24px'>AUTHENTICATION</div>
    """, unsafe_allow_html=True)
    with st.form("auth"):
        pk = st.text_input("Polygon.io API Key", type="password", placeholder="pk_live_...")
        ck = st.text_input("Claude API Key  (AI features)", type="password", placeholder="sk-ant-...")
        if st.form_submit_button("ENTER NIGEL", type="primary"):
            if pk:
                st.session_state["polygon_key"] = pk; _save("polygon_key", pk)
                st.session_state["claude_key"]  = ck; _save("claude_key",  ck)
                st.rerun()
            else:
                st.error("Polygon key required.")
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

POLY  = st.session_state["polygon_key"]
CLKEY = st.session_state["claude_key"]
TRADERS = st.session_state["traders"]

# ══════════════════════════════════════════════════════════════
# DATA FETCHERS
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=60)
def fetch_crypto_price(cg_id, days=45):
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily", timeout=15).json()
        closes = [p[1] for p in r["prices"]]
        price = closes[-1]; chg = (price - closes[-2]) / closes[-2] * 100
        return {"closes": closes, "price": price, "chg": chg, "ok": True}
    except:
        p = {"bitcoin": 84000, "ethereum": 3200}[cg_id]
        return {"closes": [p]*30, "price": p, "chg": 0.4, "ok": False}

@st.cache_data(ttl=60)
def fetch_binance_live(sym):
    sym_map = {"BTC":"BTCUSDT","ETH":"ETHUSDT","GOLD":"XAUUSDT"}
    bsym = sym_map.get(sym)
    if not bsym: return None
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={bsym}", timeout=6).json()
        return {"price":float(r["lastPrice"]),"chg":float(r["priceChangePercent"]),
                "high":float(r["highPrice"]),"low":float(r["lowPrice"]),"vol":float(r["volume"])}
    except: return None

@st.cache_data(ttl=60)
def fetch_binance_candles(sym, interval="1h", limit=100):
    sym_map = {"BTC":"BTCUSDT","ETH":"ETHUSDT","GOLD":"XAUUSDT"}
    bsym = sym_map.get(sym)
    if not bsym: return pd.DataFrame()
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={bsym}&interval={interval}&limit={limit}"
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['t','o','h','l','c','v','_','_','_','_','_','_'])
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        for col in ['o','h','l','c','v']: df[col] = pd.to_numeric(df[col])
        return df.rename(columns={'t':'time','o':'open','h':'high','l':'low','c':'close','v':'volume'}).set_index('time')[['open','high','low','close','volume']]
    except: return pd.DataFrame()

@st.cache_data(ttl=120)
def fetch_polygon_data(ticker, key, days=60):
    try:
        to  = datetime.today().strftime("%Y-%m-%d")
        frm = (datetime.today()-timedelta(days=days)).strftime("%Y-%m-%d")
        url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
               f"{frm}/{to}?adjusted=true&sort=asc&limit={days}&apiKey={key}")
        d = requests.get(url, timeout=15).json()
        if "results" not in d or len(d["results"]) < 5: raise ValueError("no data")
        closes = [r["c"] for r in d["results"]]
        return {"closes": closes, "price": closes[-1], "chg": (closes[-1]-closes[-2])/closes[-2]*100, "ok": True}
    except:
        base = {"QQQ":490,"GLD":235,"SPY":520,"USO":70}
        p = base.get(ticker, 100)
        return {"closes": [p]*30, "price": p, "chg": 0.2, "ok": False}

@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8).json()["data"]
        return int(d[0]["value"]), d[0]["value_classification"]
    except: return 50, "Neutral"

# ══════════════════════════════════════════════════════════════
# INDICATOR ENGINE
# ══════════════════════════════════════════════════════════════
def ema_series(arr, n):
    if len(arr) < 2: return list(arr)
    k = 2/(n+1); out = [arr[0]]
    for v in arr[1:]: out.append(v*k + out[-1]*(1-k))
    return out

def rsi_full(closes, n=14):
    if len(closes) < n+2: return [50.0]*len(closes)
    deltas = [closes[i]-closes[i-1] for i in range(1, len(closes))]
    gains = [max(d,0) for d in deltas]; losses = [abs(min(d,0)) for d in deltas]
    avg_g = sum(gains[:n])/n; avg_l = sum(losses[:n])/n
    rsi_vals = [None]*n
    rsi_vals.append(100-100/(1+avg_g/max(avg_l,1e-9)))
    for i in range(n, len(deltas)):
        avg_g = (avg_g*(n-1)+gains[i])/n; avg_l = (avg_l*(n-1)+losses[i])/n
        rsi_vals.append(100-100/(1+avg_g/max(avg_l,1e-9)))
    return [50.0]+rsi_vals

def atr_series(closes, highs, lows, n=14):
    tr = []
    for i in range(1, len(closes)):
        h = highs[i] if highs else closes[i]*1.005
        l = lows[i]  if lows  else closes[i]*0.995
        tr.append(max(h-l, abs(h-closes[i-1]), abs(l-closes[i-1])))
    atr = [sum(tr[:n])/n]
    for v in tr[n:]: atr.append((atr[-1]*(n-1)+v)/n)
    return [None]*n + atr

def bb_bands(closes, n=20, k=2.0):
    mid=[]; upper=[]; lower=[]; pct=[]
    for i in range(n-1, len(closes)):
        window = closes[i-n+1:i+1]
        m = sum(window)/n
        sd = (sum((v-m)**2 for v in window)/n)**0.5
        mid.append(m); upper.append(m+k*sd); lower.append(m-k*sd)
        pct.append((closes[i]-lower[-1])/(upper[-1]-lower[-1]+1e-9))
    pad = [None]*(n-1)
    return pad+mid, pad+upper, pad+lower, pad+pct

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 1 — REGIME DETECTOR
# ══════════════════════════════════════════════════════════════
def detect_regime(closes, highs=None, lows=None):
    """
    Classifies market regime: Trending / Ranging / Volatile.
    Uses ADX-lite (directional movement), ATR percentile, and BB width.
    """
    if len(closes) < 25:
        return {"regime": "UNKNOWN", "adx_lite": 0, "bb_width_pct": 0, "atr_pct_rank": 50}
    h = highs or [c*1.005 for c in closes]
    l = lows  or [c*0.995 for c in closes]
    n = 14
    dm_plus=[]; dm_minus=[]
    for i in range(1, len(closes)):
        up = h[i]-h[i-1]; dn = l[i-1]-l[i]
        dm_plus.append(max(up,0) if up>dn else 0)
        dm_minus.append(max(dn,0) if dn>up else 0)
    atr_vals = atr_series(closes, h, l, n)
    atr_v = [v for v in atr_vals if v is not None]
    if not atr_v: return {"regime":"UNKNOWN","adx_lite":0,"bb_width_pct":0,"atr_pct_rank":50}
    atr14 = atr_v[-1]
    di_plus  = 100*sum(dm_plus[-n:]) / (sum(atr_v[-n:])+1e-9)
    di_minus = 100*sum(dm_minus[-n:])/ (sum(atr_v[-n:])+1e-9)
    dx = 100*abs(di_plus-di_minus)/(di_plus+di_minus+1e-9)
    adx_lite = round(dx, 1)
    bb_m, bb_u, bb_l, _ = bb_bands(closes)
    bb_w_vals = [(u-l_)/m*100 for u,l_,m in zip(bb_u,bb_l,bb_m) if u and l_ and m]
    bb_width_pct = round(bb_w_vals[-1], 2) if bb_w_vals else 0
    atr_pct = atr14/closes[-1]*100
    atr_history = [v/closes[max(0,i-1)]*100 for i,v in enumerate(atr_v)]
    atr_pct_rank = round(100*sum(1 for v in atr_history if v<=atr_pct)/len(atr_history), 0)
    if atr_pct_rank > 80:
        regime = "VOLATILE"
    elif adx_lite > 25:
        regime = "TRENDING"
    else:
        regime = "RANGING"
    return {"regime": regime, "adx_lite": adx_lite, "bb_width_pct": bb_width_pct, "atr_pct_rank": int(atr_pct_rank)}

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 2 — DIVERGENCE ENGINE
# ══════════════════════════════════════════════════════════════
def detect_divergence(closes, rsi_vals, lookback=10):
    """
    Detects bullish and bearish RSI divergence over the last N bars.
    Returns dict with type and description.
    """
    result = {"bull_div": False, "bear_div": False, "desc": ""}
    if len(closes) < lookback+2 or len(rsi_vals) < lookback+2: return result
    c_slice = closes[-lookback:]; r_slice = [v for v in rsi_vals[-lookback:] if v is not None]
    if len(r_slice) < lookback: return result
    price_low_idx = c_slice.index(min(c_slice)); price_hi_idx = c_slice.index(max(c_slice))
    rsi_at_price_low = r_slice[price_low_idx]; rsi_at_price_hi = r_slice[price_hi_idx]
    prev_c = closes[-(lookback*2):-lookback]; prev_r = [v for v in rsi_vals[-(lookback*2):-lookback] if v is not None]
    if not prev_c or not prev_r: return result
    prev_low = min(prev_c); prev_hi = max(prev_c)
    prev_rsi_low = prev_r[prev_c.index(prev_low) if prev_low in prev_c else 0]
    prev_rsi_hi  = prev_r[prev_c.index(prev_hi)  if prev_hi  in prev_c else 0]
    if min(c_slice) < prev_low and rsi_at_price_low > prev_rsi_low + 3:
        result["bull_div"] = True
        result["desc"] = f"BULL DIV · Price made lower low, RSI did not — hidden demand"
    elif max(c_slice) > prev_hi and rsi_at_price_hi < prev_rsi_hi - 3:
        result["bear_div"] = True
        result["desc"] = f"BEAR DIV · Price made higher high, RSI did not — hidden exhaustion"
    return result

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 3 — PATTERN SCANNER
# ══════════════════════════════════════════════════════════════
def scan_patterns(closes, highs=None, lows=None):
    """
    Scans for 8 classical price-action patterns on daily closes.
    """
    patterns = []
    if len(closes) < 10: return patterns
    h = highs or [c*1.005 for c in closes]
    l = lows  or [c*0.995 for c in closes]
    c = closes
    # Higher highs + higher lows (uptrend structure)
    if h[-1]>h[-3] and h[-3]>h[-5] and l[-1]>l[-3] and l[-3]>l[-5]:
        patterns.append("HH/HL STRUCTURE")
    # Lower highs + lower lows (downtrend)
    if h[-1]<h[-3] and h[-3]<h[-5] and l[-1]<l[-3] and l[-3]<l[-5]:
        patterns.append("LH/LL STRUCTURE")
    # Inside bar
    if h[-1]<h[-2] and l[-1]>l[-2]:
        patterns.append("INSIDE BAR")
    # Outside bar
    if h[-1]>h[-2] and l[-1]<l[-2]:
        patterns.append("OUTSIDE BAR")
    # Three-bar reversal (bull)
    if c[-3]<c[-4] and c[-2]<c[-3] and c[-1]>c[-2] and c[-1]>c[-3]:
        patterns.append("3-BAR BULL REV")
    # Three-bar reversal (bear)
    if c[-3]>c[-4] and c[-2]>c[-3] and c[-1]<c[-2] and c[-1]<c[-3]:
        patterns.append("3-BAR BEAR REV")
    # Tight consolidation (< 1% range over 4 bars)
    last4_range = (max(h[-4:])-min(l[-4:]))/c[-1]*100
    if last4_range < 1.0:
        patterns.append("TIGHT COIL")
    # Wide-range bar (body > 2x average)
    avg_body = np.mean([abs(c[i]-c[i-1]) for i in range(-5,-1)]) if len(c)>5 else 0
    if abs(c[-1]-c[-2]) > 2*avg_body and avg_body > 0:
        patterns.append("WIDE RANGE BAR")
    return patterns

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 4 — SMART MONEY CLOCK
# ══════════════════════════════════════════════════════════════
def smart_money_clock():
    """
    Returns a 0-100 score for current institutional activity quality.
    Based on session overlaps, time-of-day volatility primes.
    """
    utc = datetime.now(ZoneInfo("UTC"))
    h = utc.hour + utc.minute/60
    # Scoring by hour (UTC) — peak institutional windows
    score_map = {
        (7,8): 55,   # London open approach
        (8,9): 85,   # London open
        (9,10): 90,  # London morning prime
        (10,11): 80,
        (11,12): 65,
        (12,13): 70, # NY open approach
        (13,14): 95, # NY open — peak overlap
        (14,15): 95,
        (15,16): 85,
        (16,17): 75,
        (17,18): 60,
        (18,19): 45,
        (19,20): 35,
        (20,21): 30,
        (21,22): 40, # Tokyo approach
        (22,23): 55,
        (23,24): 60,
        (0,1):   65,
        (1,2):   70, # Tokyo prime
        (2,3):   65,
        (3,4):   55,
        (4,5):   45,
        (5,6):   40,
        (6,7):   45,
    }
    score = 25
    for (h1,h2), s in score_map.items():
        if h1 <= h < h2:
            score = s
            break
    # Bonus for day of week (Mon-Fri full score, Fri afternoon reduced)
    dow = utc.weekday()
    if dow == 4 and h > 16: score = int(score * 0.7)  # Friday afternoon
    if dow in (5, 6): score = int(score * 0.4)        # Weekend
    label = "PEAK" if score >= 85 else "ACTIVE" if score >= 60 else "MODERATE" if score >= 40 else "LOW"
    return score, label

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 5 — RISK-OF-RUIN CALCULATOR
# ══════════════════════════════════════════════════════════════
def risk_of_ruin(win_rate_pct, rr_ratio, risk_pct_per_trade, ruin_threshold=0.5):
    """
    Calculates Kelly fraction and approximate risk of ruin.
    ruin_threshold: fraction of starting capital considered 'ruin' (default 50%)
    """
    w = win_rate_pct / 100
    l = 1 - w
    if rr_ratio <= 0 or w <= 0: return {"kelly": 0, "ror": 100, "edge": 0, "full_kelly": 0}
    edge = w * rr_ratio - l
    full_kelly = edge / rr_ratio if edge > 0 else 0
    half_kelly = full_kelly / 2
    # Approximation of risk of ruin via gamblers ruin formula
    if edge <= 0: ror = 100.0
    else:
        q = l / (w * rr_ratio)
        if q >= 1: ror = 100.0
        else:
            n_units = math.log(ruin_threshold) / math.log(q) if q > 0 else 999
            ror = round(min(100, max(0, (q**n_units)*100)), 1)
    return {
        "kelly": round(full_kelly*100, 2),
        "half_kelly": round(half_kelly*100, 2),
        "ror": round(ror, 1),
        "edge": round(edge*100, 2),
        "using_pct": round(risk_pct_per_trade*100, 2),
        "vs_half_kelly": "OVER" if risk_pct_per_trade*100 > half_kelly*100 else "UNDER",
    }

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 6 — VOLATILITY REGIME (GARCH-LITE)
# ══════════════════════════════════════════════════════════════
def volatility_regime(closes, window=20):
    """
    GARCH-lite: computes realized vol, its percentile rank, and forecasts direction.
    """
    if len(closes) < window+5:
        return {"rv": 0, "rv_pct_rank": 50, "forecast": "STABLE", "rv_5d": 0}
    rets = [math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
    rv_series = []
    for i in range(window, len(rets)+1):
        window_rets = rets[i-window:i]
        rv_series.append(np.std(window_rets)*math.sqrt(252)*100)
    rv_now = rv_series[-1]
    rv_5d  = np.mean([r**2 for r in rets[-5:]])**0.5 * math.sqrt(252)*100
    rank = sum(1 for v in rv_series if v <= rv_now)/len(rv_series)*100
    if rv_now > rv_series[-2]*1.15:  forecast = "EXPANDING"
    elif rv_now < rv_series[-2]*0.88:forecast = "CONTRACTING"
    else:                            forecast = "STABLE"
    return {"rv": round(rv_now,1), "rv_pct_rank": round(rank,0), "forecast": forecast, "rv_5d": round(rv_5d,1)}

# ══════════════════════════════════════════════════════════════
# MAIN SIGNAL ENGINE
# ══════════════════════════════════════════════════════════════
def compute_full_signal(closes, highs=None, lows=None, volumes=None, rules=None):
    if not closes or len(closes) < 22:
        return {"signal":"HOLD","conf":50,"rsi":50,"price":closes[-1] if closes else 0,
                "atr_pct":0,"bb_pct":50,"stoch_k":50,"mom":0,"vol_surge":1,
                "score":0,"long_pts":0,"short_pts":0,"reasons":[],"rule_block":False,
                "stop":None,"target":None,"ema8":closes[-1],"ema21":closes[-1],
                "divergence":{"bull_div":False,"bear_div":False,"desc":""},
                "regime":{"regime":"UNKNOWN"},"patterns":[],"vol_regime":{"rv":0}}
    price = closes[-1]
    e8  = ema_series(closes, 8);  e8v  = e8[-1]
    e21 = ema_series(closes, 21); e21v = e21[-1]
    e50 = ema_series(closes, 50) if len(closes)>=50 else e21; e50v = e50[-1]
    e3  = ema_series(closes, 3);  e3v  = e3[-1]; e3p = e3[-2] if len(e3)>1 else e3v
    e8p = e8[-2] if len(e8)>1 else e8v
    e12v = ema_series(closes,12)[-1]; e26v = ema_series(closes,26)[-1] if len(closes)>=26 else closes[-1]
    macd = e12v-e26v
    macd_prev_closes = closes[:-1]
    if len(macd_prev_closes)>=26:
        macd_p = ema_series(macd_prev_closes,12)[-1]-ema_series(macd_prev_closes,26)[-1]
    else: macd_p = macd
    macd_signal_line = ema_series([macd]*9,9)[-1]
    rsi_arr  = rsi_full(closes, 14); rsi_val  = rsi_arr[-1] if rsi_arr[-1] is not None else 50
    rsi7_arr = rsi_full(closes, 7);  rsi7_val = rsi7_arr[-1] if rsi7_arr[-1] is not None else 50
    bb_mid, bb_up, bb_lo, bb_pct_arr = bb_bands(closes)
    bb_pct_val = bb_pct_arr[-1]*100 if bb_pct_arr[-1] is not None else 50
    if len(closes)>=14:
        lo14=min(closes[-14:]); hi14=max(closes[-14:])
        stoch_k = 100*(price-lo14)/(hi14-lo14+1e-9)
        stoch_prev = 100*(closes[-2]-min(closes[-16:-2]))/(max(closes[-16:-2])-min(closes[-16:-2])+1e-9) if len(closes)>=16 else stoch_k
    else: stoch_k = stoch_prev = 50
    h_arr = highs or [c*1.005 for c in closes]
    l_arr = lows  or [c*0.995 for c in closes]
    atr_arr = atr_series(closes, h_arr, l_arr, 14)
    atr_val = next((v for v in reversed(atr_arr) if v is not None), price*0.01)
    atr_pct = atr_val/price*100
    vol_surge = 1.0
    if volumes and len(volumes)>=20:
        vol_ma = sum(volumes[-20:])/20; vol_surge = volumes[-1]/(vol_ma+1e-9)
    mom5  = (closes[-1]-closes[-6])/closes[-6]*100 if len(closes)>5 else 0
    mom10 = (closes[-1]-closes[-11])/closes[-11]*100 if len(closes)>10 else 0
    long_pts=0; short_pts=0; reasons=[]
    if e8v>e21v>e50v:    long_pts+=5;  reasons.append("EMA 8/21/50 fully bullish")
    elif e8v>e21v:       long_pts+=3;  reasons.append("EMA 8 > 21 bullish")
    if e8v<e21v<e50v:    short_pts+=5; reasons.append("EMA 8/21/50 fully bearish")
    elif e8v<e21v:       short_pts+=3; reasons.append("EMA 8 < 21 bearish")
    if e3v>e8v and e3p<=e8p: long_pts+=3;  reasons.append("EMA 3×8 bullish crossover")
    if e3v<e8v and e3p>=e8p: short_pts+=3; reasons.append("EMA 3×8 bearish crossover")
    macd_cross_up = macd>macd_signal_line and macd_p<=macd_signal_line
    macd_cross_dn = macd<macd_signal_line and macd_p>=macd_signal_line
    if macd_cross_up:      long_pts+=4;  reasons.append("MACD bullish crossover")
    elif macd>macd_signal_line: long_pts+=2
    if macd_cross_dn:      short_pts+=4; reasons.append("MACD bearish crossover")
    elif macd<macd_signal_line: short_pts+=2
    if rsi_val<28:          long_pts+=5;  reasons.append(f"RSI {rsi_val:.0f} — deeply oversold")
    elif rsi_val<38:        long_pts+=2;  reasons.append(f"RSI {rsi_val:.0f} — low territory")
    elif 42<rsi_val<60:     long_pts+=1
    if rsi_val>72:          short_pts+=5; reasons.append(f"RSI {rsi_val:.0f} — deeply overbought")
    elif rsi_val>62:        short_pts+=2; reasons.append(f"RSI {rsi_val:.0f} — elevated")
    if stoch_k<15 and stoch_k>stoch_prev: long_pts+=3;  reasons.append("Stoch crossed up from oversold")
    elif stoch_k<25:                      long_pts+=1
    if stoch_k>85 and stoch_k<stoch_prev: short_pts+=3; reasons.append("Stoch crossed down from overbought")
    elif stoch_k>75:                      short_pts+=1
    if bb_pct_val<8:    long_pts+=3;  reasons.append("At lower Bollinger Band")
    elif bb_pct_val<22: long_pts+=1
    if bb_pct_val>92:   short_pts+=3; reasons.append("At upper Bollinger Band")
    elif bb_pct_val>78: short_pts+=1
    if mom5>0.8:    long_pts+=3;  reasons.append(f"Strong momentum +{mom5:.1f}%")
    elif mom5>0.3:  long_pts+=1
    if mom5<-0.8:   short_pts+=3; reasons.append(f"Strong downswing {mom5:.1f}%")
    elif mom5<-0.3: short_pts+=1
    if vol_surge>1.8:
        if long_pts>short_pts:  long_pts+=2;  reasons.append(f"Volume surge {vol_surge:.1f}× confirms")
        elif short_pts>long_pts:short_pts+=2; reasons.append(f"Volume surge {vol_surge:.1f}× confirms")
    # Divergence bonus/malus
    div = detect_divergence(closes, rsi_arr)
    if div["bull_div"]:  long_pts+=4;  reasons.append("⬟ Bullish divergence detected")
    if div["bear_div"]:  short_pts+=4; reasons.append("⬟ Bearish divergence detected")
    rule_block=False
    for rule in (rules or []):
        if not rule.get("active", True): continue
        rt = rule.get("type","")
        if rt=="rsi_max" and rsi_val>float(rule.get("value",80)):
            rule_block=True; reasons.append(f"⛔ Rule: RSI>{rule['value']:.0f} blocks")
        if rt=="rsi_min" and rsi_val<float(rule.get("value",20)):
            rule_block=True; reasons.append(f"⛔ Rule: RSI<{rule['value']:.0f} blocks")
        if rt=="no_trade_hours":
            try:
                now_et=datetime.now(ZoneInfo("America/New_York")); hr=now_et.hour
                h1,h2=int(rule.get("h_from",12)),int(rule.get("h_to",13))
                if h1<=hr<h2: rule_block=True; reasons.append(f"⛔ Rule: No-trade {h1:02d}–{h2:02d} ET")
            except: pass
        if rt=="vol_min" and vol_surge<float(rule.get("value",0.5)):
            rule_block=True; reasons.append("⛔ Rule: Volume below minimum")
        if rt=="trend_only":
            if long_pts>short_pts and not (e8v>e21v>e50v):
                rule_block=True; reasons.append("⛔ Rule: Trend-only, EMAs not aligned")
            if short_pts>long_pts and not (e8v<e21v<e50v):
                rule_block=True; reasons.append("⛔ Rule: Trend-only, EMAs not aligned")
        if rt=="atr_max" and atr_pct>float(rule.get("value",4.0)):
            rule_block=True; reasons.append(f"⛔ Rule: ATR {atr_pct:.1f}% too volatile")
    score = long_pts - short_pts
    if rule_block or abs(score)<3: sig="HOLD"; conf=30
    elif score>=10:   sig="STRONG BUY";  conf=min(88,55+score*2)
    elif score>=5:    sig="BUY";         conf=min(76,44+score*2)
    elif score<=-10:  sig="STRONG SELL"; conf=min(88,55+abs(score)*2)
    elif score<=-5:   sig="SELL";        conf=min(76,44+abs(score)*2)
    elif rsi_val<28:  sig="OVERSOLD";    conf=68
    elif rsi_val>72:  sig="OVERBOUGHT";  conf=66
    else:             sig="HOLD";        conf=30
    stop_dist = atr_val*1.5
    rr = st.session_state.get("rr_ratio", 2.0)
    direction_long = "BUY" in sig or sig=="OVERSOLD"
    stop   = round(price-stop_dist if direction_long else price+stop_dist, 4)
    target = round(price+stop_dist*rr if direction_long else price-stop_dist*rr, 4)
    # Enrich with hidden gift data
    regime     = detect_regime(closes, h_arr, l_arr)
    patterns   = scan_patterns(closes, h_arr, l_arr)
    vol_regime = volatility_regime(closes)
    return {
        "signal":sig,"conf":conf,"score":score,"long_pts":long_pts,"short_pts":short_pts,
        "rsi":round(rsi_val,1),"rsi7":round(rsi7_val,1),"price":price,
        "atr_pct":round(atr_pct,2),"bb_pct":round(bb_pct_val,1),
        "stoch_k":round(stoch_k,1),"mom":round(mom5,2),"vol_surge":round(vol_surge,2),
        "macd":round(macd,4),"macd_signal":round(macd_signal_line,4),
        "ema8":round(e8v,2),"ema21":round(e21v,2),"ema50":round(e50v,2),
        "reasons":reasons[:6],"rule_block":rule_block,"stop":stop,"target":target,
        "divergence": div, "regime": regime, "patterns": patterns, "vol_regime": vol_regime,
    }

# ══════════════════════════════════════════════════════════════
# HIDDEN GIFT 7 — DRAWDOWN SHIELD
# ══════════════════════════════════════════════════════════════
def check_drawdown_shield():
    """
    If collective trader drawdown exceeds 8%, pauses all traders.
    Automatically lifts when drawdowns recover to 3%.
    """
    total_balance = sum(tr["balance"] for tr in TRADERS)
    total_peak    = sum(tr["peak"]    for tr in TRADERS)
    if total_peak <= 0: return False
    collective_dd = (total_peak - total_balance) / total_peak * 100
    if collective_dd > 8.0:
        st.session_state["shield_active"] = True
        for tr in TRADERS: tr["paused"] = True
        return True
    elif collective_dd < 3.0 and st.session_state.get("shield_active"):
        st.session_state["shield_active"] = False
        for tr in TRADERS: tr["paused"] = False
    return st.session_state.get("shield_active", False)

# ══════════════════════════════════════════════════════════════
# TRADER SIMULATION
# ══════════════════════════════════════════════════════════════
def simulate_trader(tr, market_signals):
    if tr.get("paused", False): return
    if tr["open_pos"]:
        pos = tr["open_pos"]; mk = pos["market"]
        sig = market_signals.get(mk, {}); p = sig.get("price", pos["entry"])
        is_long = pos["dir"]=="long"
        hit_sl = (is_long and p<=pos["stop"]) or (not is_long and p>=pos["stop"])
        hit_tp = (is_long and p>=pos["tp"])   or (not is_long and p<=pos["tp"])
        if tr["name"]=="CONTRARIAN":
            sig_str = sig.get("signal","HOLD")
            if is_long  and sig_str in ("STRONG SELL","SELL","OVERBOUGHT"): hit_tp=True
            if not is_long and sig_str in ("STRONG BUY","BUY","OVERSOLD"):  hit_tp=True
        if hit_sl or hit_tp:
            ep = pos["tp"] if hit_tp else pos["stop"]
            pnl = (ep-pos["entry"])*pos["units"] if is_long else (pos["entry"]-ep)*pos["units"]
            tr["balance"] = max(0, tr["balance"]+pnl)
            tr["peak"]    = max(tr["peak"], tr["balance"])
            tr["trades"].append({
                "market":mk,"dir":pos["dir"],"entry":pos["entry"],"exit":ep,
                "pnl":round(pnl,2),"result":"win" if pnl>0 else "loss",
                "reason":"TP" if hit_tp else "SL","time":datetime.now().strftime("%H:%M:%S"),
                "conf":pos.get("conf",0),
            })
            tr["history"].append(round(tr["balance"],2))
            tr["open_pos"] = None
    if tr["open_pos"]: return
    for mk, sig in market_signals.items():
        if sig.get("rule_block"): continue
        if sig["conf"] < tr["min_conf"]: continue
        signal_str = sig["signal"]
        is_buy  = signal_str in ("BUY","STRONG BUY","OVERSOLD")
        is_sell = signal_str in ("SELL","STRONG SELL","OVERBOUGHT")
        if tr["name"]=="CONTRARIAN":
            if signal_str=="OVERSOLD":    is_buy=True;  is_sell=False
            elif signal_str=="OVERBOUGHT":is_sell=True; is_buy=False
            elif signal_str in ("STRONG BUY","BUY"):   is_buy=False;  is_sell=False
            elif signal_str in ("STRONG SELL","SELL"): is_buy=False;  is_sell=False
        if tr["wait_strong"] and signal_str not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"):
            continue
        if not is_buy and not is_sell: continue
        direction = "long" if is_buy else "short"; p = sig["price"]
        atr_pct = sig.get("atr_pct",0)
        stop_mult = max(MARKETS[mk]["stop"], atr_pct/100*1.2) if atr_pct>0 else MARKETS[mk]["stop"]
        stop_dist = p*stop_mult
        stop = p-stop_dist if is_buy else p+stop_dist
        tp   = p+stop_dist*tr["rr"] if is_buy else p-stop_dist*tr["rr"]
        risk_amt = tr["balance"]*tr["risk_pct"]
        units = risk_amt/max(stop_dist,1)
        tr["open_pos"] = {
            "market":mk,"dir":direction,"entry":round(p,2),
            "stop":round(stop,2),"tp":round(tp,2),
            "units":units,"risk_amt":round(risk_amt,2),
            "time":datetime.now().strftime("%H:%M:%S"),"conf":sig["conf"],
        }
        break

# ══════════════════════════════════════════════════════════════
# DIAGNOSTICS ENGINE
# ══════════════════════════════════════════════════════════════
def run_diagnostics(sigs, fg_val):
    per={}; all_scores=[]
    for mk, sig in sigs.items():
        s=0; notes=[]
        conf=sig.get("conf",30)
        if sig["signal"]!="HOLD": s+=min(30,conf//3); notes.append(f"Signal strength +{min(30,conf//3)}")
        rsi=sig.get("rsi",50)
        if 35<rsi<65:   s+=20; notes.append("RSI in optimal zone +20")
        elif 28<rsi<72: s+=10; notes.append("RSI acceptable +10")
        else: notes.append(f"RSI extreme {rsi:.0f} — caution")
        mom=abs(sig.get("mom",0))
        if mom>0.8:  s+=20; notes.append(f"Strong momentum +20")
        elif mom>0.3:s+=10
        vs=sig.get("vol_surge",1)
        if vs>1.5:   s+=15; notes.append(f"Volume surge {vs:.1f}× +15")
        elif vs>1:   s+=7
        bb=sig.get("bb_pct",50)
        if sig["signal"] in ("BUY","STRONG BUY","OVERSOLD") and bb<45: s+=15; notes.append("Room to run +15")
        elif sig["signal"] in ("SELL","STRONG SELL","OVERBOUGHT") and bb>55: s+=15
        elif sig["signal"]!="HOLD": s+=5
        if sig.get("rule_block"): s=max(0,s-25); notes.append("Rule blocked −25")
        s=min(100,max(0,s)); all_scores.append(s)
        per[mk]={"score":s,"notes":notes,"dir":sig.get("signal","HOLD"),"conf":conf}
    overall=round(np.mean(all_scores) if all_scores else 0)
    return {"per":per,"overall":overall,"fg_score":10 if 20<fg_val<80 else 0}

# ══════════════════════════════════════════════════════════════
# AI (Claude)
# ══════════════════════════════════════════════════════════════
def call_claude(prompt, system, key, max_tokens=900):
    if not key: return None, "No Claude key"
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,"system":system,
                  "messages":[{"role":"user","content":prompt}]}, timeout=40)
        data = r.json()
        if "content" in data:
            return "".join(b.get("text","") for b in data["content"] if b.get("type")=="text"), None
        err = data.get("error",{})
        return None, f"{err.get('type','')}: {err.get('message',str(data))}"
    except Exception as e: return None, str(e)

NOTES_SYSTEM = """You are Nigel — a private wealth trading intelligence with the refined manner of a senior private banker.
You speak to your client with authority, clarity, and a touch of dry wit. No jargon. No RSI or MACD numbers.
Pure signal in elegant English. Format: JSON array of 3-4 notes, each with type (watch|buy|sell|info), market (BTC|NQ|GOLD|ES|CL|ETH), and text.
Text should read like a well-crafted telegram — decisive, precise, slightly literary. Max 2 sentences per note. Return ONLY valid JSON."""

AI_ANALYST_SYSTEM = """You are Nigel, a senior quantitative analyst at a private trading desk.
You receive real market data with full technical indicators and give sharp, specific, actionable analysis.
Use the numbers. Make clear calls. No hedging, no disclaimers. You speak like someone who has traded through 4 recessions.
Format your response with clear instrument sections. Under 400 words. End with one overall market statement."""

# HIDDEN GIFT 8 — WHISPER FEED SYSTEM
WHISPER_SYSTEM = """You are Nigel's inner voice — a one-line market intuition whispered to the trader every few minutes.
No analysis, no data. Just a single, elegant, pithy observation about markets, trading psychology, or current conditions.
It should feel like a thought from a wise trader who has seen everything. Max 20 words. No quotes around it. Return ONLY the whisper text."""

def push_note(ntype, market, text):
    st.session_state["notes"].insert(0,{"type":ntype,"market":market,"text":text,"time":datetime.now().strftime("%H:%M")})
    if len(st.session_state["notes"])>50: st.session_state["notes"].pop()

def generate_notes(sigs, sessions):
    if not CLKEY:
        for mk, sig in sigs.items():
            s=sig["signal"]; m_info=MARKETS[mk]
            if s=="STRONG BUY":    push_note("buy",mk,f"**{m_info['label']}** has aligned perfectly — EMA stack pointing up, MACD crossed. A measured long entry here carries asymmetric reward.")
            elif s=="STRONG SELL": push_note("sell",mk,f"**{m_info['label']}** is deteriorating on every timeframe. The path of least resistance is lower.")
            elif s=="OVERSOLD":    push_note("buy",mk,f"**{m_info['label']}** has been oversold into a potential flush. Wait for one confirming candle.")
            elif s=="OVERBOUGHT":  push_note("watch",mk,f"**{m_info['label']}** is extended. Protect open profits, avoid chasing.")
            elif s=="BUY":         push_note("info",mk,f"**{m_info['label']}** is building a case for the upside — monitor the next candles closely.")
        return
    cooldown=90
    if time.time()-st.session_state["last_ai_call"]<cooldown: return
    st.session_state["last_ai_call"]=time.time()
    summaries="; ".join(
        f"{MARKETS[k]['label']}: signal={v['signal']} RSI={v['rsi']:.0f} BB%={v['bb_pct']:.0f} mom={v['mom']:+.1f}% {'uptrend' if v['ema8']>v['ema21'] else 'downtrend'}"
        for k,v in sigs.items()
    )
    prompt=f"Markets right now: {summaries}. Active sessions: {', '.join(sessions)}. Generate 4 notes."
    resp,err=call_claude(prompt,NOTES_SYSTEM,CLKEY,600)
    if resp:
        try:
            parsed=json.loads(resp.strip().replace("```json","").replace("```","").strip())
            for n in parsed: push_note(n.get("type","info"),n.get("market","BTC"),n.get("text",""))
        except: pass

def generate_whisper(sigs):
    """HIDDEN GIFT 8 — Whispers a pithy market thought every 5 minutes."""
    if not CLKEY: return
    cooldown = 300  # 5 minutes
    if time.time()-st.session_state["last_whisper_call"]<cooldown: return
    st.session_state["last_whisper_call"] = time.time()
    signals_str = ", ".join(f"{k}:{v['signal']}" for k,v in sigs.items())
    prompt = f"Current signals: {signals_str}. Give me one whisper."
    resp,err = call_claude(prompt, WHISPER_SYSTEM, CLKEY, 60)
    if resp and not err:
        w = resp.strip().replace('"','').replace("'",'')
        st.session_state["whisper_feed"].insert(0, {"text": w, "time": datetime.now().strftime("%H:%M")})
        st.session_state["whisper_feed"] = st.session_state["whisper_feed"][:10]

def build_ai_context(sigs, prices_dict, diag, bt_cache=None):
    lines=[f"TIME: {datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M ET')}",
           f"OVERALL HEALTH: {diag.get('overall',0)}/100","","LIVE SIGNALS:"]
    for mk,sig in sigs.items():
        p=prices_dict.get(mk)
        lines.append(f"  {mk}: {sig['signal']} conf={sig['conf']}% price={p} RSI={sig['rsi']} "
                     f"BB%={sig['bb_pct']} mom={sig['mom']:+.1f}% ATR={sig['atr_pct']:.2f}% "
                     f"StochK={sig['stoch_k']} Vol={sig['vol_surge']:.1f}x EMA8={sig['ema8']} EMA21={sig['ema21']} "
                     f"Regime={sig['regime'].get('regime','?')} Patterns={','.join(sig['patterns'][:2]) if sig['patterns'] else 'none'} "
                     f"BullDiv={sig['divergence']['bull_div']} BearDiv={sig['divergence']['bear_div']}")
    if bt_cache:
        lines+=["","BACKTESTS:"]
        for k,bt in list(bt_cache.items())[:3]:
            if "error" not in bt:
                lines.append(f"  {bt.get('mk','?')} WR={bt.get('win_rate',0):.0f}% PF={bt.get('pf',0):.2f} DD={bt.get('max_dd',0):.1f}%")
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════
def run_backtest_nigel(closes, mk, risk_pct=0.01, rr=2.0, rules=None):
    if not closes or len(closes)<40: return {"error":"Need at least 40 data points"}
    m=MARKETS[mk]; stop_mult=m["stop"]
    cap=float(st.session_state.get("account_size",25000))
    bal=cap; peak=cap; trades=[]; equity=[]; pos=None
    highs=[c*1.005 for c in closes]; lows=[c*0.995 for c in closes]
    for i in range(22, len(closes)):
        window=closes[:i+1]; h_win=highs[:i+1]; l_win=lows[:i+1]
        sig=compute_full_signal(window,h_win,l_win,None,rules)
        price=closes[i]
        if pos:
            is_long=pos["dir"]=="long"
            hit_sl=(is_long and price<=pos["stop"]) or (not is_long and price>=pos["stop"])
            hit_tp=(is_long and price>=pos["tp"])   or (not is_long and price<=pos["tp"])
            if hit_sl or hit_tp:
                ep=pos["tp"] if hit_tp else pos["stop"]
                pnl=(ep-pos["entry"])*pos["units"] if is_long else (pos["entry"]-ep)*pos["units"]
                bal=max(0,bal+pnl); peak=max(peak,bal)
                trades.append({"i":i,"dir":pos["dir"],"entry":pos["entry"],"exit":ep,
                    "units":pos["units"],"pnl":round(pnl,2),"result":"W" if pnl>0 else "L",
                    "reason":"TP" if hit_tp else "SL","bal":round(bal,2)})
                pos=None
                if bal<cap*0.92: break
        if not pos and sig["signal"]!="HOLD" and not sig.get("rule_block"):
            is_buy  = "BUY" in sig["signal"] or sig["signal"]=="OVERSOLD"
            is_sell = "SELL" in sig["signal"] or sig["signal"]=="OVERBOUGHT"
            if is_buy or is_sell:
                direction="long" if is_buy else "short"
                sd=price*stop_mult
                stop=price-sd if is_buy else price+sd
                tp  =price+sd*rr if is_buy else price-sd*rr
                risk_amt=bal*risk_pct; units=risk_amt/max(sd,1e-9)
                pos={"dir":direction,"entry":price,"stop":stop,"tp":tp,"units":units}
        equity.append(bal)
    if not trades: return {"error":"No trades generated"}
    tdf=pd.DataFrame(trades)
    wins=tdf[tdf["pnl"]>0]; losses=tdf[tdf["pnl"]<=0]
    wr=len(wins)/len(tdf)*100
    avg_w=wins["pnl"].mean() if not wins.empty else 0
    avg_l=losses["pnl"].mean() if not losses.empty else 0
    pf=abs(avg_w/avg_l) if avg_l!=0 else 99
    eq_s=pd.Series(equity)
    max_dd=float(((eq_s-eq_s.cummax())/eq_s.cummax()*100).min())
    sharpe=0
    if len(eq_s)>2:
        r2=eq_s.pct_change().dropna()
        if r2.std()>0: sharpe=float(r2.mean()/r2.std()*np.sqrt(252))
    bh=(closes[-1]-closes[0])/closes[0]*100
    return {"mk":mk,"total_pnl":round(tdf["pnl"].sum(),2),"return_pct":round((bal-cap)/cap*100,2),
            "bh":round(bh,2),"win_rate":round(wr,1),"total_trades":len(tdf),
            "wins":len(wins),"losses":len(losses),"avg_win":round(avg_w,2),"avg_loss":round(avg_l,2),
            "pf":round(min(pf,99),2),"max_dd":round(max_dd,2),"sharpe":round(sharpe,2),
            "equity":equity,"trades":tdf,"final_bal":round(bal,2),"start":cap}

# ══════════════════════════════════════════════════════════════
# SESSION HELPERS
# ══════════════════════════════════════════════════════════════
def get_sessions():
    utc=datetime.now(ZoneInfo("UTC")); h=utc.hour+utc.minute/60
    s=[]
    if 0<=h<9:   s.append(("TOKYO",   "#7C3AED"))
    if 8<=h<17:  s.append(("LONDON",  "#1D4ED8"))
    if 13<=h<22: s.append(("NEW YORK","#059669"))
    if 13<=h<17: s.append(("OVERLAP", "#D97706"))
    if not s:    s.append(("OFF-HOURS","#374151"))
    return s

# HIDDEN GIFT 9 — TRADE JOURNAL CSV EXPORT
def build_journal_csv():
    """Builds a full session trade journal as CSV bytes."""
    rows = []
    for tr in TRADERS:
        for t in tr["trades"]:
            rows.append({
                "Desk": tr["name"],
                "Market": t["market"],
                "Direction": t["dir"],
                "Entry": t["entry"],
                "Exit": t["exit"],
                "P&L ($)": t["pnl"],
                "Result": t["result"],
                "Reason": t["reason"],
                "Time": t.get("time",""),
                "Confidence": t.get("conf",0),
                "Philosophy": tr.get("philosophy",""),
            })
    if not rows: return None
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-family:Cinzel,serif;font-weight:900;font-size:1.4rem;letter-spacing:.3em;color:#fff;margin:16px 0 4px">NIGEL</div>',unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:11px;color:#5a5570;margin-bottom:20px">Private Trading Intelligence v2.0</div>',unsafe_allow_html=True)
    st.divider()
    with st.expander("🔑 API Keys"):
        np_ = st.text_input("Polygon.io", value=POLY, type="password")
        nc_ = st.text_input("Claude AI",  value=CLKEY, type="password")
        if st.button("Save"):
            st.session_state["polygon_key"]=np_; _save("polygon_key",np_)
            st.session_state["claude_key"]=nc_;  _save("claude_key",nc_)
            st.cache_data.clear(); st.rerun()
    ai_ok=bool(CLKEY.strip()); pol_ok=bool(POLY.strip())
    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;margin:8px 0"><span style="color:{"#1aff8a" if pol_ok else "#ff2d55"}">{"✓" if pol_ok else "✗"} POLYGON</span> &nbsp; <span style="color:{"#1aff8a" if ai_ok else "#ff2d55"}">{"✓" if ai_ok else "✗"} CLAUDE</span></div>',unsafe_allow_html=True)
    st.divider()
    sel=st.multiselect("Instruments",list(MARKETS.keys()),default=st.session_state["selected_markets"])
    if sel: st.session_state["selected_markets"]=sel
    st.session_state["account_size"]=st.number_input("Account ($)",5000,1000000,st.session_state.get("account_size",25000),1000)
    st.session_state["rr_ratio"]=st.slider("Reward : Risk",1.0,5.0,2.0,0.25)
    st.session_state["refresh_interval"]=st.select_slider("Auto-refresh",[15,30,60,120,300],value=st.session_state["refresh_interval"],format_func=lambda x:f"{x}s")
    st.session_state["always_on"]=st.toggle("Always On",value=st.session_state["always_on"])
    st.divider()
    if st.button("⚡ Refresh Now"):   st.cache_data.clear(); st.rerun()
    if st.button("🗑 Clear Notes"):   st.session_state["notes"]=[]; st.rerun()
    if st.button("♻️ Reset Traders"):
        st.session_state["traders"]=[
            init_trader("CONSERVATEUR","◈","Precision entries only",0.005,2.5,72,True,"I trade once and trade right."),
            init_trader("MOMENTUM","◆","Rides breakouts and trend continuation",0.015,2.0,58,False,"The trend is my only edge."),
            init_trader("CONTRARIAN","◉","Fades extremes",0.025,1.8,45,False,"When others panic, I act."),
        ]
        st.rerun()
    if st.button("🗑 Reset Backtests"): st.session_state["bt_cache"]={};  st.rerun()

    # HIDDEN GIFT 9 — Trade Journal Download
    st.divider()
    journal_csv = build_journal_csv()
    if journal_csv:
        st.download_button(
            label="⬇ Download Trade Journal",
            data=journal_csv,
            file_name=f"nigel_journal_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
    st.caption(f"Updated {datetime.now().strftime('%H:%M:%S')}")

SEL     = st.session_state["selected_markets"] or ["BTC","NQ","GOLD"]
TRADERS = st.session_state["traders"]

# ══════════════════════════════════════════════════════════════
# LOAD LIVE DATA
# ══════════════════════════════════════════════════════════════
with st.spinner(""):
    raw_data={}; market_signals={}; live_prices={}
    for mk in SEL:
        m=MARKETS[mk]
        if mk=="BTC":
            bd=fetch_binance_live("BTC") or {}
            cg=fetch_crypto_price("bitcoin")
            closes=cg["closes"]; price=bd.get("price",cg["price"]); chg=bd.get("chg",cg["chg"])
            raw_data[mk]={"closes":closes,"price":price,"chg":chg,"high":bd.get("high",price*1.01),"low":bd.get("low",price*0.99)}
        elif mk=="ETH":
            bd=fetch_binance_live("ETH") or {}
            cg=fetch_crypto_price("ethereum")
            closes=cg["closes"]; price=bd.get("price",cg["price"]); chg=bd.get("chg",cg["chg"])
            raw_data[mk]={"closes":closes,"price":price,"chg":chg}
        else:
            ticker=TICKERS.get(mk,mk)
            pd_=fetch_polygon_data(ticker,POLY)
            raw_data[mk]={"closes":pd_["closes"],"price":pd_["price"],"chg":pd_["chg"]}
        live_prices[mk]=raw_data[mk]["price"]
        market_signals[mk]=compute_full_signal(raw_data[mk]["closes"],rules=st.session_state.get("rule_set",[]))
        market_signals[mk]["price"]=raw_data[mk]["price"]
        market_signals[mk]["chg"]=raw_data[mk]["chg"]

    fg_val,fg_label=fetch_fear_greed()
    diag=run_diagnostics(market_signals,fg_val)

# Run drawdown shield first
shield_active = check_drawdown_shield()

# Run traders
for tr in TRADERS: simulate_trader(tr, market_signals)

# Generate notes & whispers
sessions_now=get_sessions(); session_names=[s for s,_ in sessions_now]
generate_notes(market_signals, session_names)
generate_whisper(market_signals)

# Inject signal feed
now_ts=time.time()
if (now_ts-st.session_state["last_refresh"])>=st.session_state["refresh_interval"]:
    st.session_state["last_refresh"]=now_ts
    for mk,sig in market_signals.items():
        if sig["signal"]!="HOLD" and sig["conf"]>=55:
            st.session_state["signal_feed"].insert(0,{
                "time":datetime.now().strftime("%H:%M:%S"),
                "mk":mk,"signal":sig["signal"],"conf":sig["conf"],
                "price":sig["price"],"stop":sig.get("stop"),"target":sig.get("target"),
                "reasons":sig.get("reasons",[])[:2],
                "patterns":sig.get("patterns",[])[:2],
                "regime":sig.get("regime",{}).get("regime","?"),
                "div_bull":sig["divergence"]["bull_div"],
                "div_bear":sig["divergence"]["bear_div"],
            })
    st.session_state["signal_feed"]=st.session_state["signal_feed"][:80]
    st.session_state["diag_history"].append({"time":datetime.now(),"score":diag["overall"]})
    st.session_state["diag_history"]=st.session_state["diag_history"][-200:]

# Smart money clock
sm_score, sm_label = smart_money_clock()

# ══════════════════════════════════════════════════════════════
# MASTHEAD
# ══════════════════════════════════════════════════════════════
utc=datetime.now(ZoneInfo("UTC"))
ny =utc.astimezone(ZoneInfo("America/New_York"))
lon=utc.astimezone(ZoneInfo("Europe/London"))

st.markdown(f"""
<div class="nigel-masthead">
  <div>
    <div class="nigel-wordmark">NIG<em>E</em>L</div>
    <div class="nigel-tagline">Private Trading Intelligence · All Markets · Always On</div>
  </div>
  <div style="text-align:right">
    <div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#5a5570">
      ET {ny.strftime("%H:%M")} &nbsp;·&nbsp; LDN {lon.strftime("%H:%M")} &nbsp;·&nbsp; UTC {utc.strftime("%H:%M")}
    </div>
    <div style="margin-top:6px">
      {''.join(f'<span style="display:inline-block;padding:3px 14px;border-radius:1px;font-family:Cinzel,serif;font-size:10px;font-weight:700;letter-spacing:.12em;margin-right:8px;background:{c}22;color:{c};border:1px solid {c}44">{n}</span>' for n,c in sessions_now)}
    </div>
    <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570;margin-top:4px">
      {SESSION_TIPS.get(sessions_now[0][0],"")}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Shield banner
if shield_active:
    st.markdown('<div class="shield-banner">⚠ DRAWDOWN SHIELD ACTIVE — All traders paused. Collective drawdown exceeded 8%. Monitoring for recovery above 3%.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TICKER BAR
# ══════════════════════════════════════════════════════════════
def make_ticker():
    items=[]
    for mk in SEL:
        sig=market_signals.get(mk,{}); p=live_prices.get(mk,0); chg=raw_data[mk].get("chg",0)
        d=sig.get("signal","HOLD"); arrow="▲" if chg>=0 else "▼"; cc="tick-up" if chg>=0 else "tick-dn"
        fmt=f"${p:,.0f}" if mk in ("BTC","ETH") else f"${p:,.2f}"
        badge_cls="badge-long" if "BUY" in d or d=="OVERSOLD" else "badge-short" if "SELL" in d or d=="OVERBOUGHT" else "badge-hold"
        regime_badge=""
        reg=sig.get("regime",{}).get("regime","")
        if reg:
            rbc="badge-regime-trend" if reg=="TRENDING" else "badge-regime-range" if reg=="RANGING" else "badge-regime-vol"
            regime_badge=f'<span class="badge {rbc}" style="font-size:8px;padding:1px 5px;margin-left:4px">{reg[:3]}</span>'
        items.append(f'<span class="tick-item"><span class="tick-sym">{mk}</span><span class="tick-px">{fmt}</span><span class="{cc}">{arrow} {abs(chg):.2f}%</span><span class="badge {badge_cls}" style="font-size:9px;padding:1px 7px">{d}</span>{regime_badge}<span class="tick-sep">·</span></span>')
    inner="".join(items)*3
    return f'<div class="ticker-wrap"><div class="ticker-track">{inner}</div></div>'

st.markdown(make_ticker(), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# LIVE SIGNAL CARDS
# ══════════════════════════════════════════════════════════════
health=diag["overall"]
h_color="#1aff8a" if health>=70 else "#c9a84c" if health>=45 else "#ff2d55"
fg_color="#1aff8a" if fg_val<=30 else "#ff2d55" if fg_val>=70 else "#c9a84c"
sm_color="#1aff8a" if sm_score>=75 else "#c9a84c" if sm_score>=50 else "#5a5570"

header_cols=st.columns([4,1,1,1])
with header_cols[1]:
    st.markdown(f'<div style="text-align:center;padding:8px 0"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#5a5570">HEALTH</div><div style="font-family:Cinzel,serif;font-size:2.4rem;font-weight:900;line-height:1;color:{h_color}">{health}</div></div>',unsafe_allow_html=True)
with header_cols[2]:
    st.markdown(f'<div style="text-align:center;padding:8px 0"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#5a5570">FEAR/GREED</div><div style="font-family:Cinzel,serif;font-size:2.4rem;font-weight:900;line-height:1;color:{fg_color}">{fg_val}</div><div style="font-size:10px;color:#5a5570;font-style:italic">{fg_label}</div></div>',unsafe_allow_html=True)
with header_cols[3]:
    # HIDDEN GIFT 4 displayed
    st.markdown(f'<div style="text-align:center;padding:8px 0"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#5a5570">INST. FLOW</div><div style="font-family:Cinzel,serif;font-size:2.4rem;font-weight:900;line-height:1;color:{sm_color}">{sm_score}</div><div style="font-size:10px;color:#5a5570;font-style:italic">{sm_label}</div></div>',unsafe_allow_html=True)

st.markdown(f'<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#5a5570;margin-bottom:10px"><span class="live-dot"></span>LIVE SIGNALS · {"✓ CLAUDE AI" if CLKEY else "FALLBACK NOTES"}</div>',unsafe_allow_html=True)

sig_cols=st.columns(len(SEL))
for col,mk in zip(sig_cols,SEL):
    with col:
        sig=market_signals[mk]; m=MARKETS[mk]
        s=sig["signal"]; conf=sig["conf"]; p=live_prices[mk]; chg=raw_data[mk].get("chg",0)
        is_b="BUY" in s or s=="OVERSOLD"; is_s="SELL" in s or s=="OVERBOUGHT"
        card_cls="bull" if is_b else "bear" if is_s else "flat"
        badge_cls="badge-long" if is_b else "badge-short" if is_s else "badge-hold"
        chg_cls="sc-chg-up" if chg>=0 else "sc-chg-dn"
        pfmt=f"${p:,.0f}" if mk in ("BTC","ETH") else f"${p:,.2f}"
        sfmt=f"${sig['stop']:,.2f}" if sig.get("stop") else "—"
        tfmt=f"${sig['target']:,.2f}" if sig.get("target") else "—"
        dd=diag["per"].get(mk,{})
        reg=sig.get("regime",{}); reg_name=reg.get("regime","?")
        reg_cls="badge-regime-trend" if reg_name=="TRENDING" else "badge-regime-range" if reg_name=="RANGING" else "badge-regime-vol"
        div=sig.get("divergence",{}); div_html=""
        if div.get("bull_div"): div_html='<div class="divergence-bull">⬟ ' + div.get("desc","") + '</div>'
        elif div.get("bear_div"): div_html='<div class="divergence-bear">⬟ ' + div.get("desc","") + '</div>'
        pats=sig.get("patterns",[])
        pats_html="".join(f'<span class="pattern-tag">{p2}</span>' for p2 in pats[:3]) if pats else ""
        vol_r=sig.get("vol_regime",{}); vol_forecast=vol_r.get("forecast","")
        vol_fc_c="#1aff8a" if vol_forecast=="CONTRACTING" else "#ff2d55" if vol_forecast=="EXPANDING" else "#5a5570"

        st.markdown(f"""
        <div class="signal-card {card_cls}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
            <div>
              <div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin-bottom:2px">{m['sub']}</div>
              <div class="sc-sym">{mk}</div>
              <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570">{m['label']}</div>
            </div>
            <div style="text-align:right">
              <span class="badge {reg_cls}" style="display:block;margin-bottom:4px">{reg_name}</span>
              <span class="badge {badge_cls}">{s}</span>
            </div>
          </div>
          <div class="sc-price">{pfmt}</div>
          <div class="{chg_cls}" style="margin:2px 0 10px">{"▲" if chg>=0 else "▼"} {abs(chg):.2f}% today</div>
          <div class="meter-track"><div class="meter-fill" style="width:{conf}%;background:{"#1aff8a" if is_b else "#ff2d55" if is_s else "#c9a84c"}"></div></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:3px">CONF {conf}%</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:10px;font-family:JetBrains Mono,monospace;font-size:10px">
            <div style="color:#5a5570">RSI <span style="color:#d4cfc0">{sig['rsi']}</span></div>
            <div style="color:#5a5570">BB% <span style="color:#d4cfc0">{sig['bb_pct']}</span></div>
            <div style="color:#ff2d55">SL {sfmt}</div>
            <div style="color:#1aff8a">TP {tfmt}</div>
          </div>
          <div style="margin-top:6px;font-size:10px;color:#3a3550;font-family:JetBrains Mono,monospace">
            ATR {sig['atr_pct']:.2f}% · STK {sig['stoch_k']} · VOL <span style="color:{vol_fc_c}">{vol_forecast}</span>
          </div>
          {div_html}
          <div style="margin-top:6px">{pats_html}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# WHISPER FEED (HIDDEN GIFT 8 — visible strip)
# ══════════════════════════════════════════════════════════════
if st.session_state["whisper_feed"]:
    latest_whisper = st.session_state["whisper_feed"][0]
    st.markdown(f'<div class="whisper-note">◈ &nbsp;{latest_whisper["text"]}<span style="float:right;font-family:JetBrains Mono,monospace;font-size:9px;color:#3a3550">{latest_whisper["time"]}</span></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════
t1,t2,t3,t4,t5,t6,t7,t8,t9 = st.tabs([
    "INTELLIGENCE","TRADERS","SIGNAL FEED",
    "LIVE CHARTS","DIAGNOSTICS","RULES ENGINE",
    "BACKTEST","AI ANALYST","EDGE TOOLS",
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — INTELLIGENCE
# ══════════════════════════════════════════════════════════════
with t1:
    nc1,nc2=st.columns([3,2])
    with nc1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">NIGEL\'S INTELLIGENCE BRIEF</div>',unsafe_allow_html=True)
        notes=st.session_state["notes"]
        if not notes:
            st.markdown('<div class="nigel-note note-info"><div class="note-head">AWAITING ANALYSIS</div><div class="note-body">Nigel is observing the markets. Notes will appear on the next data cycle.</div></div>',unsafe_allow_html=True)
        else:
            icons={"watch":"◈ WATCH","buy":"▲ LONG BIAS","sell":"▼ SHORT BIAS","info":"◆ OBSERVE"}
            colors={"watch":"#c9a84c","buy":"#1aff8a","sell":"#ff2d55","info":"#00c4ff"}
            for n in notes[:8]:
                cls=f"note-{n['type']}"; ic=icons.get(n['type'],"◆"); cl=colors.get(n['type'],"#c9a84c")
                mk_name=MARKETS.get(n['market'],{}).get('label',n['market'])
                st.markdown(f'<div class="nigel-note {cls}"><div class="note-head" style="color:{cl}">{ic} — {mk_name} <span style="color:#3a3550;font-weight:400;float:right">{n["time"]}</span></div><div class="note-body">{n["text"]}</div></div>',unsafe_allow_html=True)

        # Whisper history
        if len(st.session_state["whisper_feed"])>1:
            st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#3a3550;margin:16px 0 8px">NIGEL\'S WHISPERS</div>',unsafe_allow_html=True)
            for w in st.session_state["whisper_feed"][:5]:
                st.markdown(f'<div class="whisper-note">◈ {w["text"]}<span style="float:right;font-family:JetBrains Mono,monospace;font-size:9px;color:#3a3550">{w["time"]}</span></div>',unsafe_allow_html=True)

    with nc2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">MARKET OVERVIEW</div>',unsafe_allow_html=True)
        best_mk=None; best_conf=0
        for mk,sig in market_signals.items():
            if sig["conf"]>best_conf and sig["signal"]!="HOLD": best_mk=mk; best_conf=sig["conf"]
        if best_mk:
            bsig=market_signals[best_mk]; bp=live_prices[best_mk]
            is_b="BUY" in bsig["signal"] or bsig["signal"]=="OVERSOLD"
            bdc="#1aff8a" if is_b else "#ff2d55"
            pfmt=f"${bp:,.0f}" if best_mk in ("BTC","ETH") else f"${bp:,.2f}"
            div_extra=""
            if bsig["divergence"]["bull_div"] or bsig["divergence"]["bear_div"]:
                div_extra=f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{"#1aff8a" if bsig["divergence"]["bull_div"] else "#ff2d55"};margin-top:6px">⬟ {bsig["divergence"]["desc"]}</div>'
            pats = bsig.get("patterns",[])
            pats_extra = "".join(f'<span class="pattern-tag">{p2}</span>' for p2 in pats[:3]) if pats else ""
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{bdc}08,transparent);border:1px solid {bdc}33;border-radius:1px;padding:20px 22px;margin-bottom:16px">
              <div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#5a5570;margin-bottom:8px">HIGHEST CONVICTION SETUP</div>
              <div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:#fff">{best_mk}</div>
              <div style="font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;margin-bottom:10px">{MARKETS[best_mk]['label']}</div>
              <div><span class="badge {"badge-long" if is_b else "badge-short"}">{bsig["signal"]}</span><span style="font-family:JetBrains Mono,monospace;color:{bdc};font-size:1.2rem;margin-left:12px">{best_conf}%</span></div>
              <div style="font-family:JetBrains Mono,monospace;font-size:1.5rem;color:#fff;margin:10px 0">{pfmt}</div>
              <div style="font-family:JetBrains Mono,monospace;font-size:11px">
                <div style="color:#ff2d55">SL {f"${bsig['stop']:,.2f}" if bsig.get("stop") else "—"}</div>
                <div style="color:#1aff8a">TP {f"${bsig['target']:,.2f}" if bsig.get("target") else "—"}</div>
              </div>
              <div style="margin-top:10px">{''.join(f'<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570">· {r}</div>' for r in bsig.get("reasons",[])[:3])}</div>
              {div_extra}
              <div style="margin-top:8px">{pats_extra}</div>
            </div>""",unsafe_allow_html=True)

        rows=[]
        for mk in SEL:
            sig=market_signals[mk]
            rows.append({"Contract":mk,"Signal":sig["signal"],"Conf":f"{sig['conf']}%",
                "RSI":f"{sig['rsi']:.0f}","StochK":f"{sig['stoch_k']:.0f}",
                "BB%":f"{sig['bb_pct']:.0f}","Mom":f"{sig['mom']:+.1f}%","ATR%":f"{sig['atr_pct']:.2f}",
                "Regime":sig['regime'].get('regime','?')})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ══════════════════════════════════════════════════════════════
# TAB 2 — TRADERS
# ══════════════════════════════════════════════════════════════
with t2:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:20px">THE THREE DESKS</div>',unsafe_allow_html=True)
    if shield_active:
        st.markdown('<div class="shield-banner">⚠ DRAWDOWN SHIELD ACTIVE — All desks paused</div>',unsafe_allow_html=True)
    sb_rows=[]
    for tr in TRADERS:
        pnl=tr["balance"]-25000
        wins=sum(1 for t in tr["trades"] if t["result"]=="win"); tot=len(tr["trades"])
        wr=round(wins/tot*100) if tot else 0
        dd=round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
        sb_rows.append({"Desk":f"{tr['emoji']} {tr['name']}","Philosophy":tr.get("philosophy",tr.get("style","")),"Balance":tr["balance"],"P&L ($)":pnl,"Win%":wr,"Trades":tot,"DD%":dd,"Status":"⏸ PAUSED" if tr.get("paused") else "● ACTIVE"})
    sb_df=pd.DataFrame(sb_rows).sort_values("P&L ($)",ascending=False).reset_index(drop=True)
    sb_df.index=sb_df.index+1
    st.dataframe(sb_df.style.format({"Balance":"${:,.0f}","P&L ($)":"${:+,.0f}","Win%":"{}%","DD%":"{}%"})
        .map(lambda v:"color:#1aff8a;font-weight:600" if isinstance(v,(int,float)) and v>0 else "color:#ff2d55;font-weight:600" if isinstance(v,(int,float)) and v<0 else "",subset=["P&L ($)"]),
        use_container_width=True)

    st.markdown("<br>",unsafe_allow_html=True)
    tr_tabs=st.tabs([f"{tr['emoji']} {tr['name']}" for tr in TRADERS])
    for tab,tr in zip(tr_tabs,TRADERS):
        with tab:
            pnl=tr["balance"]-25000; wins=sum(1 for t in tr["trades"] if t["result"]=="win")
            tot=len(tr["trades"]); wr=round(wins/tot*100) if tot else 0
            dd=round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
            pnl_c="#1aff8a" if pnl>=0 else "#ff2d55"
            st.markdown(f"""
            <div class="panel panel-gold" style="margin-bottom:16px">
              <div class="trader-header">
                <div><div class="trader-name">{tr['emoji']} {tr['name']}</div><div class="trader-style">{tr['style']}</div></div>
                <div style="text-align:right;font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570">"{tr.get('philosophy',tr.get('style',''))}"</div>
              </div>
              <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px">
                <div><div class="stat-val" style="color:#fff">${tr['balance']:,.0f}</div><div class="stat-lbl">Balance</div></div>
                <div><div class="stat-val" style="color:{pnl_c}">${pnl:+,.0f}</div><div class="stat-lbl">P&amp;L</div></div>
                <div><div class="stat-val">{wr}%</div><div class="stat-lbl">Win Rate</div></div>
                <div><div class="stat-val">{tot}</div><div class="stat-lbl">Trades</div></div>
                <div><div class="stat-val" style="color:#ff2d55">{dd}%</div><div class="stat-lbl">Drawdown</div></div>
              </div>
              {'<div style="font-family:Cinzel,serif;font-size:10px;color:#ff2d55;margin-top:10px;letter-spacing:.1em">⏸ PAUSED BY DRAWDOWN SHIELD</div>' if tr.get("paused") else ""}
            </div>""",unsafe_allow_html=True)
            pos=tr["open_pos"]
            if pos:
                mk=pos["market"]; sig=market_signals.get(mk,{}); cur=sig.get("price",pos["entry"])
                unr=(cur-pos["entry"])*pos["units"] if pos["dir"]=="long" else (pos["entry"]-cur)*pos["units"]
                uc="#1aff8a" if unr>=0 else "#ff2d55"
                cls="pos-long" if pos["dir"]=="long" else "pos-short"
                fmt=".0f" if mk in ("BTC","ETH") else ".2f"
                ml=MARKETS[mk]["label"]
                st.markdown(f'<div class="{cls} pos-panel"><div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.1em;color:#fff;margin-bottom:6px">{"▲ LONG" if pos["dir"]=="long" else "▼ SHORT"} — {ml}<span style="float:right;color:#5a5570">{pos["time"]}</span></div>Entry ${pos["entry"]:{fmt}} · Now ${cur:{fmt}} · SL <span style="color:#ff2d55">${pos["stop"]:{fmt}}</span> · TP <span style="color:#1aff8a">${pos["tp"]:{fmt}}</span><br>Unrealized <span style="color:{uc};font-weight:700">${unr:+,.2f}</span> · Confidence {pos.get("conf",0)}%</div>',unsafe_allow_html=True)
            else:
                st.markdown('<div class="pos-flat pos-panel">No open position — scanning for entry</div>',unsafe_allow_html=True)
            recent=tr["trades"][-6:][::-1]
            if recent:
                st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin:12px 0 8px">RECENT TRADES</div>',unsafe_allow_html=True)
                for t in recent:
                    is_w=t["result"]=="win"; tc="#1aff8a" if is_w else "#ff2d55"
                    ml=MARKETS.get(t["market"],{}).get("label",t["market"])
                    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #12101e"><div><span class="{"trade-pip-w" if is_w else "trade-pip-l"}">■</span><span style="font-family:JetBrains Mono,monospace;font-size:11px;color:#d4cfc0;margin-left:8px">{ml} {"▲" if t["dir"]=="long" else "▼"}</span><span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-left:8px">{t["reason"]}</span></div><span style="font-family:JetBrains Mono,monospace;font-size:12px;color:{tc};font-weight:600">${t["pnl"]:+,.2f}</span></div>',unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:12px">EQUITY CURVES</div>',unsafe_allow_html=True)
    fig_eq=go.Figure()
    colors_tr={"CONSERVATEUR":"#00c4ff","MOMENTUM":"#1aff8a","CONTRARIAN":"#ff2d55"}
    for tr in TRADERS:
        if len(tr["history"])>1:
            fig_eq.add_trace(go.Scatter(y=tr["history"],mode="lines",name=f"{tr['emoji']} {tr['name']}",line=dict(color=colors_tr.get(tr["name"],"#c9a84c"),width=2)))
    fig_eq.add_hline(y=25000,line=dict(color="#3a3550",width=1,dash="dot"))
    fig_eq.update_layout(height=280,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
        margin=dict(l=0,r=0,t=10,b=0),xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"),
        legend=dict(orientation="h",y=1.05,font=dict(family="JetBrains Mono",size=10)),
        font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
    st.plotly_chart(fig_eq,use_container_width=True,key="eq_chart")

    with st.expander("Full Trade Log"):
        log=[]
        for tr in TRADERS:
            for t in tr["trades"]:
                log.append({"Desk":tr["name"],"Market":MARKETS.get(t["market"],{}).get("label",t["market"]),"Dir":t["dir"],"Entry":t["entry"],"Exit":t["exit"],"P&L":t["pnl"],"Result":t["result"],"Reason":t["reason"],"Time":t.get("time","")})
        if log:
            ldf=pd.DataFrame(log)
            st.dataframe(ldf.style.format({"Entry":"${:,.2f}","Exit":"${:,.2f}","P&L":"${:+,.2f}"}).map(lambda v:"color:#1aff8a" if v=="win" else "color:#ff2d55",subset=["Result"]),use_container_width=True,hide_index=True)

# ══════════════════════════════════════════════════════════════
# TAB 3 — SIGNAL FEED
# ══════════════════════════════════════════════════════════════
with t3:
    sf1,sf2=st.columns([2,1])
    with sf1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">LIVE SIGNAL FEED</div>',unsafe_allow_html=True)
        feed=st.session_state["signal_feed"]
        if not feed:
            st.markdown('<div class="nigel-note note-info"><div class="note-body">Awaiting signals above 55% confidence…</div></div>',unsafe_allow_html=True)
        else:
            for item in feed[:30]:
                s=item["signal"]; is_b="BUY" in s or s=="OVERSOLD"
                dc="#1aff8a" if is_b else "#ff2d55"
                badge_cls="badge-long" if is_b else "badge-short"
                sfmt=f"${item['stop']:,.2f}" if item.get("stop") else "—"
                tfmt=f"${item['target']:,.2f}" if item.get("target") else "—"
                reasons_str=" · ".join(item.get("reasons",[])[:2])
                pats_str=" · ".join(item.get("patterns",[])[:2])
                div_str=""
                if item.get("div_bull"): div_str='<span style="color:#1aff8a;font-size:9px"> ⬟ BULL DIV</span>'
                elif item.get("div_bear"): div_str='<span style="color:#ff2d55;font-size:9px"> ⬟ BEAR DIV</span>'
                reg_str=f'<span style="font-family:JetBrains Mono,monospace;font-size:9px;color:#5a5570;margin-left:8px">[{item.get("regime","?")}]</span>'
                st.markdown(f"""
                <div style="display:flex;gap:14px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #12101e">
                  <div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#3a3550;min-width:64px;padding-top:2px">{item['time']}</div>
                  <div style="flex:1">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:3px">
                      <span style="font-family:Cinzel,serif;font-weight:700;color:#fff">{item['mk']}</span>
                      <span class="badge {badge_cls}">{s}</span>
                      <span style="font-family:JetBrains Mono,monospace;font-size:10px;color:{dc}">{item['conf']}%</span>
                      {reg_str}{div_str}
                    </div>
                    <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#3a3550">SL <span style="color:#ff2d55">{sfmt}</span> &nbsp; TP <span style="color:#1aff8a">{tfmt}</span></div>
                    <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570;margin-top:2px">{reasons_str}</div>
                    {f'<div style="font-size:10px;color:#5a5570;margin-top:2px">{pats_str}</div>' if pats_str else ""}
                  </div>
                </div>""",unsafe_allow_html=True)
    with sf2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">STATISTICS</div>',unsafe_allow_html=True)
        if feed:
            tot=len(feed); longs=sum(1 for x in feed if "BUY" in x["signal"] or x["signal"]=="OVERSOLD")
            shorts=tot-longs; avg_conf=np.mean([x["conf"] for x in feed])
            divs_bull=sum(1 for x in feed if x.get("div_bull")); divs_bear=sum(1 for x in feed if x.get("div_bear"))
            st.markdown(f"""
            <div class="panel panel-gold" style="margin-bottom:10px"><div class="stat-val" style="color:#00c4ff">{tot}</div><div class="stat-lbl">Total Signals</div></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
              <div class="panel panel-em"><div class="stat-val" style="color:#1aff8a">{longs}</div><div class="stat-lbl">Long</div></div>
              <div class="panel panel-cr"><div class="stat-val" style="color:#ff2d55">{shorts}</div><div class="stat-lbl">Short</div></div>
            </div>
            <div class="panel" style="margin-bottom:10px"><div class="stat-val" style="color:#c9a84c">{avg_conf:.0f}%</div><div class="stat-lbl">Avg Conf</div></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
              <div class="panel"><div class="stat-val" style="color:#1aff8a;font-size:1.2rem">{divs_bull}</div><div class="stat-lbl">Bull Divs</div></div>
              <div class="panel"><div class="stat-val" style="color:#ff2d55;font-size:1.2rem">{divs_bear}</div><div class="stat-lbl">Bear Divs</div></div>
            </div>""",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 4 — LIVE CHARTS
# ══════════════════════════════════════════════════════════════
with t4:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:12px">LIVE CHARTS</div>',unsafe_allow_html=True)
    ch_mk=st.selectbox("Instrument",SEL,key="ch_mk")
    show_signals=st.toggle("Overlay signals",value=True)
    ch_interval=st.select_slider("Timeframe",["1h","4h","1d"],value="1d",key="ch_int")
    df_ch=pd.DataFrame(); cm=MARKETS[ch_mk]
    if ch_mk in ("BTC","ETH"):
        df_ch=fetch_binance_candles(ch_mk,interval={"1h":"1h","4h":"4h","1d":"1d"}.get(ch_interval,"1d"),limit=120)
    elif POLY:
        ticker=TICKERS.get(ch_mk,ch_mk)
        days_map={"1h":5,"4h":30,"1d":90}
        df_ch_raw=fetch_polygon_data(ticker,POLY,days=days_map.get(ch_interval,90))
        if df_ch_raw["ok"]:
            closes=df_ch_raw["closes"]
            df_ch=pd.DataFrame({"close":closes,"open":[c*0.998 for c in closes],"high":[c*1.005 for c in closes],"low":[c*0.995 for c in closes],"volume":[1e6]*len(closes)})
    if df_ch.empty:
        st.warning("No chart data available.")
    else:
        closes_ch=list(df_ch["close"])
        e8_ch=ema_series(closes_ch,8); e21_ch=ema_series(closes_ch,21); e50_ch=ema_series(closes_ch,50)
        rsi_ch=rsi_full(closes_ch,14)
        bb_m,bb_u,bb_l,_=bb_bands(closes_ch)
        macd_ch=[ema_series(closes_ch[:i+1],12)[-1]-ema_series(closes_ch[:i+1],26)[-1] for i in range(len(closes_ch))]
        idx=df_ch.index
        fig_ch=make_subplots(rows=4,cols=1,shared_xaxes=True,row_heights=[0.50,0.18,0.18,0.14],vertical_spacing=0.015)
        fig_ch.add_trace(go.Scatter(x=idx,y=bb_u,line=dict(color="rgba(201,168,76,0.12)",width=1),showlegend=False),row=1,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=bb_l,line=dict(color="rgba(201,168,76,0.12)",width=1),fill="tonexty",fillcolor="rgba(201,168,76,0.04)",showlegend=False),row=1,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=bb_m,line=dict(color="rgba(201,168,76,0.3)",width=1,dash="dot"),showlegend=False),row=1,col=1)
        if all(c in df_ch.columns for c in ["open","high","low","close"]):
            fig_ch.add_trace(go.Candlestick(x=idx,open=df_ch["open"],high=df_ch["high"],low=df_ch["low"],close=df_ch["close"],increasing=dict(line=dict(color="#1aff8a"),fillcolor="rgba(26,255,138,0.3)"),decreasing=dict(line=dict(color="#ff2d55"),fillcolor="rgba(255,45,85,0.3)"),name="Price"),row=1,col=1)
        else:
            fig_ch.add_trace(go.Scatter(x=idx,y=df_ch["close"],line=dict(color=cm["color"],width=2),name="Price"),row=1,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=e8_ch,line=dict(color="#1aff8a",width=1.2,dash="dot"),name="EMA 8"),row=1,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=e21_ch,line=dict(color="#ff2d55",width=1.2,dash="dot"),name="EMA 21"),row=1,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=e50_ch,line=dict(color="#c9a84c",width=1.2,dash="dot"),name="EMA 50"),row=1,col=1)
        if show_signals:
            sig_now=market_signals.get(ch_mk,{})
            if sig_now.get("signal") in ("BUY","STRONG BUY","OVERSOLD") and sig_now.get("stop"):
                fig_ch.add_trace(go.Scatter(x=[idx[-1]],y=[closes_ch[-1]],mode="markers",marker=dict(symbol="triangle-up",size=14,color="#1aff8a"),name="LONG"),row=1,col=1)
                fig_ch.add_hline(y=sig_now["stop"],line=dict(color="#ff2d55",width=1,dash="dash"),row=1,col=1)
                fig_ch.add_hline(y=sig_now["target"],line=dict(color="#1aff8a",width=1,dash="dash"),row=1,col=1)
            elif sig_now.get("signal") in ("SELL","STRONG SELL","OVERBOUGHT") and sig_now.get("stop"):
                fig_ch.add_trace(go.Scatter(x=[idx[-1]],y=[closes_ch[-1]],mode="markers",marker=dict(symbol="triangle-down",size=14,color="#ff2d55"),name="SHORT"),row=1,col=1)
        macd_s_ch=ema_series(macd_ch,9); macd_h_ch=[m-s for m,s in zip(macd_ch,macd_s_ch)]
        mc_colors=["rgba(26,255,138,0.7)" if v>=0 else "rgba(255,45,85,0.7)" for v in macd_h_ch]
        fig_ch.add_trace(go.Bar(x=idx,y=macd_h_ch,marker_color=mc_colors,showlegend=False),row=2,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=macd_ch,line=dict(color="#00c4ff",width=1.5),name="MACD"),row=2,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=macd_s_ch,line=dict(color="#ff2d55",width=1.5),name="Signal"),row=2,col=1)
        fig_ch.add_trace(go.Scatter(x=idx,y=rsi_ch,line=dict(color="#c9a84c",width=2),name="RSI"),row=3,col=1)
        for lvl,lc in [(70,"rgba(255,45,85,0.35)"),(30,"rgba(26,255,138,0.35)"),(50,"rgba(201,168,76,0.2)")]:
            fig_ch.add_hline(y=lvl,line=dict(color=lc,width=1,dash="dash"),row=3,col=1)
        if "volume" in df_ch.columns:
            vc=["rgba(26,255,138,0.4)" if float(df_ch["close"].iloc[i])>=float(df_ch["open"].iloc[i]) else "rgba(255,45,85,0.4)" for i in range(len(df_ch))]
            fig_ch.add_trace(go.Bar(x=idx,y=df_ch["volume"],marker_color=vc,showlegend=False),row=4,col=1)
        fig_ch.update_layout(height=820,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",xaxis_rangeslider_visible=False,font=dict(family="JetBrains Mono",size=10,color="#5a5570"),legend=dict(orientation="h",y=1.02,font=dict(size=10),bgcolor="rgba(0,0,0,0)"),margin=dict(l=0,r=0,t=20,b=0),title=dict(text=f"{ch_mk} — {cm['label']} · {cm['sub']}",font=dict(color="#5a5570",size=11,family="Cinzel")))
        fig_ch.update_xaxes(gridcolor="#12101e",zerolinecolor="#12101e")
        fig_ch.update_yaxes(gridcolor="#12101e",zerolinecolor="#12101e")
        st.plotly_chart(fig_ch,use_container_width=True,key="main_chart")

# ══════════════════════════════════════════════════════════════
# TAB 5 — DIAGNOSTICS
# ══════════════════════════════════════════════════════════════
with t5:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:20px">SYSTEM DIAGNOSTICS</div>',unsafe_allow_html=True)
    health=diag["overall"]; h_c="#1aff8a" if health>=70 else "#c9a84c" if health>=45 else "#ff2d55"
    st.markdown(f"""
    <div class="panel panel-gold" style="margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:20px">
        <div><div style="font-family:Cinzel,serif;font-size:3.2rem;font-weight:900;line-height:1;color:{h_c}">{health}</div><div style="font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#5a5570;margin-top:4px">OVERALL HEALTH / 100</div></div>
        <div style="flex:1">
          <div class="meter-track" style="height:8px"><div class="meter-fill" style="width:{health}%;background:{h_c}"></div></div>
          <div style="display:flex;justify-content:space-between;margin-top:6px;font-family:JetBrains Mono,monospace;font-size:9px;color:#5a5570"><span>0 · AVOID</span><span>45 · SELECTIVE</span><span>70 · ACTIVE</span><span>100</span></div>
          <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:14px;color:#d4cfc0;margin-top:12px">{"Strong conditions — systematic execution appropriate." if health>=70 else "Mixed signals — be highly selective, reduce size." if health>=45 else "Unfavourable — patience is capital preservation."}</div>
        </div>
        <div style="text-align:center;min-width:100px">
          <div style="font-family:Cinzel,serif;font-size:2.4rem;font-weight:900;line-height:1;color:{fg_color}">{fg_val}</div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:4px">FEAR / GREED</div>
          <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:11px;color:#5a5570">{fg_label}</div>
        </div>
        <div style="text-align:center;min-width:100px">
          <div style="font-family:Cinzel,serif;font-size:2.4rem;font-weight:900;line-height:1;color:{sm_color}">{sm_score}</div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:4px">INST. FLOW</div>
          <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:11px;color:#5a5570">{sm_label}</div>
        </div>
      </div>
    </div>""",unsafe_allow_html=True)
    per=diag["per"]
    d_cols=st.columns(min(len(SEL),4))
    for col,mk in zip(d_cols*2,SEL):
        dd=per.get(mk,{}); sc=dd.get("score",0)
        dc="#1aff8a" if sc>=70 else "#c9a84c" if sc>=45 else "#ff2d55"
        sig=market_signals.get(mk,{})
        with col:
            st.markdown(f"""
            <div class="panel" style="margin-bottom:12px;border-top:1px solid {dc}">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                <div style="font-family:Cinzel,serif;font-weight:700;color:#fff">{mk}</div>
                <div style="font-family:Cinzel,serif;font-size:1.8rem;font-weight:900;color:{dc}">{sc}</div>
              </div>
              <div class="meter-track"><div class="meter-fill" style="width:{sc}%;background:{dc}"></div></div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:10px;font-family:JetBrains Mono,monospace;font-size:10px">
                <div style="color:#5a5570">RSI <span style="color:#d4cfc0">{sig.get("rsi",50):.0f}</span></div>
                <div style="color:#5a5570">BB% <span style="color:#d4cfc0">{sig.get("bb_pct",50):.0f}</span></div>
                <div style="color:#5a5570">Mom <span style="color:{"#1aff8a" if sig.get("mom",0)>0 else "#ff2d55"}">{sig.get("mom",0):+.2f}%</span></div>
                <div style="color:#5a5570">Vol <span style="color:#d4cfc0">{sig.get("vol_surge",1):.1f}×</span></div>
              </div>
              <div style="margin-top:8px;font-family:JetBrains Mono,monospace;font-size:9px;color:#5a5570">
                {sig.get("regime",{}).get("regime","?")} · ADX {sig.get("regime",{}).get("adx_lite",0):.0f}
              </div>
              <div style="margin-top:6px;border-top:1px solid #12101e;padding-top:6px">
                {''.join(f'<div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#{"1aff8a" if "+" in n else "ff2d55" if "−" in n else "5a5570"};margin-bottom:2px">{n}</div>' for n in dd.get("notes",[])[:4])}
              </div>
            </div>""",unsafe_allow_html=True)
    hist=st.session_state.get("diag_history",[])
    if len(hist)>2:
        hist_df=pd.DataFrame(hist[-60:])
        fig_h=go.Figure()
        fig_h.add_trace(go.Scatter(x=hist_df["time"],y=hist_df["score"],fill="tozeroy",fillcolor="rgba(201,168,76,0.05)",line=dict(color="#c9a84c",width=2),name="Health"))
        fig_h.add_hline(y=70,line=dict(color="rgba(26,255,138,0.3)",width=1,dash="dash"))
        fig_h.add_hline(y=45,line=dict(color="rgba(255,45,85,0.3)",width=1,dash="dash"))
        fig_h.update_layout(height=160,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",margin=dict(l=0,r=0,t=10,b=0),showlegend=False,font=dict(family="JetBrains Mono",size=9,color="#5a5570"),xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e",range=[0,100]))
        st.plotly_chart(fig_h,use_container_width=True,key="health_hist")
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin:16px 0 10px">INDICATOR MATRIX</div>',unsafe_allow_html=True)
    matrix=[]
    for mk in SEL:
        sig=market_signals.get(mk,{}); p=live_prices.get(mk)
        matrix.append({"Contract":mk,"Price":f"${p:,.2f}" if p else "—","Signal":sig.get("signal","HOLD"),"Conf":f"{sig.get('conf',0)}%","RSI":f"{sig.get('rsi',50):.1f}","StochK":f"{sig.get('stoch_k',50):.0f}","BB%":f"{sig.get('bb_pct',50):.0f}","ATR%":f"{sig.get('atr_pct',0):.2f}","Mom5%":f"{sig.get('mom',0):+.2f}","VolSurge":f"{sig.get('vol_surge',1):.2f}×","Regime":sig.get("regime",{}).get("regime","?"),"BullDiv":sig["divergence"]["bull_div"],"BearDiv":sig["divergence"]["bear_div"],"Blocked":sig.get("rule_block",False)})
    st.dataframe(pd.DataFrame(matrix),use_container_width=True,hide_index=True)

# ══════════════════════════════════════════════════════════════
# TAB 6 — RULES ENGINE
# ══════════════════════════════════════════════════════════════
with t6:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">RULES ENGINE</div>',unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:14px;color:#5a5570;margin-bottom:20px">Rules are applied in real time to every signal computation.</div>',unsafe_allow_html=True)
    with st.expander("＋ Define New Rule",expanded=len(st.session_state["rule_set"])==0):
        rf1,rf2=st.columns(2)
        with rf1:
            r_name=st.text_input("Rule name",placeholder="e.g. No lunch trades")
            r_type=st.selectbox("Rule type",["rsi_max","rsi_min","no_trade_hours","vol_min","atr_max","trend_only"],format_func=lambda x:{"rsi_max":"Block if RSI above","rsi_min":"Block if RSI below","no_trade_hours":"No-trade time window","vol_min":"Min volume surge","atr_max":"Max ATR%","trend_only":"Trend-only (EMA alignment)"}[x])
        with rf2:
            r_val=st.number_input("Threshold",value=0.0,step=0.1)
            r_h1=st.number_input("Hour FROM (ET)",0,23,12)
            r_h2=st.number_input("Hour TO (ET)",0,23,13)
        r_active=st.toggle("Active on creation",value=True)
        DESCS={"rsi_max":f"Block if RSI>{r_val:.0f}","rsi_min":f"Block if RSI<{r_val:.0f}","no_trade_hours":f"No trading {r_h1:02d}:00–{r_h2:02d}:00 ET","vol_min":f"Block if volume surge<{r_val:.1f}×","atr_max":f"Block if ATR>{r_val:.1f}%/day","trend_only":"Require EMA 8/21/50 fully aligned"}
        if st.button("Add Rule",type="primary"):
            st.session_state["rule_set"].append({"id":f"r_{int(time.time())}","name":r_name or r_type,"type":r_type,"value":r_val,"h_from":r_h1,"h_to":r_h2,"active":r_active,"desc":DESCS[r_type]})
            _save("rule_set",st.session_state["rule_set"]); st.rerun()
    st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin:12px 0 8px">QUICK PRESETS</div>',unsafe_allow_html=True)
    p_cols=st.columns(4)
    presets=[("No Lunch","no_trade_hours",0,12,13,"No-trade 12:00–13:00 ET"),("Trend Only","trend_only",0,0,0,"EMA 8/21/50 must align"),("No OB Entry","rsi_max",72,0,0,"Block RSI>72"),("Vol Confirm","vol_min",1.2,0,0,"Volume >1.2× avg")]
    for col,(pn,pt,pv,ph1,ph2,pd_) in zip(p_cols,presets):
        if col.button(f"+ {pn}",key=f"p_{pn}"):
            if pn not in [r["name"] for r in st.session_state["rule_set"]]:
                st.session_state["rule_set"].append({"id":f"r_{pn}_{int(time.time())}","name":pn,"type":pt,"value":pv,"h_from":ph1,"h_to":ph2,"active":True,"desc":pd_})
                _save("rule_set",st.session_state["rule_set"]); st.rerun()
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.15em;color:#c9a84c;margin:20px 0 12px">ACTIVE RULES</div>',unsafe_allow_html=True)
    if not st.session_state["rule_set"]:
        st.markdown('<div class="nigel-note note-info"><div class="note-body">No rules configured. All signals pass through unfiltered.</div></div>',unsafe_allow_html=True)
    else:
        for i,rule in enumerate(st.session_state["rule_set"]):
            active=rule.get("active",True); cls="rule-on" if active else "rule-off"
            rc1,rc2,rc3=st.columns([4,1,1])
            with rc1:
                st.markdown(f'<div class="rule-row {cls}"><div><div class="rule-name">{rule["name"]}</div><div class="rule-desc">{rule["desc"]}</div></div><span class="badge {"badge-long" if active else "badge-hold"}">{"ACTIVE" if active else "OFF"}</span></div>',unsafe_allow_html=True)
            with rc2:
                if st.button("Toggle",key=f"tog_{rule['id']}"): st.session_state["rule_set"][i]["active"]=not active; _save("rule_set",st.session_state["rule_set"]); st.rerun()
            with rc3:
                if st.button("Delete",key=f"del_{rule['id']}"): st.session_state["rule_set"].pop(i); _save("rule_set",st.session_state["rule_set"]); st.rerun()
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.15em;color:#5a5570;margin:16px 0 10px">CURRENT RULE IMPACT</div>',unsafe_allow_html=True)
    ri_cols=st.columns(len(SEL))
    for col,mk in zip(ri_cols,SEL):
        sig=market_signals.get(mk,{}); blocked=sig.get("rule_block",False)
        col.markdown(f'<div class="panel" style="text-align:center;border-top:1px solid {"#1aff8a" if not blocked else "#ff2d55"}"><div style="font-family:Cinzel,serif;font-weight:700;color:#fff;margin-bottom:4px">{mk}</div><span class="badge {"badge-long" if not blocked else "badge-short"}">{"ALLOWED" if not blocked else "BLOCKED"}</span><div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:6px">{sig.get("signal","HOLD")} {sig.get("conf",0)}%</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 7 — BACKTEST
# ══════════════════════════════════════════════════════════════
with t7:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">STRATEGY BACKTEST</div>',unsafe_allow_html=True)
    bc1,bc2=st.columns(2)
    with bc1:
        bt_mk=st.selectbox("Instrument",SEL,key="bt_mk")
        bt_rr=st.slider("R : R",1.0,5.0,2.0,0.25,key="bt_rr")
        bt_risk=st.slider("Risk % per trade",0.1,3.0,1.0,0.1,key="bt_risk")/100
    with bc2:
        bt_rules=st.toggle("Apply trading rules",value=True,key="bt_rules")
        bt_note=st.text_area("Notes",placeholder="Optional notes…",height=80,key="bt_note")
    run_bt=st.button("▶ Execute Backtest",type="primary")
    bt_key=f"{bt_mk}_{bt_rr}_{bt_risk}_{bt_rules}"
    if run_bt:
        with st.spinner("Backtesting…"):
            closes_bt=raw_data.get(bt_mk,{}).get("closes",[])
            if bt_mk in ("BTC","ETH"):
                extra=fetch_crypto_price({"BTC":"bitcoin","ETH":"ethereum"}[bt_mk],days=365)
                closes_bt=extra["closes"]
            elif POLY:
                extra=fetch_polygon_data(TICKERS.get(bt_mk,bt_mk),POLY,days=365)
                closes_bt=extra["closes"]
            rules_bt=st.session_state["rule_set"] if bt_rules else []
            res=run_backtest_nigel(closes_bt,bt_mk,bt_risk,bt_rr,rules_bt)
            res["notes"]=bt_note
            st.session_state["bt_cache"][bt_key]=res
    bt=st.session_state["bt_cache"].get(bt_key)
    if bt and "error" not in bt:
        pnl_c="#1aff8a" if bt["total_pnl"]>=0 else "#ff2d55"
        m1,m2,m3,m4,m5=st.columns(5)
        for col,(lbl,val,vc) in zip([m1,m2,m3,m4,m5],[("P&L",f'${bt["total_pnl"]:+,.0f}',pnl_c),("Return",f'{bt["return_pct"]:+.1f}%',pnl_c),("Win Rate",f'{bt["win_rate"]:.0f}%',"#fff"),("Prof. Factor",f'{bt["pf"]:.2f}',"#c9a84c" if bt["pf"]>=1.5 else "#ff2d55"),("Max DD",f'{bt["max_dd"]:.1f}%',"#ff2d55")]):
            col.markdown(f'<div class="panel" style="text-align:center;margin-bottom:8px"><div class="stat-val" style="color:{vc}">{val}</div><div class="stat-lbl">{lbl}</div></div>',unsafe_allow_html=True)
        m6,m7,m8,m9,m10=st.columns(5)
        for col,(lbl,val,vc) in zip([m6,m7,m8,m9,m10],[("Trades",str(bt["total_trades"]),"#fff"),("Wins",str(bt["wins"]),"#1aff8a"),("Losses",str(bt["losses"]),"#ff2d55"),("Avg Win",f'${bt["avg_win"]:+,.0f}',"#1aff8a"),("Sharpe",f'{bt["sharpe"]:.2f}',"#00c4ff")]):
            col.markdown(f'<div class="panel" style="text-align:center;margin-bottom:8px"><div class="stat-val" style="color:{vc}">{val}</div><div class="stat-lbl">{lbl}</div></div>',unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570;margin-bottom:12px">Strategy {bt["return_pct"]:+.1f}% vs Buy & Hold {bt["bh"]:+.1f}%</div>',unsafe_allow_html=True)
        fig_bt=go.Figure()
        fig_bt.add_trace(go.Scatter(y=bt["equity"],fill="tozeroy",fillcolor="rgba(26,255,138,0.04)" if bt["total_pnl"]>=0 else "rgba(255,45,85,0.04)",line=dict(color="#1aff8a" if bt["total_pnl"]>=0 else "#ff2d55",width=2),name="Equity"))
        fig_bt.add_hline(y=bt["start"],line=dict(color="#3a3550",width=1,dash="dot"))
        fig_bt.update_layout(height=220,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",margin=dict(l=0,r=0,t=10,b=0),showlegend=False,font=dict(family="JetBrains Mono",size=10,color="#5a5570"),xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"),title=dict(text="Equity Curve",font=dict(family="Cinzel",color="#5a5570",size=11)))
        st.plotly_chart(fig_bt,use_container_width=True,key="bt_eq")
        with st.expander("Trade Log"):
            tl=bt["trades"].copy()
            st.dataframe(tl[["dir","entry","exit","pnl","result","reason","bal"]].style.format({"entry":"${:,.2f}","exit":"${:,.2f}","pnl":"${:+,.2f}","bal":"${:,.0f}"}).map(lambda v:"color:#1aff8a" if isinstance(v,(int,float)) and v>0 else "color:#ff2d55" if isinstance(v,(int,float)) and v<0 else "",subset=["pnl"]),use_container_width=True,hide_index=True)
    elif bt and "error" in bt:
        st.warning(f"Backtest: {bt['error']}")
    else:
        st.markdown('<div class="nigel-note note-info"><div class="note-body">Configure parameters and execute a backtest to see results.</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# TAB 8 — AI ANALYST
# ══════════════════════════════════════════════════════════════
with t8:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:16px">NIGEL AI ANALYST</div>',unsafe_allow_html=True)
    if not CLKEY:
        st.markdown('<div class="panel panel-gold" style="text-align:center;padding:40px"><div style="font-family:Cinzel,serif;font-size:1.2rem;font-weight:700;color:#c9a84c;letter-spacing:.2em;margin-bottom:8px">CLAUDE API KEY REQUIRED</div><div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:15px;color:#5a5570">Add your Claude API key in the sidebar to unlock AI analysis.</div></div>',unsafe_allow_html=True)
    else:
        ai1,ai2=st.columns([3,1])
        with ai1:
            qa_cols=st.columns(4)
            qa_prompt=None
            if qa_cols[0].button("📊 Full Brief"):   qa_prompt="Give me a full market brief. For each instrument: exact signal, key price levels, stop and target, and whether you'd trade it right now. Be specific with all numbers."
            if qa_cols[1].button("⚡ Best Trade"):   qa_prompt="Which single instrument has the highest probability setup right now? Walk me through entry, stop, target, and the three most compelling technical reasons."
            if qa_cols[2].button("⚠️ Risk Check"):   qa_prompt="Assess the risk environment. Are there dangerous setups or conflicting signals? What's the biggest risk to an active position?"
            if qa_cols[3].button("🧬 Divergence"):   qa_prompt="Review all divergence signals detected. Which ones are most compelling and what trade do they suggest?"
            custom=st.text_area("Your question to Nigel:",placeholder="e.g. Should I be long or short BTC right now?",height=80,key="ai_q")
            ask=st.button("Ask Nigel →",type="primary")
            final_q=qa_prompt or (custom if ask and custom.strip() else None)
            if final_q:
                with st.spinner("Nigel is analysing…"):
                    ctx=build_ai_context(market_signals,live_prices,diag,st.session_state.get("bt_cache"))
                    resp,err=call_claude(f"LIVE DATA:\n{ctx}\n\nQUESTION: {final_q}",AI_ANALYST_SYSTEM,CLKEY,1000)
                if err: st.error(f"Claude error: {err}")
                else:
                    ts_ai=datetime.now().strftime("%H:%M")
                    st.markdown(f'<div class="ai-response"><div class="ai-header">NIGEL · {ts_ai} · LIVE ANALYSIS</div>{resp.replace(chr(10),"<br>")}</div>',unsafe_allow_html=True)
                    st.session_state["ai_feed"].insert(0,{"time":ts_ai,"q":final_q,"a":resp})
                    st.session_state["ai_feed"]=st.session_state["ai_feed"][:15]
        with ai2:
            st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#5a5570;margin-bottom:12px">RECENT RESPONSES</div>',unsafe_allow_html=True)
            for item in st.session_state.get("ai_feed",[])[:5]:
                st.markdown(f'<div style="background:#09080f;border:1px solid #12101e;border-radius:1px;padding:10px;margin-bottom:6px"><div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#c9a84c;margin-bottom:3px">{item["time"]}</div><div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:11px;color:#5a5570;margin-bottom:4px">{item["q"][:50]}{"…" if len(item["q"])>50 else ""}</div><div style="font-size:11px;color:#8a8690">{item["a"][:120]}{"…" if len(item["a"])>120 else ""}</div></div>',unsafe_allow_html=True)
        with st.expander("Live context sent to Nigel AI"):
            st.code(build_ai_context(market_signals,live_prices,diag,st.session_state.get("bt_cache")),language="text")

# ══════════════════════════════════════════════════════════════
# TAB 9 — EDGE TOOLS (Hidden Gifts Dashboard)
# ══════════════════════════════════════════════════════════════
with t9:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.2em;color:#c9a84c;margin-bottom:6px">EDGE TOOLS</div>',unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:14px;color:#5a5570;margin-bottom:24px">Advanced analytics not found in ordinary platforms.</div>',unsafe_allow_html=True)

    et1,et2=st.tabs(["RISK OF RUIN","CORRELATION MATRIX"])

    # ── RISK OF RUIN ─────────────────────────────────────────
    with et1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#c9a84c;margin-bottom:16px">KELLY CRITERION & RISK-OF-RUIN CALCULATOR</div>',unsafe_allow_html=True)
        ror_cols=st.columns([1,1,1,2])
        with ror_cols[0]:
            ror_wr=st.slider("Win Rate %",20,80,50,1,key="ror_wr")
        with ror_cols[1]:
            ror_rr=st.slider("Reward : Risk",0.5,5.0,2.0,0.25,key="ror_rr")
        with ror_cols[2]:
            ror_risk=st.slider("Risk per Trade %",0.1,5.0,1.0,0.1,key="ror_risk")
        ror=risk_of_ruin(ror_wr,ror_rr,ror_risk/100)
        edge_c="#1aff8a" if ror["edge"]>0 else "#ff2d55"
        ror_c="#1aff8a" if ror["ror"]<5 else "#c9a84c" if ror["ror"]<20 else "#ff2d55"
        kelly_warn=ror["vs_half_kelly"]=="OVER"
        with ror_cols[3]:
            st.markdown(f"""
            <div class="kelly-panel">
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
                <div><div class="stat-val" style="color:{edge_c}">{ror["edge"]:+.1f}%</div><div class="stat-lbl">Edge per Trade</div></div>
                <div><div class="stat-val" style="color:#c9a84c">{ror["kelly"]:.2f}%</div><div class="stat-lbl">Full Kelly</div></div>
                <div><div class="stat-val" style="color:#1aff8a">{ror["half_kelly"]:.2f}%</div><div class="stat-lbl">Half Kelly (recommended)</div></div>
                <div><div class="stat-val" style="color:{ror_c}">{ror["ror"]:.1f}%</div><div class="stat-lbl">Risk of Ruin</div></div>
              </div>
              {'<div style="font-family:Cinzel,serif;font-size:10px;color:#ff2d55;margin-top:12px;letter-spacing:.1em">⚠ RISKING ABOVE HALF KELLY — reduce position size</div>' if kelly_warn else '<div style="font-family:Cinzel,serif;font-size:10px;color:#1aff8a;margin-top:12px;letter-spacing:.1em">✓ POSITION SIZE WITHIN KELLY BOUNDS</div>'}
            </div>""",unsafe_allow_html=True)
        # ROR surface (win rate vs risk %)
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#5a5570;margin:20px 0 10px">RISK OF RUIN SURFACE (win rate vs position size)</div>',unsafe_allow_html=True)
        wr_range=list(range(30,75,5)); risk_range=[0.5,1.0,1.5,2.0,3.0,5.0]
        z_data=[[risk_of_ruin(wr,ror_rr,r/100)["ror"] for r in risk_range] for wr in wr_range]
        fig_ror=go.Figure(go.Heatmap(z=z_data,x=[f"{r}%" for r in risk_range],y=[f"{w}%" for w in wr_range],colorscale=[[0,"#1aff8a"],[0.3,"#c9a84c"],[0.7,"#ff2d55"],[1,"#8b0000"]],showscale=True,zmin=0,zmax=50,text=[[f"{v:.0f}%" for v in row] for row in z_data],texttemplate="%{text}",textfont=dict(family="JetBrains Mono",size=9)))
        fig_ror.update_layout(height=260,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",margin=dict(l=0,r=0,t=10,b=0),xaxis=dict(title="Risk Per Trade",gridcolor="#12101e",titlefont=dict(family="Cinzel",size=9,color="#5a5570")),yaxis=dict(title="Win Rate",gridcolor="#12101e",titlefont=dict(family="Cinzel",size=9,color="#5a5570")),font=dict(family="JetBrains Mono",size=9,color="#5a5570"))
        st.plotly_chart(fig_ror,use_container_width=True,key="ror_surface")

        # Per-trader Kelly assessment
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#5a5570;margin:20px 0 10px">DESK KELLY ASSESSMENT</div>',unsafe_allow_html=True)
        for tr in TRADERS:
            wins=sum(1 for t in tr["trades"] if t["result"]=="win"); tot=len(tr["trades"])
            if tot<3:
                st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#3a3550;margin-bottom:4px">{tr["name"]}: insufficient trades ({tot}) for Kelly</div>',unsafe_allow_html=True)
                continue
            wr_tr=wins/tot*100
            tr_ror=risk_of_ruin(wr_tr,tr["rr"],tr["risk_pct"])
            cc="#1aff8a" if tr_ror["edge"]>0 else "#ff2d55"
            st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;margin-bottom:6px;padding:8px 12px;background:#09080f;border:1px solid #12101e;border-radius:1px"><span style="color:#c9a84c;margin-right:12px">{tr["emoji"]} {tr["name"]}</span> WR {wr_tr:.0f}% · Edge <span style="color:{cc}">{tr_ror["edge"]:+.1f}%</span> · Kelly {tr_ror["kelly"]:.2f}% · ½K {tr_ror["half_kelly"]:.2f}% · Using {tr_ror["using_pct"]:.2f}% <span style="color:{"#ff2d55" if tr_ror["vs_half_kelly"]=="OVER" else "#1aff8a"}">[{tr_ror["vs_half_kelly"]} HALF-KELLY]</span> · RoR {tr_ror["ror"]:.1f}%</div>',unsafe_allow_html=True)

    # ── CORRELATION MATRIX ───────────────────────────────────
    with et2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#c9a84c;margin-bottom:16px">CROSS-INSTRUMENT CORRELATION</div>',unsafe_allow_html=True)
        st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570;margin-bottom:16px">Daily return correlations across your selected instruments. High correlation = diversification is illusory.</div>',unsafe_allow_html=True)
        # Build returns matrix
        ret_data={}
        for mk in SEL:
            closes=raw_data[mk]["closes"]
            if len(closes)>5:
                rets=[math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
                ret_data[mk]=rets
        if len(ret_data)>=2:
            min_len=min(len(v) for v in ret_data.values())
            ret_df=pd.DataFrame({k:v[-min_len:] for k,v in ret_data.items()})
            corr=ret_df.corr()
            z=corr.values.tolist(); labels=list(corr.columns)
            fig_corr=go.Figure(go.Heatmap(z=z,x=labels,y=labels,colorscale=[[0,"#ff2d55"],[0.5,"#09080f"],[1,"#1aff8a"]],zmin=-1,zmax=1,text=[[f"{v:.2f}" for v in row] for row in z],texttemplate="%{text}",textfont=dict(family="JetBrains Mono",size=11,color="#d4cfc0")))
            fig_corr.update_layout(height=320,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",margin=dict(l=0,r=0,t=10,b=0),font=dict(family="JetBrains Mono",size=10,color="#5a5570"),xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"))
            st.plotly_chart(fig_corr,use_container_width=True,key="corr_matrix")
            # Insights
            st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin:12px 0 8px">CORRELATION INSIGHTS</div>',unsafe_allow_html=True)
            for i,a in enumerate(labels):
                for j,b in enumerate(labels):
                    if j<=i: continue
                    cv=corr.loc[a,b]
                    if abs(cv)>0.65:
                        warn_c="#ff2d55" if cv>0 else "#00c4ff"
                        note=f"High positive correlation ({cv:.2f}) — holding both {a}+{b} simultaneously offers limited diversification." if cv>0 else f"Negative correlation ({cv:.2f}) — {a} and {b} move oppositely. Natural hedge."
                        st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;padding:6px 12px;background:#09080f;border-left:2px solid {warn_c};margin-bottom:4px;color:{warn_c}">{note}</div>',unsafe_allow_html=True)
        else:
            st.info("Select at least 2 instruments to see correlations.")

    # ── REGIME + VOLATILITY SUMMARY ──────────────────────────
    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;color:#c9a84c;margin:0 0 12px">REGIME & VOLATILITY OVERVIEW</div>',unsafe_allow_html=True)
    reg_cols=st.columns(len(SEL))
    for col,mk in zip(reg_cols,SEL):
        sig=market_signals.get(mk,{}); reg=sig.get("regime",{}); vr=sig.get("vol_regime",{})
        reg_name=reg.get("regime","?"); adx=reg.get("adx_lite",0); bbw=reg.get("bb_width_pct",0)
        rv=vr.get("rv",0); rv_rank=vr.get("rv_pct_rank",50); vfc=vr.get("forecast","STABLE")
        rc="badge-regime-trend" if reg_name=="TRENDING" else "badge-regime-range" if reg_name=="RANGING" else "badge-regime-vol"
        vfc_c="#1aff8a" if vfc=="CONTRACTING" else "#ff2d55" if vfc=="EXPANDING" else "#5a5570"
        with col:
            st.markdown(f"""
            <div class="panel" style="margin-bottom:8px">
              <div style="font-family:Cinzel,serif;font-weight:700;color:#fff;margin-bottom:8px">{mk}</div>
              <span class="badge {rc}">{reg_name}</span>
              <div style="font-family:JetBrains Mono,monospace;font-size:10px;margin-top:8px;color:#5a5570">
                ADX {adx:.0f} · BB Width {bbw:.1f}%<br>
                RV {rv:.0f}% ann · Pctile {rv_rank:.0f}<br>
                Vol <span style="color:{vfc_c}">{vfc}</span>
              </div>
            </div>""",unsafe_allow_html=True)
        # Pattern tags
        pats=sig.get("patterns",[])
        if pats:
            col.markdown("".join(f'<span class="pattern-tag">{p2}</span>' for p2 in pats),unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# ALWAYS-ON BAR + AUTO REFRESH
# ══════════════════════════════════════════════════════════════
now_ts2=time.time()
interval=st.session_state["refresh_interval"]
remaining=max(0,interval-(now_ts2-st.session_state["last_refresh"]))

if st.session_state["always_on"]:
    shield_str=" · ⚠ SHIELD ACTIVE" if shield_active else ""
    st.markdown(f"""
    <div class="always-on-bar">
      <div><span class="live-dot"></span>NIGEL v2.0 · ALWAYS ON · {datetime.now().strftime("%H:%M:%S")}{shield_str}</div>
      <div style="font-family:Cinzel,serif;letter-spacing:.1em">NEXT REFRESH IN {remaining:.0f}s</div>
      <div style="color:#c9a84c">{" · ".join(n for n,_ in sessions_now)}</div>
    </div>
    <div style="height:40px"></div>""",unsafe_allow_html=True)
    if now_ts2-st.session_state["last_refresh"]>=interval:
        st.cache_data.clear()
        st.session_state["last_refresh"]=now_ts2
        time.sleep(1); st.rerun()
    else:
        time.sleep(min(remaining,5)); st.rerun()
