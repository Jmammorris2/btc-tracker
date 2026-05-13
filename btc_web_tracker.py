# es_signal.py
# E-mini S&P 500 Signal Engine
# Data: Yahoo Finance API (no yfinance - pure requests)
# AI:   Claude Anthropic (add key in sidebar)
# Run:  streamlit run es_signal.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import io
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="ES Signal",
    layout="wide",
    page_icon="S",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=JetBrains+Mono:wght@400;700&family=Cormorant+Garamond:ital,wght@0,400;1,400&display=swap');
:root {
  --bg:#05040a; --bg2:#09080f; --bg3:#0d0c16; --bg4:#12101e;
  --gold:#c9a84c; --em:#1aff8a; --cr:#ff2d55;
  --sap:#00c4ff; --vio:#a855f7;
  --txt:#d4cfc0; --dim:#5a5570; --mute:#3a3550;
}
html,body,[class*="css"]{
  font-family:'Cormorant Garamond',serif!important;
  background:var(--bg)!important;
  color:var(--txt)!important;
}
.block-container{padding:0 1.5rem 4rem!important;max-width:100%!important;}
.panel{
  background:var(--bg2);
  border:1px solid rgba(201,168,76,.15);
  border-radius:2px;
  padding:14px 16px;
  margin-bottom:8px;
}
.badge{
  display:inline-block;padding:3px 10px;border-radius:1px;
  font-family:'JetBrains Mono',monospace;font-size:10px;
  font-weight:700;letter-spacing:.1em;text-transform:uppercase;
}
.bl{background:rgba(26,255,138,.08);color:#1aff8a;border:1px solid rgba(26,255,138,.3);}
.bs{background:rgba(255,45,85,.08);color:#ff2d55;border:1px solid rgba(255,45,85,.3);}
.bh{background:rgba(201,168,76,.08);color:#c9a84c;border:1px solid rgba(201,168,76,.3);}
.stTabs [data-baseweb="tab-list"]{
  background:var(--bg2)!important;
  border-bottom:1px solid rgba(201,168,76,.25)!important;
  gap:0!important;padding:0!important;
}
.stTabs [data-baseweb="tab"]{
  border-radius:0!important;color:var(--dim)!important;
  font-family:'Cinzel',serif!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:.1em!important;
  padding:12px 16px!important;border-bottom:2px solid transparent!important;
}
.stTabs [aria-selected="true"]{
  background:transparent!important;color:#c9a84c!important;
  border-bottom:2px solid #c9a84c!important;
}
section[data-testid="stSidebar"]{background:var(--bg2)!important;}
hr{border:none!important;border-top:1px solid rgba(201,168,76,.15)!important;margin:12px 0!important;}
.tw{
  border-left:2px solid #1aff8a;background:rgba(26,255,138,.04);
  padding:6px 10px;margin-bottom:4px;border-radius:1px;
  font-family:'JetBrains Mono',monospace;font-size:10px;
}
.tl{
  border-left:2px solid #ff2d55;background:rgba(255,45,85,.04);
  padding:6px 10px;margin-bottom:4px;border-radius:1px;
  font-family:'JetBrains Mono',monospace;font-size:10px;
}
.ai-box{
  background:rgba(201,168,76,.03);
  border:1px solid rgba(201,168,76,.15);
  border-left:2px solid #c9a84c;
  border-radius:1px;padding:16px 20px;margin-bottom:12px;
}
</style>
""", unsafe_allow_html=True)


def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


# ── SESSION STATE ─────────────────────────────────────────────
for k, v in [("ai_key",""), ("ai_feed",[])]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-family:Cinzel,serif;font-weight:900;font-size:1.2rem;'
        'letter-spacing:.2em;color:#fff;margin:12px 0 4px;">ES SIGNAL</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:9px;'
        'color:#1aff8a;margin-bottom:2px;">E-MINI S&amp;P 500 FUTURES</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:9px;'
        'color:#5a5570;margin-bottom:14px;">NinjaTrader: ES 06-25</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Claude API Key"):
        aik = st.text_input(
            "Anthropic key",
            type="password",
            value=st.session_state["ai_key"],
            placeholder="sk-ant-...",
        )
        if aik:
            st.session_state["ai_key"] = aik
        if st.session_state["ai_key"]:
            st.success("Claude connected")
        else:
            st.info("Add key for AI analysis")

    st.divider()
    timeframe = st.selectbox(
        "Timeframe",
        ["15min intraday","1hour","Daily"],
        index=0,
    )
    st.divider()
    st.markdown(
        '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;'
        'color:#c9a84c;margin-bottom:8px;">BACKTEST</div>',
        unsafe_allow_html=True,
    )
    bt_stop   = st.slider("Stop loss (pts)",    4,  50, 12, 1)
    bt_target = st.slider("Target (pts)",       8, 100, 28, 2)
    bt_conf   = st.slider("Min confidence %",  40,  80, 58,  1)
    st.divider()
    st.markdown(
        '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;'
        'color:#c9a84c;margin-bottom:8px;">FILTERS</div>',
        unsafe_allow_html=True,
    )
    rth_only    = st.toggle("RTH Only 9:30am-4pm ET", value=True)
    trend_only  = st.toggle("Trend Only",              value=True)
    of_required = st.toggle("Require Bullish OF",      value=False)
    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

AIKEY = st.session_state["ai_key"]


# ── DATA FETCH ────────────────────────────────────────────────
@st.cache_data(ttl=180)
def fetch_es(tf_str):
    if "15min" in tf_str:
        yf_int, yf_rng = "15m", "60d"
    elif "1hour" in tf_str:
        yf_int, yf_rng = "60m", "60d"
    else:
        yf_int, yf_rng = "1d", "1y"

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/ES=F"
        f"?interval={yf_int}&range={yf_rng}&includePrePost=false"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        d = r.json()
        result    = d["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote     = result["indicators"]["quote"][0]

        raw_c = quote.get("close",  [None]*len(timestamps))
        raw_o = quote.get("open",   [None]*len(timestamps))
        raw_h = quote.get("high",   [None]*len(timestamps))
        raw_l = quote.get("low",    [None]*len(timestamps))
        raw_v = quote.get("volume", [0]*len(timestamps))

        rows = []
        for i, ts in enumerate(timestamps):
            c = raw_c[i]; o = raw_o[i]; h = raw_h[i]; l = raw_l[i]
            v = raw_v[i] or 0
            if c is None or o is None or h is None or l is None:
                continue
            if c < 100:
                continue
            dt = datetime.fromtimestamp(ts, tz=ZoneInfo("UTC"))
            dt = dt.astimezone(ZoneInfo("America/New_York"))
            rows.append({
                "dt":     dt,
                "open":   float(o),
                "high":   float(h),
                "low":    float(l),
                "close":  float(c),
                "volume": float(v),
            })

        if not rows:
            raise ValueError("No valid rows after cleaning")

        df = pd.DataFrame(rows).set_index("dt")
        return df, yf_int

    except Exception as e:
        st.error(f"Failed to load ES=F data: {e}")
        return pd.DataFrame(), "1d"


with st.spinner("Loading ES=F (E-mini S&P 500 futures)..."):
    df_raw, interval = fetch_es(timeframe)

if df_raw.empty:
    st.error("No data. Click Refresh Data or check your connection.")
    st.stop()

if rth_only and interval in ("15m","60m"):
    df_raw = df_raw.between_time("09:30","16:00")
    df_raw = df_raw[df_raw.index.dayofweek < 5]

df_raw = df_raw.copy()
closes  = df_raw["close"].tolist()
opens   = df_raw["open"].tolist()
highs   = df_raw["high"].tolist()
lows    = df_raw["low"].tolist()
vols    = df_raw["volume"].tolist()
dates   = [str(d)[:16] for d in df_raw.index]
N       = len(closes)

if N < 30:
    st.error(f"Only {N} bars loaded — need at least 30. Try Daily timeframe.")
    st.stop()


# ── INDICATORS ────────────────────────────────────────────────
def ema(arr, p):
    if len(arr) < 2:
        return list(arr)
    k = 2.0 / (p + 1)
    out = [arr[0]]
    for v in arr[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi_fn(closes, p=14):
    if len(closes) < p + 2:
        return [50.0] * len(closes)
    d  = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    g  = [max(x, 0.0) for x in d]
    l  = [abs(min(x, 0.0)) for x in d]
    ag = sum(g[:p]) / p
    al = sum(l[:p]) / p
    out = [None] * p
    out.append(100.0 - 100.0 / (1.0 + ag / max(al, 1e-9)))
    for i in range(p, len(d)):
        ag = (ag * (p - 1) + g[i]) / p
        al = (al * (p - 1) + l[i]) / p
        out.append(100.0 - 100.0 / (1.0 + ag / max(al, 1e-9)))
    return [50.0] + out


def macd_fn(closes):
    if len(closes) < 28:
        return [0.0]*len(closes), [0.0]*len(closes), [0.0]*len(closes)
    e12  = ema(closes, 12)
    e26  = ema(closes, 26)
    line = [e12[i] - e26[i] for i in range(len(closes))]
    sig9 = ema(line, 9)
    hist = [line[i] - sig9[i] for i in range(len(closes))]
    return line, sig9, hist


def bb_fn(closes, p=20, k=2.0):
    mid=[None]*(p-1); up=[None]*(p-1); lo=[None]*(p-1); pct=[None]*(p-1)
    for i in range(p-1, len(closes)):
        w  = closes[i-p+1:i+1]
        m  = sum(w) / p
        sd = (sum((v - m)**2 for v in w) / p) ** 0.5
        mid.append(m)
        up.append(m + k * sd)
        lo.append(m - k * sd)
        rng = (up[-1] - lo[-1]) or 1e-9
        pct.append((closes[i] - lo[-1]) / rng)
    return mid, up, lo, pct


def atr_fn(closes, highs, lows, p=14):
    tr = []
    for i in range(1, len(closes)):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i]  - closes[i-1]),
        ))
    if len(tr) < p:
        fallback = closes[0] * 0.004 if closes else 1.0
        return [fallback] * len(closes)
    a = [sum(tr[:p]) / p]
    for v in tr[p:]:
        a.append((a[-1] * (p - 1) + v) / p)
    return [a[0]] * p + a


def stoch_fn(closes, highs, lows, p=14):
    out = [50.0] * (p - 1)
    for i in range(p - 1, len(closes)):
        lo = min(lows[i-p+1:i+1])
        hi = max(highs[i-p+1:i+1])
        rng = hi - lo or 1e-9
        out.append(100.0 * (closes[i] - lo) / rng)
    return out


def vwap_fn(closes, highs, lows, vols):
    out = []
    cum_tv = 0.0
    cum_v  = 0.0
    for i in range(len(closes)):
        tp      = (highs[i] + lows[i] + closes[i]) / 3.0
        cum_tv += tp * max(vols[i], 1.0)
        cum_v  += max(vols[i], 1.0)
        out.append(cum_tv / cum_v)
    return out


def regime_fn(closes, highs, lows):
    if len(closes) < 20:
        return "UNKNOWN"
    e8  = ema(closes, 8)
    e21 = ema(closes, 21)
    if e8[-1] > e21[-1] and closes[-1] > e8[-1]:
        return "UPTREND"
    if e8[-1] < e21[-1] and closes[-1] < e8[-1]:
        return "DOWNTREND"
    av = atr_fn(closes, highs, lows, 14)
    if av[-1] / closes[-1] * 100 > 1.5:
        return "VOLATILE"
    return "RANGING"


# ── ORDER FLOW ────────────────────────────────────────────────
def order_flow_fn(closes, opens, highs, lows, vols):
    of_scores  = []
    obv        = [vols[0]]
    delta      = [0.0]
    cum_delta  = [0.0]
    cd         = 0.0

    for i in range(1, len(closes)):
        rng = highs[i] - lows[i]
        if rng > 0:
            bv = vols[i] * (closes[i] - lows[i])  / rng
            sv = vols[i] * (highs[i] - closes[i]) / rng
        else:
            bv = sv = vols[i] / 2.0
        d = bv - sv
        delta.append(d)
        cd += d
        cum_delta.append(cd)
        if closes[i] > closes[i-1]:
            obv.append(obv[-1] + vols[i])
        elif closes[i] < closes[i-1]:
            obv.append(obv[-1] - vols[i])
        else:
            obv.append(obv[-1])

    vol_ma = []
    for i in range(len(vols)):
        w = vols[max(0, i-20):i+1]
        vol_ma.append(sum(w) / len(w))

    for i in range(len(closes)):
        s = 0.0
        s += 30.0 if delta[i] > 0 else -30.0
        if i >= 5:
            s += 20.0 if obv[i] > obv[i-5] else -20.0
        surge = vols[i] / max(vol_ma[i], 1.0)
        if surge > 1.5:
            s += 20.0 if closes[i] > opens[i] else -20.0
        else:
            s += 10.0 if closes[i] > opens[i] else -10.0
        if i >= 14:
            tp_arr = [(highs[j]+lows[j]+closes[j])/3.0 for j in range(i-14, i+1)]
            mf_arr = [tp_arr[j] * vols[i-14+j] for j in range(15)]
            pmf = sum(mf_arr[j] for j in range(1,15) if tp_arr[j] > tp_arr[j-1])
            nmf = sum(mf_arr[j] for j in range(1,15) if tp_arr[j] < tp_arr[j-1])
            mfi = 100.0 - 100.0 / (1.0 + pmf / max(nmf, 1e-9))
            s  += 15.0 if mfi > 65 else (-15.0 if mfi < 35 else 0.0)
        of_scores.append(max(-100.0, min(100.0, s)))

    return of_scores, obv, delta, cum_delta


# ── STRATEGY DETECTORS ────────────────────────────────────────
def detect_orb(closes, highs, lows, n=5):
    if len(closes) < n + 2:
        return {"sig":None,"rh":None,"rl":None,"type":"NO DATA","score":0}
    rh  = max(highs[-(n+1):-1])
    rl  = min(lows[-(n+1):-1])
    rng = max(rh - rl, 1.0)
    cur = closes[-1]
    if cur > rh:
        return {"sig":"LONG",  "rh":rh,"rl":rl,
                "type":f"ORB BREAK LONG +{cur-rh:.2f}pts",  "score":20}
    if cur < rl:
        return {"sig":"SHORT", "rh":rh,"rl":rl,
                "type":f"ORB BREAK SHORT -{rl-cur:.2f}pts", "score":20}
    pth = rh - cur
    ptl = cur - rl
    if pth < 6:
        return {"sig":"NEAR_L","rh":rh,"rl":rl,
                "type":f"NEAR ORB HIGH {pth:.1f}pts away","score":7}
    if ptl < 6:
        return {"sig":"NEAR_S","rh":rh,"rl":rl,
                "type":f"NEAR ORB LOW {ptl:.1f}pts away","score":7}
    return {"sig":"RANGE","rh":rh,"rl":rl,
            "type":f"INSIDE RANGE {rng:.1f}pts","score":3}


def detect_pdh_pdl(closes, highs, lows):
    if len(closes) < 3:
        return {"sig":None,"pdh":None,"pdl":None,"type":"NO DATA","score":0}
    pdh = highs[-2]
    pdl = lows[-2]
    cur = closes[-1]
    if cur > pdh:
        return {"sig":"LONG",  "pdh":pdh,"pdl":pdl,
                "type":f"PDH BREAK +{cur-pdh:.2f}pts","score":15}
    if cur < pdl:
        return {"sig":"SHORT", "pdh":pdh,"pdl":pdl,
                "type":f"PDL BREAK -{pdl-cur:.2f}pts","score":15}
    rng = pdh - pdl
    return {"sig":"RANGE","pdh":pdh,"pdl":pdl,
            "type":f"Inside PDH/PDL {rng:.1f}pts","score":3}


def detect_gap(closes, opens):
    if len(closes) < 3:
        return {"sig":None,"pts":0,"type":"NO GAP","score":0}
    gp = opens[-1] - closes[-2]
    m3 = closes[-1] - closes[-3]
    if abs(gp) < 3:
        return {"sig":None,"pts":round(gp,2),"type":"NO SIGNIFICANT GAP","score":0}
    if gp > 3 and m3 > 0:
        return {"sig":"LONG",   "pts":round(gp,2),"type":f"GAP UP GO +{gp:.1f}pts",    "score":18}
    if gp < -3 and m3 < 0:
        return {"sig":"SHORT",  "pts":round(gp,2),"type":f"GAP DOWN GO {gp:.1f}pts",   "score":18}
    if gp > 3 and m3 < 0:
        return {"sig":"FADE_S", "pts":round(gp,2),"type":f"GAP UP FADE -{gp:.1f}pts",  "score":12}
    if gp < -3 and m3 > 0:
        return {"sig":"FADE_L", "pts":round(gp,2),"type":f"GAP DOWN FADE {gp:.1f}pts", "score":12}
    return {"sig":None,"pts":round(gp,2),"type":"GAP UNCLEAR","score":0}


def detect_pullback(closes, highs, lows):
    if len(closes) < 15:
        return {"sig":None,"type":"NO DATA","ema8":0,"score":0}
    e8  = ema(closes, 8)
    e21 = ema(closes, 21)
    cur = closes[-1]
    e8v = e8[-1]
    tol = e8v * 0.003
    up   = e8[-2] > e21[-2] and e8[-3] > e21[-3]
    down = e8[-2] < e21[-2] and e8[-3] < e21[-3]
    if up and abs(cur - e8v) <= tol:
        return {"sig":"LONG",  "type":f"PULLBACK TO EMA8 @ {e8v:.2f}","ema8":round(e8v,2),"score":22}
    if down and abs(cur - e8v) <= tol:
        return {"sig":"SHORT", "type":f"PULLBACK TO EMA8 @ {e8v:.2f}","ema8":round(e8v,2),"score":22}
    if up and closes[-2] <= e8[-2] * 1.001 and cur > e8v:
        return {"sig":"LONG",  "type":f"RECLAIM EMA8 @ {e8v:.2f}","ema8":round(e8v,2),"score":14}
    if down and closes[-2] >= e8[-2] * 0.999 and cur < e8v:
        return {"sig":"SHORT", "type":f"RECLAIM EMA8 @ {e8v:.2f}","ema8":round(e8v,2),"score":14}
    return {"sig":None,"type":f"NO SETUP  EMA8 @ {e8v:.2f}","ema8":round(e8v,2),"score":0}


# ── SIGNAL ENGINE ─────────────────────────────────────────────
def compute_signal(closes, opens, highs, lows, vols, of_scores):
    if len(closes) < 22:
        return {
            "sig":"HOLD","conf":30,"why":[],"score":0,
            "entry":closes[-1],"stop":closes[-1]-10,"tp":closes[-1]+20,
            "sl_pts":10,"tp_pts":20,"atr":10.0,"of":0,
            "rsi":50,"stoch":50,"bb_pct":50,"mom":0,"vs":1,
            "vwap":closes[-1],"e8":closes[-1],"e21":closes[-1],"e50":closes[-1],
            "macd_v":0,"macd_s":0,"reg":"UNKNOWN","lp":0,"sp":0,
            "orb":{"sig":None,"type":"--","rh":None,"rl":None},
            "pdhl":{"sig":None,"type":"--","pdh":None,"pdl":None},
            "gap":{"sig":None,"type":"--","pts":0},
            "pull":{"sig":None,"type":"--","ema8":0},
        }

    e8_arr  = ema(closes, 8)
    e21_arr = ema(closes, 21)
    e50_arr = ema(closes, 50) if len(closes) >= 50 else ema(closes, 21)
    e3_arr  = ema(closes, 3)

    rsi_arr = rsi_fn(closes, 14)
    rv = next((v for v in reversed(rsi_arr) if v is not None), 50.0)

    ml, ms, mh = macd_fn(closes)
    _, bu, bl, bp_arr = bb_fn(closes)
    bp = (bp_arr[-1] or 0.5) * 100.0

    atr_arr = atr_fn(closes, highs, lows, 14)
    av = atr_arr[-1]

    stk_arr = stoch_fn(closes, highs, lows, 14)
    sk  = stk_arr[-1]
    skp = stk_arr[-2] if len(stk_arr) > 1 else sk

    vw_arr   = vwap_fn(closes, highs, lows, vols)
    vwap_now = vw_arr[-1]

    m5 = (closes[-1] - closes[-6]) / closes[-6] * 100.0 if len(closes) > 5 else 0.0
    vol_ma = sum(vols[-20:]) / 20.0 if len(vols) >= 20 else (vols[-1] or 1.0)
    vs = vols[-1] / max(vol_ma, 1.0)

    ofs = of_scores[-1] if of_scores else 0.0

    lp = 0; sp = 0; why = []

    # EMA stack
    if e8_arr[-1] > e21_arr[-1] > e50_arr[-1]:
        lp += 6; why.append("EMA 8-21-50 fully bullish")
    elif e8_arr[-1] > e21_arr[-1]:
        lp += 3; why.append("EMA 8 above 21")
    if e8_arr[-1] < e21_arr[-1] < e50_arr[-1]:
        sp += 6; why.append("EMA 8-21-50 fully bearish")
    elif e8_arr[-1] < e21_arr[-1]:
        sp += 3; why.append("EMA 8 below 21")

    # EMA 3x8 cross
    if len(e3_arr) > 1 and e3_arr[-1] > e8_arr[-1] and e3_arr[-2] <= e8_arr[-2]:
        lp += 3; why.append("EMA 3 crossed above EMA 8")
    if len(e3_arr) > 1 and e3_arr[-1] < e8_arr[-1] and e3_arr[-2] >= e8_arr[-2]:
        sp += 3; why.append("EMA 3 crossed below EMA 8")

    # MACD
    if len(ml) > 1 and ml[-1] > ms[-1] and ml[-2] <= ms[-2]:
        lp += 5; why.append("MACD bullish crossover")
    elif ml[-1] > ms[-1]:
        lp += 2
    if len(ml) > 1 and ml[-1] < ms[-1] and ml[-2] >= ms[-2]:
        sp += 5; why.append("MACD bearish crossover")
    elif ml[-1] < ms[-1]:
        sp += 2

    # RSI
    if rv < 28:
        lp += 5; why.append(f"RSI {rv:.0f} deeply oversold")
    elif rv < 40:
        lp += 2; why.append(f"RSI {rv:.0f} oversold")
    if rv > 72:
        sp += 5; why.append(f"RSI {rv:.0f} deeply overbought")
    elif rv > 60:
        sp += 2; why.append(f"RSI {rv:.0f} overbought")

    # Stochastic
    if sk < 15 and sk > skp:
        lp += 3; why.append("Stoch crossed up from oversold")
    if sk > 85 and sk < skp:
        sp += 3; why.append("Stoch crossed down from overbought")

    # Bollinger
    if bp < 8:
        lp += 3; why.append("At lower Bollinger Band")
    if bp > 92:
        sp += 3; why.append("At upper Bollinger Band")

    # VWAP
    vd = closes[-1] - vwap_now
    if 0 < vd < av * 0.5:
        lp += 2; why.append(f"Above VWAP {vwap_now:.2f}")
    elif vd > av * 2:
        sp += 2; why.append(f"Extended {vd:.1f}pts above VWAP")
    if -av * 0.5 < vd < 0:
        sp += 2; why.append(f"Below VWAP {vwap_now:.2f}")
    elif vd < -av * 2:
        lp += 2; why.append(f"Extended below VWAP - bounce potential")

    # Momentum
    if m5 > 0.5:
        lp += 3; why.append(f"Strong momentum +{m5:.1f}%")
    elif m5 > 0.2:
        lp += 1
    if m5 < -0.5:
        sp += 3; why.append(f"Downswing {m5:.1f}%")
    elif m5 < -0.2:
        sp += 1

    # Order flow
    if ofs > 40:
        lp += 5; why.append(f"Order flow strongly bullish ({ofs:.0f})")
    elif ofs > 20:
        lp += 3; why.append(f"Order flow bullish ({ofs:.0f})")
    elif ofs < -40:
        sp += 5; why.append(f"Order flow strongly bearish ({ofs:.0f})")
    elif ofs < -20:
        sp += 3; why.append(f"Order flow bearish ({ofs:.0f})")

    # Volume
    if vs > 1.8:
        if lp > sp:
            lp += 2; why.append(f"Volume surge {vs:.1f}x confirms")
        elif sp > lp:
            sp += 2; why.append(f"Volume surge {vs:.1f}x confirms")

    # Strategies
    orb  = detect_orb(closes, highs, lows)
    pdhl = detect_pdh_pdl(closes, highs, lows)
    gap  = detect_gap(closes, opens)
    pull = detect_pullback(closes, highs, lows)

    for item, key in [(orb,"sig"),(pdhl,"sig"),(gap,"sig"),(pull,"sig")]:
        v = item.get(key,"") or ""
        if "LONG" in v or v == "FADE_L":
            lp += 2
        elif "SHORT" in v or v == "FADE_S":
            sp += 2

    score = lp - sp
    if abs(score) < 4:
        sig_out, conf = "HOLD",        30
    elif score >= 12:
        sig_out, conf = "STRONG BUY",  min(92, 56 + score * 2)
    elif score >= 6:
        sig_out, conf = "BUY",          min(80, 44 + score * 2)
    elif score <= -12:
        sig_out, conf = "STRONG SELL", min(92, 56 + abs(score) * 2)
    elif score <= -6:
        sig_out, conf = "SELL",         min(80, 44 + abs(score) * 2)
    elif rv < 28:
        sig_out, conf = "OVERSOLD",    68
    elif rv > 72:
        sig_out, conf = "OVERBOUGHT",  66
    else:
        sig_out, conf = "HOLD",        30

    is_l   = "BUY" in sig_out or sig_out == "OVERSOLD"
    entry  = closes[-1]
    stop   = round(entry - av * 1.5 if is_l else entry + av * 1.5, 2)
    tp_val = round(entry + av * 3.0 if is_l else entry - av * 3.0, 2)

    return {
        "sig":    sig_out,
        "conf":   conf,
        "score":  score,
        "lp":     lp,
        "sp":     sp,
        "entry":  round(entry, 2),
        "stop":   stop,
        "tp":     tp_val,
        "sl_pts": round(abs(entry - stop),   2),
        "tp_pts": round(abs(tp_val - entry), 2),
        "atr":    round(av,          2),
        "rsi":    round(rv,          1),
        "stoch":  round(sk,          1),
        "bb_pct": round(bp,          1),
        "mom":    round(m5,          2),
        "of":     round(ofs,         1),
        "vwap":   round(vwap_now,    2),
        "vs":     round(vs,          2),
        "e8":     round(e8_arr[-1],  2),
        "e21":    round(e21_arr[-1], 2),
        "e50":    round(e50_arr[-1], 2),
        "macd_v": round(ml[-1],      4),
        "macd_s": round(ms[-1],      4),
        "reg":    regime_fn(closes, highs, lows),
        "why":    why[:8],
        "orb":    orb,
        "pdhl":   pdhl,
        "gap":    gap,
        "pull":   pull,
    }


# ── BACKTEST IN POINTS ────────────────────────────────────────
def run_backtest(closes, opens, highs, lows, vols, of_scores,
                 stop_pts, target_pts, min_conf,
                 use_trend, use_of):
    trades = []
    cum    = [0.0]
    total  = 0.0
    pos    = None

    for i in range(30, len(closes)):
        if pos is not None:
            cur  = closes[i]
            is_l = pos["dir"] == "long"
            sl   = pos["sl"]
            tp   = pos["tp"]
            bars = pos.get("bars", 0) + 1
            hit_tp = (is_l and cur >= tp) or (not is_l and cur <= tp)
            hit_sl = (is_l and cur <= sl) or (not is_l and cur >= sl)
            exit_r = None
            if hit_tp:
                exit_r = "TP"
            elif hit_sl:
                exit_r = "SL"
            elif bars >= 10:
                exit_r = "TIME"
            if exit_r:
                ep    = tp if exit_r == "TP" else sl if exit_r == "SL" else cur
                pts   = (ep - pos["entry"]) if is_l else (pos["entry"] - ep)
                pts   = round(pts, 2)
                total = round(total + pts, 2)
                cum.append(total)
                trades.append({
                    "i":      i,
                    "date":   dates[i][:10] if i < len(dates) else "",
                    "dir":    pos["dir"],
                    "entry":  round(pos["entry"], 2),
                    "exit":   round(ep, 2),
                    "sl":     round(sl, 2),
                    "tp":     round(tp, 2),
                    "pts":    pts,
                    "cum":    total,
                    "reason": exit_r,
                    "conf":   pos["conf"],
                    "bars":   bars,
                })
                pos = None
            else:
                pos["bars"] = bars
                cum.append(total)
                continue

        if pos is not None:
            cum.append(total)
            continue

        try:
            sig = compute_signal(
                closes[:i+1], opens[:i+1],
                highs[:i+1],  lows[:i+1],
                vols[:i+1],   of_scores[:i+1],
            )
        except Exception:
            cum.append(total)
            continue

        if sig["conf"] < min_conf or sig["sig"] == "HOLD":
            cum.append(total)
            continue

        is_l = "BUY" in sig["sig"] or sig["sig"] == "OVERSOLD"
        is_s = "SELL" in sig["sig"] or sig["sig"] == "OVERBOUGHT"
        if not is_l and not is_s:
            cum.append(total)
            continue

        reg = sig.get("reg","UNKNOWN")
        if use_trend:
            if is_l and reg not in ("UPTREND","VOLATILE"):
                cum.append(total); continue
            if is_s and reg not in ("DOWNTREND","VOLATILE"):
                cum.append(total); continue

        if use_of:
            of_v = sig.get("of", 0)
            if is_l and of_v < 15:
                cum.append(total); continue
            if is_s and of_v > -15:
                cum.append(total); continue

        entry = closes[i]
        sl    = entry - stop_pts   if is_l else entry + stop_pts
        tp2   = entry + target_pts if is_l else entry - target_pts
        pos   = {
            "dir":   "long" if is_l else "short",
            "entry": entry,
            "sl":    sl,
            "tp":    tp2,
            "conf":  sig["conf"],
            "bars":  0,
        }
        cum.append(total)

    return trades, cum


# ── CLAUDE AI ─────────────────────────────────────────────────
ES_SYSTEM = (
    "You are Nigel, an expert E-mini S&P 500 futures trader on NinjaTrader with an Apex account. "
    "NinjaTrader symbol: ES 06-25. "
    "Contract specs: $50 per point full ES, 0.25pt tick = $12.50. "
    "MES (Micro): $5 per point, tick = $1.25. "
    "Apex rules: $1,000 daily loss limit, $2,500 trailing drawdown, $3,000 profit target. "
    "Daily $1,000 target: 20 ES points on 1 contract, or 20 points on 10 MES contracts. "
    "Focus on exact ES point levels. Be direct and actionable. Max 350 words."
)


def call_claude(prompt, key):
    if not key:
        return None, "No key"
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         key,
                "anthropic-version": "2023-06-01",
                "Content-Type":      "application/json",
            },
            json={
                "model":      "claude-sonnet-4-5",
                "max_tokens": 900,
                "system":     ES_SYSTEM,
                "messages":   [{"role":"user","content":prompt}],
            },
            timeout=40,
        )
        d = r.json()
        if "content" in d:
            return "".join(b.get("text","") for b in d["content"] if b.get("type")=="text"), None
        err = d.get("error",{})
        return None, f"{err.get('type','error')}: {err.get('message','unknown')}"
    except Exception as e:
        return None, str(e)


def build_context(sig, bt_trades, closes, bt_stop, bt_target):
    net  = bt_trades[-1]["cum"] if bt_trades else 0
    n_t  = len(bt_trades)
    wins = sum(1 for t in bt_trades if t["pts"] > 0)
    wr   = wins / max(n_t, 1) * 100
    orb  = sig.get("orb",  {})
    pdhl = sig.get("pdhl", {})
    gap  = sig.get("gap",  {})
    pull = sig.get("pull", {})
    lines = [
        "CONTRACT: E-mini S&P 500  NinjaTrader: ES 06-25  Yahoo: ES=F",
        f"PRICE: {closes[-1]:,.2f} ES points",
        "",
        f"SIGNAL: {sig['sig']} at {sig['conf']}% confidence",
        f"Entry: {sig['entry']:,.2f}  Stop: {sig['stop']:,.2f} (-{sig['sl_pts']:.1f}pts)  Target: {sig['tp']:,.2f} (+{sig['tp_pts']:.1f}pts)",
        f"RR: {sig['tp_pts'] / max(sig['sl_pts'], 0.1):.1f}:1  ATR: {sig['atr']:.2f}pts",
        "",
        "INDICATORS:",
        f"  Regime: {sig['reg']}",
        f"  RSI(14): {sig['rsi']:.0f}  Stoch: {sig['stoch']:.0f}  BB%: {sig['bb_pct']:.0f}%",
        f"  MACD: {'above' if sig['macd_v'] > sig['macd_s'] else 'below'} signal",
        f"  VWAP: {sig['vwap']:,.2f}  (price {closes[-1] - sig['vwap']:+.2f}pts from VWAP)",
        f"  EMA8: {sig['e8']:,.2f}  EMA21: {sig['e21']:,.2f}  EMA50: {sig['e50']:,.2f}",
        f"  Momentum 5-bar: {sig['mom']:+.2f}%  Order Flow: {sig['of']:+.0f}/100",
        "",
        "STRATEGIES:",
        f"  ORB: {orb.get('type','--')}",
        f"  PDH/PDL: {pdhl.get('type','--')}  PDH:{pdhl.get('pdh',0):.1f} PDL:{pdhl.get('pdl',0):.1f}",
        f"  Gap: {gap.get('type','--')} {gap.get('pts',0):+.1f}pts",
        f"  First Pullback: {pull.get('type','--')}",
        "",
        f"SIGNAL REASONS: {' | '.join(sig.get('why',[])[:5])}",
        "",
        f"BACKTEST ({n_t} trades  stop:{bt_stop}pts  target:{bt_target}pts):",
        f"  Net points: {net:+.2f}  Win rate: {wr:.0f}%",
        f"  ES dollar value: ${net * 50:+,.0f}  MES dollar value: ${net * 5:+,.0f}",
    ]
    return "\n".join(lines)


# ── COMPUTE ───────────────────────────────────────────────────
of_scores_all, obv_all, delta_all, cum_delta_all = order_flow_fn(
    closes, opens, highs, lows, vols
)

sig_now = compute_signal(closes, opens, highs, lows, vols, of_scores_all)

with st.spinner("Running backtest in ES points..."):
    bt_trades, bt_cum = run_backtest(
        closes, opens, highs, lows, vols, of_scores_all,
        bt_stop, bt_target, bt_conf, trend_only, of_required,
    )

# Precompute chart series
e8_s   = ema(closes, 8)
e21_s  = ema(closes, 21)
e50_s  = ema(closes, 50) if N >= 50 else ema(closes, 21)
rsi_s  = [v if v is not None else 50.0 for v in rsi_fn(closes, 14)]
ml_s, ms_s, mh_s = macd_fn(closes)
_, bb_u_s, bb_l_s, _ = bb_fn(closes)
stk_s  = stoch_fn(closes, highs, lows, 14)
vwap_s = vwap_fn(closes, highs, lows, vols)


# ── COLOURS ───────────────────────────────────────────────────
s_now    = sig_now["sig"]
is_l_now = "BUY" in s_now or s_now == "OVERSOLD"
is_s_now = "SELL" in s_now or s_now == "OVERBOUGHT"
sig_color = "#1aff8a" if is_l_now else "#ff2d55" if is_s_now else "#c9a84c"
of_color  = "#1aff8a" if sig_now["of"] > 20 else "#ff2d55" if sig_now["of"] < -20 else "#c9a84c"
reg_color = "#1aff8a" if sig_now["reg"] == "UPTREND" else "#ff2d55" if sig_now["reg"] == "DOWNTREND" else "#c9a84c"
net_bt    = bt_trades[-1]["cum"] if bt_trades else 0.0
net_color = "#1aff8a" if net_bt >= 0 else "#ff2d55"
ai_color  = "#1aff8a" if AIKEY else "#5a5570"


# ── MASTHEAD ──────────────────────────────────────────────────
et_now = datetime.now(ZoneInfo("America/New_York"))
is_rth = (et_now.hour == 9 and et_now.minute >= 30) or (10 <= et_now.hour < 16)
rth_c  = "#1aff8a" if is_rth else "#5a5570"
rth_t  = "RTH OPEN" if is_rth else "OUTSIDE RTH"

h1, h2 = st.columns([2, 1])
with h1:
    st.markdown(
        '<div style="padding:16px 0 10px;">'
        '<div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;'
        'color:#fff;letter-spacing:.1em;">'
        'E-MINI <span style="color:#1aff8a;">S&amp;P 500</span></div>'
        '<div style="font-family:JetBrains Mono,monospace;font-size:10px;'
        'color:#5a5570;margin-top:4px;">'
        f'NinjaTrader: ES 06-25 &nbsp;|&nbsp; ES=F &nbsp;|&nbsp; '
        f'{interval} bars &nbsp;|&nbsp; {N} bars loaded'
        '</div></div>',
        unsafe_allow_html=True,
    )
with h2:
    st.markdown(
        f'<div style="padding:16px 0 10px;text-align:right;">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;">'
        f'ET {et_now.strftime("%H:%M")} &nbsp;|&nbsp; '
        f'<span style="color:{rth_c};">{rth_t}</span></div>'
        f'<div style="font-family:Cinzel,serif;font-size:1.6rem;font-weight:900;'
        f'color:{sig_color};margin-top:3px;">{s_now}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:12px;'
        f'color:#fff;font-weight:700;">ES {closes[-1]:,.2f}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div style="border-bottom:1px solid rgba(201,168,76,.25);margin-bottom:16px;"></div>',
    unsafe_allow_html=True,
)

# Stat bar
sc = st.columns(7)
stat_items = [
    ("ES PRICE",   f"{closes[-1]:,.2f}",                          "#fff"),
    ("SIGNAL",     f"{s_now} {sig_now['conf']}%",                 sig_color),
    ("ENTRY",      f"{sig_now['entry']:,.2f}",                     "#d4cfc0"),
    ("STOP",       f"{sig_now['stop']:,.2f} (-{sig_now['sl_pts']:.0f}pt)", "#ff2d55"),
    ("TARGET",     f"{sig_now['tp']:,.2f} (+{sig_now['tp_pts']:.0f}pt)",   "#1aff8a"),
    ("ORDER FLOW", f"{sig_now['of']:+.0f}",                       of_color),
    ("REGIME",     sig_now["reg"],                                 reg_color),
]
for col, (lbl, val, vc) in zip(sc, stat_items):
    with col:
        st.markdown(
            f'<div class="panel" style="text-align:center;border-top:2px solid {vc};">'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:.95rem;'
            f'font-weight:700;color:{vc};">{val}</div>'
            f'<div style="font-family:Cinzel,serif;font-size:7px;letter-spacing:.1em;'
            f'color:#5a5570;margin-top:3px;">{lbl}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── TABS ──────────────────────────────────────────────────────
t0, t1, t2, t3, t4 = st.tabs([
    "CHART + SIGNAL",
    "ORDER FLOW",
    "BACKTEST POINTS",
    "TRADE LOG",
    "CLAUDE AI",
])


# ── TAB 0: CHART + SIGNAL ─────────────────────────────────────
with t0:
    chart_col, side_col = st.columns([3, 1])

    with side_col:
        # Signal panel
        macd_dir = "above" if sig_now["macd_v"] > sig_now["macd_s"] else "below"
        macd_c   = "#1aff8a" if sig_now["macd_v"] > sig_now["macd_s"] else "#ff2d55"
        rsi_c    = "#1aff8a" if sig_now["rsi"] < 40 else "#ff2d55" if sig_now["rsi"] > 60 else "#fff"
        vd       = closes[-1] - sig_now["vwap"]
        vd_c     = "#1aff8a" if vd > 0 else "#ff2d55"

        st.markdown(
            '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;'
            'color:#c9a84c;margin-bottom:8px;">CURRENT SIGNAL</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="panel" style="border-top:3px solid {sig_color};">'
            f'<div style="font-family:Cinzel,serif;font-size:1.8rem;font-weight:900;'
            f'color:{sig_color};">{s_now}</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;'
            f'color:#5a5570;margin-bottom:10px;">{sig_now["conf"]}% confidence</div>'
            f'<hr>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;line-height:2.3;">'
            f'<div style="color:#5a5570;">Entry</div>'
            f'<div style="color:#fff;font-size:13px;font-weight:700;">{sig_now["entry"]:,.2f}</div>'
            f'<div style="color:#ff2d55;margin-top:4px;">Stop Loss</div>'
            f'<div style="color:#ff2d55;">{sig_now["stop"]:,.2f} &nbsp; -{sig_now["sl_pts"]:.1f}pts</div>'
            f'<div style="color:#1aff8a;margin-top:4px;">Target</div>'
            f'<div style="color:#1aff8a;">{sig_now["tp"]:,.2f} &nbsp; +{sig_now["tp_pts"]:.1f}pts</div>'
            f'</div><hr>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;line-height:2;color:#5a5570;">'
            f'<div>ATR: <span style="color:#c9a84c;">{sig_now["atr"]:.2f}pts</span></div>'
            f'<div>RSI: <span style="color:{rsi_c};">{sig_now["rsi"]:.0f}</span></div>'
            f'<div>Stoch: <span style="color:#fff;">{sig_now["stoch"]:.0f}</span></div>'
            f'<div>BB%: <span style="color:#fff;">{sig_now["bb_pct"]:.0f}%</span></div>'
            f'<div>VWAP: <span style="color:#00c4ff;">{sig_now["vwap"]:,.2f}</span></div>'
            f'<div>vs VWAP: <span style="color:{vd_c};">{vd:+.2f}pts</span></div>'
            f'<div>MACD: <span style="color:{macd_c};">{macd_dir} signal</span></div>'
            f'<div>OF: <span style="color:{of_color};">{sig_now["of"]:+.0f}</span></div>'
            f'<div>Vol: <span style="color:#fff;">{sig_now["vs"]:.1f}x avg</span></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;'
            'color:#c9a84c;margin:10px 0 6px;">WHY</div>',
            unsafe_allow_html=True,
        )
        for w in sig_now.get("why", []):
            st.markdown(
                f'<div style="font-family:Cormorant Garamond,serif;font-style:italic;'
                f'font-size:13px;color:#5a5570;padding:3px 0;'
                f'border-bottom:1px solid #12101e;">{esc(w)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;'
            'color:#c9a84c;margin:10px 0 6px;">STRATEGIES</div>',
            unsafe_allow_html=True,
        )
        for name, item, key in [
            ("ORB",      sig_now["orb"],  "sig"),
            ("PDH/PDL",  sig_now["pdhl"], "sig"),
            ("GAP",      sig_now["gap"],  "sig"),
            ("PULLBACK", sig_now["pull"], "sig"),
        ]:
            sv  = item.get(key, "") or ""
            vc2 = "#1aff8a" if ("LONG" in sv or sv == "FADE_L") else "#ff2d55" if ("SHORT" in sv or sv == "FADE_S") else "#5a5570"
            typ = esc(item.get("type","--")[:26])
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:9px;'
                f'padding:4px 0;border-bottom:1px solid #12101e;'
                f'display:flex;justify-content:space-between;">'
                f'<span style="color:#5a5570;">{name}</span>'
                f'<span style="color:{vc2};">{typ}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with chart_col:
        SHOW   = min(N, 120)
        offset = N - SHOW
        x_show = list(range(SHOW))

        def sl(arr):
            return arr[-SHOW:] if len(arr) >= SHOW else arr

        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.025,
            row_heights=[0.50, 0.17, 0.17, 0.16],
            subplot_titles=[
                f"ES E-mini S&P 500  ({interval})  Actual Futures Points",
                "Order Flow Score",
                "RSI (14)  +  Stochastic (14)",
                "MACD",
            ],
        )

        fig.add_trace(
            go.Candlestick(
                x=x_show,
                open=sl(opens), high=sl(highs),
                low=sl(lows),   close=sl(closes),
                name="ES",
                increasing=dict(line=dict(color="#1aff8a"), fillcolor="rgba(26,255,138,0.55)"),
                decreasing=dict(line=dict(color="#ff2d55"), fillcolor="rgba(255,45,85,0.55)"),
            ),
            row=1, col=1,
        )

        fig.add_trace(go.Scatter(x=x_show, y=sl(e8_s),   mode="lines", name="EMA8",
                                 line=dict(color="#c9a84c",width=1.5,dash="dot")), row=1,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=sl(e21_s),  mode="lines", name="EMA21",
                                 line=dict(color="#a855f7",width=1.5,dash="dot")), row=1,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=sl(e50_s),  mode="lines", name="EMA50",
                                 line=dict(color="#ff2d55",width=1,dash="dot")),   row=1,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=sl(vwap_s), mode="lines", name="VWAP",
                                 line=dict(color="#00c4ff",width=2)),              row=1,col=1)

        bb_u_sl = sl(bb_u_s)
        bb_l_sl = sl(bb_l_s)
        fig.add_trace(go.Scatter(x=x_show, y=bb_u_sl, mode="lines", name="BB Up",
                                 line=dict(color="rgba(201,168,76,.3)",width=1)), row=1,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=bb_l_sl, mode="lines", name="BB Lo",
                                 fill="tonexty", fillcolor="rgba(201,168,76,.04)",
                                 line=dict(color="rgba(201,168,76,.3)",width=1)), row=1,col=1)

        # Key levels
        levels = [
            (sig_now["stop"],  f"SL {sig_now['stop']:,.1f}",    "#ff2d55", "dash"),
            (sig_now["tp"],    f"TP {sig_now['tp']:,.1f}",      "#1aff8a", "dash"),
            (sig_now["entry"], f"Entry {sig_now['entry']:,.1f}", "#c9a84c", "dot"),
            (sig_now["vwap"],  f"VWAP {sig_now['vwap']:,.1f}",  "#00c4ff", "dot"),
        ]
        for y_val, lbl, clr, dash in levels:
            fig.add_hline(y=y_val, line=dict(color=clr,width=1.5,dash=dash),
                          annotation_text=lbl,
                          annotation_font=dict(color=clr, size=10),
                          row=1, col=1)

        orb_d = sig_now["orb"]
        if orb_d.get("rh"):
            fig.add_hline(y=orb_d["rh"], line=dict(color="#a855f7",width=1,dash="dot"),
                          annotation_text=f"ORB H {orb_d['rh']:,.1f}",
                          annotation_font=dict(color="#a855f7",size=9), row=1,col=1)
            fig.add_hline(y=orb_d["rl"], line=dict(color="#a855f7",width=1,dash="dot"),
                          annotation_text=f"ORB L {orb_d['rl']:,.1f}",
                          annotation_font=dict(color="#a855f7",size=9), row=1,col=1)

        pdh_d = sig_now["pdhl"]
        if pdh_d.get("pdh"):
            fig.add_hline(y=pdh_d["pdh"], line=dict(color="#1aff8a",width=1,dash="dot"),
                          annotation_text=f"PDH {pdh_d['pdh']:,.1f}",
                          annotation_font=dict(color="#1aff8a",size=9), row=1,col=1)
            fig.add_hline(y=pdh_d["pdl"], line=dict(color="#ff2d55",width=1,dash="dot"),
                          annotation_text=f"PDL {pdh_d['pdl']:,.1f}",
                          annotation_font=dict(color="#ff2d55",size=9), row=1,col=1)

        if bt_trades:
            wx = [t["i"]-offset for t in bt_trades if t["pts"]>0  and t["i"]>=offset]
            wy = [closes[t["i"]] for t in bt_trades if t["pts"]>0  and t["i"]>=offset]
            lx = [t["i"]-offset for t in bt_trades if t["pts"]<=0 and t["i"]>=offset]
            ly = [closes[t["i"]] for t in bt_trades if t["pts"]<=0 and t["i"]>=offset]
            if wx:
                fig.add_trace(go.Scatter(x=wx,y=wy,mode="markers",name="Win",
                                         marker=dict(color="#1aff8a",size=9,symbol="triangle-up",
                                                     line=dict(color="#fff",width=1))),row=1,col=1)
            if lx:
                fig.add_trace(go.Scatter(x=lx,y=ly,mode="markers",name="Loss",
                                         marker=dict(color="#ff2d55",size=9,symbol="triangle-down",
                                                     line=dict(color="#fff",width=1))),row=1,col=1)

        # OF bars
        of_sl  = sl(of_scores_all)
        of_col = ["#1aff8a" if v > 0 else "#ff2d55" for v in of_sl]
        fig.add_trace(go.Bar(x=x_show, y=of_sl, name="OF Score",
                             marker=dict(color=of_col, opacity=0.7)), row=2,col=1)
        fig.add_hline(y=0,   line=dict(color="#5a5570",width=1),          row=2,col=1)
        fig.add_hline(y=30,  line=dict(color="#1aff8a",width=0.5,dash="dot"), row=2,col=1)
        fig.add_hline(y=-30, line=dict(color="#ff2d55",width=0.5,dash="dot"), row=2,col=1)

        # RSI + Stoch
        fig.add_trace(go.Scatter(x=x_show, y=sl(rsi_s), mode="lines", name="RSI(14)",
                                 line=dict(color="#a855f7",width=2)), row=3,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=sl(stk_s), mode="lines", name="Stoch(14)",
                                 line=dict(color="#00c4ff",width=1.5)), row=3,col=1)
        for yv, cv in [(70,"#ff2d55"),(30,"#1aff8a"),(50,"#3a3550")]:
            fig.add_hline(y=yv, line=dict(color=cv,width=1,dash="dot"), row=3,col=1)

        # MACD
        mh_sl  = sl(mh_s)
        mh_col = ["#1aff8a" if v > 0 else "#ff2d55" for v in mh_sl]
        fig.add_trace(go.Bar(x=x_show, y=mh_sl, name="MACD Hist",
                             marker=dict(color=mh_col, opacity=0.5)), row=4,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=sl(ml_s), mode="lines", name="MACD",
                                 line=dict(color="#c9a84c",width=1.5)), row=4,col=1)
        fig.add_trace(go.Scatter(x=x_show, y=sl(ms_s), mode="lines", name="Signal",
                                 line=dict(color="#00c4ff",width=1)),   row=4,col=1)
        fig.add_hline(y=0, line=dict(color="#5a5570",width=1), row=4,col=1)

        step   = max(1, SHOW // 10)
        tick_v = list(range(0, SHOW, step))
        tick_t = [dates[min(offset + v, N-1)][:10] for v in tick_v]

        fig.update_layout(
            height=780,
            template="plotly_dark",
            paper_bgcolor="#05040a",
            plot_bgcolor="#09080f",
            margin=dict(l=0, r=80, t=30, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.03,
                        font=dict(family="JetBrains Mono", size=8)),
            font=dict(family="JetBrains Mono", size=9, color="#5a5570"),
        )
        for ri in range(1, 5):
            fig.update_xaxes(gridcolor="#12101e", tickvals=tick_v,
                             ticktext=tick_t, row=ri, col=1)
            fig.update_yaxes(gridcolor="#12101e", row=ri, col=1)
        fig.update_yaxes(title_text="ES Points", row=1, col=1)
        fig.update_yaxes(title_text="OF",        row=2, col=1)
        fig.update_yaxes(title_text="RSI",       row=3, col=1)
        fig.update_yaxes(title_text="MACD",      row=4, col=1)

        st.plotly_chart(fig, use_container_width=True, key="main_chart")

        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#5a5570;'
            'padding:7px 12px;background:#09080f;border:1px solid #12101e;border-radius:1px;">'
            'Cyan = VWAP &nbsp;|&nbsp; Gold dashes = EMA8 &nbsp;|&nbsp; '
            'Purple dashes = EMA21 &nbsp;|&nbsp; Purple horizontal = ORB levels &nbsp;|&nbsp; '
            'Green triangles up = backtest wins &nbsp;|&nbsp; Red triangles down = losses'
            '</div>',
            unsafe_allow_html=True,
        )


# ── TAB 1: ORDER FLOW ─────────────────────────────────────────
with t1:
    st.markdown(
        '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;'
        'color:#c9a84c;margin-bottom:12px;">ORDER FLOW - ES FUTURES</div>',
        unsafe_allow_html=True,
    )

    of_now    = of_scores_all[-1]
    delta_now = delta_all[-1]
    obv_dir   = "RISING" if len(obv_all) > 5 and obv_all[-1] > obv_all[-5] else "FALLING"
    of_c_now  = "#1aff8a" if of_now > 20 else "#ff2d55" if of_now < -20 else "#c9a84c"
    obv_c_now = "#1aff8a" if obv_dir == "RISING" else "#ff2d55"
    d_c_now   = "#1aff8a" if delta_now > 0 else "#ff2d55"

    of_cols = st.columns(4)
    of_data = [
        ("OF SCORE",  f"{of_now:+.0f}/100",       of_c_now),
        ("VOL DELTA", f"{delta_now/1e6:.1f}M",     d_c_now),
        ("OBV TREND", obv_dir,                     obv_c_now),
        ("VOL SURGE", f"{sig_now['vs']:.1f}x avg", "#1aff8a" if sig_now["vs"] > 1.5 else "#5a5570"),
    ]
    for col, (lbl, val, vc) in zip(of_cols, of_data):
        with col:
            st.markdown(
                f'<div class="panel" style="text-align:center;border-top:2px solid {vc};">'
                f'<div style="font-family:Cinzel,serif;font-size:1.4rem;font-weight:900;color:{vc};">{val}</div>'
                f'<div style="font-family:Cinzel,serif;font-size:8px;letter-spacing:.1em;color:#5a5570;">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    x_all = list(range(N))
    fig_of = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
        row_heights=[0.34, 0.33, 0.33],
        subplot_titles=[
            "Cumulative Volume Delta",
            "On-Balance Volume (OBV)",
            "Order Flow Score",
        ],
    )
    fig_of.add_trace(
        go.Scatter(x=x_all, y=cum_delta_all, mode="lines",
                   line=dict(color="#1aff8a",width=2),
                   fill="tozeroy", fillcolor="rgba(26,255,138,0.06)",
                   name="Cum Delta"),
        row=1, col=1,
    )
    fig_of.add_hline(y=0, line=dict(color="#5a5570",width=1), row=1,col=1)

    obv_max  = max(abs(max(obv_all)), 1)
    obv_norm = [o / obv_max * 100 for o in obv_all]
    fig_of.add_trace(
        go.Scatter(x=x_all, y=obv_norm, mode="lines",
                   line=dict(color="#00c4ff",width=2), name="OBV"),
        row=2, col=1,
    )
    fig_of.add_hline(y=0, line=dict(color="#5a5570",width=1), row=2,col=1)

    of_bar_c = ["#1aff8a" if v > 0 else "#ff2d55" for v in of_scores_all]
    fig_of.add_trace(
        go.Bar(x=x_all, y=of_scores_all, name="OF Score",
               marker=dict(color=of_bar_c, opacity=0.7)),
        row=3, col=1,
    )
    fig_of.add_hline(y=30,  line=dict(color="#1aff8a",width=1,dash="dot"), row=3,col=1)
    fig_of.add_hline(y=-30, line=dict(color="#ff2d55",width=1,dash="dot"), row=3,col=1)
    fig_of.add_hline(y=0,   line=dict(color="#5a5570",width=1),            row=3,col=1)

    fig_of.update_layout(
        height=500, template="plotly_dark",
        paper_bgcolor="#05040a", plot_bgcolor="#09080f",
        margin=dict(l=0,r=0,t=30,b=0), showlegend=False,
        font=dict(family="JetBrains Mono",size=9,color="#5a5570"),
    )
    for ri in range(1, 4):
        fig_of.update_xaxes(gridcolor="#12101e", row=ri,col=1)
        fig_of.update_yaxes(gridcolor="#12101e", row=ri,col=1)
    st.plotly_chart(fig_of, use_container_width=True, key="of_chart")

    if of_now > 40:
        interp = "STRONG BUY PRESSURE - institutions accumulating. Take longs on pullbacks to VWAP or EMA8."; ic = "#1aff8a"
    elif of_now > 15:
        interp = "BUY PRESSURE - order flow bullish. Favor long setups. Avoid shorts unless very strong."; ic = "#1aff8a"
    elif of_now < -40:
        interp = "STRONG SELL PRESSURE - distribution in progress. Short any bounce to VWAP."; ic = "#ff2d55"
    elif of_now < -15:
        interp = "SELL PRESSURE - order flow bearish. Avoid longs. Short on bounces."; ic = "#ff2d55"
    else:
        interp = "BALANCED FLOW - wait for order flow to pick a side before entering."; ic = "#c9a84c"

    st.markdown(
        f'<div style="border-left:3px solid {ic};padding:12px 16px;'
        f'background:rgba(201,168,76,.02);border-radius:1px;'
        f'font-family:Cormorant Garamond,serif;font-size:14px;color:#d4cfc0;">'
        f'{interp}</div>',
        unsafe_allow_html=True,
    )


# ── TAB 2: BACKTEST POINTS ────────────────────────────────────
with t2:
    st.markdown(
        '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;'
        'color:#c9a84c;margin-bottom:4px;">BACKTEST - ES POINTS</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;'
        f'color:#5a5570;margin-bottom:14px;">'
        f'Stop: {bt_stop}pts &nbsp;|&nbsp; Target: {bt_target}pts &nbsp;|&nbsp; '
        f'Min conf: {bt_conf}% &nbsp;|&nbsp; '
        f'Trend: {"ON" if trend_only else "OFF"} &nbsp;|&nbsp; '
        f'OF: {"ON" if of_required else "OFF"}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not bt_trades:
        st.warning("No trades generated. Lower min confidence or disable filters in sidebar.")
    else:
        df_bt  = pd.DataFrame(bt_trades)
        wins   = df_bt[df_bt["pts"] > 0]
        losses = df_bt[df_bt["pts"] <= 0]
        n_t    = len(df_bt)
        n_w    = len(wins)
        n_l    = len(losses)
        wr     = n_w / n_t * 100
        net    = df_bt["pts"].sum()
        aw     = wins["pts"].mean()   if not wins.empty   else 0.0
        al     = losses["pts"].mean() if not losses.empty else 0.0
        wsum   = wins["pts"].sum()    if not wins.empty   else 0.0
        lsum   = losses["pts"].sum()  if not losses.empty else 0.0
        pf     = abs(wsum / lsum) if lsum != 0 else 99.0
        exp    = (wr / 100) * aw + (1 - wr / 100) * al
        best   = df_bt["pts"].max()
        worst  = df_bt["pts"].min()
        nc     = "#1aff8a" if net >= 0 else "#ff2d55"

        def stat_card(col, lbl, val, vc):
            with col:
                st.markdown(
                    f'<div class="panel" style="text-align:center;margin-bottom:6px;">'
                    f'<div style="font-family:Cinzel,serif;font-size:1.1rem;font-weight:900;color:{vc};">{val}</div>'
                    f'<div style="font-family:Cinzel,serif;font-size:7px;letter-spacing:.1em;color:#5a5570;">{lbl}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        r1c1,r1c2,r1c3,r1c4 = st.columns(4)
        stat_card(r1c1,"NET POINTS",    f"{net:+.2f}",           nc)
        stat_card(r1c2,"WIN RATE",      f"{wr:.1f}%",            "#1aff8a" if wr>=55 else "#c9a84c")
        stat_card(r1c3,"PROFIT FACTOR", f"{min(pf,99):.2f}",    "#1aff8a" if pf>=1.5 else "#c9a84c")
        stat_card(r1c4,"EXPECTANCY",    f"{exp:+.2f}pts",        "#1aff8a" if exp>0 else "#ff2d55")

        r2c1,r2c2,r2c3,r2c4 = st.columns(4)
        stat_card(r2c1,"TRADES",     str(n_t),                "#d4cfc0")
        stat_card(r2c2,"WINS",       str(n_w),                "#1aff8a")
        stat_card(r2c3,"LOSSES",     str(n_l),                "#ff2d55")
        stat_card(r2c4,"RR RATIO",   f"{bt_target/bt_stop:.1f}:1","#c9a84c")

        r3c1,r3c2,r3c3,r3c4 = st.columns(4)
        stat_card(r3c1,"AVG WIN",     f"+{aw:.2f}pts",   "#1aff8a")
        stat_card(r3c2,"AVG LOSS",    f"{al:.2f}pts",    "#ff2d55")
        stat_card(r3c3,"BEST TRADE",  f"+{best:.2f}pts", "#1aff8a")
        stat_card(r3c4,"WORST TRADE", f"{worst:.2f}pts", "#ff2d55")

        r4c1,r4c2,r4c3,r4c4 = st.columns(4)
        stat_card(r4c1,"POINTS WON",   f"+{wsum:.1f}",       "#1aff8a")
        stat_card(r4c2,"POINTS LOST",  f"{lsum:.1f}",        "#ff2d55")
        stat_card(r4c3,"ES $ VALUE",   f"${net*50:+,.0f}",   nc)
        stat_card(r4c4,"MES $ VALUE",  f"${net*5:+,.0f}",    nc)

        # Cumulative points chart
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            y=bt_cum, mode="lines",
            line=dict(color="#c9a84c",width=2.5),
            fill="tozeroy", fillcolor="rgba(201,168,76,.07)",
            name="Cumulative Points",
        ))
        wx2 = [t["i"] for t in bt_trades if t["pts"] > 0]
        wy2 = [t["cum"] for t in bt_trades if t["pts"] > 0]
        lx2 = [t["i"] for t in bt_trades if t["pts"] <= 0]
        ly2 = [t["cum"] for t in bt_trades if t["pts"] <= 0]
        if wx2:
            fig_cum.add_trace(go.Scatter(x=wx2,y=wy2,mode="markers",name="Win",
                                          marker=dict(color="#1aff8a",size=7,symbol="circle")))
        if lx2:
            fig_cum.add_trace(go.Scatter(x=lx2,y=ly2,mode="markers",name="Loss",
                                          marker=dict(color="#ff2d55",size=7,symbol="circle")))
        fig_cum.add_hline(y=0, line=dict(color="#5a5570",width=1,dash="dot"))
        fig_cum.update_layout(
            height=250, template="plotly_dark",
            paper_bgcolor="#05040a", plot_bgcolor="#09080f",
            margin=dict(l=0,r=0,t=10,b=0),
            yaxis_title="Cumulative ES Points",
            legend=dict(orientation="h",y=1.05,font=dict(family="JetBrains Mono",size=9)),
            font=dict(family="JetBrains Mono",size=9,color="#5a5570"),
        )
        fig_cum.update_xaxes(gridcolor="#12101e")
        fig_cum.update_yaxes(gridcolor="#12101e")
        st.plotly_chart(fig_cum, use_container_width=True, key="cum_chart")

        # Distribution
        all_pts = [t["pts"] for t in bt_trades]
        fig_d = go.Figure()
        fig_d.add_trace(go.Histogram(
            x=[p for p in all_pts if p > 0],  name="Wins",
            marker=dict(color="#1aff8a",opacity=0.7), nbinsx=15))
        fig_d.add_trace(go.Histogram(
            x=[p for p in all_pts if p <= 0], name="Losses",
            marker=dict(color="#ff2d55",opacity=0.7), nbinsx=15))
        fig_d.add_vline(x=0,   line=dict(color="#5a5570",width=1))
        fig_d.add_vline(x=exp, line=dict(color="#c9a84c",width=1,dash="dash"),
                        annotation_text=f"Exp {exp:+.1f}pts",
                        annotation_font=dict(color="#c9a84c",size=9))
        fig_d.update_layout(
            height=170, template="plotly_dark",
            paper_bgcolor="#05040a", plot_bgcolor="#09080f",
            margin=dict(l=0,r=0,t=10,b=0), barmode="overlay",
            xaxis_title="Points per Trade",
            legend=dict(orientation="h",y=1.05,font=dict(family="JetBrains Mono",size=9)),
            font=dict(family="JetBrains Mono",size=9,color="#5a5570"),
        )
        fig_d.update_xaxes(gridcolor="#12101e")
        fig_d.update_yaxes(gridcolor="#12101e")
        st.plotly_chart(fig_d, use_container_width=True, key="dist_chart")


# ── TAB 3: TRADE LOG ──────────────────────────────────────────
with t3:
    if not bt_trades:
        st.info("No trades yet. Adjust settings in the sidebar.")
    else:
        df_log = pd.DataFrame([{
            "Date":      t["date"],
            "Direction": t["dir"].upper(),
            "Entry ES":  f"{t['entry']:.2f}",
            "Exit ES":   f"{t['exit']:.2f}",
            "Stop":      f"{t['sl']:.2f}",
            "Target":    f"{t['tp']:.2f}",
            "Points":    round(t["pts"], 2),
            "Result":    "WIN" if t["pts"] > 0 else "LOSS",
            "Exit Via":  t["reason"],
            "Bars":      t["bars"],
            "Conf%":     t["conf"],
            "Cum Pts":   round(t["cum"], 2),
        } for t in reversed(bt_trades)])

        st.dataframe(
            df_log.style
            .format({"Points":"{:+.2f}", "Cum Pts":"{:+.2f}"})
            .map(
                lambda v: "color:#1aff8a;font-weight:700" if isinstance(v,str) and v=="WIN"
                else "color:#ff2d55;font-weight:700" if isinstance(v,str) and v=="LOSS" else "",
                subset=["Result"],
            )
            .map(
                lambda v: "color:#1aff8a" if isinstance(v,(int,float)) and v>0
                else "color:#ff2d55" if isinstance(v,(int,float)) and v<0 else "",
                subset=["Points","Cum Pts"],
            ),
            use_container_width=True,
            hide_index=True,
        )

        bc, wc = st.columns(2)
        with bc:
            st.markdown(
                '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;'
                'color:#1aff8a;margin:8px 0 6px;">BEST 5</div>',
                unsafe_allow_html=True,
            )
            for t in sorted(bt_trades, key=lambda x: x["pts"], reverse=True)[:5]:
                st.markdown(
                    f'<div class="tw">'
                    f'<span style="color:#1aff8a;font-weight:700;">+{t["pts"]:.2f}pts</span>'
                    f' &nbsp; {t["date"]} &nbsp; {t["dir"].upper()}'
                    f' &nbsp; {t["entry"]:.1f} to {t["exit"]:.1f}'
                    f' &nbsp; {t["reason"]} in {t["bars"]}bars'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with wc:
            st.markdown(
                '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;'
                'color:#ff2d55;margin:8px 0 6px;">WORST 5</div>',
                unsafe_allow_html=True,
            )
            for t in sorted(bt_trades, key=lambda x: x["pts"])[:5]:
                st.markdown(
                    f'<div class="tl">'
                    f'<span style="color:#ff2d55;font-weight:700;">{t["pts"]:.2f}pts</span>'
                    f' &nbsp; {t["date"]} &nbsp; {t["dir"].upper()}'
                    f' &nbsp; {t["entry"]:.1f} to {t["exit"]:.1f}'
                    f' &nbsp; {t["reason"]} in {t["bars"]}bars'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        csv_buf = io.BytesIO()
        df_log.to_csv(csv_buf, index=False)
        st.download_button(
            "Download Trade Log CSV",
            data=csv_buf.getvalue(),
            file_name=f"es_trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )


# ── TAB 4: CLAUDE AI ──────────────────────────────────────────
with t4:
    st.markdown(
        '<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;'
        'color:#c9a84c;margin-bottom:8px;">CLAUDE AI - ANTHROPIC</div>',
        unsafe_allow_html=True,
    )

    if not AIKEY:
        st.warning("Add your Claude API key in the sidebar to enable AI analysis.")
    else:
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:10px;'
            'color:#1aff8a;margin-bottom:14px;">Claude connected via Anthropic API</div>',
            unsafe_allow_html=True,
        )

    qc = st.columns(4)
    question = None
    with qc[0]:
        if st.button("Signal Brief"):
            question = (
                "Analyze the current ES signal. Is it high probability? "
                "Give me exact entry, stop, and target in ES points. "
                "How many MES contracts at 1% risk on a $50K Apex account? "
                "What is my max dollar loss and dollar target on that position?"
            )
    with qc[1]:
        if st.button("ORB Setup"):
            question = (
                "Analyze the Opening Range Breakout on ES. "
                "Is there a valid 8am or 9:30am ORB breakout? "
                "What are the exact ES point levels for entry, stop, and target? "
                "Is order flow confirming the breakout direction?"
            )
    with qc[2]:
        if st.button("Point Target"):
            question = (
                "I need $1,000 today on ES or MES. "
                "How many points do I need on each? "
                "Is today's ATR big enough to hit $1,000 on one trade? "
                "What is the best current setup to get there?"
            )
    with qc[3]:
        if st.button("Risk Check"):
            question = (
                "Audit my ES trading risk right now. "
                "Is the stop placement correct given current ATR? "
                "Is order flow confirming the signal? "
                "Should I be trading now or waiting?"
            )

    cq = st.text_area("Custom question:", key="es_q", height=70)
    if st.button("Ask Claude", type="primary"):
        question = cq.strip() or question

    if question:
        if not AIKEY:
            st.warning("Add a Claude API key in the sidebar.")
        else:
            with st.spinner("Claude is analyzing ES..."):
                ctx  = build_context(sig_now, bt_trades, closes, bt_stop, bt_target)
                full = f"ES Futures Context:\n{ctx}\n\nQuestion: {question}"
                resp, err = call_claude(full, AIKEY)
            if err:
                st.error(f"Claude error: {err}")
            elif resp:
                st.session_state["ai_feed"].insert(0, {
                    "q":     question,
                    "a":     resp,
                    "ts":    datetime.now().strftime("%H:%M:%S"),
                    "price": f"{closes[-1]:,.2f}",
                    "sig":   sig_now["sig"],
                    "conf":  sig_now["conf"],
                })
                st.session_state["ai_feed"] = st.session_state["ai_feed"][:8]

    feed_ai = st.session_state.get("ai_feed", [])

    if not feed_ai and AIKEY:
        st.markdown(
            '<div style="font-family:Cormorant Garamond,serif;font-style:italic;'
            'font-size:14px;color:#5a5570;padding:20px 0;">'
            'Press a button above to get Claude analysis of the current ES signal.'
            '</div>',
            unsafe_allow_html=True,
        )

    for entry in feed_ai:
        sc2 = "#1aff8a" if "BUY" in entry["sig"] else "#ff2d55" if "SELL" in entry["sig"] else "#c9a84c"
        ans = esc(entry["a"]).replace("\n", "<br>")
        st.markdown(
            f'<div class="ai-box">'
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-bottom:10px;">'
            f'<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.15em;'
            f'color:#c9a84c;">CLAUDE &nbsp; {entry["ts"]}</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#5a5570;">'
            f'ES {entry["price"]} &nbsp;|&nbsp; '
            f'<span style="color:{sc2};font-weight:700;">{entry["sig"]} {entry["conf"]}%</span>'
            f'</div></div>'
            f'<div style="font-family:Cormorant Garamond,serif;font-style:italic;'
            f'font-size:12px;color:#5a5570;margin-bottom:10px;padding-bottom:8px;'
            f'border-bottom:1px solid #12101e;">Q: {esc(entry["q"])}</div>'
            f'<div style="font-family:Cormorant Garamond,serif;font-size:14px;'
            f'line-height:1.8;color:#d4cfc0;">{ans}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if feed_ai:
        if st.button("Clear AI History"):
            st.session_state["ai_feed"] = []
            st.rerun()


# ── FOOTER ────────────────────────────────────────────────────
n_bt   = len(bt_trades)
wr_bt  = sum(1 for t in bt_trades if t["pts"] > 0) / max(n_bt, 1) * 100
ai_str = "CLAUDE ON" if AIKEY else "NO CLAUDE"
ai_c   = "#1aff8a" if AIKEY else "#5a5570"

st.markdown(
    f'<div style="position:fixed;bottom:0;left:0;right:0;background:#09080f;'
    f'border-top:1px solid rgba(201,168,76,.15);padding:7px 24px;'
    f'display:flex;justify-content:space-between;align-items:center;'
    f'font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;z-index:999;">'
    f'<div>ES=F &nbsp;|&nbsp; NinjaTrader ES 06-25 &nbsp;|&nbsp; Yahoo Finance (no API key)</div>'
    f'<div>Signal: <span style="color:{sig_color};font-weight:700;">'
    f'{s_now} {sig_now["conf"]}%</span>'
    f' &nbsp;|&nbsp; ES: <span style="color:#fff;font-weight:700;">{closes[-1]:,.2f}</span>'
    f' &nbsp;|&nbsp; OF: <span style="color:{of_color};">{sig_now["of"]:+.0f}</span></div>'
    f'<div>BT: <span style="color:{net_color};font-weight:700;">{net_bt:+.2f}pts</span>'
    f' &nbsp;|&nbsp; {n_bt} trades &nbsp;|&nbsp; {wr_bt:.0f}% WR'
    f' &nbsp;|&nbsp; <span style="color:{ai_c};">{ai_str}</span></div>'
    f'</div>'
    f'<div style="height:36px;"></div>',
    unsafe_allow_html=True,
)
