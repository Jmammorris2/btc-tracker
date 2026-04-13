import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time, json

st.set_page_config(page_title="Nigel — AI Trading Intelligence",layout="wide",page_icon="🧠",initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;700&family=Syne:wght@400;700;800&display=swap');
html,body,[class*="css"]{font-family:'Syne',sans-serif;}
.main-title{font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:800;
  background:linear-gradient(90deg,#00ff88,#00d4ff,#a78bfa);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;letter-spacing:-0.03em;margin-bottom:0;}
.subtitle{color:#444466;font-size:12px;font-family:'JetBrains Mono',monospace;margin-bottom:18px;letter-spacing:.05em;}
.sig-badge{display:inline-block;border-radius:4px;padding:3px 12px;font-size:11px;font-weight:700;
  letter-spacing:.06em;font-family:'JetBrains Mono',monospace;}
.sig-buy{background:rgba(0,255,136,0.1);color:#00ff88;border:1px solid rgba(0,255,136,0.3);}
.sig-sell{background:rgba(255,68,68,0.1);color:#ff4444;border:1px solid rgba(255,68,68,0.3);}
.sig-hold{background:rgba(136,136,136,0.1);color:#888;border:1px solid rgba(136,136,136,0.3);}
.note-card{border-radius:10px;padding:13px 17px;margin-bottom:9px;font-size:13px;line-height:1.65;}
.note-watch{background:#1a1400;border-left:3px solid #f0a500;color:#ffd166;}
.note-buy{background:#001a0a;border-left:3px solid #00ff88;color:#88ffcc;}
.note-sell{background:#1a0000;border-left:3px solid #ff4444;color:#ff9999;}
.note-info{background:#001020;border-left:3px solid #00d4ff;color:#88ddff;}
.pos-long{background:#001a0a;border-left:3px solid #00ff88;border-radius:8px;padding:10px 14px;font-size:12px;margin-bottom:6px;}
.pos-short{background:#1a0000;border-left:3px solid #ff4444;border-radius:8px;padding:10px 14px;font-size:12px;margin-bottom:6px;}
.pos-none{background:#111;border-radius:8px;padding:10px 14px;font-size:12px;color:#555;margin-bottom:6px;}
.bt-stat{background:#0a0a1a;border:1px solid #1a1a2e;border-radius:8px;padding:10px;text-align:center;}
.bt-val{font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;}
.bt-lbl{font-size:10px;color:#555;margin-top:2px;}
.poly-card{background:#0a0a18;border:1px solid #1a1a30;border-radius:10px;padding:14px 18px;margin-bottom:10px;}
.stTabs [data-baseweb="tab-list"]{background:#080818;border-radius:10px;padding:4px;}
.stTabs [data-baseweb="tab"]{border-radius:8px;color:#666;font-size:13px;}
.stTabs [aria-selected="true"]{background:#1a1a3a;color:#fff;}
</style>
""",unsafe_allow_html=True)

# ── KEY GATE ──────────────────────────────────────────────────────────────────
def get_keys():
    p=st.secrets.get("POLYGON_KEY","") if hasattr(st,"secrets") else ""
    a=st.secrets.get("ANTHROPIC_KEY","") if hasattr(st,"secrets") else ""
    return st.session_state.get("POLYGON_KEY",p),st.session_state.get("ANTHROPIC_KEY",a)

POLYGON_KEY,ANTHROPIC_KEY=get_keys()

if not POLYGON_KEY:
    st.markdown('<div class="main-title">🧠 Nigel</div>',unsafe_allow_html=True)
    st.markdown("### Setup — Enter your API keys")
    with st.form("keys"):
        pk=st.text_input("Polygon.io API Key",type="password")
        ak=st.text_input("Anthropic API Key (optional)",type="password")
        if st.form_submit_button("Launch Nigel"):
            if pk:
                st.session_state["POLYGON_KEY"]=pk
                st.session_state["ANTHROPIC_KEY"]=ak
                st.rerun()
            else:
                st.error("Polygon key required.")
    st.stop()

# ── MARKETS ───────────────────────────────────────────────────────────────────
MARKETS={
    "BTC":{"label":"BTC / USD","poly_ticker":"X:BTCUSD","cg_id":"bitcoin","crypto":True,"color":"#f0a500"},
    "ETH":{"label":"ETH / USD","poly_ticker":"X:ETHUSD","cg_id":"ethereum","crypto":True,"color":"#627eea"},
    "NQ": {"label":"NASDAQ (QQQ)","poly_ticker":"QQQ","cg_id":None,"crypto":False,"color":"#378add"},
    "GOLD":{"label":"Gold (GLD)","poly_ticker":"GLD","cg_id":None,"crypto":False,"color":"#ba7517"},
    "SPY":{"label":"S&P 500 (SPY)","poly_ticker":"SPY","cg_id":None,"crypto":False,"color":"#22c55e"},
}

# ── 100 TRADER CONFIGS ────────────────────────────────────────────────────────
def _make_100():
    base=[(0.008,2.5,(35,65),True,False,False),(0.015,2.0,(20,80),False,True,False),
          (0.005,1.5,(25,75),False,False,True),(0.010,3.0,(30,70),True,False,False),
          (0.012,2.0,(20,80),False,False,True),(0.018,2.5,(25,75),False,True,False),
          (0.006,4.0,(40,60),True,False,False),(0.020,1.8,(20,80),False,False,False),
          (0.004,3.0,(38,62),True,False,False),(0.014,2.2,(22,78),False,True,False)]
    styles=["Momentum","Reversal","Breakout","Scalp","Swing","Position","Day","Macro","Quant","Hybrid"]
    tags=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Eta","Theta","Iota","Kappa"]
    out=[]
    for i in range(100):
        b=base[i%10]; noise=1+(i%7-3)*0.04
        risk=round(min(0.025,max(0.003,b[0]*noise)),4)
        rr=round(max(1.2,b[1]+(i%5-2)*0.15),2)
        lo=max(15,b[2][0]+(i%7-3)*2); hi=min(85,b[2][1]+(i%7-3)*2)
        out.append({"name":f"{styles[i%10]}-{tags[i%10]}{i+1}","risk":risk,"rr":rr,
                    "rsi_range":(lo,hi),"strong_only":b[3],"bb_break":b[4],"rsi_extreme":b[5]})
    return out

ALL100=_make_100()

# ── SESSION STATE ─────────────────────────────────────────────────────────────
def _make_trader(name,emoji,style,desc,risk,rr,filters,sources):
    return dict(name=name,emoji=emoji,style=style,desc=desc,risk_pct=risk,rr=rr,
                signal_filters=filters,data_sources=sources,balance=25000.0,peak=25000.0,
                trades=[],open_pos=None,history=[25000.0],win_streak=0,loss_streak=0)

if "traders" not in st.session_state:
    st.session_state["traders"]=[
        _make_trader("Macro Maya","🌍","Multi-source macro","Full alignment: RSI+MACD+MA+BB+Volume+Fear/Greed.",
            0.008,2.5,{"rsi_range":(35,65),"strong_only":True,"bb_break":False,"rsi_extreme":False},
            ["price","volume","rsi","macd","bb","fear_greed","on_chain"]),
        _make_trader("Momentum Mike","🚀","Breakout specialist","BB breakouts. ATR stops. Loves volatility.",
            0.015,2.0,{"rsi_range":(20,80),"strong_only":False,"bb_break":True,"rsi_extreme":False},
            ["price","rsi","macd","bb","atr","volume"]),
        _make_trader("Scalp Sam","⚡","RSI+VWAP scalper","Tight stops, high frequency. RSI extremes.",
            0.005,1.5,{"rsi_range":(25,75),"strong_only":False,"bb_break":False,"rsi_extreme":True},
            ["price","rsi","vwap","stoch","cci"]),
        _make_trader("Trend Tina","📈","Swing trend follower","EMA50+RSI 40-60+MACD. Bigger targets.",
            0.010,3.0,{"rsi_range":(30,70),"strong_only":True,"bb_break":False,"rsi_extreme":False},
            ["price","rsi","macd","ema50","volume"]),
        _make_trader("Contrarian Carl","🔄","Counter-trend reversal","Buys extreme oversold, sells overbought.",
            0.012,2.0,{"rsi_range":(20,80),"strong_only":False,"bb_break":False,"rsi_extreme":True},
            ["price","rsi","stoch","cci","bb"]),
    ]

for k,v in [("notes",[]),("bt_results",{}),("ensemble_results",{}),("grand_strategy",{})]:
    if k not in st.session_state: st.session_state[k]=v
if "last_ai" not in st.session_state: st.session_state["last_ai"]=0.0
if "ensemble_ran" not in st.session_state: st.session_state["ensemble_ran"]=False

TRADERS=st.session_state["traders"]

# ── DATA FETCHERS ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_cg(cg_id,days=100):
    try:
        d=requests.get(f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
                       f"?vs_currency=usd&days={days}&interval=daily",timeout=15).json()
        prices=[p[1] for p in d["prices"]]; volumes=[v[1] for v in d.get("total_volumes",[])]
        dates=[pd.Timestamp(p[0],unit="ms") for p in d["prices"]]
        return pd.DataFrame({"close":prices,"volume":volumes},index=dates)
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_poly_ohlcv(ticker,key,days=100):
    try:
        to=datetime.today().strftime("%Y-%m-%d"); fr=(datetime.today()-timedelta(days=days)).strftime("%Y-%m-%d")
        d=requests.get(f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{fr}/{to}"
                       f"?adjusted=true&sort=asc&limit={days}&apiKey={key}",timeout=15).json()
        if "results" not in d or len(d["results"])<5: return pd.DataFrame()
        df=pd.DataFrame(d["results"]); df.index=pd.to_datetime(df["t"],unit="ms")
        return df.rename(columns={"o":"open","h":"high","l":"low","c":"close","v":"volume"})[["open","high","low","close","volume"]]
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d=requests.get("https://api.alternative.me/fng/?limit=14",timeout=10).json()["data"]
        return {"value":int(d[0]["value"]),"label":d[0]["value_classification"],"history":[int(x["value"]) for x in d]}
    except: return {"value":50,"label":"Neutral","history":[50]*14}

@st.cache_data(ttl=600)
def fetch_on_chain():
    r={}
    try:
        md=requests.get("https://api.coingecko.com/api/v3/coins/bitcoin",timeout=10).json().get("market_data",{})
        r["market_cap"]=md.get("market_cap",{}).get("usd",0); r["volume_24h"]=md.get("total_volume",{}).get("usd",0)
        r["change_7d"]=md.get("price_change_percentage_7d",0); r["change_30d"]=md.get("price_change_percentage_30d",0)
        r["ath_pct"]=md.get("ath_change_percentage",{}).get("usd",0)
    except: pass
    return r

@st.cache_data(ttl=180)
def fetch_polymarket():
    try:
        resp=requests.get("https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=30&order=volume&ascending=false",timeout=12)
        if resp.status_code!=200: return []
        out=[]
        for m in resp.json():
            try:
                q=m.get("question",""); vol=float(m.get("volume","0") or 0); liq=float(m.get("liquidity","0") or 0)
                pr=m.get("outcomePrices","[]"); oc=m.get("outcomes","[]")
                if isinstance(pr,str): pr=json.loads(pr)
                if isinstance(oc,str): oc=json.loads(oc)
                if not oc or not pr: continue
                pairs=sorted(zip(oc,[float(p) for p in pr]),key=lambda x:x[1],reverse=True)
                ql=q.lower()
                is_btc=any(w in ql for w in ["bitcoin","btc","crypto","ethereum","eth","coin"])
                is_mac=any(w in ql for w in ["fed","rate","inflation","recession","nasdaq","s&p","stock","gdp"])
                tag="🟠 BTC/Crypto" if is_btc else "📈 Macro" if is_mac else "🌐 Other"
                out.append({"question":q,"volume":vol,"liquidity":liq,"top_outcome":pairs[0][0],
                            "top_pct":round(pairs[0][1]*100,1),"pairs":list(pairs[:4]),
                            "tag":tag,"is_btc":is_btc,"is_macro":is_mac})
            except: continue
        return out
    except: return []

# ── INDICATORS ────────────────────────────────────────────────────────────────
def add_indicators(df):
    if df.empty or len(df)<26: return df
    df=df.copy()
    df["ema8"]=df["close"].ewm(span=8,adjust=False).mean()
    df["ema21"]=df["close"].ewm(span=21,adjust=False).mean()
    df["ema50"]=df["close"].ewm(span=50,adjust=False).mean()
    e12=df["close"].ewm(span=12,adjust=False).mean(); e26=df["close"].ewm(span=26,adjust=False).mean()
    df["macd"]=e12-e26; df["macd_signal"]=df["macd"].ewm(span=9,adjust=False).mean(); df["macd_hist"]=df["macd"]-df["macd_signal"]
    delta=df["close"].diff(); gain=delta.where(delta>0,0.0).rolling(14).mean()
    loss=(-delta.where(delta<0,0.0)).rolling(14).mean().replace(0,1e-10)
    df["rsi"]=100-(100/(1+gain/loss))
    df["bb_mid"]=df["close"].rolling(20).mean(); df["bb_std"]=df["close"].rolling(20).std()
    df["bb_upper"]=df["bb_mid"]+2*df["bb_std"]; df["bb_lower"]=df["bb_mid"]-2*df["bb_std"]
    df["bb_pct"]=(df["close"]-df["bb_lower"])/(df["bb_upper"]-df["bb_lower"]+1e-10)
    if "high" in df.columns:
        hl=df["high"]-df["low"]; hc=(df["high"]-df["close"].shift()).abs(); lc=(df["low"]-df["close"].shift()).abs()
        df["atr"]=pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(14).mean()
    else: df["atr"]=df["close"]*0.02
    lo14=df["close"].rolling(14).min(); hi14=df["close"].rolling(14).max()
    df["stoch_k"]=100*(df["close"]-lo14)/(hi14-lo14+1e-10); df["stoch_d"]=df["stoch_k"].rolling(3).mean()
    if "high" in df.columns:
        tp=(df["high"]+df["low"]+df["close"])/3; df["cci"]=(tp-tp.rolling(20).mean())/(0.015*tp.rolling(20).std()+1e-10)
    else: df["cci"]=(df["close"]-df["close"].rolling(20).mean())/(df["close"].rolling(20).std()+1e-10)
    if "volume" in df.columns:
        df["vwap"]=(df["close"]*df["volume"]).rolling(20).sum()/(df["volume"].rolling(20).sum()+1e-10)
        df["vol_ma"]=df["volume"].rolling(20).mean(); df["vol_ratio"]=df["volume"]/(df["vol_ma"]+1e-10)
    bull_ema=df["ema8"]>df["ema21"]; bull_macd=df["macd"]>df["macd_signal"]
    mcu=bull_macd & ~bull_macd.shift(1).fillna(False); mcd=~bull_macd & bull_macd.shift(1).fillna(False)
    df["signal"]=np.where(bull_ema & mcu & df["rsi"].between(35,68),"STRONG BUY",
        np.where(bull_ema & bull_macd & df["rsi"].between(38,65),"BUY",
        np.where(~bull_ema & mcd & (df["rsi"]>32),"STRONG SELL",
        np.where(~bull_ema & ~bull_macd & (df["rsi"]>38),"SELL",
        np.where(df["rsi"]<28,"OVERSOLD",np.where(df["rsi"]>74,"OVERBOUGHT","HOLD"))))))
    return df

# ── BACKTEST ENGINE ───────────────────────────────────────────────────────────
def run_backtest(df,cfg,label=""):
    if df.empty or "signal" not in df.columns or len(df)<30: return {"error":"insufficient data"}
    df=df.dropna(subset=["close","signal","rsi"]).copy()
    capital=10000.0; cash=capital; pos=0.0; entry=0.0; trades=[]; equity=[]
    stop_pct=0.025; rr=float(cfg.get("rr",2.0))
    f=cfg.get("signal_filters",cfg)

    def direction(row):
        s=row["signal"]; r=float(row.get("rsi",50)); rng=f.get("rsi_range",(20,80))
        if not (rng[0]<=r<=rng[1]): return None
        if f.get("strong_only") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"): return None
        if f.get("bb_break"):
            bp=float(row.get("bb_pct",0.5))
            if s in ("BUY","STRONG BUY") and bp>0.8: return "long"
            if s in ("SELL","STRONG SELL") and bp<0.2: return "short"
        if f.get("rsi_extreme"):
            if r<32: return "long"
            if r>68: return "short"
        if s in ("BUY","STRONG BUY","OVERSOLD"): return "long"
        if s in ("SELL","STRONG SELL","OVERBOUGHT"): return "short"
        return None

    for i in range(1,len(df)):
        row=df.iloc[i]; price=float(row["close"])
        equity.append({"date":df.index[i],"equity":cash+pos*price})
        if pos>0 and entry>0:
            if price<=entry*(1-stop_pct) or price>=entry*(1+stop_pct*rr):
                pnl=(price-entry)*pos; cash+=pos*price
                trades.append({"type":"Long","entry":entry,"exit":price,"pnl":pnl,"date":df.index[i],"reason":"TP" if price>=entry*(1+stop_pct*rr) else "SL"})
                pos=0; entry=0; continue
        if pos<0 and entry>0:
            if price>=entry*(1+stop_pct) or price<=entry*(1-stop_pct*rr):
                pnl=(entry-price)*abs(pos); cash+=abs(pos)*price
                trades.append({"type":"Short","entry":entry,"exit":price,"pnl":pnl,"date":df.index[i],"reason":"TP" if price<=entry*(1-stop_pct*rr) else "SL"})
                pos=0; entry=0; continue
        prev=df.iloc[i-1]; d=direction(prev)
        if pos==0:
            if d=="long": u=cash*0.95/price; pos=u; cash-=u*price; entry=price
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
            "max_win_streak":max(streaks) if streaks else 0,"max_loss_streak":abs(min(streaks)) if streaks else 0,
            "equity_curve":eq,"trade_list":tdf,"final_equity":round(cash,2),"label":label}

# ── 100-AI ENSEMBLE ───────────────────────────────────────────────────────────
def run_ensemble(df_map):
    results_by_mkt={}
    for mk,df in df_map.items():
        if df.empty: continue
        mkt_res=[]
        for cfg in ALL100:
            bt=run_backtest(df,{"signal_filters":{k:cfg[k] for k in ("rsi_range","strong_only","bb_break","rsi_extreme")},"rr":cfg["rr"]},cfg["name"])
            if "error" not in bt:
                score=bt["sharpe"]*(bt["win_rate"]/50)*max(0.1,1-abs(bt["max_drawdown"])/50)
                mkt_res.append({**bt,"name":cfg["name"],"score":round(score,4),"rsi_range":cfg["rsi_range"],"rr":cfg["rr"],
                                "bb_break":cfg["bb_break"],"rsi_extreme":cfg["rsi_extreme"],"strong_only":cfg["strong_only"]})
        mkt_res.sort(key=lambda x:x["score"],reverse=True)
        results_by_mkt[mk]=mkt_res
    grand={}
    for mk,res in results_by_mkt.items():
        if not res: continue
        top=res[:20]
        lo=round(np.mean([r["rsi_range"][0] for r in top])); hi=round(np.mean([r["rsi_range"][1] for r in top]))
        rr=round(np.mean([r["rr"] for r in top]),2)
        df2=df_map.get(mk,pd.DataFrame()); sig="HOLD"; conf=50; rsi_v=50
        if not df2.empty and "rsi" in df2.columns:
            row=df2.iloc[-1]; sig=str(row.get("signal","HOLD")); rsi_v=float(row.get("rsi",50))
            in_range=lo<=rsi_v<=hi; is_b="BUY" in sig or sig=="OVERSOLD"; is_s="SELL" in sig or sig=="OVERBOUGHT"
            conf=80 if (in_range and (is_b or is_s)) else 55 if (is_b or is_s) else 30
        grand[mk]={"rsi_range":(lo,hi),"rr":rr,"use_bb":sum(1 for r in top if r["bb_break"])>10,
                   "use_extreme":sum(1 for r in top if r["rsi_extreme"])>10,"use_strong":sum(1 for r in top if r["strong_only"])>10,
                   "avg_ret":round(np.mean([r["total_return"] for r in top]),2),
                   "avg_sharpe":round(np.mean([r["sharpe"] for r in top]),2),
                   "avg_wr":round(np.mean([r["win_rate"] for r in top]),1),
                   "best":top[0]["name"],"signal":sig,"conf":conf,"rsi":round(rsi_v,1)}
    return results_by_mkt,grand

# ── SIGNAL ENGINE ─────────────────────────────────────────────────────────────
def get_signal(df,fg=None):
    if df.empty or "rsi" not in df.columns: return {"signal":"HOLD","conf":50,"rsi":50,"price":0,"bb_pct":0.5,"atr":0,"stoch_k":50}
    row=df.iloc[-1]; price=float(row["close"]); rsi_v=float(row.get("rsi",50)); s=str(row.get("signal","HOLD"))
    conf={"STRONG BUY":82,"BUY":66,"STRONG SELL":80,"SELL":64,"OVERSOLD":74,"OVERBOUGHT":72}.get(s,50)
    if fg:
        fv=fg.get("value",50)
        if s in ("BUY","STRONG BUY","OVERSOLD") and fv<30: conf=min(95,conf+8)
        if s in ("SELL","STRONG SELL","OVERBOUGHT") and fv>75: conf=min(95,conf+8)
    return {"signal":s,"conf":conf,"rsi":rsi_v,"price":price,"bb_pct":float(row.get("bb_pct",0.5)),
            "atr":float(row.get("atr",price*0.02)),"stoch_k":float(row.get("stoch_k",50))}

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
                    pnl=round(pnl,2),result=res,reason="TP" if hit_tp else "SL",time=datetime.now().strftime("%H:%M")))
                tr["history"].append(round(tr["balance"],2))
                if res=="win": tr["win_streak"]=tr.get("win_streak",0)+1; tr["loss_streak"]=0
                else: tr["loss_streak"]=tr.get("loss_streak",0)+1; tr["win_streak"]=0
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
                direction="long" if is_b else "short"; p=sig["price"]; atr=sig.get("atr",p*0.02); sd=atr*1.5
                stop=p-sd if is_b else p+sd; tp=p+sd*tr["rr"] if is_b else p-sd*tr["rr"]
                risk=tr["balance"]*tr["risk_pct"]; units=risk/max(sd,0.001)
                tr["open_pos"]=dict(market=mk,dir=direction,entry=round(p,2),stop=round(stop,2),
                    tp=round(tp,2),units=units,risk_amt=round(risk,2),time=datetime.now().strftime("%H:%M"))
                break

# ── CHART BUILDERS ────────────────────────────────────────────────────────────
def build_chart(df,title,color="#00ff88",show_sigs=True,bt=None):
    if df.empty: return None

    # ── CRITICAL FIX: build volume colors as proper rgba() strings ──
    def vol_colors(dataframe):
        closes=dataframe["close"].tolist()
        opens=dataframe["open"].tolist() if "open" in dataframe.columns else closes[:]
        n=min(len(closes),len(opens))
        # Must be "rgba(r,g,b,a)" format — hex with alpha (#rrggbbaa) rejected by Plotly Bar
        return ["rgba(0,204,102,0.6)" if float(closes[i])>=float(opens[i]) else "rgba(204,51,51,0.6)"
                for i in range(n)]

    fig=make_subplots(rows=4,cols=1,shared_xaxes=True,row_heights=[0.50,0.18,0.18,0.14],
                      vertical_spacing=0.03,subplot_titles=["","MACD","RSI","Volume"])
    # BB bands
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index,y=df["bb_upper"],line=dict(color="rgba(120,120,220,0.25)",width=1),showlegend=False,name="BB Up"),row=1,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["bb_lower"],line=dict(color="rgba(120,120,220,0.25)",width=1),fill="tonexty",fillcolor="rgba(100,100,200,0.05)",showlegend=False,name="BB Lo"),row=1,col=1)
    # Price candles or line
    if "open" in df.columns and "high" in df.columns:
        fig.add_trace(go.Candlestick(x=df.index,open=df["open"],high=df["high"],low=df["low"],close=df["close"],
            name="Price",increasing_line_color="#00ff88",decreasing_line_color="#ff4444",
            increasing_fillcolor="rgba(0,255,136,0.2)",decreasing_fillcolor="rgba(255,68,68,0.2)"),row=1,col=1)
    else:
        fig.add_trace(go.Scatter(x=df.index,y=df["close"],name="Price",line=dict(color=color,width=2)),row=1,col=1)
    # MAs
    for col_n,mc,lbl in [("ema8","#5DCAA5","EMA8"),("ema21","#ED93B1","EMA21"),("ema50","#F59E0B","EMA50")]:
        if col_n in df.columns:
            fig.add_trace(go.Scatter(x=df.index,y=df[col_n],name=lbl,line=dict(color=mc,width=1.2,dash="dot")),row=1,col=1)
    # Signals
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
    # BT trades overlay
    if bt and "trade_list" in bt and not bt["trade_list"].empty:
        for _,tr in bt["trade_list"].iterrows():
            try:
                fig.add_trace(go.Scatter(x=[tr["date"]],y=[tr["entry"]],mode="markers",
                    marker=dict(symbol="circle",size=9,color="#00ff88" if tr["pnl"]>0 else "#ff4444",opacity=0.8),
                    showlegend=False),row=1,col=1)
            except: pass
    # MACD
    if "macd" in df.columns:
        mhist=df["macd_hist"].fillna(0).tolist()
        mc2=["rgba(0,204,102,0.8)" if v>=0 else "rgba(204,51,51,0.8)" for v in mhist]
        fig.add_trace(go.Bar(x=df.index,y=df["macd_hist"],marker_color=mc2,name="MACD Hist",showlegend=False),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["macd"],line=dict(color=color,width=1.5),name="MACD"),row=2,col=1)
        fig.add_trace(go.Scatter(x=df.index,y=df["macd_signal"],line=dict(color="#ED93B1",width=1.5),name="Signal"),row=2,col=1)
    # RSI
    if "rsi" in df.columns:
        fig.add_trace(go.Scatter(x=df.index,y=df["rsi"],line=dict(color="#a78bfa",width=2),name="RSI"),row=3,col=1)
        for lvl,lc in [(70,"rgba(255,68,68,0.6)"),(30,"rgba(0,255,136,0.6)"),(50,"rgba(80,80,80,0.5)")]:
            fig.add_hline(y=lvl,line=dict(color=lc,width=1,dash="dash"),row=3,col=1)
    # Volume — THE FIX: use rgba() strings, NOT hex-with-alpha
    if "volume" in df.columns:
        vc=vol_colors(df)
        n=min(len(df.index),len(df["volume"]),len(vc))
        fig.add_trace(go.Bar(x=df.index[:n],y=df["volume"].tolist()[:n],
            marker_color=vc[:n],name="Volume",showlegend=False),row=4,col=1)
        if "vol_ma" in df.columns:
            fig.add_trace(go.Scatter(x=df.index,y=df["vol_ma"],line=dict(color="#F59E0B",width=1),name="Vol MA"),row=4,col=1)
    fig.update_layout(height=820,template="plotly_dark",title=dict(text=title,font=dict(size=14,color="#ccc")),
        paper_bgcolor="#080818",plot_bgcolor="#0a0a18",xaxis_rangeslider_visible=False,
        legend=dict(orientation="h",yanchor="bottom",y=1.02,font=dict(size=10)),margin=dict(l=0,r=0,t=50,b=0))
    fig.update_xaxes(gridcolor="#111128",zerolinecolor="#111128")
    fig.update_yaxes(gridcolor="#111128",zerolinecolor="#111128")
    return fig

def build_equity_chart(bts,start=10000):
    fig=go.Figure()
    COLORS={"Macro Maya":"#00ff88","Momentum Mike":"#00d4ff","Scalp Sam":"#f0a500","Trend Tina":"#a78bfa","Contrarian Carl":"#ff6b6b"}
    for name,bt in bts.items():
        if bt and "equity_curve" in bt:
            eq=bt["equity_curve"]; ret=(eq["equity"].iloc[-1]-start)/start*100
            fig.add_trace(go.Scatter(x=eq["date"],y=eq["equity"],name=f"{name} ({ret:+.1f}%)",
                line=dict(color=COLORS.get(name,"#fff"),width=2)))
    fig.add_hline(y=start,line=dict(color="#444",width=1,dash="dot"),annotation_text=f"${start:,} start")
    fig.update_layout(height=340,template="plotly_dark",title="Equity curves",paper_bgcolor="#080818",
        plot_bgcolor="#0a0a18",legend=dict(orientation="h",yanchor="bottom",y=1.02),margin=dict(l=0,r=0,t=50,b=0))
    return fig

def build_monthly(bt):
    if not bt or "equity_curve" not in bt: return None
    eq=bt["equity_curve"].copy(); eq["month"]=pd.to_datetime(eq["date"]).dt.to_period("M")
    mo=eq.groupby("month")["equity"].last().pct_change()*100
    fig=go.Figure(go.Bar(x=[str(m) for m in mo.index],y=mo.fillna(0),
        marker_color=["rgba(0,204,102,0.8)" if v>=0 else "rgba(204,51,51,0.8)" for v in mo.fillna(0)],
        text=[f"{v:+.1f}%" for v in mo.fillna(0)],textposition="outside",textfont=dict(size=9,color="#aaa")))
    fig.add_hline(y=0,line=dict(color="#444",width=1))
    fig.update_layout(height=220,template="plotly_dark",title="Monthly returns",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",margin=dict(l=0,r=0,t=40,b=0))
    return fig

def build_drawdown(bt):
    if not bt or "equity_curve" not in bt: return None
    eq=bt["equity_curve"].copy(); dd=(eq["equity"]-eq["equity"].cummax())/eq["equity"].cummax()*100
    fig=go.Figure(go.Scatter(x=eq["date"],y=dd,fill="tozeroy",fillcolor="rgba(255,68,68,0.12)",line=dict(color="#ff4444",width=1.5),name="DD%"))
    fig.update_layout(height=180,template="plotly_dark",title="Drawdown %",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",margin=dict(l=0,r=0,t=40,b=0))
    return fig

# ── NOTES ─────────────────────────────────────────────────────────────────────
def push_note(t,mk,txt):
    st.session_state["notes"].insert(0,{"type":t,"market":mk,"text":txt,"time":datetime.now().strftime("%H:%M")})
    if len(st.session_state["notes"])>60: st.session_state["notes"].pop()

def generate_notes(market_signals,fg,on_chain,sessions,ak):
    if time.time()-st.session_state["last_ai"]<90: return
    st.session_state["last_ai"]=time.time()
    labels={mk:v["label"] for mk,v in MARKETS.items()}
    if not ak:
        for mk,sig in market_signals.items():
            r,s=sig["rsi"],sig["signal"]; lbl=labels.get(mk,mk)
            if r>72 or s=="OVERBOUGHT": push_note("watch",mk,f"**{lbl}** running hot at RSI {r:.0f}. Don't chase — wait for a pullback.")
            elif r<30 or s=="OVERSOLD": push_note("buy",mk,f"**{lbl}** beaten down at RSI {r:.0f}. Watch for one green candle, then consider a small entry.")
            elif s=="STRONG BUY": push_note("buy",mk,f"**{lbl}** setting up — averages pointing up together. Look for confirmation candle.")
            elif s=="STRONG SELL": push_note("sell",mk,f"**{lbl}** flipped bearish. Stay out of new longs, tighten stops.")
        return
    try:
        summ="; ".join(f"{labels.get(mk,mk)}: RSI={v['rsi']:.0f} {v['signal']}" for mk,v in market_signals.items())
        fg_s=f"Fear&Greed={fg['value']} ({fg['label']})" if fg else ""
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":ak,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":900,
                  "messages":[{"role":"user","content":
                    f"You are Nigel, a friendly trading coach. Markets: {summ}. {fg_s}. Sessions: {', '.join(sessions)}. "
                    f"Write 5 short plain-English alerts like texting a mate. No jargon. "
                    f"Return ONLY JSON array: [{{'type':'watch|buy|sell|info','market':'BTC|ETH|NQ|GOLD|SPY','text':'...'}}]"}]},timeout=25)
        for n in json.loads(resp.json()["content"][0]["text"].strip().replace("```json","").replace("```","")):
            push_note(n.get("type","info"),n.get("market","BTC"),n.get("text",""))
    except:
        for mk,sig in market_signals.items():
            r,s=sig["rsi"],sig["signal"]; lbl=labels.get(mk,mk)
            if r>70: push_note("watch",mk,f"**{lbl}** RSI {r:.0f} — watch for drop.")
            elif r<30: push_note("buy",mk,f"**{lbl}** RSI {r:.0f} — watch for bounce.")

# ── SESSION BANNER ────────────────────────────────────────────────────────────
SESSION_TIPS={"Tokyo":"Quiet. BTC/ETH can drift. Avoid stocks.","London":"Gold + BTC wake up. Watch EU data breakouts.",
              "New York":"Prime time — all markets active. Sharpest signals.","Overlap":"🔥 PEAK TIME — biggest moves happen here.","Off-hours":"Very thin. Avoid new positions."}
def session_banner():
    utc=datetime.now(ZoneInfo("UTC")); hf=utc.hour+utc.minute/60
    sess=[]
    if 0<=hf<9: sess.append(("Tokyo","#7C3AED"))
    if 8<=hf<17: sess.append(("London","#2563EB"))
    if 13<=hf<22: sess.append(("New York","#059669"))
    if 13<=hf<17: sess.append(("Overlap","#D97706"))
    if not sess: sess.append(("Off-hours","#555"))
    badges=" ".join(f'<span style="background:{c};color:#fff;border-radius:5px;padding:2px 10px;font-size:12px;font-weight:700">{n}</span>' for n,c in sess)
    ny=utc.astimezone(ZoneInfo("America/New_York")); lon=utc.astimezone(ZoneInfo("Europe/London"))
    st.markdown(f'<div style="background:#0a0a18;border:1px solid #1a1a30;border-radius:10px;padding:12px 18px;margin-bottom:16px">'
                f'<div style="margin-bottom:5px">{badges}</div>'
                f'<div style="font-size:13px;color:#aaa;margin-bottom:3px">{SESSION_TIPS.get(sess[0][0],"")}</div>'
                f'<div style="font-size:11px;color:#444">UTC {utc.strftime("%H:%M")} | ET {ny.strftime("%H:%M")} | LDN {lon.strftime("%H:%M")}</div>'
                f'</div>',unsafe_allow_html=True)
    return [n for n,_ in sess]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:1.3rem;font-weight:800;color:#00ff88">🧠 Nigel</div>',unsafe_allow_html=True)
    st.caption("AI Trading Intelligence")
    st.divider()
    with st.expander("🔑 API Keys"):
        np_=st.text_input("Polygon.io Key",value=POLYGON_KEY,type="password")
        na_=st.text_input("Anthropic Key",value=ANTHROPIC_KEY,type="password")
        if st.button("Save Keys"):
            st.session_state["POLYGON_KEY"]=np_; st.session_state["ANTHROPIC_KEY"]=na_
            st.cache_data.clear(); st.rerun()
    st.divider()
    auto_refresh=st.toggle("Auto-refresh (90s)",value=False)
    selected_markets=st.multiselect("Markets",["BTC","ETH","NQ","GOLD","SPY"],default=["BTC","NQ","GOLD"])
    bt_days=st.slider("Backtest window (days)",30,365,90)
    note_filter=st.selectbox("Filter alerts",["ALL","BTC","ETH","NQ","GOLD","SPY"])
    st.divider()
    if st.button("🔄 Refresh"): st.cache_data.clear(); st.rerun()
    if st.button("🗑 Clear alerts"): st.session_state["notes"]=[]; st.rerun()
    if st.button("♻️ Reset traders"): del st.session_state["traders"]; st.rerun()
    if st.button("🧠 Re-run 100-AI Ensemble"): st.session_state["ensemble_ran"]=False
    st.divider()
    st.caption(f"Nigel · {datetime.now().strftime('%H:%M:%S')}")

# ── FETCH DATA ────────────────────────────────────────────────────────────────
if not selected_markets: selected_markets=["BTC","NQ","GOLD"]
with st.spinner("Nigel is loading market data…"):
    all_dfs={}
    for mk in selected_markets:
        info=MARKETS[mk]
        raw=fetch_cg(info["cg_id"],days=max(bt_days+10,110)) if info["crypto"] else fetch_poly_ohlcv(info["poly_ticker"],POLYGON_KEY,days=max(bt_days+10,110))
        all_dfs[mk]=add_indicators(raw)
    fg=fetch_fear_greed(); on_chain=fetch_on_chain() if "BTC" in selected_markets else {}
    poly_mkts=fetch_polymarket()

market_signals={mk:get_signal(all_dfs.get(mk,pd.DataFrame()),fg) for mk in selected_markets}
active_sessions=session_banner()
simulate_traders(market_signals)
generate_notes(market_signals,fg,on_chain,active_sessions,ANTHROPIC_KEY)

if not st.session_state["ensemble_ran"]:
    with st.spinner("🧠 Nigel running 100-AI ensemble (first load, ~30s)…"):
        try:
            ens,grand=run_ensemble(all_dfs)
            st.session_state["ensemble_results"]=ens; st.session_state["grand_strategy"]=grand
            st.session_state["ensemble_ran"]=True
        except: st.session_state["ensemble_ran"]=True

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🧠 Nigel</div>',unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI TRADING INTELLIGENCE · 100-TRADER ENSEMBLE · POLYMARKET FLOW · GRAND STRATEGY</div>',unsafe_allow_html=True)

if fg:
    fv=fg["value"]; fc="#ff4444" if fv<25 else "#ff9900" if fv<45 else "#ffdd00" if fv<55 else "#99ff44" if fv<75 else "#00ff88"
    tip="🔥 Extreme fear = smart buy zone" if fv<25 else "⚠️ Extreme greed = be careful" if fv>75 else ""
    st.markdown(f'<div style="background:#0a0a18;border:1px solid #1a1a30;border-radius:8px;padding:8px 18px;font-size:13px;margin-bottom:12px;display:inline-block">'
                f'Fear & Greed: <span style="color:{fc};font-weight:700;font-size:16px">{fv}</span> <span style="color:{fc}">{fg["label"]}</span>'
                f'<span style="color:#555;font-size:11px;margin-left:8px">{tip}</span></div>',unsafe_allow_html=True)

grand=st.session_state.get("grand_strategy",{})
if grand:
    st.markdown("### 🧠 Nigel's Grand Strategy — 100-AI Consensus")
    gcols=st.columns(len([m for m in selected_markets if m in grand]))
    for col,mk in zip(gcols,[m for m in selected_markets if m in grand]):
        with col:
            gs=grand[mk]; sig=gs["signal"]; conf=gs["conf"]
            is_b="BUY" in sig or sig=="OVERSOLD"; is_s="SELL" in sig or sig=="OVERBOUGHT"
            bc="#00ff88" if is_b else "#ff4444" if is_s else "#555"
            icon="🟢" if is_b else "🔴" if is_s else "⚪"
            st.markdown(f'<div style="border:2px solid {bc};border-radius:12px;padding:14px;background:#0a0a18;margin-bottom:6px">'
                        f'<div style="font-size:10px;color:#555;font-family:JetBrains Mono,monospace">{MARKETS[mk]["label"]} · 100-AI</div>'
                        f'<div style="font-size:1.25rem;font-weight:800;color:{bc};margin:3px 0">{icon} {sig}</div>'
                        f'<div style="font-size:11px;color:#888">Conf:<b style="color:{bc}">{conf}%</b> RSI:{gs["rsi"]} R:R 1:{gs["rr"]}</div>'
                        f'<div style="font-size:10px;color:#444;margin-top:2px">Avg ret:{gs["avg_ret"]:+.1f}% Sharpe:{gs["avg_sharpe"]:.2f}</div>'
                        f'</div>',unsafe_allow_html=True)

st.subheader("Live signals")
pcols=st.columns(len(selected_markets))
for col,mk in zip(pcols,selected_markets):
    with col:
        info=MARKETS[mk]; sig=market_signals.get(mk,{}); p=sig.get("price",0)
        df=all_dfs.get(mk,pd.DataFrame()); chg=0
        if not df.empty and len(df)>1: chg=(float(df["close"].iloc[-1])-float(df["close"].iloc[-2]))/float(df["close"].iloc[-2])*100
        s=sig.get("signal","HOLD"); c=sig.get("conf",50); r=sig.get("rsi",50)
        is_b="BUY" in s or s=="OVERSOLD"; is_s="SELL" in s or s=="OVERBOUGHT"
        bc="#00ff88" if is_b else "#ff4444" if is_s else "#1a1a30"; cc="#00ff88" if chg>=0 else "#ff4444"
        px=f"${p:,.0f}" if mk in ("BTC","ETH") else f"${p:,.2f}"; sc="sig-buy" if is_b else "sig-sell" if is_s else "sig-hold"
        st.markdown(f'<div style="border:2px solid {bc};border-radius:12px;padding:14px;background:#0a0a18;margin-bottom:4px">'
                    f'<div style="font-size:10px;color:#555">{info["label"]}</div>'
                    f'<div style="font-size:22px;font-weight:700;color:{info["color"]};font-family:JetBrains Mono,monospace">{px}</div>'
                    f'<div style="font-size:12px;color:{cc};margin-bottom:8px">{chg:+.2f}% today</div>'
                    f'<span class="sig-badge {sc}">{s}</span><br>'
                    f'<div style="font-size:11px;color:#555;margin-top:3px">Conf:{c}% RSI:{r:.0f} BB:{sig.get("bb_pct",0.5)*100:.0f}%</div>'
                    f'</div>',unsafe_allow_html=True)

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────
t_grand,t_poly,t_alerts,t_traders,t_bt,t_ensemble,t_sessions=st.tabs([
    "🧠 Grand Strategy","🎯 Polymarket","📝 Alerts","🤖 Traders","📊 Backtest","🔬 100-AI Lab","🕐 Sessions"])

# ── GRAND STRATEGY ────────────────────────────────────────────────────────────
with t_grand:
    st.subheader("🧠 Nigel's Grand Strategy")
    if not grand:
        st.info("Running ensemble on first load — refresh in a moment.")
    else:
        sess_now=active_sessions[0] if active_sessions else "Off-hours"
        sw={"Tokyo":{"BTC":1.3,"ETH":1.2,"NQ":0.5,"GOLD":0.7,"SPY":0.5},
            "London":{"BTC":1.1,"ETH":1.0,"NQ":0.8,"GOLD":1.4,"SPY":0.8},
            "New York":{"BTC":1.0,"ETH":0.9,"NQ":1.4,"GOLD":1.1,"SPY":1.4},
            "Overlap":{"BTC":1.2,"ETH":1.1,"NQ":1.2,"GOLD":1.2,"SPY":1.2},
            "Off-hours":{"BTC":0.7,"ETH":0.7,"NQ":0.3,"GOLD":0.5,"SPY":0.3}}.get(sess_now,{})
        scored={mk:{"score":grand[mk]["avg_sharpe"]*sw.get(mk,1.0),"conf":min(99,round(grand[mk]["conf"]*sw.get(mk,1.0))),
                    "signal":grand[mk]["signal"],"rsi":grand[mk]["rsi"],"rr":grand[mk]["rr"],"avg_ret":grand[mk]["avg_ret"]}
                for mk in grand if mk in selected_markets}
        if scored:
            best=max(scored,key=lambda x:scored[x]["score"]); bs=scored[best]; bsig=bs["signal"]
            is_bb="BUY" in bsig or bsig=="OVERSOLD"; is_bs="SELL" in bsig or bsig=="OVERBOUGHT"
            bc="#00ff88" if is_bb else "#ff4444" if is_bs else "#555"
            st.markdown(f'<div style="border:2px solid {bc};border-radius:14px;padding:20px 24px;'
                        f'background:{"#001a0a" if is_bb else "#1a0000" if is_bs else "#111"};margin-bottom:16px">'
                        f'<div style="font-size:11px;color:#555;font-family:JetBrains Mono,monospace">NIGEL\'S TOP PICK — {sess_now.upper()}</div>'
                        f'<div style="font-size:2rem;font-weight:800;color:{bc};margin:4px 0">{"🟢 BUY" if is_bb else "🔴 SELL" if is_bs else "⚪ HOLD"} — {MARKETS[best]["label"]}</div>'
                        f'<div style="font-size:13px;color:#aaa">Confidence: <b style="color:{bc}">{bs["conf"]}%</b> | R:R 1:{bs["rr"]} | Top-20 avg: {bs["avg_ret"]:+.1f}%</div>'
                        f'</div>',unsafe_allow_html=True)
        now_h=datetime.now(ZoneInfo("UTC")).hour
        plan=[(0,8,"00:00–08:00","Tokyo","BTC ETH","Low volume. Crypto only. Trade small.","#7C3AED"),
              (8,13,"08:00–13:00","London","GOLD BTC","EU data. Gold + BTC breakouts form.","#2563EB"),
              (13,17,"13:00–17:00","NY+London Overlap","ALL","🔥 Best window. Use your best signals here.","#D97706"),
              (17,22,"17:00–22:00","New York","NQ SPY BTC","US afternoon. Trail stops tighter.","#059669"),
              (22,24,"22:00–00:00","Off-hours","—","Very thin. Review tomorrow's plan.","#555")]
        st.markdown("### 📅 Today's Plan")
        for h0,h1,times,sname,mkts,tip,sc2 in plan:
            is_now=h0<=now_h<h1; border=sc2 if is_now else "#1a1a30"
            nb=f' <span style="background:{sc2};color:#fff;border-radius:3px;padding:1px 7px;font-size:10px">NOW</span>' if is_now else ""
            st.markdown(f'<div style="border:1.5px solid {border};border-radius:8px;padding:10px 16px;margin-bottom:6px;background:#0a0a18">'
                        f'<div style="font-size:12px;font-weight:700;color:{sc2};font-family:JetBrains Mono,monospace">{times} — {sname}{nb}</div>'
                        f'<div style="font-size:11px;color:#555">Markets: {mkts}</div>'
                        f'<div style="font-size:12px;color:#aaa;margin-top:2px">{tip}</div>'
                        f'</div>',unsafe_allow_html=True)
        st.markdown("### 🎛️ Consensus Parameters")
        param_rows=[]
        for mk in selected_markets:
            if mk not in grand: continue
            gs=grand[mk]
            param_rows.append({"Market":MARKETS[mk]["label"],"RSI":f"{gs['rsi_range'][0]}–{gs['rsi_range'][1]}","R:R":f"1:{gs['rr']}",
                               "BB Break":"✅" if gs["use_bb"] else "❌","RSI Extreme":"✅" if gs["use_extreme"] else "❌",
                               "Strong Only":"✅" if gs["use_strong"] else "❌",
                               "Avg Return":f"{gs['avg_ret']:+.1f}%","Avg WR":f"{gs['avg_wr']:.0f}%","Sharpe":f"{gs['avg_sharpe']:.2f}"})
        if param_rows: st.dataframe(pd.DataFrame(param_rows),width='stretch',hide_index=True)

# ── POLYMARKET ────────────────────────────────────────────────────────────────
with t_poly:
    st.subheader("🎯 Polymarket — Real Money Prediction Markets")
    st.caption("Real traders betting real money on where prices go. The smartest sentiment signal available.")
    if not poly_mkts:
        st.warning("Could not load Polymarket data. Try refreshing.")
    else:
        ptab_all,ptab_btc,ptab_mac=st.tabs(["📊 All","🟠 BTC/Crypto","📈 Macro"])

        def render_poly(mkts_list,label=""):
            if not mkts_list: st.info(f"No {label} markets right now."); return
            total_vol=sum(m["volume"] for m in mkts_list)
            st.markdown(f'<div style="color:#555;font-size:12px;margin-bottom:10px">Total volume: <b style="color:#00d4ff">${total_vol/1e6:.2f}M</b></div>',unsafe_allow_html=True)
            top8=sorted(mkts_list,key=lambda x:x["volume"],reverse=True)[:8]
            fig=go.Figure(go.Bar(x=[m["volume"]/1e3 for m in top8],
                y=[m["question"][:45]+"…" if len(m["question"])>45 else m["question"] for m in top8],
                orientation="h",marker_color=["rgba(240,165,0,0.8)" if m["is_btc"] else "rgba(55,138,221,0.8)" for m in top8],
                text=[f"${m['volume']/1e3:.0f}k · {m['top_outcome']}: {m['top_pct']}%" for m in top8],
                textposition="auto",textfont=dict(size=10,color="#fff")))
            fig.update_layout(height=340,template="plotly_dark",title="Volume by market ($k)",paper_bgcolor="#080818",
                plot_bgcolor="#0a0a18",xaxis_title="Volume ($k)",margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig,width='stretch',key='pc1')
            # BTC consensus
            btc_rel=[m for m in mkts_list if m["is_btc"] and m["volume"]>1000]
            if btc_rel:
                bullish_pcts=[m["top_pct"] for m in btc_rel if m["top_outcome"].lower() in ("yes","higher","up","above","bull")]
                avg_bull=np.mean(bullish_pcts) if bullish_pcts else 50
                pb="BUY" if avg_bull>55 else "SELL" if avg_bull<45 else "NEUTRAL"
                pc="#00ff88" if pb=="BUY" else "#ff4444" if pb=="SELL" else "#888"
                st.markdown(f'<div style="border:2px solid {pc};border-radius:10px;padding:14px 18px;background:#0a0a18;margin-bottom:14px">'
                            f'<div style="font-size:11px;color:#555;font-family:JetBrains Mono,monospace">POLYMARKET CRYPTO CONSENSUS</div>'
                            f'<div style="font-size:1.4rem;font-weight:800;color:{pc};margin:4px 0">{"🟢 BULLISH" if pb=="BUY" else "🔴 BEARISH" if pb=="SELL" else "⚪ NEUTRAL"}</div>'
                            f'<div style="font-size:12px;color:#888">Avg bullish across {len(btc_rel)} crypto markets: <b style="color:{pc}">{avg_bull:.0f}%</b></div>'
                            f'<div style="font-size:11px;color:#555;margin-top:4px">{"✅ Confirms BUY" if pb=="BUY" else "✅ Confirms SELL" if pb=="SELL" else "⚠️ Mixed — reduce size"}</div>'
                            f'</div>',unsafe_allow_html=True)
            st.markdown("#### Market Cards")
            for m in mkts_list[:10]:
                tp=m["top_pct"]; pc2="#00ff88" if tp>65 else "#ff4444" if tp<40 else "#f0a500"
                impl=("⚠️ Very one-sided — contrarian risk" if tp>78 else "✅ Strong consensus" if tp>60 else "⚠️ Uncertain — trade smaller" if tp>45 else "🔄 Even split — wait")
                pairs_html=" · ".join(f'<b style="color:{"#00ff88" if float(pr)>0.55 else "#ff4444" if float(pr)<0.45 else "#888"}">{oc}: {round(float(pr)*100,1)}%</b>' for oc,pr in m["pairs"])
                vol_s=f"${m['volume']/1e3:.0f}k" if m["volume"]>=1000 else f"${m['volume']:.0f}"
                st.markdown(f'<div class="poly-card">'
                            f'<div style="display:flex;justify-content:space-between">'
                            f'<div style="font-size:13px;font-weight:600;color:#eee;flex:1;margin-right:8px">{m["question"]}</div>'
                            f'<div style="font-size:10px;color:#555">{m["tag"]}</div></div>'
                            f'<div style="font-size:12px;color:#aaa;margin-top:5px">{pairs_html}</div>'
                            f'<div style="background:#1a1a30;border-radius:4px;height:10px;margin-top:8px;overflow:hidden">'
                            f'<div style="height:100%;width:{tp}%;background:{pc2};border-radius:4px"></div></div>'
                            f'<div style="display:flex;justify-content:space-between;margin-top:6px">'
                            f'<div style="font-size:11px;color:#555">Vol:{vol_s}</div>'
                            f'<div style="font-size:11px;color:{pc2}">{impl}</div></div>'
                            f'</div>',unsafe_allow_html=True)
            st.divider()
            st.markdown("""<div style="background:#0a0a18;border:1px solid #1a1a30;border-radius:10px;padding:16px;font-size:13px;color:#aaa;line-height:1.8">
<b style="color:#00d4ff">How to use Polymarket:</b><br>
🟢 <b style="color:#00ff88">&gt;65% YES</b> → Real traders confident → confirms your BUY signals<br>
🔴 <b style="color:#ff4444">&lt;40% YES</b> → Real traders bearish → confirms SELL signals<br>
⚠️ <b style="color:#f0a500">&gt;80% one-sided</b> → Overpriced? Watch for contrarian reversal<br>
⚪ <b style="color:#888">45–55% split</b> → Genuine uncertainty → cut position size by 50%<br>
💡 High volume = smarter money = more reliable signal
</div>""",unsafe_allow_html=True)

        with ptab_all: render_poly(poly_mkts)
        with ptab_btc: render_poly([m for m in poly_mkts if m["is_btc"]],"BTC/Crypto")
        with ptab_mac: render_poly([m for m in poly_mkts if m["is_macro"]],"Macro")

# ── ALERTS ────────────────────────────────────────────────────────────────────
with t_alerts:
    st.subheader("📝 Nigel's Alerts")
    notes=st.session_state["notes"]
    if note_filter!="ALL": notes=[n for n in notes if n["market"]==note_filter]
    if not notes: st.info("Alerts appear here. Nigel checks every 90 seconds.")
    icons={"watch":"👀 Watch out","buy":"🟢 Possible buy","sell":"🔴 Consider selling","info":"💡 Heads up"}
    for n in notes[:15]:
        cls={"watch":"note-watch","buy":"note-buy","sell":"note-sell","info":"note-info"}.get(n["type"],"note-info")
        lbl=MARKETS.get(n["market"],{}).get("label",n["market"])
        st.markdown(f'<div class="note-card {cls}"><div style="font-size:10px;color:#555">{n["time"]}</div>'
                    f'<div style="font-weight:700;font-size:12px;margin-bottom:3px">{icons.get(n["type"],"💡")} — {lbl}</div>'
                    f'{n["text"]}</div>',unsafe_allow_html=True)
    if fg:
        st.divider(); st.markdown("**Fear & Greed — 14 days**")
        fig_fg=go.Figure(go.Bar(x=list(range(len(fg["history"]))),y=fg["history"],
            marker_color=["rgba(255,68,68,0.8)" if v<25 else "rgba(255,153,0,0.8)" if v<45 else "rgba(255,221,68,0.8)" if v<55 else "rgba(0,255,136,0.8)" for v in fg["history"]],
            text=[str(v) for v in fg["history"]],textposition="outside"))
        fig_fg.update_layout(height=180,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",
            margin=dict(l=0,r=0,t=10,b=0),xaxis_title="Days ago",yaxis=dict(range=[0,120]))
        st.plotly_chart(fig_fg,width='stretch',key='pc2')
    if on_chain:
        st.divider(); st.markdown("**BTC on-chain**")
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Market cap",f"${on_chain.get('market_cap',0)/1e9:.1f}B"); c2.metric("24h vol",f"${on_chain.get('volume_24h',0)/1e9:.1f}B")
        c3.metric("7d change",f"{on_chain.get('change_7d',0):+.1f}%"); c4.metric("ATH dist",f"{on_chain.get('ath_pct',0):.1f}%")

# ── TRADERS ───────────────────────────────────────────────────────────────────
with t_traders:
    st.subheader("🤖 Nigel's AI Trader Team")
    rows=[]
    for tr in TRADERS:
        pnl=tr["balance"]-25000; wins=sum(1 for t in tr["trades"] if t["result"]=="win"); tot=len(tr["trades"])
        dd=round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
        rows.append({"Trader":f"{tr['emoji']} {tr['name']}","Style":tr["style"],"Balance":tr["balance"],"P&L":pnl,
                     "Win%":round(wins/tot*100) if tot else 0,"Trades":tot,"DD%":dd,
                     "WS":tr.get("win_streak",0),"LS":tr.get("loss_streak",0)})
    df_sc=pd.DataFrame(rows).sort_values("P&L",ascending=False).reset_index(drop=True); df_sc.index+=1
    st.dataframe(df_sc.style.format({"Balance":"${:,.0f}","P&L":"${:+,.0f}","Win%":"{}%","DD%":"{}%"})
        .map(lambda v:"color:#00ff88;font-weight:700" if isinstance(v,(int,float)) and v>0 else "color:#ff4444;font-weight:700" if isinstance(v,(int,float)) and v<0 else "",subset=["P&L"]),
        width='stretch')
    TCOLORS={"Macro Maya":"#00ff88","Momentum Mike":"#00d4ff","Scalp Sam":"#f0a500","Trend Tina":"#a78bfa","Contrarian Carl":"#ff6b6b"}
    hfig=go.Figure()
    for tr in TRADERS:
        if len(tr["history"])>1:
            hfig.add_trace(go.Scatter(y=tr["history"],name=f"{tr['emoji']} {tr['name']} ({(tr['balance']-25000)/25000*100:+.1f}%)",line=dict(color=TCOLORS.get(tr["name"],"#fff"),width=2)))
    hfig.add_hline(y=25000,line=dict(color="#444",width=1,dash="dot")); hfig.update_layout(height=260,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",margin=dict(l=0,r=0,t=30,b=0),legend=dict(orientation="h",y=1.05))
    st.plotly_chart(hfig,width='stretch',key='pc3')
    ttabs=st.tabs([f"{tr['emoji']} {tr['name']}" for tr in TRADERS])
    for ttab,tr in zip(ttabs,TRADERS):
        with ttab:
            pnl=tr["balance"]-25000; c1,c2,c3,c4,c5,c6=st.columns(6)
            c1.metric("Balance",f"${tr['balance']:,.0f}",delta=f"{pnl:+,.0f}"); c2.metric("P&L",f"${pnl:+,.0f}")
            wins=sum(1 for t in tr["trades"] if t["result"]=="win"); tot=len(tr["trades"])
            c3.metric("Win rate",f"{round(wins/tot*100) if tot else 0}%"); c4.metric("Trades",tot)
            c5.metric("Risk/trade",f"{tr['risk_pct']*100:.1f}%"); c6.metric("R:R",f"1:{tr['rr']}")
            st.caption(f"{tr['desc']} | Sources: {', '.join(tr['data_sources'])}")
            pos=tr["open_pos"]
            if pos:
                mk=pos["market"]; sig=market_signals.get(mk,{}); cp=sig.get("price",pos["entry"])
                ur=(cp-pos["entry"])*pos["units"] if pos["dir"]=="long" else (pos["entry"]-cp)*pos["units"]
                uc="#00ff88" if ur>=0 else "#ff4444"; info=MARKETS.get(mk,{})
                fmt="0f" if info.get("crypto") else ".2f"
                st.markdown(f'<div class="{"pos-long" if pos["dir"]=="long" else "pos-short"}">'
                            f'<b>{info.get("label",mk)} {pos["dir"].upper()}</b> Entry${pos["entry"]:{fmt}}→${cp:{fmt}}<br>'
                            f'Stop<span style="color:#ff4444">${pos["stop"]:{fmt}}</span> Target<span style="color:#00ff88">${pos["tp"]:{fmt}}</span> '
                            f'PnL<span style="color:{uc}"><b>${ur:+,.0f}</b></span></div>',unsafe_allow_html=True)
            else: st.markdown('<div class="pos-none">No open position</div>',unsafe_allow_html=True)
            if tr["trades"]:
                tdf2=pd.DataFrame(tr["trades"][-10:][::-1]); show=[c for c in ["time","market","dir","entry","exit","pnl","result","reason"] if c in tdf2.columns]
                st.dataframe(tdf2[show].style.format({c:"${:,.2f}" for c in ["entry","exit","pnl"] if c in tdf2.columns})
                    .map(lambda v:"color:#00ff88" if v=="win" else "color:#ff4444",subset=["result"] if "result" in tdf2.columns else []),
                    width='stretch',hide_index=True)

# ── BACKTEST ──────────────────────────────────────────────────────────────────
with t_bt:
    st.subheader(f"📊 Backtest — {bt_days} days")
    bt_mk=st.selectbox("Market",selected_markets,key="bt_mk")
    bt_mode=st.radio("Mode",["Single trader","Compare all 5"],horizontal=True)
    bt_trader_name=st.selectbox("Strategy",[tr["name"] for tr in TRADERS]) if bt_mode=="Single trader" else None
    show_sigs=st.toggle("Show signals on chart",value=True)
    run_bt=st.button("▶ Run Backtest",type="primary")
    df_bt=all_dfs.get(bt_mk,pd.DataFrame())
    if run_bt:
        with st.spinner("Running backtest…"):
            all_bts={}
            for tr in TRADERS:
                r=run_backtest(df_bt,tr,label=tr["name"])
                if "equity_curve" in r: all_bts[tr["name"]]=r
            if all_bts:
                mn=bt_trader_name if bt_trader_name and bt_trader_name in all_bts else list(all_bts.keys())[0]
                st.session_state["bt_results"]={"main":all_bts[mn],"all":all_bts,"market":bt_mk,"mode":bt_mode}
            else: st.error("Not enough data for backtest.")
    saved=st.session_state.get("bt_results",{}); bt=saved.get("main"); all_bts=saved.get("all",{})
    if bt and "equity_curve" in bt:
        if all_bts and (bt_mode=="Compare all 5" or saved.get("mode")=="Compare all 5"):
            st.markdown("### All 5 Head-to-Head")
            comp=[{"Trader":n,"Return%":r["total_return"],"B&H%":r["bh_return"],"Win%":r["win_rate"],
                   "Trades":r["total_trades"],"MaxDD%":r["max_drawdown"],"Sharpe":r["sharpe"],"PF":r["profit_factor"]}
                  for n,r in all_bts.items() if "total_return" in r]
            if comp:
                df_c=pd.DataFrame(comp).sort_values("Sharpe",ascending=False)
                df_c.insert(0,"#",["🥇","🥈","🥉","4️⃣","5️⃣"][:len(df_c)])
                st.dataframe(df_c.style.format({"Return%":"{:+.1f}%","B&H%":"{:+.1f}%","Win%":"{:.0f}%","MaxDD%":"{:.1f}%","Sharpe":"{:.2f}","PF":"{:.2f}"})
                    .highlight_max(subset=["Return%","Win%","Sharpe"],color="#1a3a1a").highlight_min(subset=["MaxDD%"],color="#1a3a1a"),
                    width='stretch',hide_index=True)
            ef=build_equity_chart(all_bts)
            if ef: st.plotly_chart(ef,width='stretch',key='pc4')
        sc2=st.columns(8)
        cr="#00ff88" if bt["total_return"]>0 else "#ff4444"
        for col,(val,lbl,vc) in zip(sc2,[(f"{bt['total_return']:+.1f}%","Strategy",cr),(f"{bt['bh_return']:+.1f}%","Buy&Hold","#aaa"),
                (f"{bt['win_rate']:.0f}%","Win Rate","#aaa"),(str(bt["total_trades"]),"Trades","#aaa"),
                (f"{bt['profit_factor']:.2f}","Profit Factor","#aaa"),(f"{bt['max_drawdown']:.1f}%","Max DD","#ff4444"),
                (f"{bt['sharpe']:.2f}","Sharpe","#aaa"),(f"{bt['calmar']:.2f}","Calmar","#aaa")]):
            col.markdown(f'<div class="bt-stat"><div class="bt-val" style="color:{vc}">{val}</div><div class="bt-lbl">{lbl}</div></div>',unsafe_allow_html=True)
        a1,a2,a3,a4=st.columns(4)
        a1.metric("Avg win",f"${bt['avg_win']:+,.2f}"); a2.metric("Avg loss",f"${bt['avg_loss']:+,.2f}")
        a3.metric("Win streak",bt["max_win_streak"]); a4.metric("Loss streak",bt["max_loss_streak"])
        fig_main=build_chart(df_bt,f"{bt_mk} — {bt.get('label','')}",MARKETS[bt_mk]["color"],show_sigs,bt)
        if fig_main: st.plotly_chart(fig_main,width='stretch',key='pc5')
        c_eq,c_mo=st.columns([2,1])
        with c_eq:
            ef2=build_equity_chart(all_bts)
            if ef2: st.plotly_chart(ef2,width='stretch',key='pc6')
        with c_mo:
            mf=build_monthly(bt)
            if mf: st.plotly_chart(mf,width='stretch',key='pc7')
        ddf=build_drawdown(bt)
        if ddf: st.plotly_chart(ddf,width='stretch',key='pc8')
        with st.expander("📋 Full trade log"):
            tdf3=bt["trade_list"].copy(); tdf3["pnl%"]=tdf3["pnl"]/10000*100
            st.dataframe(tdf3.style.format({"entry":"${:,.2f}","exit":"${:,.2f}","pnl":"${:+,.2f}","pnl%":"{:+.2f}%"})
                .map(lambda v:"color:#00ff88" if isinstance(v,(int,float)) and v>0 else "color:#ff4444",subset=["pnl"]),
                width='stretch',hide_index=True)
        with st.expander("⚠️ Disclaimer"): st.caption("Past results don't guarantee future performance. No fees or slippage modelled.")
    else: st.info("Select a market and click **▶ Run Backtest**.")

# ── 100-AI LAB ────────────────────────────────────────────────────────────────
with t_ensemble:
    st.subheader("🔬 100-AI Ensemble Lab")
    st.caption("Every config backtested. Top 20 per market feed the Grand Strategy.")
    if st.button("🔄 Re-run Full Ensemble",type="primary"):
        with st.spinner("Testing 100 AI traders… ~30s…"):
            try:
                ens,grand2=run_ensemble(all_dfs)
                st.session_state["ensemble_results"]=ens; st.session_state["grand_strategy"]=grand2
                st.session_state["ensemble_ran"]=True; st.success("✅ Done! Grand Strategy updated.")
            except Exception as e: st.error(f"Error: {e}")
    ens=st.session_state.get("ensemble_results",{})
    if not ens: st.info("Ensemble runs on first load. Click above to re-run.")
    else:
        e_mk=st.selectbox("Market leaderboard",list(ens.keys()),key="emk")
        if e_mk and e_mk in ens:
            res=ens[e_mk]; rets=[r["total_return"] for r in res]; sharpes=[r["sharpe"] for r in res]
            c1,c2,c3,c4,c5=st.columns(5)
            c1.metric("AIs",len(res)); c2.metric("Winners",len([r for r in res if r["total_return"]>0]))
            c3.metric("Avg return",f"{np.mean(rets):+.1f}%"); c4.metric("Best",f"{max(rets):+.1f}%"); c5.metric("Avg Sharpe",f"{np.mean(sharpes):.2f}")
            top20=res[:20]; names=[r["name"] for r in top20]; trets=[r["total_return"] for r in top20]; tsharpes=[r["sharpe"] for r in top20]
            fig_lb=make_subplots(rows=1,cols=2,subplot_titles=["Top-20 Returns %","Top-20 Sharpe"])
            fig_lb.add_trace(go.Bar(x=trets,y=names,orientation="h",marker_color=["rgba(0,204,102,0.8)" if r>=0 else "rgba(204,51,51,0.8)" for r in trets],text=[f"{r:+.1f}%" for r in trets],textposition="auto"),row=1,col=1)
            fig_lb.add_trace(go.Bar(x=tsharpes,y=names,orientation="h",marker_color=["rgba(167,139,250,0.8)" if s>=0 else "rgba(255,107,107,0.8)" for s in tsharpes],text=[f"{s:.2f}" for s in tsharpes],textposition="auto"),row=1,col=2)
            fig_lb.update_layout(height=480,template="plotly_dark",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",showlegend=False,margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_lb,width='stretch',key='pc9')
            fig_dist=go.Figure(go.Histogram(x=rets,nbinsx=20,marker_color=["rgba(0,204,102,0.7)" if r>=0 else "rgba(204,51,51,0.7)" for r in rets]))
            fig_dist.add_vline(x=0,line=dict(color="#555",width=1,dash="dash")); fig_dist.add_vline(x=np.mean(rets),line=dict(color="#00d4ff",width=2),annotation_text=f"Mean {np.mean(rets):.1f}%")
            fig_dist.update_layout(height=230,template="plotly_dark",title="Return distribution — 100 AIs",paper_bgcolor="#080818",plot_bgcolor="#0a0a18",margin=dict(l=0,r=0,t=50,b=0))
            st.plotly_chart(fig_dist,width='stretch',key='pc10')
            with st.expander("📋 Full table"):
                df_ens=pd.DataFrame([{"Rank":i+1,"Trader":r["name"],"Return%":r["total_return"],"WR%":r["win_rate"],"Sharpe":r["sharpe"],"MaxDD%":r["max_drawdown"],"PF":r["profit_factor"],"Trades":r["total_trades"],"RSI":f"{r['rsi_range'][0]}-{r['rsi_range'][1]}","RR":r["rr"],"Score":round(r["score"],3)} for i,r in enumerate(res)])
                st.dataframe(df_ens.style.format({"Return%":"{:+.1f}%","WR%":"{:.0f}%","Sharpe":"{:.2f}","MaxDD%":"{:.1f}%","PF":"{:.2f}","Score":"{:.3f}"})
                    .highlight_max(subset=["Return%","WR%","Sharpe","Score"],color="#1a3a1a").highlight_min(subset=["MaxDD%"],color="#1a3a1a"),
                    width='stretch',hide_index=True)

# ── SESSIONS ──────────────────────────────────────────────────────────────────
with t_sessions:
    st.subheader("🕐 Session Guide")
    utc_now=datetime.now(ZoneInfo("UTC")); hf_now=utc_now.hour+utc_now.minute/60
    for name,hours,best,mkts,desc,sc2,h0,h1 in [
        ("Tokyo","00:00–09:00","03:00–08:00","BTC, ETH","Low volume. BTC drifts. Avoid stocks.","#7C3AED",0,9),
        ("London","08:00–17:00","08:00–10:00","Gold, BTC","Breakouts at open. Gold reacts to EU data.","#2563EB",8,17),
        ("New York","13:00–22:00","13:30–16:00","NQ, SPY, Gold, BTC","Highest volume. US open spikes everything.","#059669",13,22),
        ("Overlap","13:00–17:00","13:00–15:00","All","PRIME TIME. Tightest spreads. Sharpest signals.","#D97706",13,17),
        ("Off-hours","22:00–00:00","Avoid","None","Very thin. Stay out.","#555",22,24)]:
        is_now=h0<=hf_now<h1; border=sc2 if is_now else "#1a1a30"
        badge=f' <span style="background:{sc2};color:#fff;border-radius:4px;padding:1px 8px;font-size:11px">NOW</span>' if is_now else ""
        st.markdown(f'<div style="border:1.5px solid {border};border-radius:10px;padding:14px 18px;margin-bottom:10px;background:#0a0a18">'
                    f'<div style="font-size:15px;font-weight:700;color:{sc2}">{name}{badge}</div>'
                    f'<div style="font-size:12px;color:#555;margin-top:3px">Hours: {hours} | Best: {best} | Markets: {mkts}</div>'
                    f'<div style="font-size:13px;color:#aaa;margin-top:6px">{desc}</div>'
                    f'</div>',unsafe_allow_html=True)
    st.markdown("""
| Market | Best session | Ideal time (UTC) | Why |
|---|---|---|---|
| BTC | London or Overlap | 08:00–10:00 / 13:00–16:00 | Peak momentum |
| ETH | Same as BTC | 08:00–10:00 / 13:00–16:00 | Follows BTC |
| NASDAQ | New York | 13:30–16:00 | After US open |
| Gold | London + Overlap | 08:00–10:00 / 13:30–15:00 | EU/US data |
| S&P 500 | New York | 13:30–15:30 | US open liquidity |
""")

if auto_refresh:
    time.sleep(90)
    st.cache_data.clear()
    st.rerun()
