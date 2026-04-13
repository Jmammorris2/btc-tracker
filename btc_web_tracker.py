import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json, math, random
from collections import defaultdict

st.set_page_config(
    page_title="Alpha Trader Pro",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Syne:wght@400;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
.main-title { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800;
              background: linear-gradient(90deg, #00ff88, #00d4ff, #7B61FF); -webkit-background-clip: text;
              -webkit-text-fill-color: transparent; margin-bottom: 0; letter-spacing:-0.02em; }
.subtitle { color:#3a3a5a; font-size:13px; margin-bottom:16px; font-family:'JetBrains Mono',monospace; }
.signal-badge { display:inline-block; border-radius:4px; padding:2px 10px; font-size:11px; font-weight:700;
                letter-spacing:.05em; font-family:'JetBrains Mono',monospace; }
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
.metric-val { font-family:'JetBrains Mono',monospace; font-size:1.3rem; font-weight:700; }
.metric-lbl { font-size:10px; color:#666; text-transform:uppercase; letter-spacing:.08em; margin-top:2px; }
.pos-long  { background:#001a0a; border-left:3px solid #00ff88; border-radius:8px; padding:10px 14px; font-size:12px; margin-bottom:6px; }
.pos-short { background:#1a0000; border-left:3px solid #ff4444; border-radius:8px; padding:10px 14px; font-size:12px; margin-bottom:6px; }
.pos-none  { background:#111; border-radius:8px; padding:10px 14px; font-size:12px; color:#555; margin-bottom:6px; }
.bt-stat   { background:#0a0a1a; border:1px solid #1a1a2e; border-radius:8px; padding:10px; text-align:center; }
.bt-val    { font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:700; }
.bt-lbl    { font-size:10px; color:#555; margin-top:2px; }
.grand-signal { background: linear-gradient(135deg, #0a0a1e, #0d1a0a); border:2px solid #00ff88;
                border-radius:16px; padding:20px 24px; margin-bottom:16px; }
.grand-signal-buy { border-color:#00ff88; background: linear-gradient(135deg, #001a0a, #0a0a1e); }
.grand-signal-sell { border-color:#ff4444; background: linear-gradient(135deg, #1a0000, #0a0a1e); }
.grand-signal-hold { border-color:#555; background: linear-gradient(135deg, #111, #0a0a1e); }
.poly-card { background:#0d0d1a; border:1px solid #1a1a3a; border-radius:10px; padding:12px 16px; margin-bottom:8px; }
.poly-bar-wrap { background:#1a1a2e; border-radius:4px; height:8px; margin-top:6px; overflow:hidden; }
.stTabs [data-baseweb="tab-list"] { background:#080818; border-radius:10px; padding:4px; }
.stTabs [data-baseweb="tab"] { border-radius:8px; color:#666; font-size:13px; }
.stTabs [aria-selected="true"] { background:#1a1a3a; color:#fff; }
.session-badge { display:inline-block; border-radius:6px; padding:3px 12px; font-size:12px; font-weight:700; margin-right:6px; color:#fff; }
.winner-crown { font-size:18px; margin-right:4px; }
.rank-1 { color:#ffd700; }
.rank-2 { color:#c0c0c0; }
.rank-3 { color:#cd7f32; }
</style>
""", unsafe_allow_html=True)

# ─── KEY GATE ─────────────────────────────────────────────────────────────────
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
    st.info("Add keys to `.streamlit/secrets.toml` to skip this screen.")
    st.stop()

# ─── 100-TRADER ENSEMBLE SETUP ─────────────────────────────────────────────────
ENSEMBLE_CONFIGS = [
    # (name, risk_pct, rr, rsi_range, strong_only, bb_break, rsi_extreme)
    ("Macro Maya",    0.008, 2.5, (35,65), True,  False, False),
    ("Momentum Mike", 0.015, 2.0, (20,80), False, True,  False),
    ("Scalp Sam",     0.005, 1.5, (25,75), False, False, True),
    ("Trend Tina",    0.010, 3.0, (30,70), True,  False, False),
    ("Contrarian Carl",0.012,2.0, (20,80), False, False, True),
    ("Breakout Bob",  0.018, 2.5, (25,75), False, True,  False),
    ("Patient Pete",  0.006, 4.0, (40,60), True,  False, False),
    ("Aggressive Ana", 0.020,1.8, (20,80), False, False, False),
    ("Conservative Kim",0.004,3.0,(38,62), True, False, False),
    ("Volatility Vic", 0.014,2.2,(22,78), False, True,  False),
]
# Expand to 100 by varying parameters
def expand_to_100():
    configs = []
    base_names = ["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta","Iota","Kappa"]
    styles = ["Momentum","Reversal","Breakout","Scalp","Swing","Position","Day","Macro","Quant","Hybrid"]
    for i in range(100):
        base = ENSEMBLE_CONFIGS[i % len(ENSEMBLE_CONFIGS)]
        noise = 1 + (i % 7 - 3) * 0.05
        risk  = min(0.025, max(0.003, base[1] * noise))
        rr    = max(1.2, base[2] + (i % 5 - 2) * 0.2)
        lo    = max(15, base[3][0] + (i % 6 - 3) * 3)
        hi    = min(85, base[3][1] + (i % 6 - 3) * 3)
        name  = f"{styles[i%10]} {base_names[i%10]}-{i+1}"
        configs.append({
            "name": name, "risk_pct": round(risk,4), "rr": round(rr,2),
            "rsi_range": (lo,hi), "strong_only": base[4], "bb_break": base[5],
            "rsi_extreme": base[6],
        })
    return configs

ALL_100_CONFIGS = expand_to_100()

# ─── SESSION STATE ─────────────────────────────────────────────────────────────
def make_trader(name, emoji, style, desc, risk, rr, filters, sources):
    return dict(name=name, emoji=emoji, style=style, desc=desc,
                risk_pct=risk, rr=rr, signal_filters=filters, data_sources=sources,
                balance=25000.0, peak=25000.0, trades=[], open_pos=None,
                history=[25000.0], win_streak=0, loss_streak=0)

if "traders" not in st.session_state:
    st.session_state["traders"] = [
        make_trader("Macro Maya","🌍","Multi-source macro + technicals",
            "Waits for RSI, MACD, MA, Bollinger AND volume all aligned. Checks fear/greed + on-chain.",
            0.008,2.5,{"rsi_range":(35,65),"need_macd":True,"need_ma":True,"need_vol":True,"strong_only":True},
            ["price","volume","rsi","macd","bb","fear_greed","on_chain"]),
        make_trader("Momentum Mike","🚀","Momentum + breakout specialist",
            "Trades breakouts above Bollinger bands. Uses ATR for stop sizing. Loves volatility.",
            0.015,2.0,{"rsi_range":(20,80),"need_macd":False,"need_ma":True,"need_vol":False,"strong_only":False,"bb_break":True},
            ["price","rsi","macd","bb","atr","volume"]),
        make_trader("Scalp Sam","⚡","Fast RSI + VWAP scalper",
            "Tight stops, high frequency. Enters on RSI extremes confirmed by VWAP position.",
            0.005,1.5,{"rsi_range":(25,75),"need_macd":False,"need_ma":False,"need_vol":False,"strong_only":False,"rsi_extreme":True},
            ["price","rsi","vwap","stoch","cci"]),
        make_trader("Trend Tina","📈","Trend-following swing trader",
            "Waits for confluence of EMA50, RSI 40-60 zone and MACD alignment. Bigger targets.",
            0.010,3.0,{"rsi_range":(30,70),"need_macd":True,"need_ma":True,"need_vol":False,"strong_only":True},
            ["price","rsi","macd","ema50","volume"]),
        make_trader("Contrarian Carl","🔄","Counter-trend reversal hunter",
            "Buys extreme oversold, sells extreme overbought. Fades momentum at extremes.",
            0.012,2.0,{"rsi_range":(20,80),"need_macd":False,"need_ma":False,"need_vol":False,"strong_only":False,"rsi_extreme":True},
            ["price","rsi","stoch","cci","bb"]),
    ]

if "notes" not in st.session_state:
    st.session_state["notes"] = []
if "last_ai" not in st.session_state:
    st.session_state["last_ai"] = 0.0
if "bt_results" not in st.session_state:
    st.session_state["bt_results"] = {}
if "ensemble_results" not in st.session_state:
    st.session_state["ensemble_results"] = {}
if "grand_strategy" not in st.session_state:
    st.session_state["grand_strategy"] = {}
if "last_ensemble_run" not in st.session_state:
    st.session_state["last_ensemble_run"] = 0.0

TRADERS = st.session_state["traders"]

MARKETS = {
    "BTC":  {"label":"BTC / USD",    "poly_ticker":"X:BTCUSD","cg_id":"bitcoin",  "stop_mult":0.025,"crypto":True, "lot":1.0,  "color":"#f0a500"},
    "ETH":  {"label":"ETH / USD",    "poly_ticker":"X:ETHUSD","cg_id":"ethereum", "stop_mult":0.030,"crypto":True, "lot":1.0,  "color":"#627eea"},
    "NQ":   {"label":"NASDAQ (QQQ)", "poly_ticker":"QQQ",     "cg_id":None,       "stop_mult":0.010,"crypto":False,"lot":100.0,"color":"#378add"},
    "GOLD": {"label":"Gold (GLD)",   "poly_ticker":"GLD",     "cg_id":None,       "stop_mult":0.008,"crypto":False,"lot":100.0,"color":"#ba7517"},
    "SPY":  {"label":"S&P 500 (SPY)","poly_ticker":"SPY",     "cg_id":None,       "stop_mult":0.008,"crypto":False,"lot":100.0,"color":"#22c55e"},
}

# ─── DATA FETCHERS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_cg_chart(cg_id, days=90):
    try:
        d = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily", timeout=15).json()
        prices  = [p[1] for p in d["prices"]]
        volumes = [v[1] for v in d.get("total_volumes",[])]
        dates   = [pd.Timestamp(p[0],unit="ms") for p in d["prices"]]
        return pd.DataFrame({"close":prices,"volume":volumes},index=dates)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_polygon_ohlcv(ticker, poly_key, days=90):
    try:
        to_d = datetime.today().strftime("%Y-%m-%d")
        fr_d = (datetime.today()-timedelta(days=days)).strftime("%Y-%m-%d")
        url  = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
                f"{fr_d}/{to_d}?adjusted=true&sort=asc&limit={days}&apiKey={poly_key}")
        d = requests.get(url,timeout=15).json()
        if "results" not in d or len(d["results"])<5:
            return pd.DataFrame()
        df = pd.DataFrame(d["results"])
        df.index = pd.to_datetime(df["t"],unit="ms")
        df = df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})
        return df[["open","high","low","close","volume"]]
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d = requests.get("https://api.alternative.me/fng/?limit=10",timeout=10).json()
        data = d.get("data",[])
        return {"value":int(data[0]["value"]),"label":data[0]["value_classification"],
                "history":[int(x["value"]) for x in data[:10]]}
    except:
        return {"value":50,"label":"Neutral","history":[50]*10}

@st.cache_data(ttl=600)
def fetch_on_chain():
    result = {}
    try:
        r  = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin",timeout=10).json()
        md = r.get("market_data",{})
        result["market_cap"]       = md.get("market_cap",{}).get("usd",0)
        result["volume_24h"]       = md.get("total_volume",{}).get("usd",0)
        result["price_change_7d"]  = md.get("price_change_percentage_7d",0)
        result["price_change_30d"] = md.get("price_change_percentage_30d",0)
        result["ath"]              = md.get("ath",{}).get("usd",0)
        result["ath_change_pct"]   = md.get("ath_change_percentage",{}).get("usd",0)
        result["circulating"]      = md.get("circulating_supply",0)
        result["dev_score"]        = r.get("developer_score",0)
        result["community_score"]  = r.get("community_score",0)
    except:
        pass
    return result

@st.cache_data(ttl=300)
def fetch_polymarket_data():
    """Fetch Polymarket prediction market data for today's top markets."""
    try:
        url = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=20&order=volume&ascending=false"
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
        markets = []
        for m in data[:15]:
            try:
                question  = m.get("question","")
                volume    = float(m.get("volume","0") or 0)
                liquidity = float(m.get("liquidity","0") or 0)
                # outcomes_prices
                prices_raw = m.get("outcomePrices","[]")
                outcomes   = m.get("outcomes","[]")
                if isinstance(prices_raw, str):
                    prices = json.loads(prices_raw)
                else:
                    prices = prices_raw
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)
                if not outcomes or not prices:
                    continue
                pairs = list(zip(outcomes, [float(p) for p in prices]))
                pairs.sort(key=lambda x: x[1], reverse=True)
                markets.append({
                    "question": question,
                    "volume":   volume,
                    "liquidity":liquidity,
                    "top_outcome": pairs[0][0] if pairs else "Yes",
                    "top_pct":     round(pairs[0][1]*100,1) if pairs else 50.0,
                    "pairs":       pairs[:3],
                    "url":         m.get("url",""),
                })
            except:
                continue
        return markets
    except:
        return []

# ─── INDICATORS ────────────────────────────────────────────────────────────────
def add_indicators(df):
    if df.empty or len(df)<26:
        return df
    df = df.copy()
    df["ema8"]   = df["close"].ewm(span=8, adjust=False).mean()
    df["ema21"]  = df["close"].ewm(span=21,adjust=False).mean()
    df["ema50"]  = df["close"].ewm(span=50,adjust=False).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    e12 = df["close"].ewm(span=12,adjust=False).mean()
    e26 = df["close"].ewm(span=26,adjust=False).mean()
    df["macd"]        = e12-e26
    df["macd_signal"] = df["macd"].ewm(span=9,adjust=False).mean()
    df["macd_hist"]   = df["macd"]-df["macd_signal"]
    delta = df["close"].diff()
    gain  = delta.where(delta>0,0.0).rolling(14).mean()
    loss  = (-delta.where(delta<0,0.0)).rolling(14).mean().replace(0,1e-10)
    df["rsi"] = 100-(100/(1+gain/loss))
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"]+2*df["bb_std"]
    df["bb_lower"] = df["bb_mid"]-2*df["bb_std"]
    df["bb_pct"]   = (df["close"]-df["bb_lower"])/(df["bb_upper"]-df["bb_lower"])
    if "high" in df.columns and "low" in df.columns:
        hl = df["high"]-df["low"]
        hc = (df["high"]-df["close"].shift()).abs()
        lc = (df["low"] -df["close"].shift()).abs()
        df["atr"] = pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(14).mean()
    else:
        df["atr"] = df["close"]*0.02
    lo14 = df["close"].rolling(14).min()
    hi14 = df["close"].rolling(14).max()
    df["stoch_k"] = 100*(df["close"]-lo14)/(hi14-lo14+1e-10)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    if "high" in df.columns and "low" in df.columns:
        tp = (df["high"]+df["low"]+df["close"])/3
        df["cci"] = (tp-tp.rolling(20).mean())/(0.015*tp.rolling(20).std()+1e-10)
    else:
        df["cci"] = (df["close"]-df["close"].rolling(20).mean())/(df["close"].rolling(20).std()+1e-10)
    if "volume" in df.columns:
        df["vwap"]      = (df["close"]*df["volume"]).rolling(20).sum()/df["volume"].rolling(20).sum()
        df["vol_ma"]    = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"]/df["vol_ma"]
    bull_ema      = df["ema8"]>df["ema21"]
    bull_macd     = df["macd"]>df["macd_signal"]
    macd_cross_up = bull_macd & ~bull_macd.shift(1).fillna(False)
    macd_cross_dn = ~bull_macd & bull_macd.shift(1).fillna(False)
    rsi_ok_buy    = df["rsi"].between(35,68)
    rsi_ok_sell   = df["rsi"]>32
    df["signal"] = np.where(
        bull_ema & macd_cross_up & rsi_ok_buy,  "STRONG BUY",
        np.where(bull_ema & bull_macd & df["rsi"].between(38,65), "BUY",
        np.where(~bull_ema & macd_cross_dn & rsi_ok_sell, "STRONG SELL",
        np.where(~bull_ema & ~bull_macd & (df["rsi"]>38), "SELL",
        np.where(df["rsi"]<28, "OVERSOLD",
        np.where(df["rsi"]>74, "OVERBOUGHT","HOLD"))))))
    return df

# ─── BACKTESTING ENGINE ────────────────────────────────────────────────────────
def run_backtest(df, trader_config, label="Strategy"):
    if df.empty or "signal" not in df.columns or len(df)<30:
        return {"error":"Not enough data"}
    df = df.dropna(subset=["close","signal","rsi"]).copy()
    capital    = 10000.0; cash=capital; position=0.0; entry_px=0.0
    trades=[]; equity=[]
    filters    = trader_config.get("signal_filters",{}) or trader_config
    stop_pct   = 0.025
    target_mult= trader_config.get("rr",2.0)

    def check_entry(row):
        s  = row["signal"]
        r  = row.get("rsi",50)
        rng= filters.get("rsi_range",(20,80))
        if not (rng[0]<=r<=rng[1]): return None
        if filters.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"):
            return None
        if filters.get("bb_break") and "bb_pct" in row:
            bp = row["bb_pct"]
            if s in ("BUY","STRONG BUY") and bp>0.8: return "long"
            if s in ("SELL","STRONG SELL") and bp<0.2: return "short"
        if filters.get("rsi_extreme"):
            if r<32 and s!="OVERBOUGHT": return "long"
            if r>68 and s!="OVERSOLD":  return "short"
        if s in ("BUY","STRONG BUY","OVERSOLD"): return "long"
        if s in ("SELL","STRONG SELL","OVERBOUGHT"): return "short"
        return None

    for i in range(1,len(df)):
        row   = df.iloc[i]
        price = row["close"]
        val   = cash+position*price
        equity.append({"date":df.index[i],"equity":val})
        if position>0 and entry_px>0:
            sl=entry_px*(1-stop_pct); tp=entry_px*(1+stop_pct*target_mult)
            if price<=sl or price>=tp:
                pnl=(price-entry_px)*position; cash+=position*price
                trades.append({"type":"Long","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"TP" if price>=tp else "SL"})
                position=0; entry_px=0; continue
        if position<0 and entry_px>0:
            sl=entry_px*(1+stop_pct); tp=entry_px*(1-stop_pct*target_mult)
            if price>=sl or price<=tp:
                pnl=(entry_px-price)*abs(position); cash+=abs(position)*price
                trades.append({"type":"Short","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"TP" if price<=tp else "SL"})
                position=0; entry_px=0; continue
        prev_row=df.iloc[i-1]
        if position==0:
            direction=check_entry(prev_row)
            if direction=="long":
                units=cash*0.95/price; position=units; cash-=units*price; entry_px=price
            elif direction=="short":
                units=cash*0.95/price; position=-units; cash+=units*price; entry_px=price
        else:
            cur_dir=check_entry(prev_row)
            if position>0 and cur_dir=="short":
                pnl=(price-entry_px)*position; cash+=position*price
                trades.append({"type":"Long","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"Signal flip"})
                position=0; entry_px=0
            elif position<0 and cur_dir=="long":
                pnl=(entry_px-price)*abs(position); cash+=abs(position)*price
                trades.append({"type":"Short","entry":entry_px,"exit":price,"pnl":pnl,
                                "date":df.index[i],"reason":"Signal flip"})
                position=0; entry_px=0
    if position!=0:
        fp=df.iloc[-1]["close"]
        pnl=(fp-entry_px)*position if position>0 else (entry_px-fp)*abs(position)
        cash+=abs(position)*fp
        trades.append({"type":"Open@end","entry":entry_px,"exit":fp,"pnl":pnl,
                       "date":df.index[-1],"reason":"End"})
    if not trades:
        return {"error":"No trades generated"}
    eq_df=pd.DataFrame(equity); tdf=pd.DataFrame(trades)
    wins=tdf[tdf["pnl"]>0]; losses=tdf[tdf["pnl"]<=0]
    total_ret=(cash-capital)/capital*100
    bh_ret=(df.iloc[-1]["close"]-df.iloc[0]["close"])/df.iloc[0]["close"]*100
    win_rate=len(wins)/len(tdf)*100 if len(tdf) else 0
    profit_factor=abs(wins["pnl"].sum()/losses["pnl"].sum()) if not losses.empty and losses["pnl"].sum()!=0 else 99.0
    avg_win=wins["pnl"].mean() if not wins.empty else 0
    avg_loss=losses["pnl"].mean() if not losses.empty else 0
    sharpe=0.0
    if len(eq_df)>1:
        eq_df["ret"]=eq_df["equity"].pct_change()
        mu=eq_df["ret"].mean(); sig=eq_df["ret"].std()
        sharpe=(mu/sig*np.sqrt(252)) if sig>0 else 0.0
    roll_max=eq_df["equity"].cummax()
    max_dd=((eq_df["equity"]-roll_max)/roll_max*100).min()
    calmar=total_ret/abs(max_dd) if max_dd!=0 else 0
    streaks=[]; cur=0
    for p in tdf["pnl"]:
        cur=max(1,cur+1) if p>0 else min(-1,cur-1)
        streaks.append(cur)
    return {
        "total_return":round(total_ret,2),"bh_return":round(bh_ret,2),
        "win_rate":round(win_rate,1),"total_trades":len(tdf),"wins":len(wins),
        "losses":len(losses),"avg_win":round(avg_win,2),"avg_loss":round(avg_loss,2),
        "profit_factor":round(min(profit_factor,99.0),2),"max_drawdown":round(max_dd,2),
        "sharpe":round(sharpe,2),"calmar":round(calmar,2),
        "max_win_streak":max(streaks) if streaks else 0,
        "max_loss_streak":abs(min(streaks)) if streaks else 0,
        "equity_curve":eq_df,"trade_list":tdf,"final_equity":round(cash,2),"label":label,
    }

# ─── 100-TRADER ENSEMBLE BACKTESTER ──────────────────────────────────────────
def run_ensemble_backtest(df_map, days=90):
    """Run all 100 trader configs on each market and synthesize grand strategy."""
    results_by_market = {}
    all_returns = []
    
    for mk, df in df_map.items():
        if df.empty:
            continue
        market_results = []
        for cfg in ALL_100_CONFIGS:
            filters = {
                "rsi_range": cfg["rsi_range"],
                "strong_only": cfg["strong_only"],
                "bb_break": cfg["bb_break"],
                "rsi_extreme": cfg["rsi_extreme"],
            }
            bt = run_backtest(df, {"signal_filters": filters, "rr": cfg["rr"]}, label=cfg["name"])
            if "error" not in bt:
                market_results.append({
                    "name": cfg["name"],
                    "return": bt["total_return"],
                    "win_rate": bt["win_rate"],
                    "sharpe": bt["sharpe"],
                    "max_dd": bt["max_drawdown"],
                    "profit_factor": bt["profit_factor"],
                    "trades": bt["total_trades"],
                    "score": bt["sharpe"] * (bt["win_rate"]/50) * max(0.1, 1-(abs(bt["max_drawdown"])/50)),
                    "rsi_range": cfg["rsi_range"],
                    "rr": cfg["rr"],
                    "bb_break": cfg["bb_break"],
                    "rsi_extreme": cfg["rsi_extreme"],
                    "strong_only": cfg["strong_only"],
                    "equity_curve": bt.get("equity_curve"),
                })
                all_returns.append(bt["total_return"])
        market_results.sort(key=lambda x: x["score"], reverse=True)
        results_by_market[mk] = market_results

    # Synthesize grand strategy from top performers
    grand = synthesize_grand_strategy(results_by_market, df_map)
    return results_by_market, grand

def synthesize_grand_strategy(results_by_market, df_map):
    """Aggregate top-20 winners per market into a consensus grand strategy."""
    grand = {}
    for mk, results in results_by_market.items():
        if not results:
            continue
        top20 = results[:20]
        # Consensus parameters
        avg_rsi_lo = np.mean([r["rsi_range"][0] for r in top20])
        avg_rsi_hi = np.mean([r["rsi_range"][1] for r in top20])
        avg_rr     = np.mean([r["rr"] for r in top20])
        use_bb     = sum(1 for r in top20 if r["bb_break"]) > 10
        use_extreme= sum(1 for r in top20 if r["rsi_extreme"]) > 10
        use_strong = sum(1 for r in top20 if r["strong_only"]) > 10
        avg_ret    = np.mean([r["return"] for r in top20])
        avg_sharpe = np.mean([r["sharpe"] for r in top20])
        avg_wr     = np.mean([r["win_rate"] for r in top20])
        best       = top20[0]
        
        # Current signal from market
        df = df_map.get(mk, pd.DataFrame())
        current_signal = "HOLD"; current_conf = 50; current_rsi = 50
        if not df.empty and "rsi" in df.columns and len(df)>0:
            row = df.iloc[-1]
            current_signal = str(row.get("signal","HOLD"))
            current_rsi    = float(row.get("rsi",50))
            rsi_lo = int(avg_rsi_lo); rsi_hi = int(avg_rsi_hi)
            in_range = rsi_lo <= current_rsi <= rsi_hi
            if in_range and current_signal in ("STRONG BUY","BUY","OVERSOLD"):
                if use_strong and current_signal not in ("STRONG BUY","OVERSOLD"):
                    current_conf = 45
                else:
                    current_conf = 78
            elif in_range and current_signal in ("STRONG SELL","SELL","OVERBOUGHT"):
                if use_strong and current_signal not in ("STRONG SELL","OVERBOUGHT"):
                    current_conf = 45
                else:
                    current_conf = 76
            else:
                current_conf = 35

        grand[mk] = {
            "consensus_rsi_range": (round(avg_rsi_lo), round(avg_rsi_hi)),
            "consensus_rr":        round(avg_rr, 2),
            "use_bb_break":        use_bb,
            "use_rsi_extreme":     use_extreme,
            "use_strong_only":     use_strong,
            "avg_return":          round(avg_ret, 2),
            "avg_sharpe":          round(avg_sharpe, 2),
            "avg_win_rate":        round(avg_wr, 1),
            "best_trader":         best["name"],
            "best_return":         round(best["return"], 2),
            "current_signal":      current_signal,
            "current_conf":        current_conf,
            "current_rsi":         round(current_rsi, 1),
            "n_winners":           len(top20),
        }
    return grand

# ─── SESSION BEST TRADERS ─────────────────────────────────────────────────────
def get_session_best(grand_strategy, active_sessions):
    """Determine which traders perform best for the current trading session."""
    session = active_sessions[0] if active_sessions else "Off-hours"
    session_weights = {
        "Tokyo":    {"BTC":1.2,"ETH":1.2,"NQ":0.6,"GOLD":0.8,"SPY":0.5},
        "London":   {"BTC":1.1,"ETH":1.0,"NQ":0.8,"GOLD":1.3,"SPY":0.8},
        "New York": {"BTC":1.0,"ETH":0.9,"NQ":1.3,"GOLD":1.1,"SPY":1.3},
        "Overlap":  {"BTC":1.2,"ETH":1.1,"NQ":1.2,"GOLD":1.2,"SPY":1.2},
        "Off-hours":{"BTC":0.8,"ETH":0.8,"NQ":0.3,"GOLD":0.5,"SPY":0.3},
    }
    weights = session_weights.get(session, session_weights["Off-hours"])
    scored = {}
    for mk, gs in grand_strategy.items():
        w = weights.get(mk, 1.0)
        scored[mk] = {
            "score": gs["avg_sharpe"] * w,
            "signal": gs["current_signal"],
            "conf": round(gs["current_conf"] * w),
            "rr": gs["consensus_rr"],
            "rsi": gs["current_rsi"],
            "avg_return": gs["avg_return"],
            "best_trader": gs["best_trader"],
        }
    return scored, session

# ─── CHART BUILDERS ───────────────────────────────────────────────────────────
def safe_vol_colors(df):
    """Safely build volume bar colors without list comprehension mismatches."""
    colors = []
    closes = df["close"].tolist()
    if "open" in df.columns:
        opens = df["open"].tolist()
    else:
        opens = closes  # fallback: compare close to itself (all green)
    for i in range(len(closes)):
        c = closes[i]
        o = opens[i] if i < len(opens) else c
        try:
            colors.append("#00ff8866" if float(c) >= float(o) else "#ff444466")
        except:
            colors.append("#00ff8866")
    return colors

def build_advanced_chart(df, title, color="#00ff88", show_signals=True, bt=None):
    if df.empty:
        return None
    rows=4; heights=[0.5,0.18,0.18,0.14]
    fig = make_subplots(rows=rows,cols=1,shared_xaxes=True,row_heights=heights,
                        vertical_spacing=0.03,subplot_titles=["","MACD","RSI","Volume"])
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index,y=df["bb_upper"],
            line=dict(color="rgba(100,100,200,0.3)",width=1),showlegend=False,name="BB Upper"),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["bb_lower"],
            line=dict(color="rgba(100,100,200,0.3)",width=1),
            fill="tonexty",fillcolor="rgba(100,100,200,0.05)",showlegend=False,name="BB Lower"),row=1,col=1)
    if "open" in df.columns and "high" in df.columns:
        fig.add_trace(go.Candlestick(x=df.index,open=df["open"],high=df["high"],
            low=df["low"],close=df["close"],name="Price",
            increasing_line_color="#00ff88",decreasing_line_color="#ff4444",
            increasing_fillcolor="#00ff8833",decreasing_fillcolor="#ff444433"),row=1,col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index,y=df["close"],name="Price",
            line=dict(color=color,width=2)),row=1,col=1)
    for col_name,mc,lbl in [("ema8","#5DCAA5","EMA8"),("ema21","#ED93B1","EMA21"),("ema50","#F59E0B","EMA50")]:
        if col_name in df.columns:
            fig.add_trace(go.Scatter(x=df.index,y=df[col_name],name=lbl,
                line=dict(color=mc,width=1.2,dash="dot")),row=1,col=1)
    if show_signals and "signal" in df.columns:
        buys  = df[df["signal"].isin(["BUY","STRONG BUY","OVERSOLD"])]
        sells = df[df["signal"].isin(["SELL","STRONG SELL","OVERBOUGHT"])]
        sb    = df[df["signal"]=="STRONG BUY"]
        ss    = df[df["signal"]=="STRONG SELL"]
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys.index,y=buys["close"],mode="markers",
                marker=dict(symbol="triangle-up",size=10,color="#00ff88"),name="Buy"),row=1,col=1)
        if not sb.empty:
            fig.add_trace(go.Scatter(x=sb.index,y=sb["close"],mode="markers",
                marker=dict(symbol="star",size=15,color="#00ffcc"),name="Strong Buy"),row=1,col=1)
        if not sells.empty:
            fig.add_trace(go.Scatter(x=sells.index,y=sells["close"],mode="markers",
                marker=dict(symbol="triangle-down",size=10,color="#ff4444"),name="Sell"),row=1,col=1)
        if not ss.empty:
            fig.add_trace(go.Scatter(x=ss.index,y=ss["close"],mode="markers",
                marker=dict(symbol="x",size=12,color="#ff0000"),name="Strong Sell"),row=1,col=1)
    if bt and "trade_list" in bt and not bt["trade_list"].empty:
        for _,tr in bt["trade_list"].iterrows():
            col_t="#00ff88" if tr["pnl"]>0 else "#ff4444"
            try:
                fig.add_trace(go.Scatter(x=[tr["date"]],y=[tr["entry"]],mode="markers",
                    marker=dict(symbol="circle",size=8,color=col_t,opacity=0.7),
                    showlegend=False,name="Trade"),row=1,col=1)
            except:
                pass
    if "macd" in df.columns:
        bar_cols=["#00ff88" if v>=0 else "#ff4444" for v in df["macd_hist"].fillna(0)]
        fig.add_trace(go.Bar(x=df.index,y=df["macd_hist"],marker_color=bar_cols,
            name="MACD Hist",showlegend=False),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["macd"],
            line=dict(color=color,width=1.5),name="MACD"),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["macd_signal"],
            line=dict(color="#ED93B1",width=1.5),name="Signal"),row=2,col=1)
    if "rsi" in df.columns:
        fig.add_trace(go.Scatter(x=df.index,y=df["rsi"],
            line=dict(color="#7C3AED",width=2),name="RSI"),row=3,col=1)
        fig.add_hline(y=70,line=dict(color="#ff4444",width=1,dash="dash"),row=3,col=1)
        fig.add_hline(y=30,line=dict(color="#00ff88",width=1,dash="dash"),row=3,col=1)
        fig.add_hline(y=50,line=dict(color="#555",width=1,dash="dot"),row=3,col=1)
    if "volume" in df.columns:
        vol_colors = safe_vol_colors(df)
        fig.add_trace(go.Bar(x=df.index,y=df["volume"],
            marker_color=vol_colors,name="Volume",showlegend=False),row=4,col=1)
        if "vol_ma" in df.columns:
            fig.add_trace(go.Scatter(x=df.index,y=df["vol_ma"],
                line=dict(color="#F59E0B",width=1),name="Vol MA"),row=4,col=1)
    fig.update_layout(height=800,template="plotly_dark",
        title=dict(text=title,font=dict(size=14,color="#ccc")),
        paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=10)),
        margin=dict(l=0,r=0,t=50,b=0))
    fig.update_xaxes(gridcolor="#1a1a2e",zerolinecolor="#1a1a2e")
    fig.update_yaxes(gridcolor="#1a1a2e",zerolinecolor="#1a1a2e")
    return fig

def build_equity_chart(bt_results):
    fig=go.Figure()
    colors={"Macro Maya":"#00ff88","Momentum Mike":"#00d4ff","Scalp Sam":"#f0a500",
            "Trend Tina":"#7B61FF","Contrarian Carl":"#ff6b6b"}
    for name,bt in bt_results.items():
        if bt and "equity_curve" in bt:
            eq=bt["equity_curve"]
            c=colors.get(name,"#fff")
            final_val=eq["equity"].iloc[-1] if not eq.empty else 10000
            ret=(final_val-10000)/10000*100
            fig.add_trace(go.Scatter(x=eq["date"],y=eq["equity"],
                name=f"{name} ({ret:+.1f}%)",line=dict(color=c,width=2)))
    fig.add_hline(y=10000,line=dict(color="#555",width=1,dash="dot"),annotation_text="$10k start")
    fig.update_layout(height=350,template="plotly_dark",
        title="Equity curves — all traders vs $10k start",
        paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
        legend=dict(orientation="h",yanchor="bottom",y=1.02),
        xaxis_title="Date",yaxis_title="Portfolio ($)",margin=dict(l=0,r=0,t=50,b=0))
    return fig

def build_monthly_returns(bt):
    if not bt or "equity_curve" not in bt: return None
    eq=bt["equity_curve"].copy()
    if eq.empty: return None
    eq["month"]=pd.to_datetime(eq["date"]).dt.to_period("M")
    monthly=eq.groupby("month")["equity"].last()
    monthly_ret=monthly.pct_change()*100
    colors=["#00ff88" if v>=0 else "#ff4444" for v in monthly_ret.fillna(0)]
    fig=go.Figure(go.Bar(x=[str(m) for m in monthly_ret.index],y=monthly_ret.fillna(0),
        marker_color=colors,text=[f"{v:+.1f}%" for v in monthly_ret.fillna(0)],
        textposition="outside",textfont=dict(size=9,color="#aaa")))
    fig.add_hline(y=0,line=dict(color="#555",width=1))
    fig.update_layout(height=220,template="plotly_dark",title="Monthly returns",
        paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",yaxis_title="Return %",
        margin=dict(l=0,r=0,t=40,b=0))
    return fig

def build_drawdown_chart(bt):
    if not bt or "equity_curve" not in bt: return None
    eq=bt["equity_curve"].copy()
    if eq.empty: return None
    roll_max=eq["equity"].cummax()
    dd=(eq["equity"]-roll_max)/roll_max*100
    fig=go.Figure(go.Scatter(x=eq["date"],y=dd,fill="tozeroy",
        fillcolor="rgba(255,68,68,0.15)",line=dict(color="#ff4444",width=1.5),name="Drawdown %"))
    fig.update_layout(height=180,template="plotly_dark",title="Drawdown %",
        paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",yaxis_title="%",
        margin=dict(l=0,r=0,t=40,b=0))
    return fig

def build_ensemble_leaderboard(results_by_market, mk):
    if mk not in results_by_market: return None
    top = results_by_market[mk][:20]
    names=[r["name"] for r in top]
    returns=[r["return"] for r in top]
    sharpes=[r["sharpe"] for r in top]
    colors=["#00ff88" if r>=0 else "#ff4444" for r in returns]
    fig=make_subplots(rows=1,cols=2,subplot_titles=["Top 20 Returns %","Top 20 Sharpe"])
    fig.add_trace(go.Bar(x=returns,y=names,orientation="h",marker_color=colors,
        name="Return %",text=[f"{r:+.1f}%" for r in returns],textposition="auto"),row=1,col=1)
    fig.add_trace(go.Bar(x=sharpes,y=names,orientation="h",
        marker_color=["#7B61FF" if s>=0 else "#ff6b6b" for s in sharpes],
        name="Sharpe",text=[f"{s:.2f}" for s in sharpes],textposition="auto"),row=1,col=2)
    fig.update_layout(height=500,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
        showlegend=False,margin=dict(l=0,r=0,t=40,b=0))
    return fig

# ─── SIGNAL ENGINE ────────────────────────────────────────────────────────────
def get_market_signal(df, fg=None, on_chain=None):
    if df.empty or "rsi" not in df.columns:
        return {"signal":"HOLD","conf":50,"rsi":50,"ma_bull":False,"macd_bull":False,"price":0}
    row=df.iloc[-1]; price=float(row["close"]); rsi_v=float(row.get("rsi",50))
    sig_v=str(row.get("signal","HOLD")); ma_b=bool(row.get("ema8",0)>row.get("ema21",0))
    macd_b=bool(row.get("macd",0)>row.get("macd_signal",0))
    conf=50
    if sig_v=="STRONG BUY":   conf=82
    elif sig_v=="BUY":         conf=66
    elif sig_v=="STRONG SELL": conf=80
    elif sig_v=="SELL":        conf=64
    elif sig_v=="OVERSOLD":    conf=74
    elif sig_v=="OVERBOUGHT":  conf=72
    if fg:
        fg_val=fg.get("value",50)
        if sig_v in ("BUY","STRONG BUY","OVERSOLD") and fg_val<30: conf=min(95,conf+8)
        if sig_v in ("SELL","STRONG SELL","OVERBOUGHT") and fg_val>75: conf=min(95,conf+8)
    return {"signal":sig_v,"conf":conf,"rsi":rsi_v,"ma_bull":ma_b,"macd_bull":macd_b,
            "price":price,"bb_pct":float(row.get("bb_pct",0.5)),
            "atr":float(row.get("atr",price*0.02)),
            "stoch_k":float(row.get("stoch_k",50)),"cci":float(row.get("cci",0))}

# ─── TRADER SIMULATION ─────────────────────────────────────────────────────────
def simulate_all_traders(market_signals):
    for tr in TRADERS:
        if tr["open_pos"]:
            pos=tr["open_pos"]; mk=pos["market"]; sig=market_signals.get(mk)
            if not sig: continue
            p=sig["price"]; is_long=pos["dir"]=="long"
            hit_sl=(is_long and p<=pos["stop"]) or (not is_long and p>=pos["stop"])
            hit_tp=(is_long and p>=pos["tp"])   or (not is_long and p<=pos["tp"])
            if hit_sl or hit_tp:
                pnl=(p-pos["entry"])*pos["units"] if is_long else (pos["entry"]-p)*pos["units"]
                tr["balance"]=max(0,tr["balance"]+pnl); tr["peak"]=max(tr["peak"],tr["balance"])
                result="win" if pnl>0 else "loss"
                tr["trades"].append(dict(market=mk,dir=pos["dir"],entry=pos["entry"],exit=p,
                    pnl=round(pnl,2),result=result,reason="TP" if hit_tp else "SL",
                    time=datetime.now().strftime("%H:%M:%S")))
                tr["history"].append(round(tr["balance"],2))
                if result=="win": tr["win_streak"]=tr.get("win_streak",0)+1; tr["loss_streak"]=0
                else: tr["loss_streak"]=tr.get("loss_streak",0)+1; tr["win_streak"]=0
                tr["open_pos"]=None
        if not tr["open_pos"]:
            for mk,sig in market_signals.items():
                if sig["conf"]<50: continue
                f=tr["signal_filters"]; rng=f.get("rsi_range",(20,80))
                rsi_v=sig["rsi"]; s=sig["signal"]
                if not (rng[0]<=rsi_v<=rng[1]): continue
                if f.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"): continue
                is_buy=s in ("BUY","STRONG BUY","OVERSOLD"); is_sell=s in ("SELL","STRONG SELL","OVERBOUGHT")
                if f.get("bb_break"):
                    bp=sig.get("bb_pct",0.5)
                    if is_buy and bp<0.8: continue
                    if is_sell and bp>0.2: continue
                if f.get("rsi_extreme"):
                    is_buy=rsi_v<32; is_sell=rsi_v>68
                if not is_buy and not is_sell: continue
                direction="long" if is_buy else "short"
                p=sig["price"]; atr=sig.get("atr",p*0.02); stop_dist=atr*1.5
                stop=p-stop_dist if is_buy else p+stop_dist
                tp=p+stop_dist*tr["rr"] if is_buy else p-stop_dist*tr["rr"]
                risk=tr["balance"]*tr["risk_pct"]; units=risk/stop_dist
                tr["open_pos"]=dict(market=mk,dir=direction,entry=round(p,2),
                    stop=round(stop,2),tp=round(tp,2),units=units,risk_amt=round(risk,2),
                    time=datetime.now().strftime("%H:%M:%S"))
                break

# ─── AI NOTES ─────────────────────────────────────────────────────────────────
def push_note(ntype,market,text):
    st.session_state["notes"].insert(0,{"type":ntype,"market":market,"text":text,
                                        "time":datetime.now().strftime("%H:%M:%S")})
    if len(st.session_state["notes"])>50: st.session_state["notes"].pop()

def generate_notes(market_signals, fg, on_chain, sessions, anthropic_key):
    cooldown=90
    if time.time()-st.session_state["last_ai"]<cooldown: return
    st.session_state["last_ai"]=time.time()
    labels={mk:v["label"] for mk,v in MARKETS.items()}
    summaries=". ".join(
        f"{labels.get(mk,mk)}: RSI {v['rsi']:.0f}, signal {v['signal']}, "
        f"BB at {v.get('bb_pct',0.5)*100:.0f}%, Stoch {v.get('stoch_k',50):.0f}"
        for mk,v in market_signals.items())
    fg_str=f"Fear & Greed: {fg['value']} ({fg['label']})" if fg else ""
    oc_str=""
    if on_chain:
        oc_str=(f"BTC 7d: {on_chain.get('price_change_7d',0):.1f}%, "
                f"30d: {on_chain.get('price_change_30d',0):.1f}%, "
                f"ATH dist: {on_chain.get('ath_change_pct',0):.1f}%")
    sess=", ".join(sessions)
    if not anthropic_key:
        for mk,sig in market_signals.items():
            r,s,bp=sig["rsi"],sig["signal"],sig.get("bb_pct",0.5)
            label=labels.get(mk,mk)
            if r>72 or s=="OVERBOUGHT":
                push_note("watch",mk,f"**{label}** is really high right now — watch for a pullback. Don't buy here.")
            elif r<30 or s=="OVERSOLD":
                push_note("buy",mk,f"**{label}** got beaten down low. Wait for a green candle, then sneak in small.")
            elif s=="STRONG BUY":
                push_note("buy",mk,f"**{label}** looking good — averages going up together. Wait for a green candle close.")
            elif s=="STRONG SELL":
                push_note("sell",mk,f"**{label}** flipped to downtrend. Stay out of new buys. Tighten your stops.")
        return
    try:
        prompt=(
            f"You are a friendly trading coach texting a beginner. Markets: {summaries}. {fg_str}. {oc_str}. Session: {sess}. "
            f"Write 4-5 short plain-English notes like texting a mate. No jargon. "
            f"Format as JSON array only: [{{'type':'watch|buy|sell|info','market':'BTC|ETH|NQ|GOLD|SPY','text':'...'}}]. Return ONLY JSON."
        )
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":anthropic_key,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":800,
                  "messages":[{"role":"user","content":prompt}]},timeout=25)
        raw=resp.json()["content"][0]["text"].strip()
        parsed=json.loads(raw.replace("```json","").replace("```","").strip())
        for n in parsed:
            push_note(n.get("type","info"),n.get("market","BTC"),n.get("text",""))
    except:
        for mk,sig in market_signals.items():
            r,s=sig["rsi"],sig["signal"]
            label=labels.get(mk,mk)
            if r>70: push_note("watch",mk,f"**{label}** running hot — RSI {r:.0f}. Watch for drop.")
            elif r<30: push_note("buy",mk,f"**{label}** oversold at RSI {r:.0f}. Watch for bounce.")
            elif "BUY" in s: push_note("buy",mk,f"**{label}** signal pointing up. Wait for green candle close.")
            elif "SELL" in s: push_note("sell",mk,f"**{label}** signal pointing down. Stay out or tighten stops.")

# ─── SESSION BANNER ───────────────────────────────────────────────────────────
SESSION_TIPS={
    "Tokyo":"Quiet session. BTC/ETH can drift or spike randomly. Gold and stocks mostly flat.",
    "London":"Things picking up! Gold and BTC usually make moves at London open.",
    "New York":"Prime time — all markets active. US market open, sharpest signals.",
    "Overlap":"🔥 Peak time — London + NY both open. Biggest moves happen here.",
    "Off-hours":"Slow and thin. Wider spreads. Better to watch than trade.",
}
def session_banner():
    utc=datetime.now(ZoneInfo("UTC")); hf=utc.hour+utc.minute/60
    sessions=[]
    if 0<=hf<9:   sessions.append(("Tokyo","#7C3AED"))
    if 8<=hf<17:  sessions.append(("London","#2563EB"))
    if 13<=hf<22: sessions.append(("New York","#059669"))
    if 13<=hf<17: sessions.append(("Overlap","#D97706"))
    if not sessions: sessions.append(("Off-hours","#555"))
    badges=" ".join(f'<span class="session-badge" style="background:{c}">{n}</span>' for n,c in sessions)
    tip=SESSION_TIPS.get(sessions[0][0],"")
    ny=utc.astimezone(ZoneInfo("America/New_York")); lon=utc.astimezone(ZoneInfo("Europe/London"))
    st.markdown(
        f'<div style="background:#0d0d1a;border:1px solid #1a1a3a;border-radius:10px;padding:12px 18px;margin-bottom:16px">'
        f'<div style="margin-bottom:6px">{badges}</div>'
        f'<div style="font-size:13px;color:#aaa;margin-bottom:4px">{tip}</div>'
        f'<div style="font-size:11px;color:#555">UTC {utc.strftime("%H:%M")} | ET {ny.strftime("%H:%M")} | LDN {lon.strftime("%H:%M")}</div>'
        f'</div>',unsafe_allow_html=True)
    return [n for n,_ in sessions]

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:#00ff88">⚡ Alpha Trader Pro</div>',unsafe_allow_html=True)
    st.divider()
    with st.expander("🔑 API Keys",expanded=False):
        np_=st.text_input("Polygon.io Key",value=POLYGON_KEY,type="password")
        na_=st.text_input("Anthropic Key",value=ANTHROPIC_KEY,type="password")
        if st.button("Save"):
            st.session_state["POLYGON_KEY"]=np_; st.session_state["ANTHROPIC_KEY"]=na_
            st.cache_data.clear(); st.rerun()
    st.divider()
    auto_refresh=st.toggle("Auto-refresh (90s)",value=False)
    selected_markets=st.multiselect("Markets to watch",["BTC","ETH","NQ","GOLD","SPY"],default=["BTC","NQ","GOLD"])
    bt_days=st.slider("Backtest period (days)",30,365,90)
    note_filter=st.selectbox("Filter alerts",["ALL"]+["BTC","ETH","NQ","GOLD","SPY"])
    st.divider()
    if st.button("🔄 Refresh data"):
        st.cache_data.clear(); st.rerun()
    if st.button("🗑 Clear alerts"):
        st.session_state["notes"]=[]; st.rerun()
    if st.button("♻️ Reset traders"):
        del st.session_state["traders"]; st.rerun()
    if st.button("🧠 Run 100-AI Ensemble"):
        st.session_state["last_ensemble_run"]=0.0
    st.divider()
    st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

# ─── FETCH ALL DATA ────────────────────────────────────────────────────────────
if not selected_markets: selected_markets=["BTC","NQ","GOLD"]

with st.spinner("Loading live data from all sources..."):
    all_dfs={}
    for mk in selected_markets:
        info=MARKETS[mk]
        if info["crypto"]: raw=fetch_cg_chart(info["cg_id"],days=max(bt_days+10,100))
        else: raw=fetch_polygon_ohlcv(info["poly_ticker"],POLYGON_KEY,days=max(bt_days+10,100))
        all_dfs[mk]=add_indicators(raw)
    fg=fetch_fear_greed()
    on_chain=fetch_on_chain() if "BTC" in selected_markets else {}
    poly_markets=fetch_polymarket_data()

market_signals={}
for mk in selected_markets:
    df=all_dfs.get(mk,pd.DataFrame())
    market_signals[mk]=get_market_signal(df,fg,on_chain)

active_sessions=session_banner()
simulate_all_traders(market_signals)
generate_notes(market_signals,fg,on_chain,active_sessions,ANTHROPIC_KEY)

# Auto-run ensemble on first load (lightweight: only if not run recently)
if not st.session_state["ensemble_results"] and not st.session_state["grand_strategy"]:
    with st.spinner("Running 100-AI ensemble backtest (first load)..."):
        try:
            ens_res, grand = run_ensemble_backtest(all_dfs, days=bt_days)
            st.session_state["ensemble_results"] = ens_res
            st.session_state["grand_strategy"]   = grand
            st.session_state["last_ensemble_run"]= time.time()
        except Exception as e:
            pass

# ─── PAGE HEADER ──────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">⚡ Alpha Trader Pro</div>',unsafe_allow_html=True)
st.markdown('<div class="subtitle">100-AI ensemble · Grand strategy signals · Polymarket flow · Advanced backtesting</div>',unsafe_allow_html=True)

# ─── FEAR & GREED ─────────────────────────────────────────────────────────────
if fg:
    fv=fg["value"]; fl=fg["label"]
    fc="#ff4444" if fv<25 else "#ff9900" if fv<45 else "#ffff00" if fv<55 else "#99ff44" if fv<75 else "#00ff88"
    tip_txt="Extreme fear = potential buy zone" if fv<25 else "Extreme greed = be careful" if fv>75 else ""
    st.markdown(
        f'<div style="display:inline-block;background:#0d0d1a;border:1px solid #1a1a3a;'
        f'border-radius:8px;padding:8px 18px;font-size:13px;margin-bottom:16px">'
        f'Market Fear & Greed: <span style="color:{fc};font-weight:700;font-size:16px">{fv}</span> '
        f'<span style="color:{fc}">{fl}</span>'
        f'<span style="color:#555;font-size:11px;margin-left:12px">{tip_txt}</span></div>',
        unsafe_allow_html=True)

# ─── GRAND STRATEGY SIGNAL BANNER ────────────────────────────────────────────
grand = st.session_state.get("grand_strategy",{})
if grand:
    st.markdown("### 🧠 Grand Strategy — 100-AI Consensus")
    session_scored, cur_session = get_session_best(grand, active_sessions)
    cols_gs = st.columns(len([mk for mk in selected_markets if mk in grand]))
    for col, mk in zip(cols_gs, [m for m in selected_markets if m in grand]):
        with col:
            gs = grand[mk]
            sig = gs["current_signal"]
            conf = gs["current_conf"]
            is_buy  = "BUY" in sig or sig=="OVERSOLD"
            is_sell = "SELL" in sig or sig=="OVERBOUGHT"
            cls = "grand-signal-buy" if is_buy else "grand-signal-sell" if is_sell else "grand-signal-hold"
            icon = "🟢" if is_buy else "🔴" if is_sell else "⚪"
            border_c = "#00ff88" if is_buy else "#ff4444" if is_sell else "#555"
            info = MARKETS[mk]
            st.markdown(
                f'<div class="{cls}" style="border:2px solid {border_c};border-radius:12px;padding:14px 18px;margin-bottom:8px">'
                f'<div style="font-size:11px;color:#666;font-family:JetBrains Mono,monospace">{info["label"]} · 100-AI</div>'
                f'<div style="font-size:1.3rem;font-weight:700;margin:4px 0">{icon} {sig}</div>'
                f'<div style="font-size:12px;color:#888">Confidence: <b style="color:{border_c}">{conf}%</b></div>'
                f'<div style="font-size:11px;color:#555;margin-top:4px">'
                f'RSI: {gs["current_rsi"]} | Best R:R 1:{gs["consensus_rr"]} | '
                f'Avg return: {gs["avg_return"]:+.1f}%</div>'
                f'<div style="font-size:10px;color:#444;margin-top:2px">Best: {gs["best_trader"][:30]}</div>'
                f'</div>',unsafe_allow_html=True)

# ─── LIVE PRICE CARDS ─────────────────────────────────────────────────────────
st.subheader("Live signals")
cols=st.columns(len(selected_markets))
for col,mk in zip(cols,selected_markets):
    with col:
        info=MARKETS[mk]; sig=market_signals.get(mk,{}); p=sig.get("price",0)
        df=all_dfs.get(mk,pd.DataFrame()); chg=0
        if not df.empty and len(df)>1:
            chg=(df["close"].iloc[-1]-df["close"].iloc[-2])/df["close"].iloc[-2]*100
        s=sig.get("signal","HOLD"); c=sig.get("conf",50); r=sig.get("rsi",50)
        isBuy="BUY" in s or s=="OVERSOLD"; isSell="SELL" in s or s=="OVERBOUGHT"
        border="#00ff88" if isBuy else "#ff4444" if isSell else "#1a1a3a"
        chg_col="#00ff88" if chg>=0 else "#ff4444"
        px_fmt=f"${p:,.0f}" if mk in ("BTC","ETH") else f"${p:,.2f}"
        sig_cls="sig-buy" if isBuy else "sig-sell" if isSell else "sig-hold"
        st.markdown(
            f'<div style="border:2px solid {border};border-radius:12px;padding:14px;background:#0d0d1a;margin-bottom:4px">'
            f'<div style="font-size:11px;color:#555;margin-bottom:4px">{info["label"]}</div>'
            f'<div style="font-size:22px;font-weight:700;color:{info["color"]};font-family:JetBrains Mono,monospace">{px_fmt}</div>'
            f'<div style="font-size:12px;color:{chg_col};margin-bottom:8px">{chg:+.2f}% today</div>'
            f'<span class="signal-badge {sig_cls}">{s}</span><br>'
            f'<div style="font-size:11px;color:#555;margin-top:4px">Conf: {c}% | RSI: {r:.0f} | BB: {sig.get("bb_pct",0.5)*100:.0f}%</div>'
            f'</div>',unsafe_allow_html=True)

st.divider()

# ─── MAIN TABS ────────────────────────────────────────────────────────────────
tab_grand, tab_alerts, tab_poly, tab_traders, tab_backtest, tab_ensemble, tab_sessions = st.tabs([
    "🧠 Grand Strategy","📝 Alerts","🎯 Polymarket","🤖 AI Traders","📊 Backtesting","🔬 100-AI Ensemble","🕐 Sessions"
])

# ─── GRAND STRATEGY TAB ───────────────────────────────────────────────────────
with tab_grand:
    st.subheader("🧠 Grand Strategy — What 100 AI Traders Agree On")
    st.caption("Synthesized from 100 different trading configurations. The consensus tells you what style works best right now.")

    if not grand:
        st.info("Grand strategy is computed on first load. Click **🔄 Refresh data** or wait.")
    else:
        # Session-adjusted signals
        session_scored, cur_session = get_session_best(grand, active_sessions)
        st.markdown(f"**Current session: {cur_session}** — markets weighted accordingly")
        
        # Best market to trade right now
        best_mk = max(session_scored, key=lambda x: session_scored[x]["score"]) if session_scored else None
        if best_mk:
            bs = session_scored[best_mk]
            bsig = bs["signal"]; is_buy_b="BUY" in bsig or bsig=="OVERSOLD"
            bc = "#00ff88" if is_buy_b else "#ff4444" if "SELL" in bsig else "#555"
            st.markdown(
                f'<div style="background:#0d1a0d;border:2px solid {bc};border-radius:14px;padding:18px 24px;margin-bottom:16px">'
                f'<div style="font-size:11px;color:#555;font-family:JetBrains Mono,monospace">BEST OPPORTUNITY RIGHT NOW</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{bc};margin:4px 0">'
                f'{"🟢 BUY" if is_buy_b else "🔴 SELL" if "SELL" in bsig else "⚪ HOLD"} — {MARKETS[best_mk]["label"]}</div>'
                f'<div style="font-size:13px;color:#aaa">Session-adjusted confidence: <b style="color:{bc}">{bs["conf"]}%</b> | '
                f'R:R 1:{bs["rr"]} | Session: {cur_session}</div>'
                f'<div style="font-size:12px;color:#555;margin-top:4px">'
                f'RSI: {bs["rsi"]} | Avg return of top 20: {bs["avg_return"]:+.1f}%</div>'
                f'</div>',unsafe_allow_html=True)

        # Day schedule
        st.markdown("### 📅 Today's Trading Schedule")
        schedule_data = [
            ("00:00–08:00 UTC","Tokyo / Off-hours","BTC, ETH","Low volume. Crypto scalps only. Use tight stops.","#7C3AED"),
            ("08:00–13:00 UTC","London","Gold, BTC","EU data moves gold. BTC often follows. Watch for breakouts.","#2563EB"),
            ("13:00–17:00 UTC","NY + London Overlap","ALL","🔥 Best time to trade. Sharpest signals. All markets active.","#D97706"),
            ("17:00–22:00 UTC","New York only","NQ, SPY, BTC","US afternoon. Momentum can fade. Trail stops tighter.","#059669"),
            ("22:00–00:00 UTC","Off-hours","None","Very thin. Avoid new positions.","#555"),
        ]
        for times, sess, mkts, tip, sc in schedule_data:
            utc_h = datetime.now(ZoneInfo("UTC")).hour
            h_start = int(times.split("–")[0].split(":")[0])
            h_end   = int(times.split("–")[1].split(" ")[0].split(":")[0]) if "–" in times else 24
            is_now  = h_start <= utc_h < h_end
            border  = sc if is_now else "#1a1a2e"
            now_badge = f' <span style="background:{sc};color:#fff;border-radius:3px;padding:1px 6px;font-size:10px">NOW</span>' if is_now else ""
            st.markdown(
                f'<div style="border:1.5px solid {border};border-radius:8px;padding:10px 16px;margin-bottom:6px;background:#0d0d1a">'
                f'<div style="font-size:12px;font-weight:700;color:{sc};font-family:JetBrains Mono,monospace">{times}{now_badge}</div>'
                f'<div style="font-size:11px;color:#666">{sess} · {mkts}</div>'
                f'<div style="font-size:12px;color:#aaa;margin-top:2px">{tip}</div>'
                f'</div>',unsafe_allow_html=True)

        # Consensus parameters table
        st.markdown("### 🎛️ Consensus Trading Parameters (from 100 AIs)")
        param_rows=[]
        for mk, gs in grand.items():
            if mk in selected_markets:
                param_rows.append({
                    "Market": MARKETS[mk]["label"],
                    "RSI Range": f"{gs['consensus_rsi_range'][0]}–{gs['consensus_rsi_range'][1]}",
                    "R:R": f"1:{gs['consensus_rr']}",
                    "BB Break": "✅" if gs["use_bb_break"] else "❌",
                    "RSI Extreme": "✅" if gs["use_rsi_extreme"] else "❌",
                    "Strong Only": "✅" if gs["use_strong_only"] else "❌",
                    "Avg Return": f"{gs['avg_return']:+.1f}%",
                    "Avg Win Rate": f"{gs['avg_win_rate']:.0f}%",
                    "Avg Sharpe": f"{gs['avg_sharpe']:.2f}",
                })
        if param_rows:
            st.dataframe(pd.DataFrame(param_rows),use_container_width=True,hide_index=True)

# ─── ALERTS TAB ───────────────────────────────────────────────────────────────
with tab_alerts:
    st.subheader("Plain-English market alerts")
    st.caption("No jargon — written like a text from a mate who's been watching the charts.")
    notes=st.session_state["notes"]
    if note_filter!="ALL": notes=[n for n in notes if n["market"]==note_filter]
    if not notes: st.info("Notes will appear here. Hit Refresh to generate them.")
    icons={"watch":"👀 Watch out","buy":"🟢 Possible buy","sell":"🔴 Consider selling","info":"💡 Heads up"}
    for n in notes[:12]:
        cls={"watch":"note-watch","buy":"note-buy","sell":"note-sell","info":"note-info"}.get(n["type"],"note-info")
        label=MARKETS.get(n["market"],{}).get("label",n["market"])
        st.markdown(
            f'<div class="note-card {cls}">'
            f'<div style="font-size:10px;color:#555;margin-bottom:2px">{n["time"]}</div>'
            f'<div style="font-weight:600;font-size:12px;margin-bottom:4px">{icons.get(n["type"],"💡")} — {label}</div>'
            f'{n["text"]}</div>',unsafe_allow_html=True)
    if fg:
        st.divider()
        st.markdown("**Fear & Greed history (last 10 days)**")
        fig_fg=go.Figure(go.Bar(x=list(range(len(fg["history"]))),y=fg["history"],
            marker_color=["#ff4444" if v<25 else "#ff9900" if v<45 else "#ffff44" if v<55 else "#00ff88" for v in fg["history"]],
            text=[str(v) for v in fg["history"]],textposition="outside"))
        fig_fg.update_layout(height=180,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
                             margin=dict(l=0,r=0,t=10,b=0),xaxis_title="Days ago",yaxis=dict(range=[0,120]))
        st.plotly_chart(fig_fg,use_container_width=True)
    if on_chain:
        st.divider()
        st.markdown("**BTC on-chain snapshot**")
        oc1,oc2,oc3,oc4=st.columns(4)
        oc1.metric("Market cap",f"${on_chain.get('market_cap',0)/1e9:.1f}B")
        oc2.metric("24h volume",f"${on_chain.get('volume_24h',0)/1e9:.1f}B")
        oc3.metric("7d change",f"{on_chain.get('price_change_7d',0):+.1f}%")
        oc4.metric("Dist from ATH",f"{on_chain.get('ath_change_pct',0):.1f}%")

# ─── POLYMARKET TAB ───────────────────────────────────────────────────────────
with tab_poly:
    st.subheader("🎯 Polymarket — Who's Betting on What Today")
    st.caption("Live prediction market odds. Shows what traders think will happen — useful contrarian/confirmation signal.")
    
    if not poly_markets:
        st.warning("Could not load Polymarket data. Check network or try refreshing.")
        st.info("Polymarket shows real-money prediction markets — very useful for gauging trader sentiment beyond just price.")
    else:
        # Top volume overview
        total_vol = sum(m["volume"] for m in poly_markets)
        st.markdown(f'<div style="color:#555;font-size:12px;margin-bottom:12px">Total volume in top markets: <b style="color:#00d4ff">${total_vol/1e6:.1f}M</b></div>',unsafe_allow_html=True)
        
        # Volume bar chart
        top10 = sorted(poly_markets, key=lambda x: x["volume"], reverse=True)[:10]
        fig_poly = go.Figure(go.Bar(
            x=[m["volume"]/1e3 for m in top10],
            y=[m["question"][:50]+"…" if len(m["question"])>50 else m["question"] for m in top10],
            orientation="h",
            marker_color=["#00d4ff" if m["top_pct"]>60 else "#f0a500" if m["top_pct"]>40 else "#ff4444" for m in top10],
            text=[f"${m['volume']/1e3:.0f}k · {m['top_outcome']}: {m['top_pct']}%" for m in top10],
            textposition="auto",textfont=dict(size=10,color="#fff"),
        ))
        fig_poly.update_layout(height=400,template="plotly_dark",
            title="Top Polymarket contracts by volume (today)",
            paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
            xaxis_title="Volume ($k)",margin=dict(l=0,r=0,t=50,b=0))
        st.plotly_chart(fig_poly,use_container_width=True)

        # Detailed cards
        st.markdown("### Market Details")
        for m in poly_markets[:10]:
            top_pct = m["top_pct"]
            pct_color = "#00ff88" if top_pct > 65 else "#f0a500" if top_pct > 40 else "#ff4444"
            pairs_str = " · ".join(f"{o}: <b style='color:{pct_color}'>{round(float(p)*100,1)}%</b>" for o,p in m["pairs"])
            vol_str   = f"${m['volume']/1e3:.0f}k" if m["volume"]>1000 else f"${m['volume']:.0f}"
            liq_str   = f"${m['liquidity']/1e3:.0f}k" if m["liquidity"]>1000 else f"${m['liquidity']:.0f}"
            st.markdown(
                f'<div class="poly-card">'
                f'<div style="font-size:13px;font-weight:600;color:#eee;margin-bottom:4px">{m["question"]}</div>'
                f'<div style="font-size:12px;color:#888">{pairs_str}</div>'
                f'<div class="poly-bar-wrap"><div style="height:100%;width:{top_pct}%;background:{pct_color};border-radius:4px"></div></div>'
                f'<div style="font-size:11px;color:#555;margin-top:4px">Volume: {vol_str} · Liquidity: {liq_str}</div>'
                f'</div>',unsafe_allow_html=True)

        # Trading implications
        st.divider()
        st.markdown("### 📊 What This Means For Your Trades")
        st.markdown("""
        <div style="background:#0d0d1a;border:1px solid #1a1a3a;border-radius:10px;padding:16px;font-size:13px;color:#aaa;line-height:1.7">
        <b style="color:#00d4ff">How to use Polymarket:</b><br>
        • High conviction (>70%) on a direction → real traders are very certain → treat as strong signal confirmation<br>
        • Near 50/50 split → genuine uncertainty → reduce position size or wait<br>
        • Extreme one-sided bets (>85%) → contrarian opportunity — markets may be overpriced on that side<br>
        • BTC/crypto-related markets → cross-check with your RSI + MACD signals for confluence<br>
        • Economic/election markets → macro backdrop for NQ, SPY, Gold trades
        </div>
        """,unsafe_allow_html=True)

# ─── AI TRADERS TAB ───────────────────────────────────────────────────────────
with tab_traders:
    st.subheader("5 AI traders — different strategies, same markets")
    rows=[]
    for tr in TRADERS:
        pnl=tr["balance"]-25000
        wins=sum(1 for t in tr["trades"] if t["result"]=="win")
        tot=len(tr["trades"]); wr=round(wins/tot*100) if tot else 0
        dd=round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
        rows.append({"Trader":f"{tr['emoji']} {tr['name']}","Style":tr["style"],
                     "Balance":tr["balance"],"P&L":pnl,"Win%":wr,"Trades":tot,"DD%":dd,
                     "W-Streak":tr.get("win_streak",0),"L-Streak":tr.get("loss_streak",0)})
    df_score=pd.DataFrame(rows).sort_values("P&L",ascending=False).reset_index(drop=True)
    df_score.index+=1
    st.dataframe(
        df_score.style
            .format({"Balance":"${:,.0f}","P&L":"${:+,.0f}","Win%":"{}%","DD%":"{}%"})
            .map(lambda v:"color:#00ff88;font-weight:700" if v>0 else "color:#ff4444;font-weight:700",subset=["P&L"]),
        use_container_width=True)

    hist_fig=go.Figure()
    hc={"Macro Maya":"#00ff88","Momentum Mike":"#00d4ff","Scalp Sam":"#f0a500",
        "Trend Tina":"#7B61FF","Contrarian Carl":"#ff6b6b"}
    for tr in TRADERS:
        if len(tr["history"])>1:
            pnl_pct=(tr["balance"]-25000)/25000*100
            hist_fig.add_trace(go.Scatter(y=tr["history"],name=f"{tr['emoji']} {tr['name']} ({pnl_pct:+.1f}%)",
                line=dict(color=hc.get(tr["name"],"#fff"),width=2)))
    hist_fig.add_hline(y=25000,line=dict(color="#555",width=1,dash="dot"),annotation_text="$25k start")
    hist_fig.update_layout(height=280,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
                           margin=dict(l=0,r=0,t=30,b=0),legend=dict(orientation="h",y=1.05))
    st.plotly_chart(hist_fig,use_container_width=True)

    tr_tabs=st.tabs([f"{tr['emoji']} {tr['name']}" for tr in TRADERS])
    for ttab,tr in zip(tr_tabs,TRADERS):
        with ttab:
            pnl=tr["balance"]-25000
            m1,m2,m3,m4,m5,m6=st.columns(6)
            m1.metric("Balance",f"${tr['balance']:,.0f}",delta=f"{pnl:+,.0f}")
            m2.metric("Net P&L",f"${pnl:+,.0f}")
            wins=sum(1 for t in tr["trades"] if t["result"]=="win"); tot=len(tr["trades"])
            m3.metric("Win rate",f"{round(wins/tot*100) if tot else 0}%")
            m4.metric("Trades",tot); m5.metric("Risk/trade",f"{tr['risk_pct']*100:.1f}%"); m6.metric("R:R",f"1:{tr['rr']}")
            st.caption(f"**Sources:** {', '.join(tr['data_sources'])} | **Strategy:** {tr['desc']}")
            pos=tr["open_pos"]
            if pos:
                mk=pos["market"]; info=MARKETS.get(mk,{}); sig=market_signals.get(mk,{})
                cur_p=sig.get("price",pos["entry"])
                unreal=(cur_p-pos["entry"])*pos["units"] if pos["dir"]=="long" else (pos["entry"]-cur_p)*pos["units"]
                uc="#00ff88" if unreal>=0 else "#ff4444"
                fmt="0f" if info.get("crypto") else ".2f"
                st.markdown(
                    f'<div class="{"pos-long" if pos["dir"]=="long" else "pos-short"}">'
                    f'<b>{info.get("label",mk)} — {pos["dir"].upper()}</b> | '
                    f'Entry ${pos["entry"]:{fmt}} | Now ${cur_p:{fmt}}<br>'
                    f'Stop: <span style="color:#ff4444">${pos["stop"]:{fmt}}</span> | '
                    f'Target: <span style="color:#00ff88">${pos["tp"]:{fmt}}</span> | '
                    f'Unrealized: <span style="color:{uc}"><b>${unreal:+,.0f}</b></span>'
                    f'</div>',unsafe_allow_html=True)
            else:
                st.markdown('<div class="pos-none">No open position right now</div>',unsafe_allow_html=True)
            if tr["trades"]:
                st.markdown("**Recent trades**")
                tdf=pd.DataFrame(tr["trades"][-10:][::-1])
                show=[c for c in ["time","market","dir","entry","exit","pnl","result","reason"] if c in tdf.columns]
                st.dataframe(
                    tdf[show].style
                        .format({c:"${:,.2f}" for c in ["entry","exit","pnl"] if c in tdf.columns})
                        .map(lambda v:"color:#00ff88" if v=="win" else "color:#ff4444",subset=["result"] if "result" in tdf.columns else []),
                    use_container_width=True,hide_index=True)

# ─── BACKTESTING TAB ──────────────────────────────────────────────────────────
with tab_backtest:
    st.subheader(f"Advanced backtesting — last {bt_days} days")
    
    bt_market=st.selectbox("Market to backtest",selected_markets)
    
    # Let user pick ONE trader OR compare all
    bt_mode=st.radio("Mode",["Single trader","Compare all 5 traders"],horizontal=True)
    
    if bt_mode=="Single trader":
        bt_trader=st.selectbox("Strategy",["Macro Maya","Momentum Mike","Scalp Sam","Trend Tina","Contrarian Carl"])
    
    show_sigs=st.toggle("Show buy/sell signals on chart",value=True)
    run_bt=st.button("▶ Run backtest",type="primary")

    df_bt=all_dfs.get(bt_market,pd.DataFrame())
    
    if run_bt:
        with st.spinner("Running backtest..."):
            all_bts={}
            for tr in TRADERS:
                bt_r=run_backtest(df_bt,tr,label=tr["name"])
                if "equity_curve" in bt_r:
                    all_bts[tr["name"]]=bt_r
            if all_bts:
                chosen_name = bt_trader if bt_mode=="Single trader" else list(all_bts.keys())[0]
                main_bt = all_bts.get(chosen_name, list(all_bts.values())[0])
                st.session_state["bt_results"]={"main":main_bt,"all":all_bts,"market":bt_market,"mode":bt_mode}
            else:
                st.error("Backtest failed — not enough data.")

    saved=st.session_state.get("bt_results",{})
    bt=saved.get("main"); all_bts=saved.get("all",{})

    if bt and "equity_curve" in bt:
        if bt_mode=="Compare all 5 traders" or saved.get("mode")=="Compare all 5 traders":
            st.markdown("### 📊 All 5 Strategies Head-to-Head")
            
            # Comparison grid
            comp_rows=[]
            for tname,tbt in all_bts.items():
                if tbt and "total_return" in tbt:
                    comp_rows.append({
                        "Trader":tname,"Return %":tbt["total_return"],"B&H %":tbt["bh_return"],
                        "Win rate":tbt["win_rate"],"Trades":tbt["total_trades"],
                        "Max DD %":tbt["max_drawdown"],"Sharpe":tbt["sharpe"],
                        "Calmar":tbt["calmar"],"PF":tbt["profit_factor"],
                        "Avg Win":tbt["avg_win"],"Avg Loss":tbt["avg_loss"],
                    })
            if comp_rows:
                df_comp=pd.DataFrame(comp_rows)
                # Rank by Sharpe
                df_comp["Rank"]=df_comp["Sharpe"].rank(ascending=False).astype(int)
                df_comp=df_comp.sort_values("Rank")
                medals=["🥇","🥈","🥉","4️⃣","5️⃣"]
                df_comp.insert(0,"#",[medals[i] for i in range(len(df_comp))])
                st.dataframe(
                    df_comp.style
                        .format({"Return %":"{:+.1f}%","B&H %":"{:+.1f}%","Win rate":"{:.0f}%",
                                 "Max DD %":"{:.1f}%","Sharpe":"{:.2f}","Calmar":"{:.2f}",
                                 "PF":"{:.2f}","Avg Win":"${:+.2f}","Avg Loss":"${:+.2f}"})
                        .highlight_max(subset=["Return %","Win rate","Sharpe"],color="#1a3a1a")
                        .highlight_min(subset=["Max DD %"],color="#1a3a1a"),
                    use_container_width=True,hide_index=True)

            # Equity curves
            fig_eq=build_equity_chart(all_bts)
            if fig_eq: st.plotly_chart(fig_eq,use_container_width=True)
            
            # Session best
            st.markdown("### 🏆 Which Trader Works Best Per Session?")
            session_bt_data=[]
            for sname in ["Tokyo","London","New York","Overlap"]:
                sw={"Tokyo":{"BTC":1.2,"ETH":1.1},"London":{"GOLD":1.3,"BTC":1.1},
                    "New York":{"NQ":1.3,"SPY":1.3},"Overlap":{"ALL":1.2}}.get(sname,{})
                best_by_sharpe=max(all_bts.items(),key=lambda x:x[1].get("sharpe",0))
                best_name=best_by_sharpe[0]; best_ret=best_by_sharpe[1].get("total_return",0)
                session_bt_data.append({"Session":sname,"Best Trader":best_name,
                                        "Sharpe":f"{best_by_sharpe[1].get('sharpe',0):.2f}",
                                        "Return":f"{best_ret:+.1f}%"})
            st.dataframe(pd.DataFrame(session_bt_data),use_container_width=True,hide_index=True)

        # Stats for main/selected trader
        st.markdown(f"### 📈 {bt.get('label','')} — Detailed Stats")
        s1,s2,s3,s4,s5,s6,s7,s8=st.columns(8)
        color_ret="#00ff88" if bt["total_return"]>0 else "#ff4444"
        s1.markdown(f'<div class="bt-stat"><div class="bt-val" style="color:{color_ret}">{bt["total_return"]:+.1f}%</div><div class="bt-lbl">Strategy</div></div>',unsafe_allow_html=True)
        s2.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["bh_return"]:+.1f}%</div><div class="bt-lbl">Buy & Hold</div></div>',unsafe_allow_html=True)
        s3.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["win_rate"]:.0f}%</div><div class="bt-lbl">Win Rate</div></div>',unsafe_allow_html=True)
        s4.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["total_trades"]}</div><div class="bt-lbl">Trades</div></div>',unsafe_allow_html=True)
        s5.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["profit_factor"]:.2f}</div><div class="bt-lbl">Profit Factor</div></div>',unsafe_allow_html=True)
        s6.markdown(f'<div class="bt-stat"><div class="bt-val" style="color:#ff4444">{bt["max_drawdown"]:.1f}%</div><div class="bt-lbl">Max DD</div></div>',unsafe_allow_html=True)
        s7.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["sharpe"]:.2f}</div><div class="bt-lbl">Sharpe</div></div>',unsafe_allow_html=True)
        s8.markdown(f'<div class="bt-stat"><div class="bt-val">{bt["calmar"]:.2f}</div><div class="bt-lbl">Calmar</div></div>',unsafe_allow_html=True)
        a1,a2,a3,a4=st.columns(4)
        a1.metric("Avg win",f"${bt['avg_win']:+,.2f}"); a2.metric("Avg loss",f"${bt['avg_loss']:+,.2f}")
        a3.metric("Max win streak",bt["max_win_streak"]); a4.metric("Max loss streak",bt["max_loss_streak"])
        
        fig_main=build_advanced_chart(df_bt,f"{bt_market} — {bt.get('label','')}",MARKETS[bt_market]["color"],show_sigs,bt)
        if fig_main: st.plotly_chart(fig_main,use_container_width=True)
        
        c_eq,c_mo=st.columns([2,1])
        with c_eq:
            fig_eq2=build_equity_chart(all_bts)
            if fig_eq2: st.plotly_chart(fig_eq2,use_container_width=True)
        with c_mo:
            fig_mo=build_monthly_returns(bt)
            if fig_mo: st.plotly_chart(fig_mo,use_container_width=True)
        
        fig_dd=build_drawdown_chart(bt)
        if fig_dd: st.plotly_chart(fig_dd,use_container_width=True)
        
        with st.expander("📋 Full trade log"):
            tdf=bt["trade_list"].copy()
            tdf["pnl_pct"]=tdf["pnl"]/10000*100
            st.dataframe(
                tdf.style
                    .format({"entry":"${:,.2f}","exit":"${:,.2f}","pnl":"${:+,.2f}","pnl_pct":"{:+.2f}%"})
                    .map(lambda v:"color:#00ff88" if v>0 else "color:#ff4444",subset=["pnl"]),
                use_container_width=True,hide_index=True)
        
        with st.expander("⚠️ Disclaimer"):
            st.caption("Past performance does not guarantee future results. No slippage, commissions, or fees modelled. Do not trade based solely on backtest results.")
    else:
        st.info("Click **▶ Run backtest** to start.")

# ─── 100-AI ENSEMBLE TAB ──────────────────────────────────────────────────────
with tab_ensemble:
    st.subheader("🔬 100-AI Ensemble — Full Leaderboard & Analysis")
    st.caption("All 100 trading configurations backtested. The top performers are combined into the Grand Strategy.")

    if st.button("🔄 Re-run Full Ensemble (takes ~30s)",type="primary"):
        with st.spinner("Running 100 AI traders across all markets... this takes a moment..."):
            ens_res,grand=run_ensemble_backtest(all_dfs,days=bt_days)
            st.session_state["ensemble_results"]=ens_res
            st.session_state["grand_strategy"]=grand
            st.session_state["last_ensemble_run"]=time.time()
            st.success("Ensemble complete! Grand strategy updated.")

    ens_res=st.session_state.get("ensemble_results",{})
    grand_s=st.session_state.get("grand_strategy",{})
    
    if not ens_res:
        st.info("Ensemble runs automatically on first load. Click the button above to re-run.")
    else:
        last_run=st.session_state.get("last_ensemble_run",0)
        if last_run:
            st.caption(f"Last run: {datetime.fromtimestamp(last_run).strftime('%H:%M:%S')}")
        
        ens_mk=st.selectbox("View leaderboard for market",list(ens_res.keys()))
        
        if ens_mk and ens_mk in ens_res:
            mk_results=ens_res[ens_mk]
            
            # Summary stats
            all_rets=[r["return"] for r in mk_results]
            all_sharpes=[r["sharpe"] for r in mk_results]
            winners=[r for r in mk_results if r["return"]>0]
            
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("Total AIs tested",len(mk_results))
            c2.metric("Winners (>0%)",len(winners),f"{len(winners)/max(1,len(mk_results))*100:.0f}% win rate")
            c3.metric("Avg return",f"{np.mean(all_rets):+.1f}%")
            c4.metric("Best return",f"{max(all_rets):+.1f}%")
            c5.metric("Avg Sharpe",f"{np.mean(all_sharpes):.2f}")
            
            # Leaderboard chart
            fig_lb=build_ensemble_leaderboard(ens_res,ens_mk)
            if fig_lb: st.plotly_chart(fig_lb,use_container_width=True)
            
            # Full table
            with st.expander(f"📋 Full 100-trader table for {ens_mk}"):
                df_ens=pd.DataFrame([{
                    "Rank":i+1,"Trader":r["name"],"Return %":r["return"],
                    "Win Rate":r["win_rate"],"Sharpe":r["sharpe"],
                    "Max DD %":r["max_dd"],"Profit Factor":r["profit_factor"],
                    "Trades":r["trades"],"RSI Range":f"{r['rsi_range'][0]}-{r['rsi_range'][1]}",
                    "R:R":r["rr"],"Score":round(r["score"],3),
                } for i,r in enumerate(mk_results)])
                st.dataframe(
                    df_ens.style
                        .format({"Return %":"{:+.1f}%","Win Rate":"{:.0f}%","Sharpe":"{:.2f}",
                                 "Max DD %":"{:.1f}%","Profit Factor":"{:.2f}","Score":"{:.3f}"})
                        .highlight_max(subset=["Return %","Win Rate","Sharpe","Score"],color="#1a3a1a")
                        .highlight_min(subset=["Max DD %"],color="#1a3a1a"),
                    use_container_width=True,hide_index=True)
            
            # Grand strategy consensus for this market
            if ens_mk in grand_s:
                st.markdown(f"### 🏆 Grand Strategy Consensus for {MARKETS[ens_mk]['label']}")
                gs=grand_s[ens_mk]
                gcols=st.columns(4)
                gcols[0].metric("Consensus RSI Range",f"{gs['consensus_rsi_range'][0]}–{gs['consensus_rsi_range'][1]}")
                gcols[1].metric("Consensus R:R",f"1:{gs['consensus_rr']}")
                gcols[2].metric("Avg Return (top 20)",f"{gs['avg_return']:+.1f}%")
                gcols[3].metric("Avg Win Rate",f"{gs['avg_win_rate']:.0f}%")
                
                # Return distribution
                fig_dist=go.Figure()
                fig_dist.add_trace(go.Histogram(x=all_rets,nbinsx=20,
                    marker_color=["#00ff88" if r>=0 else "#ff4444" for r in all_rets],
                    name="Return distribution"))
                fig_dist.add_vline(x=0,line=dict(color="#555",width=1,dash="dash"))
                fig_dist.add_vline(x=np.mean(all_rets),line=dict(color="#00d4ff",width=2),
                    annotation_text=f"Mean: {np.mean(all_rets):.1f}%")
                fig_dist.update_layout(height=250,template="plotly_dark",
                    title="Return distribution across all 100 AIs",
                    paper_bgcolor="#080818",plot_bgcolor="#0d0d1a",
                    margin=dict(l=0,r=0,t=50,b=0))
                st.plotly_chart(fig_dist,use_container_width=True)

# ─── SESSIONS TAB ─────────────────────────────────────────────────────────────
with tab_sessions:
    st.subheader("Trading session guide")
    st.markdown("All times **UTC**. Best signals at session opens and London/NY overlap.")
    utc_now=datetime.now(ZoneInfo("UTC")); hf_now=utc_now.hour+utc_now.minute/60
    session_rows=[
        ("Tokyo",   "00:00–09:00","03:00–08:00","BTC, ETH","Low volume. BTC drifts or spikes randomly. Avoid stocks and gold.","#7C3AED"),
        ("London",  "08:00–17:00","08:00–10:00","Gold, BTC","Strong breakout potential at open. Gold reacts to EU data. BTC picks up.","#2563EB"),
        ("New York","13:00–22:00","13:30–16:00","NQ, SPY, Gold, BTC","Highest volume. US open at 13:30 UTC spikes all markets.","#059669"),
        ("Overlap", "13:00–17:00","13:00–15:00","All","PRIME TIME — tightest spreads, sharpest signals, biggest moves.","#D97706"),
        ("Off-hours","22:00–00:00","Avoid","None","Very thin. Random BTC gaps. Stay out unless you know why.","#555"),
    ]
    starts_map={"Tokyo":0,"London":8,"New York":13,"Overlap":13,"Off-hours":22}
    ends_map  ={"Tokyo":9,"London":17,"New York":22,"Overlap":17,"Off-hours":24}
    for sname,hours,best,mkts,desc,sc in session_rows:
        is_now=starts_map.get(sname,0)<=hf_now<ends_map.get(sname,99)
        border=sc if is_now else "#1a1a2e"
        badge=f' <span style="background:{sc};color:#fff;border-radius:4px;padding:1px 8px;font-size:11px">ACTIVE NOW</span>' if is_now else ""
        st.markdown(
            f'<div style="border:1.5px solid {border};border-radius:10px;padding:14px 18px;margin-bottom:10px;background:#0d0d1a">'
            f'<div style="font-size:15px;font-weight:700;color:{sc}">{sname}{badge}</div>'
            f'<div style="font-size:12px;color:#666;margin-top:4px">Hours: {hours} | Best entry: {best} | Markets: {mkts}</div>'
            f'<div style="font-size:13px;color:#aaa;margin-top:6px">{desc}</div>'
            f'</div>',unsafe_allow_html=True)
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
