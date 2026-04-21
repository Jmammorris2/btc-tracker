"""
NIGEL — Private Trading Intelligence  v3.0
Ultra-luxury AI trading platform.
Run: streamlit run nigel.py

REQUIREMENTS:
  pip install streamlit pandas numpy plotly requests

HIDDEN GIFTS (now fully active):
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

API KEYS NEEDED:
  - Polygon.io (free tier works for equities/ETFs)
  - Anthropic Claude (optional, for AI analysis & whisper feed)

LAUNCH:
  streamlit run nigel.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
.gift-badge{display:inline-block;background:rgba(201,168,76,0.1);border:1px solid rgba(201,168,76,0.3);border-radius:1px;padding:2px 10px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--gold);letter-spacing:.1em;margin-bottom:8px;}
.macd-bull{background:rgba(26,255,138,0.04);border:1px solid rgba(26,255,138,0.15);border-radius:1px;padding:6px 12px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--emerald);margin-top:4px;}
.macd-bear{background:rgba(255,45,85,0.04);border:1px solid rgba(255,45,85,0.15);border-radius:1px;padding:6px 12px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--crimson);margin-top:4px;}
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
    "polygon_key":       _get("polygon_key", ""),
    "claude_key":        _get("claude_key", ""),
    "notes":             [],
    "signal_feed":       [],
    "last_ai_call":      0.0,
    "last_whisper_call": 0.0,
    "rule_set":          _get("rule_set", []),
    "bt_cache":          {},
    "ai_feed":           [],
    "diag_history":      [],
    "whisper_feed":      [],
    "always_on":         True,
    "refresh_interval":  60,
    "last_refresh":      0.0,
    "selected_markets":  ["BTC","NQ","GOLD","ES"],
    "shield_active":     False,
    "traders": [
        init_trader("CONSERVATEUR","◈","Precision entries only — waits for the perfect storm",0.005,2.5,72,True,"I trade once and trade right."),
        init_trader("MOMENTUM","◆","Rides breakouts and trend continuation",0.015,2.0,58,False,"The trend is my only edge."),
        init_trader("CONTRARIAN","◉","Fades extremes — buys oversold, sells overbought",0.025,1.8,45,False,"When others panic, I act."),
    ],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

for tr in st.session_state["traders"]:
    if "philosophy" not in tr: tr["philosophy"] = tr.get("style", "")
    if "paused" not in tr: tr["paused"] = False

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
        p = {"bitcoin": 84000, "ethereum": 3200}.get(cg_id, 1000)
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
        df = pd.DataFrame(data, columns=['t','o','h','l','c','v','_1','_2','_3','_4','_5','_6'])
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
    if len(tr) < n: return [None]*len(closes)
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
# GIFT 1 — REGIME DETECTOR
# ══════════════════════════════════════════════════════════════
def detect_regime(closes, highs=None, lows=None):
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
    atr_pct_rank = round(100*sum(1 for v in atr_history if v<=atr_pct)/len(atr_history), 0) if atr_history else 50
    if atr_pct_rank > 80:   regime = "VOLATILE"
    elif adx_lite > 25:     regime = "TRENDING"
    else:                   regime = "RANGING"
    return {"regime": regime, "adx_lite": adx_lite, "bb_width_pct": bb_width_pct, "atr_pct_rank": int(atr_pct_rank)}

# ══════════════════════════════════════════════════════════════
# GIFT 2 — DIVERGENCE ENGINE (RSI + MACD)
# ══════════════════════════════════════════════════════════════
def detect_divergence(closes, rsi_vals, lookback=10):
    result = {"bull_div": False, "bear_div": False, "desc": "",
              "macd_bull": False, "macd_bear": False, "macd_desc": ""}
    if len(closes) < lookback+2 or len(rsi_vals) < lookback+2: return result
    c_slice = closes[-lookback:]; r_slice = [v for v in rsi_vals[-lookback:] if v is not None]
    if len(r_slice) >= lookback:
        price_low_idx  = c_slice.index(min(c_slice))
        price_hi_idx   = c_slice.index(max(c_slice))
        rsi_at_price_low = r_slice[price_low_idx]
        rsi_at_price_hi  = r_slice[price_hi_idx]
        prev_c = closes[-(lookback*2):-lookback]
        prev_r = [v for v in rsi_vals[-(lookback*2):-lookback] if v is not None]
        if prev_c and prev_r:
            prev_low = min(prev_c); prev_hi = max(prev_c)
            try:
                prev_rsi_low = prev_r[prev_c.index(prev_low)]
                prev_rsi_hi  = prev_r[prev_c.index(prev_hi)]
                if min(c_slice) < prev_low and rsi_at_price_low > prev_rsi_low + 3:
                    result["bull_div"] = True
                    result["desc"] = "BULL DIV · Price lower low, RSI did not — hidden demand"
                elif max(c_slice) > prev_hi and rsi_at_price_hi < prev_rsi_hi - 3:
                    result["bear_div"] = True
                    result["desc"] = "BEAR DIV · Price higher high, RSI did not — hidden exhaustion"
            except (ValueError, IndexError): pass
    if len(closes) >= 26:
        macd_series = []
        for i in range(26, len(closes)+1):
            sl = closes[:i]
            macd_series.append(ema_series(sl,12)[-1] - ema_series(sl,26)[-1])
        if len(macd_series) >= lookback*2:
            m_slice  = macd_series[-lookback:]
            m_prev   = macd_series[-(lookback*2):-lookback]
            p_slice  = closes[-lookback:]
            p_prev_s = closes[-(lookback*2):-lookback]
            if p_prev_s and m_prev:
                if min(p_slice) < min(p_prev_s) and min(m_slice) > min(m_prev)+0.0001:
                    result["macd_bull"] = True
                    result["macd_desc"] = "MACD BULL DIV · Price new low, MACD held higher — momentum diverging"
                elif max(p_slice) > max(p_prev_s) and max(m_slice) < max(m_prev)-0.0001:
                    result["macd_bear"] = True
                    result["macd_desc"] = "MACD BEAR DIV · Price new high, MACD turned lower — momentum fading"
    return result

# ══════════════════════════════════════════════════════════════
# GIFT 3 — PATTERN SCANNER (8 patterns)
# ══════════════════════════════════════════════════════════════
def scan_patterns(closes, highs=None, lows=None):
    patterns = []
    if len(closes) < 10: return patterns
    h = highs or [c*1.005 for c in closes]
    l = lows  or [c*0.995 for c in closes]
    c = closes
    # 1. Higher High / Higher Low structure
    if h[-1]>h[-3] and h[-3]>h[-5] and l[-1]>l[-3] and l[-3]>l[-5]:
        patterns.append("HH/HL STRUCTURE")
    # 2. Lower Low / Lower High structure
    if h[-1]<h[-3] and h[-3]<h[-5] and l[-1]<l[-3] and l[-3]<l[-5]:
        patterns.append("LH/LL STRUCTURE")
    # 3. Bullish engulfing (last 2 candles)
    if len(c) >= 2:
        o1, c1 = c[-2], c[-2]
        o2, c2 = c[-1], c[-1]
        if c[-2] < c[-3] and c[-1] > c[-2] and c[-1] > c[-3]:
            patterns.append("ENGULFING BULL")
    # 4. Bearish engulfing
    if len(c) >= 2:
        if c[-2] > c[-3] and c[-1] < c[-2] and c[-1] < c[-3]:
            patterns.append("ENGULFING BEAR")
    # 5. Inside bar (consolidation)
    if len(h) >= 2 and len(l) >= 2:
        if h[-1] < h[-2] and l[-1] > l[-2]:
            patterns.append("INSIDE BAR")
    # 6. Outside bar (expansion)
    if len(h) >= 2 and len(l) >= 2:
        if h[-1] > h[-2] and l[-1] < l[-2]:
            patterns.append("OUTSIDE BAR")
    # 7. Three-bar reversal (bull)
    if len(c) >= 3:
        if c[-3] > c[-4] and c[-2] > c[-3] and c[-1] < c[-2] and c[-1] < c[-3]:
            patterns.append("3-BAR REVERSAL ↓")
        if c[-3] < c[-4] and c[-2] < c[-3] and c[-1] > c[-2] and c[-1] > c[-3]:
            patterns.append("3-BAR REVERSAL ↑")
    # 8. Doji-like (open ≈ close within 0.1%)
    if abs(c[-1] - c[-2]) / (c[-2]+1e-9) < 0.001:
        patterns.append("DOJI / INDECISION")
    return patterns

# ══════════════════════════════════════════════════════════════
# GIFT 4 — SMART MONEY CLOCK (session overlap scoring)
# ══════════════════════════════════════════════════════════════
def smart_money_clock():
    try:
        now_utc = datetime.now(ZoneInfo("UTC"))
        h = now_utc.hour + now_utc.minute / 60
        sessions = {
            "TOKYO":    (0, 9),
            "LONDON":   (7, 16),
            "NEW YORK": (13, 22),
        }
        active = [s for s, (start, end) in sessions.items() if start <= h < end]
        if "LONDON" in active and "NEW YORK" in active:
            session = "OVERLAP"; score = 100
        elif "NEW YORK" in active:
            session = "NEW YORK"; score = 85
        elif "LONDON" in active:
            session = "LONDON"; score = 75
        elif "TOKYO" in active:
            session = "TOKYO"; score = 55
        else:
            session = "OFF-HOURS"; score = 20
        tip = SESSION_TIPS.get(session, "")
        return {"session": session, "score": score, "tip": tip,
                "utc_hour": round(h, 1), "active_sessions": active}
    except:
        return {"session": "UNKNOWN", "score": 50, "tip": "", "utc_hour": 0, "active_sessions": []}

# ══════════════════════════════════════════════════════════════
# GIFT 5 — KELLY / RISK-OF-RUIN
# ══════════════════════════════════════════════════════════════
def kelly_ruin(trades, risk_pct, rr):
    if not trades:
        return {"kelly": risk_pct, "ruin_prob": 0.05, "wins": 0, "losses": 0,
                "win_rate": 0.5, "edge": 0.0, "half_kelly": risk_pct/2}
    wins   = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = len(trades) - wins
    wr = wins / len(trades) if trades else 0.5
    edge = wr * rr - (1 - wr)
    kelly = edge / rr if rr > 0 else risk_pct
    kelly = max(0.001, min(kelly, 0.25))
    # Monte Carlo ruin probability (simplified)
    ruin_prob = max(0.001, ((1 - wr) / (wr + 1e-9)) ** (int(1/risk_pct)))
    ruin_prob = min(ruin_prob, 0.99)
    return {
        "kelly": round(kelly, 4),
        "half_kelly": round(kelly/2, 4),
        "ruin_prob": round(ruin_prob, 4),
        "wins": wins, "losses": losses,
        "win_rate": round(wr, 3),
        "edge": round(edge, 4),
    }

# ══════════════════════════════════════════════════════════════
# CORE SIGNAL ENGINE
# ══════════════════════════════════════════════════════════════
def compute_signal(sym, closes):
    if len(closes) < 30:
        return {"signal":"WATCH","conf":50,"rsi":50,"bb_pct":0.5,"trend":"—",
                "regime":{"regime":"UNKNOWN","adx_lite":0,"bb_width_pct":0,"atr_pct_rank":50},
                "divergence":{},"patterns":[]}
    rsi = rsi_full(closes)
    cur_rsi = next((v for v in reversed(rsi) if v is not None), 50)
    bb_m, bb_u, bb_l, bb_p = bb_bands(closes)
    cur_bb  = next((v for v in reversed(bb_p) if v is not None), 0.5)
    ema20   = ema_series(closes, 20)[-1]
    ema50   = ema_series(closes, 50)[-1] if len(closes) >= 50 else ema_series(closes, 20)[-1]
    price   = closes[-1]
    trend   = "BULL" if price > ema20 > ema50 else ("BEAR" if price < ema20 < ema50 else "MIXED")
    regime  = detect_regime(closes)
    div     = detect_divergence(closes, rsi)
    pats    = scan_patterns(closes)

    # Scoring
    score = 0
    if cur_rsi < 35:  score += 25
    elif cur_rsi > 65: score -= 25
    if cur_bb < 0.2:  score += 20
    elif cur_bb > 0.8: score -= 20
    if trend == "BULL": score += 20
    elif trend == "BEAR": score -= 20
    if div.get("bull_div"): score += 15
    if div.get("bear_div"): score -= 15
    if div.get("macd_bull"): score += 10
    if div.get("macd_bear"): score -= 10
    if "HH/HL STRUCTURE" in pats: score += 10
    if "LH/LL STRUCTURE" in pats: score -= 10
    if "ENGULFING BULL" in pats:  score += 8
    if "ENGULFING BEAR" in pats:  score -= 8

    conf = min(95, max(10, 50 + score))
    if score >= 25:    signal = "LONG"
    elif score <= -25: signal = "SHORT"
    else:              signal = "WATCH"

    return {
        "signal": signal, "conf": conf, "rsi": round(cur_rsi,1), "bb_pct": round(cur_bb,3),
        "trend": trend, "regime": regime, "divergence": div, "patterns": pats,
        "score": score,
    }

# ══════════════════════════════════════════════════════════════
# GIFT 6 — DRAWDOWN SHIELD
# ══════════════════════════════════════════════════════════════
def check_drawdown_shield():
    total_balance = sum(t["balance"] for t in TRADERS)
    total_peak    = sum(t["peak"] for t in TRADERS)
    dd_pct = (total_peak - total_balance) / (total_peak + 1e-9)
    shield = dd_pct >= 0.08
    st.session_state["shield_active"] = shield
    if shield:
        for tr in TRADERS: tr["paused"] = True
    return dd_pct, shield

# ══════════════════════════════════════════════════════════════
# SIMULATED TRADE EXECUTION (paper trading)
# ══════════════════════════════════════════════════════════════
def maybe_trade(trader, sym, sig_data, price):
    if trader.get("paused"): return
    conf  = sig_data["conf"]
    sig   = sig_data["signal"]
    min_c = trader["min_conf"]
    if trader["wait_strong"] and conf < 70: return
    if conf < min_c: return
    if sig == "WATCH": return
    # Sanitize stale/incomplete open_pos from old session state
    op = trader.get("open_pos")
    if op and not all(k in op for k in ("sym","dir","entry","size","conf")):
        trader["open_pos"] = None; op = None
    # Close open position if direction flipped
    if op and op["sym"] == sym:
        if (op["dir"] == "LONG" and sig == "SHORT") or (op["dir"] == "SHORT" and sig == "LONG"):
            entry = op["entry"]; size = op["size"]
            pnl_raw = (price - entry) / entry if op["dir"] == "LONG" else (entry - price) / entry
            pnl_dollar = pnl_raw * size
            trader["balance"] = round(trader["balance"] + pnl_dollar, 2)
            trader["peak"]    = max(trader["peak"], trader["balance"])
            trader["history"].append(trader["balance"])
            trader["trades"].append({
                "sym": sym, "dir": op["dir"], "entry": entry, "exit": price,
                "pnl": round(pnl_dollar, 2), "conf": conf,
                "time": datetime.now().strftime("%H:%M"),
            })
            trader["open_pos"] = None
    # Open new position
    if not trader.get("open_pos"):
        size = trader["balance"] * trader["risk_pct"] * trader["rr"] * 10
        trader["open_pos"] = {
            "sym": sym, "dir": sig, "entry": price, "size": size,
            "conf": conf, "time": datetime.now().strftime("%H:%M"),
        }

# ══════════════════════════════════════════════════════════════
# GIFT 7 — CLAUDE AI ANALYSIS
# ══════════════════════════════════════════════════════════════
def call_claude(prompt, system="You are NIGEL, an elite private trading intelligence. Respond with sharp, concise insights. No disclaimers. No hedging. Speak with conviction."):
    if not CLKEY: return None
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": CLKEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model":"claude-opus-4-5","max_tokens":600,"system":system,
                  "messages":[{"role":"user","content":prompt}]}, timeout=25)
        return r.json()["content"][0]["text"]
    except: return None

def get_whisper():
    now = time.time()
    if now - st.session_state["last_whisper_call"] < 300: return
    st.session_state["last_whisper_call"] = now
    session_info = smart_money_clock()
    prompt = (f"Market session: {session_info['session']}. "
              f"Session quality score: {session_info['score']}/100. "
              "Give me one sharp, actionable micro-observation — a whisper. "
              "Maximum 2 sentences. Cryptic but useful. No preamble.")
    text = call_claude(prompt)
    if text:
        st.session_state["whisper_feed"].insert(0, {
            "time": datetime.now().strftime("%H:%M"), "text": text
        })
        if len(st.session_state["whisper_feed"]) > 12:
            st.session_state["whisper_feed"] = st.session_state["whisper_feed"][:12]

# ══════════════════════════════════════════════════════════════
# GIFT 8 — CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════
def build_correlation_matrix(market_closes):
    syms = list(market_closes.keys())
    n = min(30, min(len(v) for v in market_closes.values()))
    if n < 5: return None, syms
    slices = {s: market_closes[s][-n:] for s in syms}
    mat = [[0.0]*len(syms) for _ in range(len(syms))]
    for i, s1 in enumerate(syms):
        for j, s2 in enumerate(syms):
            a = slices[s1]; b = slices[s2]
            if len(a) != len(b): mat[i][j] = 0; continue
            ra = [a[k]-a[k-1] for k in range(1,len(a))]
            rb = [b[k]-b[k-1] for k in range(1,len(b))]
            ma_ = sum(ra)/len(ra); mb_ = sum(rb)/len(rb)
            num = sum((ra[k]-ma_)*(rb[k]-mb_) for k in range(len(ra)))
            da  = (sum((x-ma_)**2 for x in ra))**0.5
            db  = (sum((x-mb_)**2 for x in rb))**0.5
            mat[i][j] = round(num/(da*db+1e-9), 3)
    return mat, syms

# ══════════════════════════════════════════════════════════════
# TRADE JOURNAL CSV
# ══════════════════════════════════════════════════════════════
def build_journal_csv():
    rows = []
    for tr in TRADERS:
        for t in tr.get("trades", []):
            rows.append({
                "trader":   tr["name"],
                "symbol":   t.get("sym",""),
                "direction":t.get("dir",""),
                "entry":    t.get("entry",""),
                "exit":     t.get("exit",""),
                "pnl":      t.get("pnl",""),
                "conf":     t.get("conf",""),
                "time":     t.get("time",""),
            })
    if not rows: rows = [{"trader":"—","symbol":"—","direction":"—","entry":"—","exit":"—","pnl":"—","conf":"—","time":"—"}]
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════
# FETCH ALL MARKET DATA
# ══════════════════════════════════════════════════════════════
def load_all_market_data():
    data = {}
    for sym in MARKETS:
        m = MARKETS[sym]
        if m["crypto"]:
            cg_map = {"BTC":"bitcoin","ETH":"ethereum"}
            cg = cg_map.get(sym, sym.lower())
            d = fetch_crypto_price(cg)
            live = fetch_binance_live(sym)
            if live:
                d["price"] = live["price"]
                d["chg"]   = live["chg"]
        else:
            ticker = TICKERS.get(sym, sym)
            d = fetch_polygon_data(ticker, POLY)
        d["signal"] = compute_signal(sym, d["closes"])
        data[sym] = d
    return data

# ══════════════════════════════════════════════════════════════
# CHART BUILDER
# ══════════════════════════════════════════════════════════════
def build_chart(sym, closes, color):
    if len(closes) < 5: return go.Figure()
    rsi = rsi_full(closes)
    bb_m, bb_u, bb_l, _ = bb_bands(closes)
    ema20 = ema_series(closes, 20)
    ema50 = ema_series(closes, 50) if len(closes) >= 50 else ema20
    idx = list(range(len(closes)))

    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3],
                        shared_xaxes=True, vertical_spacing=0.03)
    # Price
    fig.add_trace(go.Scatter(x=idx, y=closes, line=dict(color=color, width=1.5),
                             name="Price", fill='tonexty',
                             fillcolor=f"rgba({_hex_to_rgb(color)},0.04)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=bb_u, line=dict(color="rgba(201,168,76,0.3)", width=0.8, dash='dot'), name="BB Upper"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=bb_l, line=dict(color="rgba(201,168,76,0.3)", width=0.8, dash='dot'), name="BB Lower",
                             fill='tonexty', fillcolor="rgba(201,168,76,0.03)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=ema20, line=dict(color="rgba(0,196,255,0.5)", width=1), name="EMA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=idx, y=ema50, line=dict(color="rgba(255,45,85,0.4)", width=1), name="EMA50"), row=1, col=1)
    # RSI
    rsi_clean = [v if v is not None else 50 for v in rsi]
    fig.add_trace(go.Scatter(x=idx, y=rsi_clean, line=dict(color="#c9a84c", width=1.2), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line=dict(color="rgba(255,45,85,0.3)", dash="dot", width=0.8), row=2, col=1)
    fig.add_hline(y=30, line=dict(color="rgba(26,255,138,0.3)", dash="dot", width=0.8), row=2, col=1)

    fig.update_layout(
        paper_bgcolor="#05040a", plot_bgcolor="#05040a",
        margin=dict(l=0, r=0, t=0, b=0), height=320,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(201,168,76,0.05)", zeroline=False,
                   tickfont=dict(color="#5a5570", size=9), side="right"),
        xaxis2=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis2=dict(showgrid=True, gridcolor="rgba(201,168,76,0.05)", zeroline=False,
                    tickfont=dict(color="#5a5570", size=9), range=[0,100], side="right"),
    )
    return fig

def _hex_to_rgb(h):
    h = h.lstrip("#")
    r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return f"{r},{g},{b}"

# ══════════════════════════════════════════════════════════════
# VOLATILITY FORECAST (GARCH-lite)
# ══════════════════════════════════════════════════════════════
def vol_forecast(closes):
    if len(closes) < 20: return {"vol_1d": 0, "regime": "UNKNOWN", "atr_rank": 50}
    returns = [(closes[i]-closes[i-1])/closes[i-1] for i in range(1, len(closes))]
    recent_vol = (sum(r**2 for r in returns[-10:])/10)**0.5 * 100
    long_vol   = (sum(r**2 for r in returns[-30:])/30)**0.5 * 100 if len(returns) >= 30 else recent_vol
    atr_v = atr_series(closes, None, None, 14)
    atr_clean = [v for v in atr_v if v is not None]
    atr_rank = 50
    if atr_clean:
        cur_atr_pct = atr_clean[-1]/closes[-1]*100
        atr_pcts = [v/closes[max(0,i)]*100 for i,v in enumerate(atr_clean)]
        atr_rank = int(100*sum(1 for v in atr_pcts if v <= cur_atr_pct)/len(atr_pcts))
    vol_regime = "HIGH" if recent_vol > long_vol * 1.3 else ("LOW" if recent_vol < long_vol * 0.7 else "NORMAL")
    return {"vol_1d": round(recent_vol, 3), "long_vol": round(long_vol, 3),
            "vol_regime": vol_regime, "atr_rank": atr_rank}

# ══════════════════════════════════════════════════════════════
# MASTHEAD & TICKER
# ══════════════════════════════════════════════════════════════
def render_masthead(session_info, fg_val, fg_label):
    now_str = datetime.now().strftime("%A, %d %B %Y  ·  %H:%M")
    sess_color = {"NEW YORK":"#1aff8a","OVERLAP":"#1aff8a","LONDON":"#c9a84c","TOKYO":"#00c4ff","OFF-HOURS":"#5a5570"}.get(session_info["session"], "#c9a84c")
    st.markdown(f"""
    <div class="nigel-masthead">
      <div>
        <div class="nigel-wordmark">N<em>·</em>I<em>·</em>G<em>·</em>E<em>·</em>L</div>
        <div class="nigel-tagline">Private Trading Intelligence &nbsp;·&nbsp; v3.0</div>
      </div>
      <div style="text-align:right">
        <div style="font-family:'Cinzel',serif;font-size:10px;letter-spacing:.14em;color:{sess_color};margin-bottom:4px">
          <span class="live-dot"></span>{session_info['session']} SESSION &nbsp;·&nbsp; Score {session_info['score']}/100
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a5570">{now_str}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a5570;margin-top:2px">
          Fear &amp; Greed: <span style="color:#c9a84c">{fg_val}</span> · {fg_label}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_ticker(market_data):
    items_html = ""
    for sym, d in market_data.items():
        m = MARKETS[sym]
        price = d.get("price", 0)
        chg   = d.get("chg", 0)
        chg_cls = "tick-up" if chg >= 0 else "tick-dn"
        chg_str = f"{'+'if chg>=0 else ''}{chg:.2f}%"
        price_fmt = f"{price:,.2f}" if price < 10000 else f"{price:,.0f}"
        items_html += f'<span class="tick-item"><span class="tick-sym">{m["emoji"]} {sym}</span><span class="tick-px">{price_fmt}</span><span class="{chg_cls}">{chg_str}</span></span><span class="tick-sep">·</span>'
    double = items_html * 2
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-track">{double}</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════
def main():
    session_info = smart_money_clock()
    fg_val, fg_label = fetch_fear_greed()

    # Sidebar settings
    with st.sidebar:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:11px;letter-spacing:.15em;color:#c9a84c;padding:20px 0 12px">NIGEL SETTINGS</div>', unsafe_allow_html=True)
        new_poly = st.text_input("Polygon Key", value=POLY, type="password")
        new_clk  = st.text_input("Claude Key",  value=CLKEY, type="password")
        if st.button("Save Keys"):
            st.session_state["polygon_key"] = new_poly; _save("polygon_key", new_poly)
            st.session_state["claude_key"]  = new_clk;  _save("claude_key",  new_clk)
            st.success("Saved")
        st.markdown("---")
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#5a5570">ACTIVE MARKETS</div>', unsafe_allow_html=True)
        sel = st.multiselect("", list(MARKETS.keys()), default=st.session_state["selected_markets"], label_visibility="collapsed")
        if sel: st.session_state["selected_markets"] = sel
        st.markdown("---")
        interval = st.selectbox("Auto-refresh (s)", [30,60,120,300], index=1)
        st.session_state["refresh_interval"] = interval
        st.markdown("---")
        if st.button("⬇  Journal CSV"):
            csv = build_journal_csv()
            st.download_button("Download", csv, "nigel_journal.csv", "text/csv")
        st.markdown("---")
        if st.button("🔄  Reset Traders"):
            st.session_state["traders"] = DEFAULTS["traders"]
            st.rerun()

    # Auto-refresh
    now = time.time()
    if now - st.session_state["last_refresh"] > st.session_state["refresh_interval"]:
        st.session_state["last_refresh"] = now
        st.cache_data.clear()

    market_data = load_all_market_data()
    active_syms = [s for s in st.session_state["selected_markets"] if s in market_data]

    # Fire whisper
    if CLKEY: get_whisper()

    # Drawdown shield
    dd_pct, shield = check_drawdown_shield()

    render_masthead(session_info, fg_val, fg_label)
    render_ticker(market_data)

    if shield:
        st.markdown('<div class="shield-banner">⚠ DRAWDOWN SHIELD ACTIVE — Collective drawdown exceeded 8%. All traders paused. Review positions before resuming.</div>', unsafe_allow_html=True)

    # ── TABS ─────────────────────────────────────────────────
    tabs = st.tabs(["◈ SIGNALS", "◆ TRADERS", "◉ INTELLIGENCE", "⬡ ANALYTICS", "⊕ PLAYBOOK"])

    # ════════════════════════
    # TAB 1 — SIGNALS
    # ════════════════════════
    with tabs[0]:
        cols = st.columns(len(active_syms)) if active_syms else [st.container()]
        for i, sym in enumerate(active_syms):
            d  = market_data[sym]
            m  = MARKETS[sym]
            sig = d["signal"]
            price = d.get("price", 0)
            chg   = d.get("chg", 0)
            chg_cls = "sc-chg-up" if chg >= 0 else "sc-chg-dn"
            chg_str = f"{'+'if chg>=0 else ''}{chg:.2f}%"
            price_fmt = f"{price:,.2f}" if price < 10000 else f"{price:,.0f}"
            card_cls = "bull" if sig["signal"]=="LONG" else ("bear" if sig["signal"]=="SHORT" else "flat")
            badge_cls = "badge-long" if sig["signal"]=="LONG" else ("badge-short" if sig["signal"]=="SHORT" else "badge-watch")

            reg = sig["regime"]
            reg_name = reg.get("regime","—")
            reg_badge_cls = {"TRENDING":"badge-regime-trend","RANGING":"badge-regime-range","VOLATILE":"badge-regime-vol"}.get(reg_name,"badge-regime-range")

            div = sig.get("divergence", {})
            pats = sig.get("patterns", [])

            with cols[i]:
                st.markdown(f"""
                <div class="signal-card {card_cls}">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                    <div>
                      <div class="sc-sym">{m['emoji']} {sym}</div>
                      <div style="font-family:'Cormorant Garamond',serif;font-style:italic;font-size:11px;color:#5a5570;margin-top:2px">{m['sub']}</div>
                    </div>
                    <div style="text-align:right">
                      <span class="badge {badge_cls}">{sig['signal']}</span><br>
                      <span class="{reg_badge_cls} badge" style="margin-top:4px;display:inline-block">{reg_name}</span>
                    </div>
                  </div>
                  <div class="sc-price">{price_fmt}</div>
                  <div class="{chg_cls}">{chg_str} · 24h</div>
                  <div class="meter-track" style="margin-top:12px">
                    <div class="meter-fill" style="width:{sig['conf']}%;background:{'#1aff8a' if sig['signal']=='LONG' else ('#ff2d55' if sig['signal']=='SHORT' else '#c9a84c')}"></div>
                  </div>
                  <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:9px;color:#5a5570;margin-top:2px">
                    <span>CONFIDENCE</span><span>{sig['conf']}%</span>
                  </div>
                  <div style="margin-top:10px;display:flex;gap:16px;font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a5570">
                    <span>RSI <span style="color:#d4cfc0">{sig['rsi']}</span></span>
                    <span>BB% <span style="color:#d4cfc0">{sig['bb_pct']:.2f}</span></span>
                    <span>ADX <span style="color:#d4cfc0">{reg.get('adx_lite',0)}</span></span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Divergence badges
                if div.get("bull_div"):
                    st.markdown(f'<div class="divergence-bull">⟰ {div["desc"]}</div>', unsafe_allow_html=True)
                if div.get("bear_div"):
                    st.markdown(f'<div class="divergence-bear">⟱ {div["desc"]}</div>', unsafe_allow_html=True)
                if div.get("macd_bull"):
                    st.markdown(f'<div class="macd-bull">≋ {div["macd_desc"]}</div>', unsafe_allow_html=True)
                if div.get("macd_bear"):
                    st.markdown(f'<div class="macd-bear">≋ {div["macd_desc"]}</div>', unsafe_allow_html=True)

                # Pattern tags
                if pats:
                    tags = "".join(f'<span class="pattern-tag">{p}</span>' for p in pats)
                    st.markdown(f'<div style="margin-top:6px">{tags}</div>', unsafe_allow_html=True)

                # Chart
                fig = build_chart(sym, d["closes"], m["color"])
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # Session tip
        st.markdown(f"""
        <div class="nigel-note note-info" style="margin-top:8px">
          <div class="note-head">Smart Money Clock · {session_info['session']} · Score {session_info['score']}/100</div>
          <div class="note-body">{session_info['tip']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════
    # TAB 2 — TRADERS
    # ════════════════════════
    with tabs[1]:
        # Run paper trades
        for sym in active_syms:
            d   = market_data[sym]
            sig = d["signal"]
            price = d.get("price", 0)
            for tr in TRADERS:
                maybe_trade(tr, sym, sig, price)

        col_a, col_b = st.columns([2,1])
        with col_a:
            for tr in TRADERS:
                dd = (tr["peak"] - tr["balance"]) / (tr["peak"] + 1e-9) * 100
                pnl_total = tr["balance"] - 25000
                pnl_cls = "#1aff8a" if pnl_total >= 0 else "#ff2d55"
                paused_tag = '<span style="color:#ff2d55;font-size:9px;font-family:JetBrains Mono,monospace"> · PAUSED</span>' if tr.get("paused") else ""
                kk = kelly_ruin(tr["trades"], tr["risk_pct"], tr["rr"])

                st.markdown(f"""
                <div class="panel panel-gold" style="margin-bottom:16px">
                  <div class="trader-header">
                    <div>
                      <div class="trader-name">{tr['emoji']} {tr['name']}{paused_tag}</div>
                      <div class="trader-style">{tr['style']}</div>
                    </div>
                    <div style="text-align:right">
                      <div style="font-family:'JetBrains Mono',monospace;font-size:1.4rem;color:{pnl_cls}">
                        {'+'if pnl_total>=0 else ''}${pnl_total:,.0f}
                      </div>
                      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a5570">
                        Balance ${tr['balance']:,.0f} · DD {dd:.1f}%
                      </div>
                    </div>
                  </div>
                  <div style="display:flex;gap:20px;font-family:'JetBrains Mono',monospace;font-size:10px;margin-bottom:10px">
                    <span style="color:#5a5570">WIN RATE <span style="color:#d4cfc0">{kk['win_rate']*100:.0f}%</span></span>
                    <span style="color:#5a5570">TRADES <span style="color:#d4cfc0">{len(tr['trades'])}</span></span>
                    <span style="color:#5a5570">KELLY <span style="color:#c9a84c">{kk['kelly']*100:.1f}%</span></span>
                    <span style="color:#5a5570">RUIN <span style="color:#ff2d55">{kk['ruin_prob']*100:.1f}%</span></span>
                  </div>
                """, unsafe_allow_html=True)

                # Open position — guard against stale state missing keys
                op = tr.get("open_pos")
                if op and not all(k in op for k in ("sym","dir","entry","conf")):
                    tr["open_pos"] = None; op = None
                if op:
                    current_price = market_data.get(op["sym"],{}).get("price", op["entry"])
                    unrealized = (current_price - op["entry"])/op["entry"] if op["dir"]=="LONG" else (op["entry"]-current_price)/op["entry"]
                    unr_pct = unrealized * 100
                    pos_cls = "pos-long" if op["dir"]=="LONG" else "pos-short"
                    pip_cls = "trade-pip-w" if unr_pct >= 0 else "trade-pip-l"
                    st.markdown(f"""
                    <div class="pos-panel {pos_cls}">
                      OPEN · {op['dir']} {op['sym']} @ {op['entry']:,.2f}
                      &nbsp;|&nbsp; Now {current_price:,.2f}
                      &nbsp;|&nbsp; <span class="{pip_cls}">{'+'if unr_pct>=0 else ''}{unr_pct:.2f}%</span>
                      &nbsp;|&nbsp; Conf {op['conf']}%
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown('<div class="pos-panel pos-flat">— No open position</div>', unsafe_allow_html=True)

                # Recent trades
                if tr["trades"]:
                    recent = tr["trades"][-5:][::-1]
                    for t in recent:
                        pip_cls = "trade-pip-w" if t["pnl"] >= 0 else "trade-pip-l"
                        st.markdown(f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570">{t["time"]} {t["sym"]} {t["dir"]} &nbsp;</span><span class="{pip_cls}">${t["pnl"]:+.0f}</span><br>', unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                # Pause/resume button
                b_label = "▶ Resume" if tr.get("paused") else "⏸ Pause"
                if st.button(b_label, key=f"pause_{tr['name']}"):
                    tr["paused"] = not tr.get("paused", False)
                    st.rerun()

        with col_b:
            # Equity curves
            st.markdown('<div class="panel panel-em">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.12em;color:#1aff8a;margin-bottom:12px">EQUITY CURVES</div>', unsafe_allow_html=True)
            fig_eq = go.Figure()
            colors_eq = ["#c9a84c","#1aff8a","#ff2d55"]
            for idx, tr in enumerate(TRADERS):
                h = tr["history"]
                fig_eq.add_trace(go.Scatter(
                    y=h, mode="lines", name=tr["name"],
                    line=dict(color=colors_eq[idx % len(colors_eq)], width=1.5)
                ))
            fig_eq.update_layout(
                paper_bgcolor="#09080f", plot_bgcolor="#09080f",
                height=200, margin=dict(l=0,r=0,t=0,b=0),
                showlegend=True,
                legend=dict(font=dict(size=9, color="#5a5570"), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(201,168,76,0.05)",
                           tickfont=dict(color="#5a5570", size=8), side="right"),
            )
            st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar":False})
            st.markdown("</div>", unsafe_allow_html=True)

            # Kelly panel
            st.markdown('<div class="kelly-panel" style="margin-top:14px">', unsafe_allow_html=True)
            st.markdown('<div class="gift-badge">◈ RISK-OF-RUIN ENGINE</div>', unsafe_allow_html=True)
            for tr in TRADERS:
                kk = kelly_ruin(tr["trades"], tr["risk_pct"], tr["rr"])
                ruin_color = "#ff2d55" if kk["ruin_prob"] > 0.1 else "#c9a84c"
                st.markdown(f"""
                <div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid rgba(201,168,76,0.08)">
                  <div style="font-family:'Cinzel',serif;font-size:9px;letter-spacing:.1em;color:#5a5570">{tr['name']}</div>
                  <div style="display:flex;gap:16px;margin-top:4px">
                    <div>
                      <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;color:#c9a84c">{kk['kelly']*100:.1f}%</div>
                      <div style="font-family:'Cinzel',serif;font-size:8px;color:#5a5570;letter-spacing:.1em">KELLY F</div>
                    </div>
                    <div>
                      <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;color:{ruin_color}">{kk['ruin_prob']*100:.1f}%</div>
                      <div style="font-family:'Cinzel',serif;font-size:8px;color:#5a5570;letter-spacing:.1em">RUIN PROB</div>
                    </div>
                    <div>
                      <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;color:#d4cfc0">{kk['edge']:+.3f}</div>
                      <div style="font-family:'Cinzel',serif;font-size:8px;color:#5a5570;letter-spacing:.1em">EDGE</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════
    # TAB 3 — INTELLIGENCE
    # ════════════════════════
    with tabs[2]:
        col_ai, col_w = st.columns([3,2])

        with col_ai:
            st.markdown('<div class="gift-badge">◈ NIGEL AI — CLAUDE INTELLIGENCE</div>', unsafe_allow_html=True)
            if not CLKEY:
                st.markdown('<div class="nigel-note note-watch"><div class="note-head">Claude Key Required</div><div class="note-body">Add your Anthropic Claude API key in Settings to unlock AI analysis, whisper feed, and market intelligence.</div></div>', unsafe_allow_html=True)
            else:
                # Build market summary for Claude
                summary_lines = []
                for sym in active_syms:
                    d   = market_data[sym]
                    sig = d["signal"]
                    summary_lines.append(
                        f"{sym}: price={d.get('price',0):,.2f}, chg={d.get('chg',0):+.2f}%, "
                        f"signal={sig['signal']}, conf={sig['conf']}%, rsi={sig['rsi']}, "
                        f"regime={sig['regime']['regime']}, trend={sig['trend']}"
                    )
                mkt_summary = "\n".join(summary_lines)
                session_str = f"Session: {session_info['session']} (score {session_info['score']}/100)"
                fg_str = f"Fear & Greed: {fg_val} ({fg_label})"

                user_q = st.text_area("Ask NIGEL anything", placeholder="What is the highest-conviction trade right now?", height=80)
                if st.button("Analyse", type="primary"):
                    now_t = time.time()
                    if now_t - st.session_state["last_ai_call"] < 10:
                        st.warning("Rate limit — wait 10 seconds.")
                    else:
                        st.session_state["last_ai_call"] = now_t
                        prompt = f"""Market data:\n{mkt_summary}\n\n{session_str}\n{fg_str}\n\nUser question: {user_q or 'Give me your single highest conviction trade with entry reasoning, stop placement and target.'}"""
                        with st.spinner("NIGEL is thinking..."):
                            resp = call_claude(prompt)
                        if resp:
                            ts = datetime.now().strftime("%H:%M")
                            st.session_state["ai_feed"].insert(0, {"time": ts, "q": user_q or "Top conviction trade", "a": resp})
                            if len(st.session_state["ai_feed"]) > 10:
                                st.session_state["ai_feed"] = st.session_state["ai_feed"][:10]

                # Show AI feed
                for item in st.session_state["ai_feed"]:
                    st.markdown(f"""
                    <div class="ai-response" style="margin-bottom:12px">
                      <div class="ai-header">NIGEL · {item['time']} · {item['q'][:60]}</div>
                      {item['a']}
                    </div>
                    """, unsafe_allow_html=True)

                if not st.session_state["ai_feed"]:
                    # Auto-brief on load
                    if st.button("Generate Market Brief"):
                        prompt = f"Market data:\n{mkt_summary}\n\n{session_str}\n{fg_str}\n\nGive me a sharp 3-bullet morning brief: the one risk, the one opportunity, and the one thing to watch. Be precise."
                        with st.spinner("Generating brief..."):
                            resp = call_claude(prompt)
                        if resp:
                            st.session_state["ai_feed"].insert(0, {"time": datetime.now().strftime("%H:%M"), "q": "Morning Brief", "a": resp})
                            st.rerun()

        with col_w:
            st.markdown('<div class="gift-badge">◈ WHISPER FEED</div>', unsafe_allow_html=True)
            if st.session_state["whisper_feed"]:
                for w in st.session_state["whisper_feed"]:
                    st.markdown(f'<div class="whisper-note"><span style="color:#3a3550">{w["time"]}</span> · {w["text"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="whisper-note">Whispers will appear here. Add a Claude API key to activate.</div>', unsafe_allow_html=True)

    # ════════════════════════
    # TAB 4 — ANALYTICS
    # ════════════════════════
    with tabs[3]:
        col_c, col_v = st.columns(2)

        with col_c:
            st.markdown('<div class="gift-badge">◈ CORRELATION MATRIX</div>', unsafe_allow_html=True)
            market_closes_map = {sym: market_data[sym]["closes"] for sym in active_syms}
            mat, syms_c = build_correlation_matrix(market_closes_map)
            if mat:
                z_text = [[f"{mat[i][j]:.2f}" for j in range(len(syms_c))] for i in range(len(syms_c))]
                z_vals  = [[mat[i][j] for j in range(len(syms_c))] for i in range(len(syms_c))]
                fig_cor = go.Figure(go.Heatmap(
                    z=z_vals, x=syms_c, y=syms_c, text=z_text, texttemplate="%{text}",
                    colorscale=[[0,"#ff2d55"],[0.5,"#09080f"],[1,"#1aff8a"]],
                    zmid=0, zmin=-1, zmax=1,
                    showscale=False,
                    textfont=dict(size=11, color="#d4cfc0"),
                ))
                fig_cor.update_layout(
                    paper_bgcolor="#09080f", plot_bgcolor="#09080f",
                    height=280, margin=dict(l=0,r=0,t=0,b=0),
                    xaxis=dict(tickfont=dict(color="#c9a84c", size=10, family="JetBrains Mono")),
                    yaxis=dict(tickfont=dict(color="#c9a84c", size=10, family="JetBrains Mono")),
                )
                st.plotly_chart(fig_cor, use_container_width=True, config={"displayModeBar":False})
            else:
                st.info("Insufficient data for correlation matrix.")

        with col_v:
            st.markdown('<div class="gift-badge">◈ VOLATILITY FORECAST</div>', unsafe_allow_html=True)
            for sym in active_syms:
                vf = vol_forecast(market_data[sym]["closes"])
                color = {"HIGH":"#ff2d55","NORMAL":"#c9a84c","LOW":"#1aff8a"}.get(vf["vol_regime"],"#c9a84c")
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#09080f;border:1px solid rgba(201,168,76,0.08);border-radius:1px;margin-bottom:6px">
                  <div style="font-family:'Cinzel',serif;font-size:10px;letter-spacing:.08em;color:#fff">{sym}</div>
                  <div style="display:flex;gap:18px;font-family:'JetBrains Mono',monospace;font-size:10px">
                    <span style="color:#5a5570">VOL <span style="color:#d4cfc0">{vf['vol_1d']:.2f}%</span></span>
                    <span style="color:#5a5570">ATR RANK <span style="color:#d4cfc0">{vf['atr_rank']}</span></span>
                    <span style="color:{color};font-weight:700">{vf['vol_regime']}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="gift-badge" style="margin-bottom:12px">◈ REGIME DASHBOARD</div>', unsafe_allow_html=True)
        reg_cols = st.columns(len(active_syms))
        for i, sym in enumerate(active_syms):
            sig = market_data[sym]["signal"]
            reg = sig["regime"]
            reg_name = reg.get("regime","—")
            reg_color = {"TRENDING":"#1aff8a","RANGING":"#c9a84c","VOLATILE":"#ff2d55"}.get(reg_name,"#5a5570")
            with reg_cols[i]:
                st.markdown(f"""
                <div class="panel" style="text-align:center;padding:16px">
                  <div style="font-family:'Cinzel',serif;font-size:11px;font-weight:700;letter-spacing:.12em;color:{reg_color};margin-bottom:8px">{reg_name}</div>
                  <div style="font-family:'Cinzel',serif;font-size:9px;letter-spacing:.1em;color:#5a5570;margin-bottom:4px">{sym}</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a5570">ADX {reg.get('adx_lite',0)} · BB {reg.get('bb_width_pct',0):.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════
    # TAB 5 — PLAYBOOK
    # ════════════════════════
    with tabs[4]:
        col_p1, col_p2 = st.columns([3,2])

        with col_p1:
            st.markdown('<div style="font-family:Cinzel,serif;font-size:11px;letter-spacing:.14em;color:#c9a84c;margin-bottom:16px">TRADING RULES</div>', unsafe_allow_html=True)

            default_rules = [
                {"name": "No counter-trend trades below 50% confidence", "on": True},
                {"name": "Minimum 2:1 reward-to-risk on every entry",    "on": True},
                {"name": "Maximum 3 open positions simultaneously",       "on": True},
                {"name": "No trading in first 15min of New York open",    "on": True},
                {"name": "Reduce size by 50% after two consecutive losses","on": True},
                {"name": "Honor stop losses — no exceptions",             "on": True},
                {"name": "Log every trade in the journal",                "on": True},
                {"name": "Wait for session overlap before high-risk entries","on": False},
            ]
            if not st.session_state["rule_set"]:
                st.session_state["rule_set"] = default_rules
                _save("rule_set", default_rules)

            rules = st.session_state["rule_set"]
            for idx, rule in enumerate(rules):
                on_cls = "rule-on" if rule["on"] else "rule-off"
                toggle = "ON" if rule["on"] else "OFF"
                cols_r = st.columns([6,1])
                with cols_r[0]:
                    st.markdown(f'<div class="rule-row {on_cls}"><div><div class="rule-name">{rule["name"]}</div></div><div style="font-family:JetBrains Mono,monospace;font-size:9px;color:{"#1aff8a" if rule["on"] else "#3a3550"}">{toggle}</div></div>', unsafe_allow_html=True)
                with cols_r[1]:
                    if st.button("⟳", key=f"rule_{idx}"):
                        rules[idx]["on"] = not rules[idx]["on"]
                        _save("rule_set", rules)
                        st.rerun()

            st.markdown("---")
            new_rule = st.text_input("Add rule", placeholder="Your rule...")
            if st.button("Add Rule") and new_rule:
                rules.append({"name": new_rule, "on": True})
                st.session_state["rule_set"] = rules
                _save("rule_set", rules)
                st.rerun()

        with col_p2:
            st.markdown('<div style="font-family:Cinzel,serif;font-size:11px;letter-spacing:.14em;color:#c9a84c;margin-bottom:16px">NOTES</div>', unsafe_allow_html=True)
            note_input = st.text_area("New note", height=80, placeholder="Market observation, setup, insight...")
            note_type = st.selectbox("Type", ["watch","buy","sell","info"])
            if st.button("Save Note"):
                st.session_state["notes"].insert(0, {
                    "text": note_input, "type": note_type,
                    "time": datetime.now().strftime("%H:%M")
                })
                st.rerun()
            for note in st.session_state["notes"][:15]:
                st.markdown(f"""
                <div class="nigel-note note-{note['type']}">
                  <div class="note-head">{note['type'].upper()} · {note['time']}</div>
                  <div class="note-body">{note['text']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── ALWAYS-ON BAR ─────────────────────────────────────────
    total_pnl = sum(t["balance"] - 25000 for t in TRADERS)
    pnl_color = "#1aff8a" if total_pnl >= 0 else "#ff2d55"
    open_pos  = sum(1 for t in TRADERS if t.get("open_pos"))
    dd_pct_v, _ = check_drawdown_shield()
    shield_str = "  ·  ⚠ SHIELD" if shield else ""

    st.markdown(f"""
    <div class="always-on-bar">
      <div><span class="live-dot"></span>NIGEL LIVE &nbsp;·&nbsp; {session_info['session']} &nbsp;·&nbsp; Session Quality {session_info['score']}/100{shield_str}</div>
      <div>
        <span style="color:{pnl_color}">Portfolio {'+'if total_pnl>=0 else ''}{total_pnl:,.0f}</span>
        &nbsp;·&nbsp; Open Positions {open_pos}
        &nbsp;·&nbsp; Drawdown {dd_pct_v*100:.1f}%
        &nbsp;·&nbsp; F&G {fg_val}
        &nbsp;·&nbsp; <span style="color:#3a3550">{datetime.now().strftime('%H:%M:%S')}</span>
      </div>
    </div>
    <div style="height:40px"></div>
    """, unsafe_allow_html=True)

    # Auto-rerun
    if st.session_state.get("always_on"):
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__" or True:
    main()
