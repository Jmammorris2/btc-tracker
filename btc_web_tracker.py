"""
NIGEL - Private Trading Intelligence v5.3 - APEX EDITION
Apex Trader Funding $50K rules built-in.
Instruments: SOL, SOXL, AVAX, LINK, TQQQ, XBI
SIMULATION ONLY - no real orders execute.
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
import random

st.set_page_config(
    page_title="NIGEL APEX",
    layout="wide",
    page_icon="N",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600;700;900&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=JetBrains+Mono:wght@300;400;500;700&display=swap');
:root{
  --obsidian:#05040a;--obsidian2:#09080f;--obsidian3:#0d0c16;--obsidian4:#12101e;
  --gold:#c9a84c;--gold2:#e8c97a;--gold-dim:rgba(201,168,76,0.12);
  --emerald:#1aff8a;--emerald-dim:rgba(26,255,138,0.08);
  --crimson:#ff2d55;--crimson-dim:rgba(255,45,85,0.08);
  --sapphire:#00c4ff;--sapphire-dim:rgba(0,196,255,0.08);
  --violet:#a855f7;--violet-dim:rgba(168,85,247,0.08);
  --apex:#ff9500;--apex-dim:rgba(255,149,0,0.10);
  --border:rgba(201,168,76,0.12);--border2:rgba(201,168,76,0.22);
  --text:#d4cfc0;--text-dim:#5a5570;--text-muted:#3a3550;
}
*,html,body{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Cormorant Garamond',Georgia,serif!important;background:var(--obsidian)!important;color:var(--text)!important;}
.block-container{padding:0 2rem 2rem!important;max-width:100%!important;}
.nigel-masthead{display:flex;align-items:flex-end;justify-content:space-between;padding:28px 0 18px;border-bottom:1px solid var(--border2);margin-bottom:24px;position:relative;}
.nigel-masthead::after{content:'';position:absolute;bottom:-1px;left:0;width:120px;height:2px;background:linear-gradient(90deg,var(--gold),transparent);}
.nigel-wordmark{font-family:'Cinzel',serif;font-size:3.4rem;font-weight:900;letter-spacing:0.3em;color:#fff;line-height:1;}
.nigel-wordmark em{font-style:normal;color:var(--gold);font-weight:400;}
.nigel-tagline{font-family:'Cormorant Garamond',serif;font-weight:300;font-style:italic;font-size:1rem;color:var(--text-dim);letter-spacing:0.12em;margin-top:4px;}
.ticker-wrap{overflow:hidden;background:var(--obsidian2);border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:8px 0;margin:0 0 24px;}
.ticker-track{display:inline-flex;gap:60px;animation:ticker-scroll 30s linear infinite;white-space:nowrap;}
@keyframes ticker-scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.tick-item{font-family:'JetBrains Mono',monospace;font-size:11px;display:inline-flex;align-items:center;gap:8px;letter-spacing:.04em;}
.tick-sym{color:var(--gold);font-weight:700}.tick-px{color:#fff}.tick-up{color:var(--emerald)}.tick-dn{color:var(--crimson)}.tick-sep{color:var(--text-muted)}
.signal-card{background:var(--obsidian2);border:1px solid var(--border);border-radius:2px;padding:18px;position:relative;overflow:hidden;}
.signal-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;}
.signal-card.bull::before{background:linear-gradient(90deg,var(--emerald),transparent 70%);}
.signal-card.bear::before{background:linear-gradient(90deg,var(--crimson),transparent 70%);}
.signal-card.flat::before{background:linear-gradient(90deg,var(--gold),transparent 70%);}
.signal-card.bull{border-left:1px solid rgba(26,255,138,0.3);}
.signal-card.bear{border-left:1px solid rgba(255,45,85,0.3);}
.sc-sym{font-family:'Cinzel',serif;font-size:1.3rem;font-weight:700;color:#fff;letter-spacing:.1em;}
.sc-price{font-family:'JetBrains Mono',monospace;font-size:1.6rem;font-weight:500;color:#fff;line-height:1.1;}
.sc-chg-up{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--emerald);}
.sc-chg-dn{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--crimson);}
.badge{display:inline-block;border-radius:1px;padding:3px 10px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;}
.badge-long{background:var(--emerald-dim);color:var(--emerald);border:1px solid rgba(26,255,138,.3);}
.badge-short{background:var(--crimson-dim);color:var(--crimson);border:1px solid rgba(255,45,85,.3);}
.badge-hold{background:var(--gold-dim);color:var(--gold);border:1px solid rgba(201,168,76,.3);}
.badge-regime-trend{background:rgba(26,255,138,0.08);color:var(--emerald);border:1px solid rgba(26,255,138,.2);font-size:9px;padding:2px 7px;}
.badge-regime-range{background:rgba(201,168,76,0.08);color:var(--gold);border:1px solid rgba(201,168,76,.2);font-size:9px;padding:2px 7px;}
.badge-regime-vol{background:rgba(255,45,85,0.08);color:var(--crimson);border:1px solid rgba(255,45,85,.2);font-size:9px;padding:2px 7px;}
.meter-track{background:var(--obsidian4);height:3px;border-radius:2px;overflow:hidden;margin:5px 0 2px;}
.meter-fill{height:100%;border-radius:2px;}
.panel{background:var(--obsidian2);border:1px solid var(--border);border-radius:2px;padding:18px 20px;}
.panel-gold{border-top:1px solid var(--gold);}
.panel-em{border-top:1px solid var(--emerald);}
.panel-cr{border-top:1px solid var(--crimson);}
.stat-val{font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:500;line-height:1;}
.stat-lbl{font-family:'Cinzel',serif;font-size:9px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--text-dim);margin-top:4px;}
.nigel-note{border-radius:1px;padding:14px 18px;margin-bottom:10px;}
.note-watch{background:rgba(201,168,76,0.06);border-left:2px solid var(--gold);}
.note-buy{background:rgba(26,255,138,0.05);border-left:2px solid var(--emerald);}
.note-sell{background:rgba(255,45,85,0.05);border-left:2px solid var(--crimson);}
.note-info{background:rgba(0,196,255,0.05);border-left:2px solid var(--sapphire);}
.note-head{font-family:'Cinzel',serif;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:5px;}
.note-body{font-family:'Cormorant Garamond',serif;font-size:14px;line-height:1.65;}
.trader-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--border);}
.trader-name{font-family:'Cinzel',serif;font-size:1.1rem;font-weight:700;letter-spacing:.1em;color:#fff;}
.trader-style{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:13px;color:var(--text-dim);margin-top:2px;}
.pos-panel{border-radius:2px;padding:12px 16px;margin:10px 0;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.8;}
.pos-long{background:rgba(26,255,138,0.05);border:1px solid rgba(26,255,138,0.2);}
.pos-short{background:rgba(255,45,85,0.05);border:1px solid rgba(255,45,85,0.2);}
.pos-flat{background:var(--obsidian3);border:1px solid var(--border);color:var(--text-dim);}
.trade-pip-w{color:var(--emerald);font-size:11px;}
.trade-pip-l{color:var(--crimson);font-size:11px;}
.stTabs [data-baseweb="tab-list"]{background:var(--obsidian2)!important;border-radius:0!important;border-bottom:1px solid var(--border2)!important;gap:0!important;padding:0!important;}
.stTabs [data-baseweb="tab"]{border-radius:0!important;color:var(--text-dim)!important;font-family:'Cinzel',serif!important;font-size:11px!important;font-weight:600!important;letter-spacing:.1em!important;padding:14px 22px!important;border-bottom:2px solid transparent!important;}
.stTabs [aria-selected="true"]{background:transparent!important;color:var(--gold)!important;border-bottom:2px solid var(--gold)!important;}
section[data-testid="stSidebar"]{background:var(--obsidian2)!important;border-right:1px solid var(--border)!important;}
hr{border:none!important;border-top:1px solid var(--border)!important;margin:18px 0!important;}
.ai-response{background:linear-gradient(135deg,rgba(201,168,76,0.04),transparent);border:1px solid var(--border);border-left:2px solid var(--gold);border-radius:1px;padding:18px 22px;font-family:'Cormorant Garamond',serif;font-size:15px;line-height:1.75;}
.ai-header{font-family:'Cinzel',serif;font-size:9px;font-weight:700;letter-spacing:.16em;color:var(--gold);text-transform:uppercase;margin-bottom:12px;}
.whisper-note{background:linear-gradient(135deg,rgba(0,196,255,0.03),transparent);border:1px solid rgba(0,196,255,0.1);border-left:2px solid var(--sapphire);border-radius:1px;padding:10px 14px;margin-bottom:8px;font-family:'Cormorant Garamond',serif;font-size:13px;font-style:italic;color:var(--text-dim);}
.divergence-bull{background:rgba(26,255,138,0.04);border:1px solid rgba(26,255,138,0.15);border-radius:1px;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--emerald);margin-top:3px;}
.divergence-bear{background:rgba(255,45,85,0.04);border:1px solid rgba(255,45,85,0.15);border-radius:1px;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--crimson);margin-top:3px;}
.macd-bull{background:rgba(26,255,138,0.04);border:1px solid rgba(26,255,138,0.15);border-radius:1px;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--emerald);margin-top:3px;}
.macd-bear{background:rgba(255,45,85,0.04);border:1px solid rgba(255,45,85,0.15);border-radius:1px;padding:5px 10px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--crimson);margin-top:3px;}
.pattern-tag{display:inline-block;border-radius:1px;padding:2px 7px;font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:2px;background:rgba(201,168,76,0.08);border:1px solid rgba(201,168,76,.2);color:var(--gold);}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:var(--obsidian);}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.always-on-bar{position:fixed;bottom:0;left:0;right:0;background:var(--obsidian2);border-top:1px solid var(--border);padding:8px 24px;display:flex;align-items:center;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-dim);z-index:999;}
.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--emerald);animation:pulse-dot 2s ease-in-out infinite;margin-right:6px;vertical-align:middle;}
.apex-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--apex);animation:pulse-dot 2s ease-in-out infinite;margin-right:6px;vertical-align:middle;}
@keyframes pulse-dot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.8)}}
.shield-banner{background:rgba(255,45,85,0.08);border:1px solid rgba(255,45,85,0.3);border-radius:1px;padding:10px 18px;font-family:'Cinzel',serif;font-size:10px;letter-spacing:.1em;color:var(--crimson);text-align:center;margin-bottom:16px;}
.apex-banner{background:rgba(255,149,0,0.08);border:1px solid rgba(255,149,0,0.3);border-radius:1px;padding:10px 18px;font-family:'Cinzel',serif;font-size:10px;letter-spacing:.1em;color:var(--apex);text-align:center;margin-bottom:16px;}
.apex-clear{background:rgba(26,255,138,0.05);border:1px solid rgba(26,255,138,0.2);border-radius:1px;padding:10px 18px;font-family:'Cinzel',serif;font-size:10px;letter-spacing:.1em;color:var(--emerald);text-align:center;margin-bottom:16px;}
.rule-row{display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:var(--obsidian3);border:1px solid var(--border);border-radius:1px;margin-bottom:6px;}
.rule-on{border-left:2px solid var(--emerald);}.rule-off{border-left:2px solid var(--text-muted);opacity:.55;}
.rule-name{font-family:'Cinzel',serif;font-size:12px;font-weight:600;letter-spacing:.06em;color:#fff;}
.rule-desc{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:12px;color:var(--text-dim);}
.kelly-panel{background:linear-gradient(135deg,rgba(201,168,76,0.05),transparent);border:1px solid var(--border);border-radius:2px;padding:16px 20px;}
.persist-banner{background:rgba(26,255,138,0.04);border:1px solid rgba(26,255,138,0.15);border-left:2px solid var(--emerald);border-radius:1px;padding:8px 14px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--emerald);margin-bottom:12px;}
.tqs-cell{padding:14px;border-radius:2px;text-align:center;background:var(--obsidian2);border:1px solid var(--border);}
.tqs-score{font-family:'Cinzel',serif;font-size:2rem;font-weight:900;line-height:1;}
.tqs-label{font-family:'Cinzel',serif;font-size:9px;letter-spacing:.12em;color:var(--text-dim);margin-top:4px;}
.council-bar{display:flex;height:22px;border-radius:1px;overflow:hidden;background:var(--obsidian3);border:1px solid var(--border);margin:5px 0;}
.council-long{background:linear-gradient(90deg,#1aff8a,#0c8a4a);height:100%;}
.council-short{background:linear-gradient(90deg,#ff2d55,#a01838);height:100%;}
.council-hold{background:linear-gradient(90deg,#5a5570,#3a3550);height:100%;}
.dna-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px dashed var(--border);font-family:'JetBrains Mono',monospace;font-size:11px;}
.dna-key{color:var(--text-dim);}.dna-val{color:#fff;font-weight:500;}
.adaptive-tag{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--violet);letter-spacing:.08em;background:var(--violet-dim);padding:2px 8px;border:1px solid rgba(168,85,247,.25);border-radius:1px;}
.apex-progress-track{background:var(--obsidian4);height:8px;border-radius:4px;overflow:hidden;margin:5px 0 2px;}
.apex-progress-fill{height:100%;border-radius:4px;}
.proxy-tag{display:inline-block;background:rgba(255,149,0,0.10);border:1px solid rgba(255,149,0,0.3);border-radius:1px;padding:2px 8px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--apex);letter-spacing:.08em;}
</style>
""", unsafe_allow_html=True)

# ==============================================================
# APEX CONFIG
# ==============================================================
APEX_CONFIG = {
    "account_size":       50_000.0,
    "daily_loss_limit":    1_000.0,
    "trailing_drawdown":   2_500.0,
    "profit_target":       3_000.0,
    "min_trading_days":        7,
    "consistency_cap_pct":    40,
    "warn_at_pct":           0.70,
}

# ==============================================================
# MARKETS
# ==============================================================
MARKETS = {
    "SOL":  {"label":"Solana",    "sub":"SOL/USD",   "stop":0.040, "crypto":True,  "color":"#9945FF", "emoji":"S", "apex_proxy":"MBT",  "apex_note":"Micro Bitcoin futures - 0.1 BTC/contract"},
    "SOXL": {"label":"Semis 3x",  "sub":"SOXL ETF",  "stop":0.030, "crypto":False, "color":"#00C4FF", "emoji":"X", "apex_proxy":"MNQ",  "apex_note":"Micro E-mini Nasdaq - $2/point"},
    "AVAX": {"label":"Avalanche", "sub":"AVAX/USD",  "stop":0.045, "crypto":True,  "color":"#E84142", "emoji":"A", "apex_proxy":"MET",  "apex_note":"Micro Ether futures - 0.1 ETH/contract"},
    "LINK": {"label":"Chainlink", "sub":"LINK/USD",  "stop":0.035, "crypto":True,  "color":"#2A5ADA", "emoji":"L", "apex_proxy":"MBT",  "apex_note":"Micro Bitcoin futures - closest crypto"},
    "TQQQ": {"label":"Nasdaq 3x", "sub":"TQQQ ETF",  "stop":0.025, "crypto":False, "color":"#1AFF8A", "emoji":"Q", "apex_proxy":"MNQ",  "apex_note":"Micro E-mini Nasdaq - $2/point"},
    "XBI":  {"label":"Biotech",   "sub":"XBI ETF",   "stop":0.020, "crypto":False, "color":"#FF6644", "emoji":"B", "apex_proxy":"RTY",  "apex_note":"Russell 2000 - $5/point micro"},
}

CRYPTO_MAP = {
    "SOL":  {"cg_id":"solana",      "binance":"SOLUSDT",  "fallback":150.0},
    "AVAX": {"cg_id":"avalanche-2", "binance":"AVAXUSDT", "fallback":38.0},
    "LINK": {"cg_id":"chainlink",   "binance":"LINKUSDT", "fallback":16.0},
}

TICKERS = {"SOXL":"SOXL", "TQQQ":"TQQQ", "XBI":"XBI"}

SESSION_TIPS = {
    "TOKYO":    "SOL and AVAX most active. Asian crypto flows favour momentum.",
    "LONDON":   "LINK often trends hard at open. SOXL pre-market range sets the day.",
    "NEW YORK": "All six live. TQQQ and SOXL peak volatility window.",
    "OVERLAP":  "Peak liquidity. Decisive moves on all crypto. Best hour for XBI.",
    "OFF-HOURS":"Patience is a position. Review your Apex daily P&L limits.",
}

STARTING_BALANCE = 50_000.0
MAX_BARS_IN_TRADE = 12

SCORE_MAP = {
    (7,8):55,(8,9):85,(9,10):90,(10,11):80,(11,12):65,(12,13):70,
    (13,14):95,(14,15):95,(15,16):85,(16,17):75,(17,18):60,(18,19):45,
    (19,20):35,(20,21):30,(21,22):40,(22,23):55,(23,24):60,
    (0,1):65,(1,2):70,(2,3):65,(3,4):55,(4,5):45,(5,6):40,(6,7):45
}

# ==============================================================
# PERSISTENCE
# ==============================================================
PERSIST_PATH = pathlib.Path("nigel_state.json")
STATE_VERSION = "5.3"
PERSIST_KEYS = [
    "polygon_key","claude_key","rule_set","notes","signal_feed","ai_feed",
    "whisper_feed","diag_history","bt_cache","traders","last_ai_call",
    "last_whisper_call","refresh_interval","selected_markets","account_size",
    "rr_ratio","always_on","shield_active","last_refresh","council_history",
    "apex_cumulative_pnl","apex_daily_pnl","apex_last_day","apex_high_water",
    "apex_trading_days","apex_locked","apex_lock_reason","apex_daily_history",
]
REQUIRED_POS_FIELDS = {"market","dir","entry","stop","tp","units","risk_amt","time","conf"}


def _is_valid_position(pos):
    if pos is None: return True
    if not isinstance(pos, dict): return False
    return REQUIRED_POS_FIELDS.issubset(pos.keys())


def _serialize(obj):
    if isinstance(obj, datetime): return {"__dt__": obj.isoformat()}
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, pd.DataFrame): return {"__df__": obj.to_dict(orient="records")}
    raise TypeError(f"Not serializable: {type(obj)}")


def _deserialize(obj):
    if isinstance(obj, dict):
        if "__dt__" in obj: return datetime.fromisoformat(obj["__dt__"])
        if "__df__" in obj: return pd.DataFrame(obj["__df__"])
        return {k: _deserialize(v) for k, v in obj.items()}
    if isinstance(obj, list): return [_deserialize(i) for i in obj]
    return obj


def _sanitize_trader(tr):
    defaults = {
        "name":"UNKNOWN","emoji":"o","style":"","philosophy":"",
        "risk_pct":0.01,"rr":2.0,"min_conf":55,"wait_strong":False,
        "balance":STARTING_BALANCE,"peak":STARTING_BALANCE,
        "trades":[],"open_pos":None,"history":[STARTING_BALANCE],"paused":False,
        "base_min_conf":55,"fitness":0.0,"fitness_history":[],"best_market":None,
        "win_streak":0,"loss_streak":0,"longest_win":0,"longest_loss":0,
        "adapt_log":[],"fitness_per_market":{},
    }
    for k, v in defaults.items():
        if k not in tr: tr[k] = v
    if not _is_valid_position(tr.get("open_pos")): tr["open_pos"] = None
    return tr


def state_save():
    payload = {"__version__": STATE_VERSION, "__saved_at__": datetime.now().isoformat()}
    for k in PERSIST_KEYS:
        if k not in st.session_state: continue
        v = st.session_state[k]
        try:
            if k == "bt_cache":
                safe = {}
                for bk, bv in v.items():
                    if not isinstance(bv, dict): continue
                    entry = {}
                    for ek, ev in bv.items():
                        if isinstance(ev, pd.DataFrame):
                            entry[ek] = {"__df__": ev.to_dict(orient="records")}
                        else:
                            try: json.dumps(ev, default=_serialize); entry[ek] = ev
                            except Exception: pass
                    safe[bk] = entry
                payload[k] = safe
            elif k == "traders":
                safe_t = []
                for tr in v:
                    tr_copy = dict(tr)
                    if not _is_valid_position(tr_copy.get("open_pos")): tr_copy["open_pos"] = None
                    try: json.dumps(tr_copy, default=_serialize); safe_t.append(tr_copy)
                    except Exception: tr_copy["open_pos"] = None; safe_t.append(tr_copy)
                payload[k] = safe_t
            else:
                json.dumps(v, default=_serialize)
                payload[k] = v
        except Exception: pass
    try:
        tmp = PERSIST_PATH.with_suffix(".tmp")
        with open(tmp, "w") as f: json.dump(payload, f, default=_serialize, indent=2)
        tmp.replace(PERSIST_PATH)
    except Exception: pass


def state_load():
    if not PERSIST_PATH.exists(): return {}
    try:
        with open(PERSIST_PATH) as f: raw = json.load(f)
        data = _deserialize(raw)
        if "bt_cache" in data:
            for bk, bv in data["bt_cache"].items():
                if isinstance(bv, dict) and "trades" in bv:
                    t = bv["trades"]
                    if isinstance(t, dict) and "__df__" in t: bv["trades"] = pd.DataFrame(t["__df__"])
                    elif isinstance(t, list): bv["trades"] = pd.DataFrame(t)
        if "traders" in data: data["traders"] = [_sanitize_trader(tr) for tr in data["traders"]]
        return data
    except Exception: return {}


if "__nigel_restored__" not in st.session_state:
    _disk = state_load()
    for k in PERSIST_KEYS:
        if k in _disk and k not in st.session_state: st.session_state[k] = _disk[k]
    st.session_state["__nigel_restored__"] = True
    st.session_state["__restore_ts__"] = datetime.now().strftime("%H:%M:%S")# ==============================================================
# TRADER FACTORY
# ==============================================================
def _generate_trade_history(win_rate, rr, risk_pct, n_trades, starting_bal, seed=42):
    rng = random.Random(seed)
    bal = starting_bal; peak = starting_bal; trades = []; equity = [starting_bal]
    base_prices = {"SOL":150,"AVAX":38,"LINK":16,"SOXL":45,"TQQQ":58,"XBI":82}
    markets_pool = list(base_prices.keys())
    for i in range(n_trades):
        mk = rng.choice(markets_pool)
        direction = rng.choice(["long","short"])
        risk_amt = bal * risk_pct
        entry = base_prices[mk] * (1 + rng.uniform(-0.08, 0.08))
        stop_dist = entry * MARKETS[mk]["stop"]
        units = risk_amt / max(stop_dist, 1e-9)
        tp = entry + stop_dist*rr if direction=="long" else entry - stop_dist*rr
        stop = entry - stop_dist if direction=="long" else entry + stop_dist
        is_win = rng.random() < (win_rate / 100)
        if is_win: pnl = risk_amt*rr; exit_p = tp; result = "win"; reason = "TP"
        else: pnl = -risk_amt; exit_p = stop; result = "loss"; reason = "SL"
        bal = max(0, bal+pnl); peak = max(peak, bal); equity.append(round(bal,2))
        hours_ago = (n_trades-i) * rng.uniform(2,18)
        t = (datetime.now()-timedelta(hours=hours_ago)).strftime("%H:%M:%S")
        trades.append({"market":mk,"dir":direction,"entry":round(entry,2),
                       "exit":round(exit_p,2),"pnl":round(pnl,2),"result":result,
                       "reason":reason,"time":t,"conf":rng.randint(55,90)})
    return trades, equity, round(bal,2), round(peak,2)


def _make_trader(name, emoji, style, risk_pct, rr, min_conf, wait_strong, philosophy,
                 preload_trades=0, preload_win_rate=55, seed=42):
    if preload_trades > 0:
        trades, equity, final_bal, peak_bal = _generate_trade_history(
            preload_win_rate, rr, risk_pct, preload_trades, STARTING_BALANCE, seed)
    else:
        trades = []; equity = [STARTING_BALANCE]
        final_bal = STARTING_BALANCE; peak_bal = STARTING_BALANCE
    return {
        "name":name,"emoji":emoji,"style":style,"philosophy":philosophy,
        "risk_pct":risk_pct,"rr":rr,"min_conf":min_conf,"wait_strong":wait_strong,
        "balance":final_bal,"peak":peak_bal,"trades":trades,"open_pos":None,
        "history":equity,"paused":False,"base_min_conf":min_conf,"fitness":0.0,
        "fitness_history":[],"best_market":None,"win_streak":0,"loss_streak":0,
        "longest_win":0,"longest_loss":0,"adapt_log":[],"fitness_per_market":{},
    }


DEFAULT_TRADERS = [
    _make_trader("CONSERVATEUR","C","Precision entries only - waits for the perfect storm",
                 0.005,2.5,65,True,"I trade once and trade right.",18,63,11),
    _make_trader("MOMENTUM","M","Rides breakouts and trend continuation aggressively",
                 0.015,2.0,52,False,"The trend is my only edge.",42,54,22),
    _make_trader("CONTRARIAN","X","Fades extremes - buys oversold, sells overbought",
                 0.020,1.8,45,False,"When others panic, I act.",35,50,33),
    _make_trader("SCALPER","S","High-frequency micro-positions - small wins, tight stops",
                 0.008,1.4,50,False,"A hundred small edges compound into one large fortune.",87,61,44),
    _make_trader("MACRO","R","Slow macro thesis trades - holds positions over sessions",
                 0.015,3.5,60,True,"I don't trade noise. I trade the story beneath the price.",12,67,55),
    _make_trader("ALGOBOT","A","Pure systematic - no discretion, rules-only execution",
                 0.010,2.2,55,False,"Emotion is a bug. My only input is the signal.",61,57,66),
]

# ==============================================================
# SESSION DEFAULTS
# ==============================================================
DEFAULTS = {
    "polygon_key":"","claude_key":"","notes":[],"signal_feed":[],
    "last_ai_call":0.0,"last_whisper_call":0.0,"rule_set":[],"bt_cache":{},
    "ai_feed":[],"diag_history":[],"whisper_feed":[],"always_on":True,
    "refresh_interval":60,"last_refresh":0.0,
    "selected_markets":["SOL","SOXL","AVAX","LINK"],
    "shield_active":False,"traders":DEFAULT_TRADERS,"account_size":50_000,
    "rr_ratio":2.0,"council_history":[],
    "apex_cumulative_pnl":0.0,"apex_daily_pnl":0.0,"apex_last_day":"",
    "apex_high_water":APEX_CONFIG["account_size"],"apex_trading_days":[],
    "apex_locked":False,"apex_lock_reason":"","apex_daily_history":[],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v
st.session_state["traders"] = [_sanitize_trader(tr) for tr in st.session_state["traders"]]

# ==============================================================
# API GATE
# ==============================================================
if not st.session_state["polygon_key"]:
    st.markdown("""
    <div style='min-height:100vh;display:flex;flex-direction:column;align-items:center;
    justify-content:center;padding:60px 40px;'>
    <div style='font-family:Cinzel,serif;font-size:3.5rem;font-weight:900;letter-spacing:.4em;
    color:#fff;margin-bottom:6px;'>NIGEL</div>
    <div style='font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;
    font-size:1rem;letter-spacing:.2em;margin-bottom:4px;'>Private Trading Intelligence v5.3</div>
    <div style='font-family:JetBrains Mono,monospace;font-size:10px;color:rgba(255,149,0,0.7);
    letter-spacing:.15em;margin-bottom:40px;'>APEX TRADER FUNDING $50K EDITION</div>
    <div style='background:#09080f;border:1px solid rgba(201,168,76,0.2);border-radius:2px;
    padding:36px 48px;max-width:480px;width:100%;'>
    <div style='font-family:Cinzel,serif;font-size:11px;letter-spacing:.12em;color:#c9a84c;
    margin-bottom:24px;'>AUTHENTICATION</div>
    """, unsafe_allow_html=True)
    with st.form("auth"):
        pk = st.text_input("Polygon.io API Key", type="password", placeholder="pk_live_...")
        ck = st.text_input("Claude API Key (AI features)", type="password", placeholder="sk-ant-...")
        if st.form_submit_button("ENTER NIGEL", type="primary"):
            if pk:
                st.session_state["polygon_key"] = pk
                st.session_state["claude_key"] = ck
                state_save(); st.rerun()
            else: st.error("Polygon key required.")
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

POLY = st.session_state["polygon_key"]
CLKEY = st.session_state["claude_key"]
TRADERS = st.session_state["traders"]# ==============================================================
# DATA FETCHERS
# ==============================================================
@st.cache_data(ttl=60)
def fetch_crypto_price(cg_id, days=45, fallback=50.0):
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily", timeout=15).json()
        closes = [p[1] for p in r["prices"]]
        return {"closes":closes,"price":closes[-1],"chg":(closes[-1]-closes[-2])/closes[-2]*100,"ok":True}
    except Exception:
        return {"closes":[fallback]*30,"price":fallback,"chg":0.4,"ok":False}


@st.cache_data(ttl=60)
def fetch_binance_live(sym):
    sym_map = {"SOL":"SOLUSDT","AVAX":"AVAXUSDT","LINK":"LINKUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT"}
    bsym = sym_map.get(sym)
    if not bsym: return None
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={bsym}", timeout=6).json()
        return {"price":float(r["lastPrice"]),"chg":float(r["priceChangePercent"]),
                "high":float(r["highPrice"]),"low":float(r["lowPrice"]),"vol":float(r["volume"])}
    except Exception: return None


@st.cache_data(ttl=120)
def fetch_polygon_data(ticker, key, days=60):
    try:
        to = datetime.today().strftime("%Y-%m-%d")
        frm = (datetime.today()-timedelta(days=days)).strftime("%Y-%m-%d")
        url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
               f"{frm}/{to}?adjusted=true&sort=asc&limit={days}&apiKey={key}")
        d = requests.get(url, timeout=15).json()
        if "results" not in d or len(d["results"]) < 5: raise ValueError("no data")
        closes = [r["c"] for r in d["results"]]
        return {"closes":closes,"price":closes[-1],"chg":(closes[-1]-closes[-2])/closes[-2]*100,"ok":True}
    except Exception:
        base = {"SOXL":45,"TQQQ":58,"XBI":82}
        p = base.get(ticker, 50)
        return {"closes":[p]*30,"price":p,"chg":0.2,"ok":False}


@st.cache_data(ttl=300)
def fetch_fear_greed():
    try:
        d = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8).json()["data"]
        return int(d[0]["value"]), d[0]["value_classification"]
    except Exception: return 50, "Neutral"


@st.cache_data(ttl=30)
def fetch_order_flow(sym, limit=500):
    sym_map = {"SOL":"SOLUSDT","AVAX":"AVAXUSDT","LINK":"LINKUSDT","BTC":"BTCUSDT","ETH":"ETHUSDT"}
    bsym = sym_map.get(sym)
    if not bsym:
        return {"ok":False,"flow_ratio":0.5,"flow_score":0,"buy_vol":0,
                "sell_vol":0,"momentum":False,"verdict":"N/A","price_chg_pct":0}
    try:
        url = f"https://api.binance.com/api/v3/aggTrades?symbol={bsym}&limit={limit}"
        data = requests.get(url, timeout=8).json()
        if not isinstance(data, list) or not data: raise ValueError("empty")
        buy_vol = 0.0; sell_vol = 0.0
        first_p = float(data[0]["p"]); last_p = float(data[-1]["p"])
        for t in data:
            q = float(t["q"])
            if t["m"]: sell_vol += q
            else: buy_vol += q
        total = buy_vol + sell_vol
        if total <= 0: raise ValueError("zero")
        flow_ratio = buy_vol / total
        flow_score = int((flow_ratio - 0.5) * 200)
        price_chg = (last_p - first_p) / first_p * 100
        momentum = (flow_score > 10 and price_chg > 0) or (flow_score < -10 and price_chg < 0)
        if flow_score > 25: verdict = "STRONG BUY FLOW"
        elif flow_score > 10: verdict = "BUY FLOW"
        elif flow_score < -25: verdict = "STRONG SELL FLOW"
        elif flow_score < -10: verdict = "SELL FLOW"
        else: verdict = "BALANCED"
        return {"ok":True,"flow_ratio":round(flow_ratio,3),"flow_score":flow_score,
                "buy_vol":round(buy_vol,2),"sell_vol":round(sell_vol,2),
                "momentum":momentum,"verdict":verdict,"price_chg_pct":round(price_chg,3)}
    except Exception:
        return {"ok":False,"flow_ratio":0.5,"flow_score":0,"buy_vol":0,
                "sell_vol":0,"momentum":False,"verdict":"FETCH ERROR","price_chg_pct":0}

# ==============================================================
# INDICATORS
# ==============================================================
def ema_series(arr, n):
    if not arr or len(arr) < 2: return list(arr) if arr else []
    k = 2/(n+1); out = [arr[0]]
    for v in arr[1:]: out.append(v*k + out[-1]*(1-k))
    return out


def rsi_full(closes, n=14):
    if len(closes) < n+2: return [50.0]*len(closes)
    deltas = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains = [max(d,0) for d in deltas]; losses = [abs(min(d,0)) for d in deltas]
    avg_g = sum(gains[:n])/n; avg_l = sum(losses[:n])/n
    rsi_vals = [None]*n
    rsi_vals.append(100 - 100/(1+avg_g/max(avg_l,1e-9)))
    for i in range(n,len(deltas)):
        avg_g = (avg_g*(n-1)+gains[i])/n; avg_l = (avg_l*(n-1)+losses[i])/n
        rsi_vals.append(100 - 100/(1+avg_g/max(avg_l,1e-9)))
    return [50.0] + rsi_vals


def atr_series(closes, highs, lows, n=14):
    tr = []
    for i in range(1,len(closes)):
        h = highs[i] if highs else closes[i]*1.005
        l = lows[i] if lows else closes[i]*0.995
        tr.append(max(h-l, abs(h-closes[i-1]), abs(l-closes[i-1])))
    if len(tr) < n: return [None]*len(closes)
    atr = [sum(tr[:n])/n]
    for v in tr[n:]: atr.append((atr[-1]*(n-1)+v)/n)
    return [None]*n + atr


def bb_bands(closes, n=20, k=2.0):
    mid=[]; upper=[]; lower=[]; pct=[]
    for i in range(n-1,len(closes)):
        window = closes[i-n+1:i+1]
        m = sum(window)/n
        sd = (sum((v-m)**2 for v in window)/n)**0.5
        mid.append(m); upper.append(m+k*sd); lower.append(m-k*sd)
        pct.append((closes[i]-lower[-1])/(upper[-1]-lower[-1]+1e-9))
    pad = [None]*(n-1)
    return pad+mid, pad+upper, pad+lower, pad+pct


def detect_regime(closes, highs=None, lows=None):
    if len(closes) < 25:
        return {"regime":"UNKNOWN","adx_lite":0,"bb_width_pct":0,"atr_pct_rank":50}
    h = highs or [c*1.005 for c in closes]
    l = lows or [c*0.995 for c in closes]
    n = 14; dm_plus=[]; dm_minus=[]
    for i in range(1,len(closes)):
        up = h[i]-h[i-1]; dn = l[i-1]-l[i]
        dm_plus.append(max(up,0) if up>dn else 0)
        dm_minus.append(max(dn,0) if dn>up else 0)
    atr_vals = atr_series(closes,h,l,n)
    atr_v = [v for v in atr_vals if v is not None]
    if not atr_v: return {"regime":"UNKNOWN","adx_lite":0,"bb_width_pct":0,"atr_pct_rank":50}
    di_plus = 100*sum(dm_plus[-n:])/(sum(atr_v[-n:])+1e-9)
    di_minus = 100*sum(dm_minus[-n:])/(sum(atr_v[-n:])+1e-9)
    dx = 100*abs(di_plus-di_minus)/(di_plus+di_minus+1e-9)
    adx_lite = round(dx,1)
    bb_m,bb_u,bb_l,_ = bb_bands(closes)
    bb_w = [(u-l_)/m*100 for u,l_,m in zip(bb_u,bb_l,bb_m) if u and l_ and m]
    bb_width_pct = round(bb_w[-1],2) if bb_w else 0
    atr_pct = atr_v[-1]/closes[-1]*100
    atr_hist = [v/closes[max(0,i-1)]*100 for i,v in enumerate(atr_v)]
    atr_pct_rank = round(100*sum(1 for v in atr_hist if v<=atr_pct)/len(atr_hist),0) if atr_hist else 50
    if atr_pct_rank > 80: regime = "VOLATILE"
    elif adx_lite > 25: regime = "TRENDING"
    else: regime = "RANGING"
    return {"regime":regime,"adx_lite":adx_lite,"bb_width_pct":bb_width_pct,"atr_pct_rank":int(atr_pct_rank)}


def detect_divergence(closes, rsi_vals, lookback=10):
    result = {"bull_div":False,"bear_div":False,"desc":"","macd_bull":False,"macd_bear":False,"macd_desc":""}
    if len(closes)<lookback+2 or len(rsi_vals)<lookback+2: return result
    c_slice = closes[-lookback:]
    r_slice = [v for v in rsi_vals[-lookback:] if v is not None]
    if len(r_slice) >= lookback:
        pli = c_slice.index(min(c_slice)); phi = c_slice.index(max(c_slice))
        prev_c = closes[-(lookback*2):-lookback]
        prev_r = [v for v in rsi_vals[-(lookback*2):-lookback] if v is not None]
        if prev_c and prev_r:
            try:
                prl = prev_r[prev_c.index(min(prev_c))]; prh = prev_r[prev_c.index(max(prev_c))]
                if min(c_slice)<min(prev_c) and r_slice[pli]>prl+3:
                    result["bull_div"]=True; result["desc"]="BULL DIV - Price lower low, RSI did not"
                elif max(c_slice)>max(prev_c) and r_slice[phi]<prh-3:
                    result["bear_div"]=True; result["desc"]="BEAR DIV - Price higher high, RSI did not"
            except (ValueError,IndexError): pass
    if len(closes)>=26:
        macd_s=[]
        for i in range(26,len(closes)+1):
            sl=closes[:i]; macd_s.append(ema_series(sl,12)[-1]-ema_series(sl,26)[-1])
        if len(macd_s)>=lookback*2:
            ms=macd_s[-lookback:]; mp=macd_s[-(lookback*2):-lookback]
            ps=closes[-lookback:]; pp=closes[-(lookback*2):-lookback]
            if pp and mp:
                if min(ps)<min(pp) and min(ms)>min(mp)+0.0001:
                    result["macd_bull"]=True; result["macd_desc"]="MACD BULL DIV - Momentum diverging up"
                elif max(ps)>max(pp) and max(ms)<max(mp)-0.0001:
                    result["macd_bear"]=True; result["macd_desc"]="MACD BEAR DIV - Momentum fading"
    return result


def scan_patterns(closes, highs=None, lows=None):
    patterns = []
    if len(closes) < 10: return patterns
    h = highs or [c*1.005 for c in closes]
    l = lows or [c*0.995 for c in closes]
    c = closes
    if h[-1]>h[-3]>h[-5] and l[-1]>l[-3]>l[-5]: patterns.append("HH/HL STRUCTURE")
    if h[-1]<h[-3]<h[-5] and l[-1]<l[-3]<l[-5]: patterns.append("LH/LL STRUCTURE")
    if h[-1]<h[-2] and l[-1]>l[-2]: patterns.append("INSIDE BAR")
    if h[-1]>h[-2] and l[-1]<l[-2]: patterns.append("OUTSIDE BAR")
    if c[-3]<c[-4] and c[-2]<c[-3] and c[-1]>c[-2] and c[-1]>c[-3]: patterns.append("3-BAR BULL REV")
    if c[-3]>c[-4] and c[-2]>c[-3] and c[-1]<c[-2] and c[-1]<c[-3]: patterns.append("3-BAR BEAR REV")
    if (max(h[-4:])-min(l[-4:]))/c[-1]*100 < 1.5: patterns.append("TIGHT COIL")
    if len(c)>5:
        avg_body = np.mean([abs(c[i]-c[i-1]) for i in range(-5,-1)])
        if abs(c[-1]-c[-2])>2*avg_body and avg_body>0: patterns.append("WIDE RANGE BAR")
    return patterns


def smart_money_clock():
    utc = datetime.now(ZoneInfo("UTC")); h = utc.hour + utc.minute/60
    score = 25
    for (h1,h2),s in SCORE_MAP.items():
        if h1<=h<h2: score=s; break
    dow = utc.weekday()
    if dow==4 and h>16: score=int(score*0.7)
    if dow in (5,6): score=int(score*0.4)
    sessions=[]
    if 0<=h<9: sessions.append("Tokyo")
    if 8<=h<17: sessions.append("London")
    if 13<=h<22: sessions.append("New York")
    if 13<=h<17: sessions.append("Overlap")
    label = "PEAK" if score>=85 else "ACTIVE" if score>=60 else "MODERATE" if score>=40 else "LOW"
    return score, label, sessions


def risk_of_ruin(win_rate_pct, rr_ratio, risk_pct_per_trade, ruin_threshold=0.5):
    w = win_rate_pct/100; l = 1-w
    if rr_ratio<=0 or w<=0:
        return {"kelly":0,"ror":100,"edge":0,"half_kelly":0,"using_pct":0,"vs_half_kelly":"OVER"}
    edge = w*rr_ratio - l
    full_kelly = edge/rr_ratio if edge>0 else 0
    half_kelly = full_kelly/2
    if edge<=0: ror=100.0
    else:
        q = l/(w*rr_ratio)
        if q>=1: ror=100.0
        else:
            n_units = math.log(ruin_threshold)/math.log(q) if q>0 else 999
            ror = round(min(100,max(0,(q**n_units)*100)),1)
    return {"kelly":round(full_kelly*100,2),"half_kelly":round(half_kelly*100,2),
            "ror":round(ror,1),"edge":round(edge*100,2),
            "using_pct":round(risk_pct_per_trade*100,2),
            "vs_half_kelly":"OVER" if risk_pct_per_trade*100>half_kelly*100 else "UNDER"}


def volatility_regime(closes, window=20):
    if len(closes)<window+5: return {"rv":0,"rv_pct_rank":50,"forecast":"STABLE","rv_5d":0}
    rets = [math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
    rv_series = []
    for i in range(window,len(rets)+1):
        rv_series.append(np.std(rets[i-window:i])*math.sqrt(252)*100)
    rv_now = rv_series[-1]
    rv_5d = np.mean([r**2 for r in rets[-5:]])**0.5*math.sqrt(252)*100
    rank = sum(1 for v in rv_series if v<=rv_now)/len(rv_series)*100
    if rv_now>rv_series[-2]*1.15: forecast="EXPANDING"
    elif rv_now<rv_series[-2]*0.88: forecast="CONTRACTING"
    else: forecast="STABLE"
    return {"rv":round(rv_now,1),"rv_pct_rank":round(rank,0),"forecast":forecast,"rv_5d":round(rv_5d,1)}


def compute_liquidity_zones(closes, n_bins=20):
    if not closes or len(closes)<30:
        return {"hvn":[],"lvn":[],"poc":None,"liq_score":0,
                "zone_type":"NEUTRAL","dist_to_poc_pct":0,"current_zone_density":0}
    arr = np.array(closes)
    p_min,p_max = float(arr.min()),float(arr.max())
    if p_max<=p_min:
        return {"hvn":[],"lvn":[],"poc":None,"liq_score":0,
                "zone_type":"NEUTRAL","dist_to_poc_pct":0,"current_zone_density":0}
    bin_edges = np.linspace(p_min,p_max,n_bins+1)
    counts,_ = np.histogram(arr,bins=bin_edges)
    bin_centers = (bin_edges[:-1]+bin_edges[1:])/2
    max_count = counts.max() if counts.max()>0 else 1
    density = counts/max_count
    hvn = [round(float(bin_centers[i]),2) for i in np.where(density>=0.70)[0]]
    lvn = [round(float(bin_centers[i]),2) for i in np.where((density<=0.25)&(counts>0))[0]]
    poc_idx = int(counts.argmax()); poc = round(float(bin_centers[poc_idx]),2)
    cur = float(closes[-1])
    cur_bin = min(n_bins-1,max(0,int((cur-p_min)/(p_max-p_min)*n_bins)))
    cur_density = float(density[cur_bin])
    dist_to_poc = (cur-poc)/poc*100 if poc else 0
    liq_score=0; zone_type="NEUTRAL"
    if cur_density<=0.25: zone_type="LVN_BREAKOUT"; liq_score=18
    elif cur_density>=0.70: zone_type="HVN_CHOP"; liq_score=5
    else:
        if cur_bin>0 and density[cur_bin-1]>=0.70 and cur_density<0.50:
            zone_type="HVN_REJECT_UP"; liq_score=12
        elif cur_bin<n_bins-1 and density[cur_bin+1]>=0.70 and cur_density<0.50:
            zone_type="HVN_REJECT_DOWN"; liq_score=12
        else: zone_type="NEUTRAL"; liq_score=7
    return {"hvn":hvn,"lvn":lvn,"poc":poc,"liq_score":liq_score,
            "zone_type":zone_type,"dist_to_poc_pct":round(dist_to_poc,2),
            "current_zone_density":round(cur_density,3)}


def ks_regime_shift(closes, recent_n=10, baseline_n=30):
    if not closes or len(closes)<recent_n+baseline_n+2:
        return {"ks_stat":0,"p_value":1.0,"regime_stable":True,"verdict":"INSUFFICIENT_DATA","trust_fitness":True}
    rets = np.diff(np.log(np.array(closes)))
    if len(rets)<recent_n+baseline_n:
        return {"ks_stat":0,"p_value":1.0,"regime_stable":True,"verdict":"INSUFFICIENT_DATA","trust_fitness":True}
    recent = rets[-recent_n:]; baseline = rets[-(recent_n+baseline_n):-recent_n]
    combined = np.sort(np.concatenate([recent,baseline]))
    cdf_r = np.searchsorted(np.sort(recent),combined,'right')/len(recent)
    cdf_b = np.searchsorted(np.sort(baseline),combined,'right')/len(baseline)
    ks_stat = float(np.max(np.abs(cdf_r-cdf_b)))
    n1,n2 = len(recent),len(baseline)
    en = math.sqrt(n1*n2/(n1+n2))
    lam = (en+0.12+0.11/en)*ks_stat
    p_value = 0.0
    for j in range(1,101):
        term = ((-1)**(j-1))*math.exp(-2*lam*lam*j*j)
        p_value += term
        if abs(term)<1e-10: break
    p_value = max(0.0,min(1.0,2*p_value))
    if p_value>0.10: verdict="STABLE"; stable=True; trust=True
    elif p_value>0.01: verdict="SHIFTING"; stable=False; trust=False
    else: verdict="BROKEN"; stable=False; trust=False
    return {"ks_stat":round(ks_stat,3),"p_value":round(p_value,4),
            "regime_stable":stable,"verdict":verdict,"trust_fitness":trust} # ==============================================================
# SMART MONEY FOOTPRINTS
# ==============================================================
def find_rejection_blocks(closes, highs=None, lows=None, lookback=20):
    if not closes or len(closes)<5: return {"blocks":[],"active":None,"rb_score":0}
    h = highs or [c*1.005 for c in closes]
    l = lows or [c*0.995 for c in closes]
    blocks=[]
    for i in range(max(1,len(closes)-lookback), len(closes)):
        op=closes[i-1]; cl=closes[i]; hi=h[i]; lo=l[i]; rng=hi-lo
        if rng<=0: continue
        uw=hi-max(op,cl); lw=min(op,cl)-lo; body=abs(cl-op)
        if lw/rng>0.55 and (cl-lo)/rng>0.66 and body/rng<0.4:
            strength=int(min(100,(lw/rng)*100+(cl-lo)/rng*30))
            blocks.append({"bar":i,"type":"BULL_RB","price":round(lo,2),"strength":strength,"age":len(closes)-1-i})
        if uw/rng>0.55 and (hi-cl)/rng>0.66 and body/rng<0.4:
            strength=int(min(100,(uw/rng)*100+(hi-cl)/rng*30))
            blocks.append({"bar":i,"type":"BEAR_RB","price":round(hi,2),"strength":strength,"age":len(closes)-1-i})
    active=None
    for b in reversed(blocks):
        if b["age"]<=5: active=b; break
    rb_score = max(0,15-active["age"]*2) if active else 0
    return {"blocks":blocks[-8:],"active":active,"rb_score":rb_score}


def find_liquidity_sweeps(closes, highs=None, lows=None, lookback=15):
    if not closes or len(closes)<lookback+2: return {"sweeps":[],"active":None,"sweep_score":0}
    h = highs or [c*1.005 for c in closes]
    l = lows or [c*0.995 for c in closes]
    sweeps=[]
    for i in range(max(5,len(closes)-8), len(closes)):
        ph=h[max(0,i-lookback):i]; pl=l[max(0,i-lookback):i]
        if not ph or not pl: continue
        swing_hi=max(ph); swing_lo=min(pl)
        if l[i]<swing_lo and closes[i]>swing_lo:
            sweeps.append({"bar":i,"type":"BULL_SWEEP","swept_level":round(swing_lo,2),
                           "age":len(closes)-1-i,"depth_pct":round((swing_lo-l[i])/swing_lo*100,2)})
        if h[i]>swing_hi and closes[i]<swing_hi:
            sweeps.append({"bar":i,"type":"BEAR_SWEEP","swept_level":round(swing_hi,2),
                           "age":len(closes)-1-i,"depth_pct":round((h[i]-swing_hi)/swing_hi*100,2)})
    active=None
    for s in reversed(sweeps):
        if s["age"]<=3: active=s; break
    sweep_score=0
    if active:
        sweep_score=max(0,15-active["age"]*3)+min(3,int(active.get("depth_pct",0)*5))
        sweep_score=min(15,sweep_score)
    return {"sweeps":sweeps[-6:],"active":active,"sweep_score":sweep_score}


def detect_smt_divergence(closes_a, closes_b, name_a, name_b, lookback=10):
    if not closes_a or not closes_b or len(closes_a)<lookback+2 or len(closes_b)<lookback+2:
        return {"smt":None,"desc":"","smt_score":0,"pair":""}
    n=min(len(closes_a),len(closes_b),lookback*2+2)
    a=closes_a[-n:]; b=closes_b[-n:]
    ar=a[-lookback:]; ap=a[-(lookback*2):-lookback]
    br=b[-lookback:]; bp=b[-(lookback*2):-lookback]
    if not ap or not bp: return {"smt":None,"desc":"","smt_score":0,"pair":""}
    a_hh=max(ar)>max(ap); b_hh=max(br)>max(bp)
    a_ll=min(ar)<min(ap); b_ll=min(br)<min(bp)
    smt=None; desc=""; score=0
    if a_hh and not b_hh: smt="BEAR_SMT"; desc=f"{name_a} new high - {name_b} did not"; score=10
    elif b_hh and not a_hh: smt="BEAR_SMT"; desc=f"{name_b} new high - {name_a} did not"; score=10
    elif a_ll and not b_ll: smt="BULL_SMT"; desc=f"{name_a} new low - {name_b} held"; score=10
    elif b_ll and not a_ll: smt="BULL_SMT"; desc=f"{name_b} new low - {name_a} held"; score=10
    return {"smt":smt,"desc":desc,"smt_score":score,"pair":f"{name_a}/{name_b}"}


# ==============================================================
# SIGNAL ENGINE
# ==============================================================
def compute_full_signal(closes, highs=None, lows=None, volumes=None, rules=None):
    empty = {"signal":"HOLD","conf":50,"rsi":50,"price":closes[-1] if closes else 0,
             "atr_pct":0,"bb_pct":50,"stoch_k":50,"mom":0,"vol_surge":1,"score":0,
             "long_pts":0,"short_pts":0,"reasons":[],"rule_block":False,
             "stop":None,"target":None,"ema8":0,"ema21":0,"ema50":0,
             "divergence":{"bull_div":False,"bear_div":False,"desc":"",
                           "macd_bull":False,"macd_bear":False,"macd_desc":""},
             "regime":{"regime":"UNKNOWN"},"patterns":[],"vol_regime":{"rv":0},
             "macd":0,"macd_signal":0,"rsi7":50}
    if not closes or len(closes)<22: return empty
    price=closes[-1]
    e8=ema_series(closes,8);   e8v=e8[-1];  e8p=e8[-2] if len(e8)>1 else e8v
    e21=ema_series(closes,21); e21v=e21[-1]
    e50=ema_series(closes,50) if len(closes)>=50 else ema_series(closes,21); e50v=e50[-1]
    e3=ema_series(closes,3);   e3v=e3[-1];  e3p=e3[-2] if len(e3)>1 else e3v
    e12v=ema_series(closes,12)[-1]
    e26v=ema_series(closes,26)[-1] if len(closes)>=26 else closes[-1]
    macd=e12v-e26v
    macd_p=(ema_series(closes[:-1],12)[-1]-ema_series(closes[:-1],26)[-1]
            if len(closes[:-1])>=26 else macd)
    macd_sl=ema_series([macd]*9,9)[-1]
    rsi_arr=rsi_full(closes,14); rsi_val=next((v for v in reversed(rsi_arr) if v is not None),50)
    rsi7_arr=rsi_full(closes,7); rsi7_val=next((v for v in reversed(rsi7_arr) if v is not None),50)
    _,bb_u,bb_l,bb_pct_arr=bb_bands(closes)
    bb_pct_val=bb_pct_arr[-1]*100 if bb_pct_arr and bb_pct_arr[-1] is not None else 50
    if len(closes)>=14:
        lo14=min(closes[-14:]); hi14=max(closes[-14:])
        stoch_k=100*(price-lo14)/(hi14-lo14+1e-9)
        stoch_prev=(100*(closes[-2]-min(closes[-16:-2]))/(max(closes[-16:-2])-min(closes[-16:-2])+1e-9)
                    if len(closes)>=16 else stoch_k)
    else: stoch_k=stoch_prev=50
    h_arr=highs or [c*1.005 for c in closes]
    l_arr=lows  or [c*0.995 for c in closes]
    atr_arr=atr_series(closes,h_arr,l_arr,14)
    atr_val=next((v for v in reversed(atr_arr) if v is not None),price*0.01)
    atr_pct=atr_val/price*100
    vol_surge=1.0
    if volumes and len(volumes)>=20:
        vol_ma=sum(volumes[-20:])/20; vol_surge=volumes[-1]/(vol_ma+1e-9)
    mom5=(closes[-1]-closes[-6])/closes[-6]*100 if len(closes)>5 else 0
    long_pts=0; short_pts=0; reasons=[]
    if e8v>e21v>e50v: long_pts+=5; reasons.append("EMA 8/21/50 fully bullish")
    elif e8v>e21v: long_pts+=3; reasons.append("EMA 8 > 21 bullish")
    if e8v<e21v<e50v: short_pts+=5; reasons.append("EMA 8/21/50 fully bearish")
    elif e8v<e21v: short_pts+=3; reasons.append("EMA 8 < 21 bearish")
    if e3v>e8v and e3p<=e8p: long_pts+=3; reasons.append("EMA 3x8 bullish crossover")
    if e3v<e8v and e3p>=e8p: short_pts+=3; reasons.append("EMA 3x8 bearish crossover")
    if macd>macd_sl and macd_p<=macd_sl: long_pts+=4; reasons.append("MACD bullish crossover")
    elif macd>macd_sl: long_pts+=2
    if macd<macd_sl and macd_p>=macd_sl: short_pts+=4; reasons.append("MACD bearish crossover")
    elif macd<macd_sl: short_pts+=2
    if rsi_val<28: long_pts+=5; reasons.append(f"RSI {rsi_val:.0f} - deeply oversold")
    elif rsi_val<38: long_pts+=2; reasons.append(f"RSI {rsi_val:.0f} - low territory")
    elif 42<rsi_val<60: long_pts+=1
    if rsi_val>72: short_pts+=5; reasons.append(f"RSI {rsi_val:.0f} - deeply overbought")
    elif rsi_val>62: short_pts+=2; reasons.append(f"RSI {rsi_val:.0f} - elevated")
    if stoch_k<15 and stoch_k>stoch_prev: long_pts+=3; reasons.append("Stoch crossed up from oversold")
    elif stoch_k<25: long_pts+=1
    if stoch_k>85 and stoch_k<stoch_prev: short_pts+=3; reasons.append("Stoch crossed down from overbought")
    elif stoch_k>75: short_pts+=1
    if bb_pct_val<8: long_pts+=3; reasons.append("At lower Bollinger Band")
    elif bb_pct_val<22: long_pts+=1
    if bb_pct_val>92: short_pts+=3; reasons.append("At upper Bollinger Band")
    elif bb_pct_val>78: short_pts+=1
    if mom5>0.8: long_pts+=3; reasons.append(f"Strong momentum +{mom5:.1f}%")
    elif mom5>0.3: long_pts+=1
    if mom5<-0.8: short_pts+=3; reasons.append(f"Strong downswing {mom5:.1f}%")
    elif mom5<-0.3: short_pts+=1
    if vol_surge>1.8:
        if long_pts>short_pts: long_pts+=2; reasons.append(f"Volume surge {vol_surge:.1f}x confirms")
        elif short_pts>long_pts: short_pts+=2; reasons.append(f"Volume surge {vol_surge:.1f}x confirms")
    div=detect_divergence(closes,rsi_arr)
    if div["bull_div"]:  long_pts+=4;  reasons.append("RSI Bullish divergence")
    if div["bear_div"]:  short_pts+=4; reasons.append("RSI Bearish divergence")
    if div["macd_bull"]: long_pts+=3;  reasons.append("MACD Bullish divergence")
    if div["macd_bear"]: short_pts+=3; reasons.append("MACD Bearish divergence")
    rule_block=False
    for rule in (rules or []):
        if not rule.get("active",True): continue
        rt=rule.get("type",""); rv=float(rule.get("value",0))
        if rt=="rsi_max" and rsi_val>rv: rule_block=True; reasons.append(f"Rule: RSI>{rv:.0f} blocks")
        if rt=="rsi_min" and rsi_val<rv: rule_block=True; reasons.append(f"Rule: RSI<{rv:.0f} blocks")
        if rt=="no_trade_hours":
            try:
                now_et=datetime.now(ZoneInfo("America/New_York")); hr=now_et.hour
                h1=int(rule.get("h_from",12)); h2=int(rule.get("h_to",13))
                if h1<=hr<h2: rule_block=True; reasons.append(f"Rule: No-trade {h1:02d}-{h2:02d} ET")
            except Exception: pass
        if rt=="vol_min" and vol_surge<rv: rule_block=True; reasons.append("Rule: Volume below minimum")
        if rt=="trend_only":
            if long_pts>short_pts and not (e8v>e21v>e50v): rule_block=True; reasons.append("Rule: Trend-only, EMAs not aligned")
            if short_pts>long_pts and not (e8v<e21v<e50v): rule_block=True; reasons.append("Rule: Trend-only, EMAs not aligned")
        if rt=="atr_max" and atr_pct>rv: rule_block=True; reasons.append(f"Rule: ATR {atr_pct:.1f}% too volatile")
        if rt=="apex_daily_guard":
            daily_left=APEX_CONFIG["daily_loss_limit"]+st.session_state.get("apex_daily_pnl",0)
            if daily_left<rv: rule_block=True; reasons.append(f"Apex: less than ${rv:.0f} daily headroom")
    score=long_pts-short_pts
    if rule_block or abs(score)<3: sig="HOLD"; conf=30
    elif score>=10: sig="STRONG BUY"; conf=min(88,55+score*2)
    elif score>=5:  sig="BUY"; conf=min(76,44+score*2)
    elif score<=-10: sig="STRONG SELL"; conf=min(88,55+abs(score)*2)
    elif score<=-5:  sig="SELL"; conf=min(76,44+abs(score)*2)
    elif rsi_val<28: sig="OVERSOLD"; conf=68
    elif rsi_val>72: sig="OVERBOUGHT"; conf=66
    else: sig="HOLD"; conf=30
    stop_dist=atr_val*1.5; rr=st.session_state.get("rr_ratio",2.0)
    is_long="BUY" in sig or sig=="OVERSOLD"
    stop=round(price-stop_dist if is_long else price+stop_dist,4)
    target=round(price+stop_dist*rr if is_long else price-stop_dist*rr,4)
    return {"signal":sig,"conf":conf,"score":score,"long_pts":long_pts,"short_pts":short_pts,
            "rsi":round(rsi_val,1),"rsi7":round(rsi7_val,1),"price":price,
            "atr_pct":round(atr_pct,2),"bb_pct":round(bb_pct_val,1),
            "stoch_k":round(stoch_k,1),"mom":round(mom5,2),"vol_surge":round(vol_surge,2),
            "macd":round(macd,4),"macd_signal":round(macd_sl,4),
            "ema8":round(e8v,2),"ema21":round(e21v,2),"ema50":round(e50v,2),
            "reasons":reasons[:8],"rule_block":rule_block,"stop":stop,"target":target,
            "divergence":div,"regime":detect_regime(closes,h_arr,l_arr),
            "patterns":scan_patterns(closes,h_arr,l_arr),"vol_regime":volatility_regime(closes)}


def compute_tqs(sig, sm_score, liq_info=None, flow_info=None, rb_info=None, sweep_info=None, smt_info=None):
    pts=0; pts+=min(30,sig.get("conf",30)*0.35)
    reg=sig.get("regime",{}).get("regime","UNKNOWN")
    if reg=="TRENDING": pts+=15
    elif reg=="RANGING": pts+=8
    elif reg=="VOLATILE": pts+=3
    div=sig.get("divergence",{})
    if (div.get("bull_div") and div.get("macd_bull")) or (div.get("bear_div") and div.get("macd_bear")): pts+=15
    elif any([div.get("bull_div"),div.get("bear_div"),div.get("macd_bull"),div.get("macd_bear")]): pts+=8
    pts+=min(10,len(sig.get("patterns",[]))*3)
    vfc=sig.get("vol_regime",{}).get("forecast","STABLE")
    if vfc=="CONTRACTING": pts+=10
    elif vfc=="STABLE": pts+=6
    elif vfc=="EXPANDING": pts+=3
    pts+=min(15,sm_score*0.16)
    vs=sig.get("vol_surge",1)
    if vs>1.5: pts+=5
    elif vs>1.2: pts+=3
    if liq_info: pts+=liq_info.get("liq_score",0)
    if flow_info and flow_info.get("ok"):
        fs=flow_info.get("flow_score",0); s=sig.get("signal","HOLD")
        sl=s in ("BUY","STRONG BUY","OVERSOLD"); ss=s in ("SELL","STRONG SELL","OVERBOUGHT")
        if sl and fs>10: pts+=min(12,fs*0.2)
        elif ss and fs<-10: pts+=min(12,abs(fs)*0.2)
        elif (sl and fs<-25) or (ss and fs>25): pts-=8
    if rb_info and rb_info.get("active"):
        rb=rb_info["active"]; s=sig.get("signal","HOLD")
        sl=s in ("BUY","STRONG BUY","OVERSOLD"); ss=s in ("SELL","STRONG SELL","OVERBOUGHT")
        if (rb["type"]=="BULL_RB" and sl) or (rb["type"]=="BEAR_RB" and ss): pts+=rb_info.get("rb_score",0)
        elif (rb["type"]=="BULL_RB" and ss) or (rb["type"]=="BEAR_RB" and sl): pts-=5
    if sweep_info and sweep_info.get("active"):
        sw=sweep_info["active"]; s=sig.get("signal","HOLD")
        sl=s in ("BUY","STRONG BUY","OVERSOLD"); ss=s in ("SELL","STRONG SELL","OVERBOUGHT")
        if (sw["type"]=="BULL_SWEEP" and sl) or (sw["type"]=="BEAR_SWEEP" and ss): pts+=sweep_info.get("sweep_score",0)
        elif (sw["type"]=="BULL_SWEEP" and ss) or (sw["type"]=="BEAR_SWEEP" and sl): pts-=4
    if smt_info and smt_info.get("smt"):
        s=sig.get("signal","HOLD")
        sl=s in ("BUY","STRONG BUY","OVERSOLD"); ss=s in ("SELL","STRONG SELL","OVERBOUGHT")
        if (smt_info["smt"]=="BULL_SMT" and sl) or (smt_info["smt"]=="BEAR_SMT" and ss): pts+=smt_info.get("smt_score",0)
        elif (smt_info["smt"]=="BULL_SMT" and ss) or (smt_info["smt"]=="BEAR_SMT" and sl): pts-=5
    if sig.get("rule_block"): pts-=20
    if sig.get("signal")=="HOLD": pts=pts*0.4
    return int(min(100,max(0,pts)))


def trader_vote(tr, sig):
    if sig.get("rule_block"): return "hold"
    if sig.get("conf",0)<tr.get("min_conf",55)-5: return "hold"
    s=sig.get("signal","HOLD"); name=tr.get("name","")
    if name=="CONTRARIAN":
        if s=="OVERSOLD": return "long"
        if s=="OVERBOUGHT": return "short"
        return "hold"
    if name=="MACRO" and sig.get("regime",{}).get("regime")!="TRENDING": return "hold"
    if name=="ALGOBOT" and sig.get("conf",0)<60: return "hold"
    is_buy=s in ("BUY","STRONG BUY","OVERSOLD"); is_sell=s in ("SELL","STRONG SELL","OVERBOUGHT")
    if tr.get("wait_strong") and s not in ("STRONG BUY","STRONG SELL"): return "hold"
    if is_buy: return "long"
    if is_sell: return "short"
    return "hold"


def council_vote(traders, sig):
    votes={"long":0,"short":0,"hold":0}; voters={"long":[],"short":[],"hold":[]}
    for tr in traders:
        v=trader_vote(tr,sig); votes[v]+=1; voters[v].append(tr["name"])
    total=sum(votes.values())
    if votes["long"]>votes["short"] and votes["long"]>votes["hold"]:
        verdict="LONG"; strength=votes["long"]/total*100
    elif votes["short"]>votes["long"] and votes["short"]>votes["hold"]:
        verdict="SHORT"; strength=votes["short"]/total*100
    else: verdict="STAND"; strength=votes["hold"]/total*100
    return {**votes,"verdict":verdict,"strength":round(strength,0),"voters":voters}


def quick_fitness(closes, mk, risk_pct, rr, min_conf, name=""):
    if not closes or len(closes)<35: return 0.0
    bal=1000.0; peak=1000.0; wins=losses=0; pos=None
    stop_mult=MARKETS.get(mk,{}).get("stop",0.02)
    for i in range(max(22,len(closes)-60), len(closes)):
        sig=compute_full_signal(closes[:i+1]); price=closes[i]
        if pos:
            is_long=pos["dir"]=="long"
            hit_sl=(is_long and price<=pos["stop"]) or (not is_long and price>=pos["stop"])
            hit_tp=(is_long and price>=pos["tp"]) or (not is_long and price<=pos["tp"])
            if hit_sl or hit_tp:
                ep=pos["tp"] if hit_tp else pos["stop"]
                pnl=(ep-pos["entry"])*pos["units"] if is_long else (pos["entry"]-ep)*pos["units"]
                bal=max(0,bal+pnl); peak=max(peak,bal)
                if pnl>0: wins+=1
                else: losses+=1
                pos=None
        if not pos and sig.get("conf",0)>=min_conf and not sig.get("rule_block"):
            s=sig.get("signal","HOLD")
            is_buy=s in ("BUY","STRONG BUY","OVERSOLD"); is_sell=s in ("SELL","STRONG SELL","OVERBOUGHT")
            if name=="CONTRARIAN": is_buy=(s=="OVERSOLD"); is_sell=(s=="OVERBOUGHT")
            if is_buy or is_sell:
                d="long" if is_buy else "short"; sd=price*stop_mult
                pos={"dir":d,"entry":price,"stop":price-sd if is_buy else price+sd,
                     "tp":price+sd*rr if is_buy else price-sd*rr,"units":(bal*risk_pct)/max(sd,1e-9)}
    total=wins+losses
    if total==0: return 0.0
    ret=(bal-1000)/1000; dd=(peak-bal)/peak if peak>0 else 0
    return round(min(100,max(0,(wins/total*40)+(max(0,ret)*100*0.4)+(total*1.5)-(dd*30))),1)


def update_trader_fitness(tr, all_market_closes):
    scores={mk:quick_fitness(closes,mk,tr["risk_pct"],tr["rr"],tr["min_conf"],tr.get("name",""))
            for mk,closes in all_market_closes.items()}
    if scores:
        avg=round(np.mean(list(scores.values())),1)
        tr["fitness"]=avg; tr["fitness_history"]=(tr.get("fitness_history",[])+[avg])[-30:]
        best=max(scores.items(),key=lambda kv:kv[1])
        tr["best_market"]=best[0]; tr["fitness_per_market"]=scores
    return scores


def adapt_trader(tr):
    trades=tr.get("trades",[])
    if len(trades)<10: return None
    recent=trades[-10:]; wins=sum(1 for t in recent if t.get("result")=="win")
    wr=wins/10*100; base=tr.get("base_min_conf",tr["min_conf"]); current=tr["min_conf"]
    if wr<35 and current<base+12: new=current+2; msg=f"Low WR {wr:.0f}% - raised min_conf to {new}"
    elif wr>65 and current>base-8: new=current-1; msg=f"High WR {wr:.0f}% - lowered min_conf to {new}"
    elif abs(current-base)>3 and 40<=wr<=60:
        new=current+(1 if current<base else -1); msg=f"WR {wr:.0f}% normal - drifting toward base ({new})"
    else: return None
    new=max(40,min(80,new))
    if new!=current:
        tr["min_conf"]=new
        tr.setdefault("adapt_log",[]).append({"time":datetime.now().strftime("%H:%M:%S"),
            "wr":round(wr,0),"old":current,"new":new,"msg":msg})
        tr["adapt_log"]=tr["adapt_log"][-20:]
        return msg
    return None


# ==============================================================
# APEX ENFORCEMENT
# ==============================================================
def check_apex_limits():
    now_et=datetime.now(ZoneInfo("America/New_York"))
    today_str=now_et.strftime("%Y-%m-%d")
    if st.session_state.get("apex_last_day","")!=today_str:
        prev_day=st.session_state.get("apex_last_day","")
        prev_pnl=st.session_state.get("apex_daily_pnl",0.0)
        if prev_day:
            hist=st.session_state.get("apex_daily_history",[])
            hist.append({"date":prev_day,"pnl":round(prev_pnl,2)})
            st.session_state["apex_daily_history"]=hist[-60:]
        st.session_state["apex_daily_pnl"]=0.0
        st.session_state["apex_last_day"]=today_str
        state_save()
    cum_pnl=st.session_state.get("apex_cumulative_pnl",0.0)
    daily_pnl=st.session_state.get("apex_daily_pnl",0.0)
    apex_equity=APEX_CONFIG["account_size"]+cum_pnl
    hw=st.session_state.get("apex_high_water",APEX_CONFIG["account_size"])
    if apex_equity>hw:
        hw=apex_equity; st.session_state["apex_high_water"]=hw
    trailing_dd=hw-apex_equity
    trading_days=st.session_state.get("apex_trading_days",[])
    target_reached=cum_pnl>=APEX_CONFIG["profit_target"]
    locked=False; lock_reason=""
    if daily_pnl<=-APEX_CONFIG["daily_loss_limit"]:
        locked=True; lock_reason=f"Daily loss limit hit: ${abs(daily_pnl):,.0f} lost today"
    elif trailing_dd>=APEX_CONFIG["trailing_drawdown"]:
        locked=True; lock_reason=f"Trailing drawdown limit hit: ${trailing_dd:,.0f} below peak"
    warnings=[]
    warn_at=APEX_CONFIG["warn_at_pct"]
    if not locked:
        dl_used=abs(min(0,daily_pnl))
        if dl_used>=APEX_CONFIG["daily_loss_limit"]*warn_at:
            pct=int(dl_used/APEX_CONFIG["daily_loss_limit"]*100)
            warnings.append(f"Daily loss {pct}% used - ${APEX_CONFIG['daily_loss_limit']-dl_used:.0f} remaining")
        if trailing_dd>=APEX_CONFIG["trailing_drawdown"]*warn_at:
            pct=int(trailing_dd/APEX_CONFIG["trailing_drawdown"]*100)
            warnings.append(f"Trailing drawdown {pct}% used - ${APEX_CONFIG['trailing_drawdown']-trailing_dd:.0f} remaining")
        if len(trading_days)<APEX_CONFIG["min_trading_days"]:
            warnings.append(f"Only {len(trading_days)}/{APEX_CONFIG['min_trading_days']} trading days completed")
    prev_locked=st.session_state.get("apex_locked",False)
    if locked!=prev_locked:
        st.session_state["apex_locked"]=locked
        st.session_state["apex_lock_reason"]=lock_reason
        for tr in TRADERS: tr["paused"]=locked
        state_save()
    return {
        "locked":locked,"lock_reason":lock_reason,"warnings":warnings,
        "apex_equity":round(apex_equity,2),"high_water":round(hw,2),
        "trailing_dd":round(trailing_dd,2),"daily_pnl":round(daily_pnl,2),
        "cumulative_pnl":round(cum_pnl,2),"trading_days":len(trading_days),
        "target_reached":target_reached,
        "pct_to_target":min(100,max(0,cum_pnl/APEX_CONFIG["profit_target"]*100)),
        "daily_loss_pct":min(100,max(0,abs(min(0,daily_pnl))/APEX_CONFIG["daily_loss_limit"]*100)),
        "trailing_dd_pct":min(100,max(0,trailing_dd/APEX_CONFIG["trailing_drawdown"]*100)),
    }


def _apex_record_trade(pnl):
    now_et=datetime.now(ZoneInfo("America/New_York"))
    today_str=now_et.strftime("%Y-%m-%d")
    if st.session_state.get("apex_last_day","")!=today_str:
        st.session_state["apex_daily_pnl"]=0.0
        st.session_state["apex_last_day"]=today_str
    st.session_state["apex_cumulative_pnl"]=st.session_state.get("apex_cumulative_pnl",0.0)+pnl
    st.session_state["apex_daily_pnl"]=st.session_state.get("apex_daily_pnl",0.0)+pnl
    days=st.session_state.get("apex_trading_days",[])
    if today_str not in days:
        st.session_state["apex_trading_days"]=days+[today_str]


def simulate_trader(tr, market_signals):
    if tr.get("paused",False): return
    pos=tr.get("open_pos")
    if pos is not None and not _is_valid_position(pos):
        tr["open_pos"]=None; state_save(); pos=None
    if pos is not None:
        mk=pos.get("market","")
        if not mk or mk not in market_signals:
            tr["open_pos"]=None; state_save(); return
        sig=market_signals.get(mk,{}); p=sig.get("price",pos.get("entry",0))
        is_long=pos.get("dir")=="long"
        stop_price=pos.get("stop",0); tp_price=pos.get("tp",0); entry=pos.get("entry",p)
        units=pos.get("units",0)
        pos["bars_in_trade"]=pos.get("bars_in_trade",0)+1
        risk_pu=abs(entry-stop_price) if abs(entry-stop_price)>1e-9 else 1
        r_mult=(p-entry)/risk_pu if is_long else (entry-p)/risk_pu
        if r_mult>=1.0 and not pos.get("trailed"):
            if is_long and entry>stop_price: pos["stop"]=entry; pos["trailed"]=True; stop_price=entry
            elif not is_long and entry<stop_price: pos["stop"]=entry; pos["trailed"]=True; stop_price=entry
        if r_mult>=2.0:
            if is_long:
                ts=p-risk_pu*0.7
                if ts>stop_price: pos["stop"]=ts; stop_price=ts
            else:
                ts=p+risk_pu*0.7
                if ts<stop_price: pos["stop"]=ts; stop_price=ts
        hit_sl=(is_long and p<=stop_price) or (not is_long and p>=stop_price)
        hit_tp=(is_long and p>=tp_price) or (not is_long and p<=tp_price)
        exit_reason=None
        if hit_tp: exit_reason="TP"
        elif hit_sl: exit_reason="TRAIL" if pos.get("trailed") else "SL"
        sig_str=sig.get("signal","HOLD")
        if not exit_reason:
            if is_long and sig_str in ("STRONG SELL","SELL"): exit_reason="FLIP"
            elif not is_long and sig_str in ("STRONG BUY","BUY"): exit_reason="FLIP"
        if not exit_reason and tr.get("name")=="SCALPER":
            unr=((p-entry)/entry*100) if is_long else ((entry-p)/entry*100)
            if unr>0.5: exit_reason="SCALP"
        if not exit_reason and pos["bars_in_trade"]>=MAX_BARS_IN_TRADE: exit_reason="TIME"
        if exit_reason:
            ep=tp_price if exit_reason=="TP" else stop_price if exit_reason in ("SL","TRAIL") else p
            pnl=(ep-entry)*units if is_long else (entry-ep)*units
            tr["balance"]=max(0.0,tr["balance"]+pnl); tr["peak"]=max(tr["peak"],tr["balance"])
            is_win=pnl>0
            tr["trades"].append({"market":mk,"dir":pos.get("dir","long"),"entry":entry,
                "exit":round(ep,4),"pnl":round(pnl,2),"result":"win" if is_win else "loss",
                "reason":exit_reason,"time":datetime.now().strftime("%H:%M:%S"),
                "conf":pos.get("conf",0),"bars":pos["bars_in_trade"]})
            if is_win:
                tr["win_streak"]=tr.get("win_streak",0)+1; tr["loss_streak"]=0
                tr["longest_win"]=max(tr.get("longest_win",0),tr["win_streak"])
            else:
                tr["loss_streak"]=tr.get("loss_streak",0)+1; tr["win_streak"]=0
                tr["longest_loss"]=max(tr.get("longest_loss",0),tr["loss_streak"])
            tr["history"].append(round(tr["balance"],2)); tr["open_pos"]=None
            _apex_record_trade(pnl); adapt_trader(tr); state_save()
    if tr.get("open_pos") is not None: return
    daily_left=APEX_CONFIG["daily_loss_limit"]+st.session_state.get("apex_daily_pnl",0.0)
    if daily_left<=0: return
    for mk,sig in market_signals.items():
        if sig.get("rule_block"): continue
        if sig.get("conf",0)<tr.get("min_conf",55): continue
        s=sig.get("signal","HOLD")
        is_buy=s in ("BUY","STRONG BUY","OVERSOLD"); is_sell=s in ("SELL","STRONG SELL","OVERBOUGHT")
        if tr.get("name")=="CONTRARIAN":
            if s=="OVERSOLD": is_buy=True; is_sell=False
            elif s=="OVERBOUGHT": is_sell=True; is_buy=False
            elif s in ("STRONG BUY","BUY","STRONG SELL","SELL"): is_buy=is_sell=False
        if tr.get("name")=="MACRO" and sig.get("regime",{}).get("regime")!="TRENDING": continue
        if tr.get("name")=="ALGOBOT" and sig.get("conf",0)<60: continue
        if tr.get("wait_strong") and s not in ("STRONG BUY","STRONG SELL","OVERSOLD","OVERBOUGHT"): continue
        if not is_buy and not is_sell: continue
        d="long" if is_buy else "short"; p=sig.get("price",0)
        if p<=0: continue
        atr_pct=sig.get("atr_pct",0)
        stop_mult=max(MARKETS[mk]["stop"],atr_pct/100*1.2) if atr_pct>0 else MARKETS[mk]["stop"]
        if tr.get("name")=="SCALPER": stop_mult*=0.5
        sd=p*stop_mult; stop=p-sd if is_buy else p+sd; tp=p+sd*tr["rr"] if is_buy else p-sd*tr["rr"]
        risk_amt=min(tr["balance"]*tr["risk_pct"],max(0,daily_left*0.8))
        if risk_amt<=0: continue
        units=risk_amt/max(sd,1e-9)
        tr["open_pos"]={"market":mk,"dir":d,"entry":round(p,2),"stop":round(stop,2),
            "tp":round(tp,2),"units":units,"risk_amt":round(risk_amt,2),
            "time":datetime.now().strftime("%H:%M:%S"),"conf":sig.get("conf",0),
            "bars_in_trade":0,"trailed":False}
        state_save(); break


# ==============================================================
# UTILS
# ==============================================================
def run_diagnostics(sigs, fg_val):
    per={}; all_scores=[]
    for mk,sig in sigs.items():
        s=0; notes=[]
        conf=sig.get("conf",30)
        if sig.get("signal")!="HOLD": s+=min(30,conf//3); notes.append(f"Signal +{min(30,conf//3)}")
        rsi=sig.get("rsi",50)
        if 35<rsi<65: s+=20; notes.append("RSI optimal +20")
        elif 28<rsi<72: s+=10
        else: notes.append(f"RSI extreme {rsi:.0f}")
        mom=abs(sig.get("mom",0))
        if mom>0.8: s+=20; notes.append("Strong momentum +20")
        elif mom>0.3: s+=10
        vs=sig.get("vol_surge",1)
        if vs>1.5: s+=15; notes.append(f"Vol surge {vs:.1f}x +15")
        elif vs>1: s+=7
        bb=sig.get("bb_pct",50); ss=sig.get("signal","HOLD")
        if ss in ("BUY","STRONG BUY","OVERSOLD") and bb<45: s+=15
        elif ss in ("SELL","STRONG SELL","OVERBOUGHT") and bb>55: s+=15
        elif ss!="HOLD": s+=5
        if sig.get("rule_block"): s=max(0,s-25); notes.append("Rule blocked -25")
        div=sig.get("divergence",{})
        if div.get("bull_div") or div.get("macd_bull"): s+=10; notes.append("Div confluence +10")
        if div.get("bear_div") or div.get("macd_bear"): s+=10; notes.append("Div confluence +10")
        s=min(100,max(0,s)); all_scores.append(s)
        per[mk]={"score":s,"notes":notes,"dir":ss,"conf":conf}
    return {"per":per,"overall":round(np.mean(all_scores) if all_scores else 0),"fg_score":10 if 20<fg_val<80 else 0}


def call_claude(prompt, system, key, max_tokens=900):
    if not key: return None, "No Claude key"
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key":key,"anthropic-version":"2023-06-01","Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-5","max_tokens":max_tokens,"system":system,
                  "messages":[{"role":"user","content":prompt}]},timeout=40)
        data=r.json()
        if "content" in data: return "".join(b.get("text","") for b in data["content"] if b.get("type")=="text"),None
        err=data.get("error",{}); return None,f"{err.get('type','')}: {err.get('message',str(data))}"
    except Exception as e: return None,str(e)


NOTES_SYSTEM = "You are Nigel, private trading intelligence for an Apex Trader Funding $50K account. Format: JSON array of 3-4 notes, each with type (watch|buy|sell|info), market (SOL|SOXL|AVAX|LINK|TQQQ|XBI), and text. Max 2 sentences per note. Return ONLY valid JSON."
AI_ANALYST_SYSTEM = "You are Nigel, senior quant running an Apex Trader Funding $50K account. Rules: $1,000 daily loss limit, $2,500 trailing drawdown, $3,000 profit target. Markets: SOL, SOXL, AVAX, LINK, TQQQ, XBI. Give sharp, specific, actionable analysis under 400 words. Always note which Apex futures proxy to use."
WHISPER_SYSTEM = "You are Nigel's inner voice. One elegant market observation. Max 20 words. Return ONLY the text."


def push_note(ntype, market, text):
    st.session_state["notes"].insert(0,{"type":ntype,"market":market,"text":text,"time":datetime.now().strftime("%H:%M")})
    if len(st.session_state["notes"])>50: st.session_state["notes"].pop()
    state_save()


def generate_notes(sigs, sessions):
    if not CLKEY:
        for mk,sig in sigs.items():
            s=sig.get("signal","HOLD"); m=MARKETS[mk]
            if s=="STRONG BUY": push_note("buy",mk,f"{m['label']} aligned perfectly. Apex proxy: {m['apex_proxy']}.")
            elif s=="STRONG SELL": push_note("sell",mk,f"{m['label']} deteriorating. Consider {m['apex_proxy']} short.")
            elif s=="OVERSOLD": push_note("buy",mk,f"{m['label']} flush complete. Wait one confirming bar.")
            elif s=="OVERBOUGHT": push_note("watch",mk,f"{m['label']} extended. Protect profits.")
            elif s=="BUY": push_note("info",mk,f"{m['label']} building a case for the upside.")
        return
    if time.time()-st.session_state["last_ai_call"]<90: return
    st.session_state["last_ai_call"]=time.time()
    summaries=" | ".join(f"{MARKETS[k]['label']}: {v['signal']} RSI={v['rsi']:.0f}" for k,v in sigs.items())
    resp,_=call_claude(f"Markets: {summaries}. Sessions: {', '.join(sessions)}. Generate 4 notes.",NOTES_SYSTEM,CLKEY,600)
    if resp:
        try:
            parsed=json.loads(resp.strip().replace("```json","").replace("```","").strip())
            for n in parsed: push_note(n.get("type","info"),n.get("market","SOL"),n.get("text",""))
        except Exception: pass


def generate_whisper(sigs):
    if not CLKEY: return
    if time.time()-st.session_state["last_whisper_call"]<300: return
    st.session_state["last_whisper_call"]=time.time()
    signals_str=", ".join(f"{k}:{v['signal']}" for k,v in sigs.items())
    resp,err=call_claude(f"Apex $50K signals: {signals_str}. One whisper.",WHISPER_SYSTEM,CLKEY,60)
    if resp and not err:
        w=resp.strip().replace('"','').replace("'",'')
        st.session_state["whisper_feed"].insert(0,{"text":w,"time":datetime.now().strftime("%H:%M")})
        st.session_state["whisper_feed"]=st.session_state["whisper_feed"][:10]; state_save()


def build_ai_context(sigs, prices_dict, diag, apex_status):
    now_et=datetime.now(ZoneInfo("America/New_York"))
    lines=[
        f"TIME: {now_et.strftime('%H:%M ET')}",
        f"APEX: equity=${apex_status['apex_equity']:,.0f} | daily={apex_status['daily_pnl']:+,.0f} | dd=${apex_status['trailing_dd']:,.0f} | profit=${apex_status['cumulative_pnl']:,.0f}",
        f"STATUS: {'LOCKED' if apex_status['locked'] else 'CLEAR'}",
        f"HEALTH: {diag.get('overall',0)}/100","","SIGNALS:",
    ]
    for mk,sig in sigs.items():
        m=MARKETS[mk]
        lines.append(f"  {mk} ({m['apex_proxy']}): {sig['signal']} conf={sig['conf']}% RSI={sig['rsi']} mom={sig['mom']:+.1f}% regime={sig['regime'].get('regime','?')}")
    return "\n".join(lines)


def run_backtest_nigel(closes, mk, risk_pct=0.01, rr=2.0, rules=None):
    if not closes or len(closes)<40: return {"error":"Need at least 40 data points"}
    stop_mult=MARKETS[mk]["stop"]
    cap=float(st.session_state.get("account_size",50_000))
    bal=cap; peak=cap; trades=[]; equity=[]; pos=None; sim_daily=0.0
    highs=[c*1.005 for c in closes]; lows=[c*0.995 for c in closes]
    for i in range(22,len(closes)):
        sig=compute_full_signal(closes[:i+1],highs[:i+1],lows[:i+1],None,rules)
        price=closes[i]
        if i%5==0: sim_daily=0.0
        if pos:
            is_long=pos["dir"]=="long"
            hit_sl=(is_long and price<=pos["stop"]) or (not is_long and price>=pos["stop"])
            hit_tp=(is_long and price>=pos["tp"]) or (not is_long and price<=pos["tp"])
            if hit_sl or hit_tp:
                ep=pos["tp"] if hit_tp else pos["stop"]
                pnl=(ep-pos["entry"])*pos["units"] if is_long else (pos["entry"]-ep)*pos["units"]
                bal=max(0,bal+pnl); peak=max(peak,bal); sim_daily+=pnl
                trades.append({"i":i,"dir":pos["dir"],"entry":pos["entry"],"exit":ep,
                    "pnl":round(pnl,2),"result":"W" if pnl>0 else "L","reason":"TP" if hit_tp else "SL","bal":round(bal,2)})
                pos=None
                if bal<cap*0.92: break
        if sim_daily<=-APEX_CONFIG["daily_loss_limit"]: continue
        if not pos and sig.get("signal")!="HOLD" and not sig.get("rule_block"):
            is_buy="BUY" in sig["signal"] or sig["signal"]=="OVERSOLD"
            is_sell="SELL" in sig["signal"] or sig["signal"]=="OVERBOUGHT"
            if is_buy or is_sell:
                d="long" if is_buy else "short"; sd=price*stop_mult
                stop_p=price-sd if is_buy else price+sd; tp=price+sd*rr if is_buy else price-sd*rr
                ra=min(bal*risk_pct,APEX_CONFIG["daily_loss_limit"]+sim_daily)
                if ra>0: pos={"dir":d,"entry":price,"stop":stop_p,"tp":tp,"units":ra/max(sd,1e-9)}
        equity.append(bal)
    if not trades: return {"error":"No trades generated"}
    tdf=pd.DataFrame(trades); wins=tdf[tdf["pnl"]>0]; losses=tdf[tdf["pnl"]<=0]
    wr=len(wins)/len(tdf)*100
    avg_w=wins["pnl"].mean() if not wins.empty else 0
    avg_l=losses["pnl"].mean() if not losses.empty else 0
    pf=abs(avg_w/avg_l) if avg_l!=0 else 99
    eq_s=pd.Series(equity); max_dd=float(((eq_s-eq_s.cummax())/eq_s.cummax()*100).min())
    sharpe=0
    if len(eq_s)>2:
        r2=eq_s.pct_change().dropna()
        if r2.std()>0: sharpe=float(r2.mean()/r2.std()*np.sqrt(252))
    return {"mk":mk,"total_pnl":round(tdf["pnl"].sum(),2),"return_pct":round((bal-cap)/cap*100,2),
            "bh":round((closes[-1]-closes[0])/closes[0]*100,2),"win_rate":round(wr,1),
            "total_trades":len(tdf),"wins":len(wins),"losses":len(losses),
            "avg_win":round(avg_w,2),"avg_loss":round(avg_l,2),"pf":round(min(pf,99),2),
            "max_dd":round(max_dd,2),"sharpe":round(sharpe,2),"equity":equity,"trades":tdf,
            "final_bal":round(bal,2),"start":cap}


def get_sessions():
    utc=datetime.now(ZoneInfo("UTC")); h=utc.hour+utc.minute/60; s=[]
    if 0<=h<9: s.append(("TOKYO","#7C3AED"))
    if 8<=h<17: s.append(("LONDON","#1D4ED8"))
    if 13<=h<22: s.append(("NEW YORK","#059669"))
    if 13<=h<17: s.append(("OVERLAP","#D97706"))
    if not s: s.append(("OFF-HOURS","#374151"))
    return s


def build_journal_csv():
    rows=[]
    for tr in TRADERS:
        for t in tr.get("trades",[]):
            rows.append({"Desk":tr["name"],"Market":t.get("market",""),"Direction":t.get("dir",""),
                "Entry":t.get("entry",""),"Exit":t.get("exit",""),"PnL":t.get("pnl",0),
                "Result":t.get("result",""),"Reason":t.get("reason",""),
                "Time":t.get("time",""),"Confidence":t.get("conf",0),
                "ApexProxy":MARKETS.get(t.get("market",""),{}).get("apex_proxy","")})
    if not rows: return None
    buf=io.BytesIO(); pd.DataFrame(rows).to_csv(buf,index=False)
    return buf.getvalue()


def fmt_price(mk, p):
    return f"${p:,.0f}" if p>=1000 else f"${p:,.2f}" # ==============================================================
# SIDEBAR
# ==============================================================
with st.sidebar:
    st.markdown('<div style="font-family:Cinzel,serif;font-weight:900;font-size:1.3rem;letter-spacing:.3em;color:#fff;margin:16px 0 2px;">NIGEL</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:9px;color:rgba(255,149,0,0.7);letter-spacing:.12em;margin-bottom:14px;">APEX $50K EDITION</div>', unsafe_allow_html=True)
    restore_ts=st.session_state.get("__restore_ts__","--")
    state_kb=PERSIST_PATH.stat().st_size/1024 if PERSIST_PATH.exists() else 0
    st.markdown(f'<div class="persist-banner"><div style="font-size:9px;">STATE PERSISTENCE</div><div style="font-size:9px;color:#3a3550;margin-top:2px;">Restored {restore_ts} - {state_kb:.1f} KB</div></div>', unsafe_allow_html=True)
    with st.expander("API Keys"):
        np_ = st.text_input("Polygon.io", value=POLY, type="password", key="sb_poly")
        nc_ = st.text_input("Claude AI", value=CLKEY, type="password", key="sb_cla")
        if st.button("Save Keys"):
            st.session_state["polygon_key"]=np_; st.session_state["claude_key"]=nc_
            state_save(); st.cache_data.clear(); st.rerun()
    ai_ok=bool(CLKEY.strip()); pol_ok=bool(POLY.strip())
    pol_color="#1aff8a" if pol_ok else "#ff2d55"
    ai_color="#1aff8a" if ai_ok else "#ff2d55"
    pol_icon="OK" if pol_ok else "X"
    ai_icon="OK" if ai_ok else "X"
    st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;margin:8px 0;"><span style="color:{pol_color};">{pol_icon} POLYGON</span> &nbsp; <span style="color:{ai_color};">{ai_icon} CLAUDE</span></div>', unsafe_allow_html=True)
    st.divider()
    sel=st.multiselect("Instruments",list(MARKETS.keys()),default=st.session_state["selected_markets"])
    if sel: st.session_state["selected_markets"]=sel; state_save()
    new_account=st.number_input("Account ($)",5000,1000000,st.session_state.get("account_size",50_000),1000)
    if new_account!=st.session_state.get("account_size"): st.session_state["account_size"]=new_account; state_save()
    new_rr=st.slider("Reward:Risk",1.0,5.0,float(st.session_state.get("rr_ratio",2.0)),0.25)
    if new_rr!=st.session_state.get("rr_ratio"): st.session_state["rr_ratio"]=new_rr; state_save()
    new_interval=st.select_slider("Auto-refresh",[15,30,60,120,300],value=st.session_state["refresh_interval"],format_func=lambda x:f"{x}s")
    if new_interval!=st.session_state["refresh_interval"]: st.session_state["refresh_interval"]=new_interval; state_save()
    new_ao=st.toggle("Always On",value=st.session_state["always_on"])
    if new_ao!=st.session_state["always_on"]: st.session_state["always_on"]=new_ao; state_save()
    st.divider()
    if st.button("Refresh Now"): st.cache_data.clear(); st.rerun()
    if st.button("Clear Notes"): st.session_state["notes"]=[]; state_save(); st.rerun()
    if st.button("Reset Traders"): st.session_state["traders"]=DEFAULT_TRADERS; state_save(); st.rerun()
    if st.button("Reset Apex PnL"):
        for k in ["apex_cumulative_pnl","apex_daily_pnl","apex_last_day","apex_trading_days","apex_locked","apex_lock_reason","apex_daily_history"]:
            st.session_state[k]=DEFAULTS[k]
        st.session_state["apex_high_water"]=APEX_CONFIG["account_size"]
        for tr in TRADERS: tr["paused"]=False
        state_save(); st.rerun()
    if st.button("Reset Backtests"): st.session_state["bt_cache"]={};  state_save(); st.rerun()
    if st.button("Force Save"):
        state_save(); sz=PERSIST_PATH.stat().st_size/1024 if PERSIST_PATH.exists() else 0
        st.success(f"Saved {sz:.1f} KB")
    if st.button("Clear All State"):
        if PERSIST_PATH.exists(): PERSIST_PATH.unlink()
        for k in PERSIST_KEYS:
            if k in st.session_state: del st.session_state[k]
        st.rerun()
    st.divider()
    jcsv=build_journal_csv()
    if jcsv:
        st.download_button("Download Trade Journal",data=jcsv,
            file_name=f"nigel_apex_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",mime="text/csv")
    st.caption(f"Updated {datetime.now().strftime('%H:%M:%S')}")

SEL=st.session_state["selected_markets"] or ["SOL","SOXL","AVAX","LINK"]
TRADERS=st.session_state["traders"]

# ==============================================================
# LOAD LIVE DATA
# ==============================================================
with st.spinner(""):
    raw_data={}; market_signals={}; live_prices={}
    for mk in SEL:
        m=MARKETS[mk]
        if m.get("crypto") and mk in CRYPTO_MAP:
            cmap=CRYPTO_MAP[mk]
            bd=fetch_binance_live(mk) or {}
            cg=fetch_crypto_price(cmap["cg_id"],fallback=cmap["fallback"])
            price=bd.get("price",cg["price"]); chg=bd.get("chg",cg["chg"])
            raw_data[mk]={"closes":cg["closes"],"price":price,"chg":chg,
                "high":bd.get("high",price*1.01),"low":bd.get("low",price*0.99)}
        else:
            ticker=TICKERS.get(mk,mk); pd_=fetch_polygon_data(ticker,POLY)
            raw_data[mk]={"closes":pd_["closes"],"price":pd_["price"],"chg":pd_["chg"]}
        live_prices[mk]=raw_data[mk]["price"]
        market_signals[mk]=compute_full_signal(raw_data[mk]["closes"],rules=st.session_state.get("rule_set",[]))
        market_signals[mk]["price"]=raw_data[mk]["price"]
        market_signals[mk]["chg"]=raw_data[mk]["chg"]
    fg_val,fg_label=fetch_fear_greed()
    diag=run_diagnostics(market_signals,fg_val)

apex_status=check_apex_limits()
sm_score,sm_label,sm_sessions=smart_money_clock()

liq_per_market={mk:compute_liquidity_zones(raw_data[mk]["closes"]) for mk in SEL}
ks_per_market={mk:ks_regime_shift(raw_data[mk]["closes"]) for mk in SEL}
flow_per_market={mk:(fetch_order_flow(mk) if mk in CRYPTO_MAP
                     else {"ok":False,"flow_ratio":0.5,"flow_score":0,"buy_vol":0,"sell_vol":0,"momentum":False,"verdict":"N/A","price_chg_pct":0})
                 for mk in SEL}
rb_per_market={mk:find_rejection_blocks(raw_data[mk]["closes"]) for mk in SEL}
sweep_per_market={mk:find_liquidity_sweeps(raw_data[mk]["closes"]) for mk in SEL}
smt_per_market={mk:{"smt":None,"desc":"","smt_score":0,"pair":""} for mk in SEL}
for a,b in [("SOL","AVAX"),("TQQQ","SOXL")]:
    if a in SEL and b in SEL:
        res=detect_smt_divergence(raw_data[a]["closes"],raw_data[b]["closes"],a,b)
        if res.get("smt"): smt_per_market[a]=res; smt_per_market[b]=res

tqs_per_market={mk:compute_tqs(market_signals[mk],sm_score,
    liq_info=liq_per_market[mk],flow_info=flow_per_market[mk],
    rb_info=rb_per_market[mk],sweep_info=sweep_per_market[mk],
    smt_info=smt_per_market[mk]) for mk in SEL}
council_per_market={mk:council_vote(TRADERS,market_signals[mk]) for mk in SEL}

for tr in TRADERS: simulate_trader(tr,market_signals)

fit_ctr=st.session_state.get("__fit_ctr__",0)
st.session_state["__fit_ctr__"]=fit_ctr+1
if fit_ctr%3==0:
    for tr in TRADERS: update_trader_fitness(tr,{mk:raw_data[mk]["closes"] for mk in SEL})

sessions_now=get_sessions(); session_names=[s for s,_ in sessions_now]
generate_notes(market_signals,session_names)
generate_whisper(market_signals)

now_ts=time.time()
if (now_ts-st.session_state["last_refresh"])>=st.session_state["refresh_interval"]:
    st.session_state["last_refresh"]=now_ts
    for mk,sig in market_signals.items():
        if sig.get("signal")!="HOLD" and sig.get("conf",0)>=55:
            div=sig.get("divergence",{})
            st.session_state["signal_feed"].insert(0,{
                "time":datetime.now().strftime("%H:%M:%S"),"mk":mk,
                "signal":sig["signal"],"conf":sig["conf"],"price":sig["price"],
                "stop":sig.get("stop"),"target":sig.get("target"),
                "reasons":sig.get("reasons",[])[:2],"patterns":sig.get("patterns",[])[:2],
                "regime":sig.get("regime",{}).get("regime","?"),
                "div_bull":div.get("bull_div",False),"div_bear":div.get("bear_div",False),
                "macd_bull":div.get("macd_bull",False),"macd_bear":div.get("macd_bear",False),
                "tqs":tqs_per_market.get(mk,0),"apex_proxy":MARKETS[mk]["apex_proxy"]})
    st.session_state["signal_feed"]=st.session_state["signal_feed"][:80]
    st.session_state["diag_history"].append({"time":datetime.now(),"score":diag["overall"]})
    st.session_state["diag_history"]=st.session_state["diag_history"][-200:]
    state_save()

fg_color="#1aff8a" if fg_val<=30 else "#ff2d55" if fg_val>=70 else "#c9a84c"
sm_color="#1aff8a" if sm_score>=75 else "#c9a84c" if sm_score>=50 else "#5a5570"

# ==============================================================
# MASTHEAD
# ==============================================================
utc=datetime.now(ZoneInfo("UTC"))
ny=utc.astimezone(ZoneInfo("America/New_York"))
lon=utc.astimezone(ZoneInfo("Europe/London"))
session_badges="".join(f'<span style="display:inline-block;padding:3px 12px;font-family:Cinzel,serif;font-size:10px;font-weight:700;letter-spacing:.1em;margin-right:6px;background:{c}22;color:{c};border:1px solid {c}44;">{n}</span>' for n,c in sessions_now)
st.markdown(f"""
<div class="nigel-masthead">
  <div>
    <div class="nigel-wordmark">NIG<em>E</em>L</div>
    <div class="nigel-tagline">Private Trading Intelligence v5.3 - Apex Edition - $50K Account - 6 Adaptive Desks</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:JetBrains Mono,monospace;font-size:11px;color:#5a5570;">ET {ny.strftime("%H:%M")} &nbsp;-&nbsp; LDN {lon.strftime("%H:%M")} &nbsp;-&nbsp; UTC {utc.strftime("%H:%M")}</div>
    <div style="margin-top:6px;">{session_badges}</div>
    <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570;margin-top:4px;">{SESSION_TIPS.get(sessions_now[0][0],"")}</div>
  </div>
</div>
""", unsafe_allow_html=True)

if apex_status["locked"]:
    st.markdown(f'<div class="shield-banner">APEX LOCK ACTIVE - {apex_status["lock_reason"]}</div>', unsafe_allow_html=True)
elif apex_status["warnings"]:
    for w in apex_status["warnings"]:
        st.markdown(f'<div class="apex-banner">{w}</div>', unsafe_allow_html=True)
elif apex_status["target_reached"]:
    st.markdown('<div class="apex-clear">EVALUATION TARGET REACHED - $3,000 profit achieved.</div>', unsafe_allow_html=True)

# TICKER
def make_ticker():
    items=[]
    for mk in SEL:
        sig=market_signals.get(mk,{}); p=live_prices.get(mk,0); chg=raw_data[mk].get("chg",0)
        d=sig.get("signal","HOLD"); arrow="UP" if chg>=0 else "DN"
        cc="tick-up" if chg>=0 else "tick-dn"
        bc="badge-long" if ("BUY" in d or d=="OVERSOLD") else "badge-short" if ("SELL" in d or d=="OVERBOUGHT") else "badge-hold"
        reg=sig.get("regime",{}).get("regime","")
        rc="badge-regime-trend" if reg=="TRENDING" else "badge-regime-range" if reg=="RANGING" else "badge-regime-vol"
        tqs=tqs_per_market.get(mk,0)
        tc="#1aff8a" if tqs>=70 else "#c9a84c" if tqs>=45 else "#5a5570"
        proxy=MARKETS[mk]["apex_proxy"]
        items.append(f'<span class="tick-item"><span class="tick-sym">{mk}</span><span class="tick-px">{fmt_price(mk,p)}</span><span class="{cc}">{arrow} {abs(chg):.2f}%</span><span class="badge {bc}" style="font-size:9px;padding:1px 6px;">{d}</span><span class="badge {rc}">{reg[:3]}</span><span style="font-family:JetBrains Mono,monospace;font-size:9px;color:{tc};">TQS {tqs}</span><span class="proxy-tag">{proxy}</span><span class="tick-sep">--</span></span>')
    inner="".join(items)*3
    return f'<div class="ticker-wrap"><div class="ticker-track">{inner}</div></div>'

st.markdown(make_ticker(), unsafe_allow_html=True)

# HEADER STATS
health=diag["overall"]
hc="#1aff8a" if health>=70 else "#c9a84c" if health>=45 else "#ff2d55"
apex_eq=apex_status["apex_equity"]
aeq_c="#1aff8a" if apex_status["cumulative_pnl"]>=0 else "#ff2d55"
td_color="#ff2d55" if apex_status["trailing_dd_pct"]>70 else "#c9a84c" if apex_status["trailing_dd_pct"]>40 else "#1aff8a"
hcols=st.columns([3,1,1,1,1,1])
with hcols[1]: st.markdown(f'<div style="text-align:center;padding:8px 0;"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;">HEALTH</div><div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:{hc};">{health}</div></div>', unsafe_allow_html=True)
with hcols[2]: st.markdown(f'<div style="text-align:center;padding:8px 0;"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;">FEAR/GREED</div><div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:{fg_color};">{fg_val}</div><div style="font-size:10px;color:#5a5570;font-style:italic;">{fg_label}</div></div>', unsafe_allow_html=True)
with hcols[3]: st.markdown(f'<div style="text-align:center;padding:8px 0;"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;">APEX EQUITY</div><div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:{aeq_c};">${apex_eq:,.0f}</div><div style="font-size:10px;color:#5a5570;">today {apex_status["daily_pnl"]:+,.0f}</div></div>', unsafe_allow_html=True)
with hcols[4]: st.markdown(f'<div style="text-align:center;padding:8px 0;"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;">TRAIL DD</div><div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:{td_color};">${apex_status["trailing_dd"]:,.0f}</div><div style="font-size:10px;color:#5a5570;">/ $2,500</div></div>', unsafe_allow_html=True)
with hcols[5]: st.markdown(f'<div style="text-align:center;padding:8px 0;"><div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;">TO TARGET</div><div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:#c9a84c;">${max(0,3000-apex_status["cumulative_pnl"]):,.0f}</div><div style="font-size:10px;color:#5a5570;">{apex_status["pct_to_target"]:.0f}% done</div></div>', unsafe_allow_html=True)
st.markdown(f'<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin-bottom:10px;"><span class="live-dot"></span>LIVE - APEX $50K - SOL/SOXL/AVAX/LINK/TQQQ/XBI - {"CLAUDE ON" if CLKEY else "FALLBACK"}</div>', unsafe_allow_html=True)

# SIGNAL CARDS
sig_cols=st.columns(len(SEL))
for col,mk in zip(sig_cols,SEL):
    with col:
        sig=market_signals[mk]; m=MARKETS[mk]; s=sig["signal"]
        conf=sig["conf"]; p=live_prices[mk]; chg=raw_data[mk].get("chg",0)
        is_b="BUY" in s or s=="OVERSOLD"; is_s="SELL" in s or s=="OVERBOUGHT"
        card_cls="bull" if is_b else "bear" if is_s else "flat"
        badge_cls="badge-long" if is_b else "badge-short" if is_s else "badge-hold"
        chg_cls="sc-chg-up" if chg>=0 else "sc-chg-dn"
        reg=sig.get("regime",{}); rn=reg.get("regime","?")
        rc="badge-regime-trend" if rn=="TRENDING" else "badge-regime-range" if rn=="RANGING" else "badge-regime-vol"
        div=sig.get("divergence",{}); div_html=""
        if div.get("bull_div"): div_html+=f'<div class="divergence-bull">{div.get("desc","")}</div>'
        if div.get("bear_div"): div_html+=f'<div class="divergence-bear">{div.get("desc","")}</div>'
        if div.get("macd_bull"): div_html+=f'<div class="macd-bull">{div.get("macd_desc","")}</div>'
        if div.get("macd_bear"): div_html+=f'<div class="macd-bear">{div.get("macd_desc","")}</div>'
        pats=sig.get("patterns",[]); pats_html="".join(f'<span class="pattern-tag">{p2}</span>' for p2 in pats[:3])
        tqs=tqs_per_market.get(mk,0)
        tqs_c="#1aff8a" if tqs>=70 else "#c9a84c" if tqs>=45 else "#ff2d55"
        cv=council_per_market[mk]
        vc="#1aff8a" if cv["verdict"]=="LONG" else "#ff2d55" if cv["verdict"]=="SHORT" else "#5a5570"
        mc_color="#1aff8a" if is_b else "#ff2d55" if is_s else "#c9a84c"
        sfmt=f'${sig["stop"]:,.2f}' if sig.get("stop") else "--"
        tfmt=f'${sig["target"]:,.2f}' if sig.get("target") else "--"
        st.markdown(f"""
        <div class="signal-card {card_cls}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
            <div>
              <div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;color:#5a5570;">{m['sub']}</div>
              <div class="sc-sym">{mk}</div>
              <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:11px;color:#5a5570;">{m['label']}</div>
            </div>
            <div style="text-align:right;">
              <span class="badge {rc}" style="display:block;margin-bottom:3px;">{rn}</span>
              <span class="badge {badge_cls}">{s}</span>
              <div style="margin-top:3px;"><span class="proxy-tag">{m['apex_proxy']}</span></div>
            </div>
          </div>
          <div class="sc-price">{fmt_price(mk,p)}</div>
          <div class="{chg_cls}" style="margin:2px 0 8px;">{"UP" if chg>=0 else "DN"} {abs(chg):.2f}% today</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:6px 0;padding:8px;background:#0d0c16;border-radius:1px;">
            <div style="text-align:center;"><div style="font-family:Cinzel,serif;font-size:1.4rem;font-weight:900;color:{tqs_c};">{tqs}</div><div style="font-family:Cinzel,serif;font-size:7px;letter-spacing:.08em;color:#5a5570;">TQS</div></div>
            <div style="text-align:center;"><div style="font-family:Cinzel,serif;font-size:.9rem;font-weight:900;color:{vc};">{cv["verdict"]}</div><div style="font-family:Cinzel,serif;font-size:7px;letter-spacing:.08em;color:#5a5570;">COUNCIL</div></div>
          </div>
          <div class="meter-track"><div class="meter-fill" style="width:{conf}%;background:{mc_color};"></div></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:2px;">CONF {conf}%</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:8px;font-family:JetBrains Mono,monospace;font-size:10px;">
            <div style="color:#5a5570;">RSI <span style="color:#d4cfc0;">{sig["rsi"]}</span></div>
            <div style="color:#5a5570;">BB% <span style="color:#d4cfc0;">{sig["bb_pct"]}</span></div>
            <div style="color:#ff2d55;">SL {sfmt}</div>
            <div style="color:#1aff8a;">TP {tfmt}</div>
          </div>
          {div_html}
          <div style="margin-top:5px;">{pats_html}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if st.session_state["whisper_feed"]:
    w=st.session_state["whisper_feed"][0]
    st.markdown(f'<div class="whisper-note">{w["text"]}<span style="float:right;font-family:JetBrains Mono,monospace;font-size:9px;color:#3a3550;">{w["time"]}</span></div>', unsafe_allow_html=True)

# ==============================================================
# TABS
# ==============================================================
t0,t1,t2,t3,t4,t5,t6,t7,t8,t9=st.tabs([
    "APEX DESK","PULSE","INTELLIGENCE","TRADERS",
    "SIGNAL FEED","LIVE CHARTS","RULES ENGINE",
    "BACKTEST","AI ANALYST","EDGE TOOLS",
])

# ==============================================================
# TAB 0 - APEX DESK
# ==============================================================
with t0:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#ff9500;margin-bottom:8px;">APEX TRADER FUNDING - $50K ACCOUNT COMPLIANCE</div>', unsafe_allow_html=True)
    if apex_status["locked"]: status_color="#ff2d55"; status_text="LOCKED"; status_sub=apex_status["lock_reason"]
    elif apex_status["target_reached"]: status_color="#1aff8a"; status_text="TARGET HIT"; status_sub="$3,000 profit achieved"
    elif apex_status["warnings"]: status_color="#ff9500"; status_text="WARNING"; status_sub=apex_status["warnings"][0]
    else: status_color="#1aff8a"; status_text="CLEAR"; status_sub="All limits healthy - trade with discipline"
    a0c1,a0c2=st.columns([2,3])
    with a0c1:
        st.markdown(f"""
        <div class="panel" style="border-top:3px solid {status_color};text-align:center;padding:28px 18px;">
          <div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.18em;color:#5a5570;margin-bottom:10px;">ACCOUNT STATUS</div>
          <div style="font-family:Cinzel,serif;font-size:2.8rem;font-weight:900;color:{status_color};line-height:1;">{status_text}</div>
          <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570;margin-top:8px;">{status_sub}</div>
          <hr>
          <div style="font-family:JetBrains Mono,monospace;font-size:11px;line-height:2;text-align:left;">
            <div><span style="color:#5a5570;">Equity:</span> <span style="color:#fff;">${apex_status["apex_equity"]:,.2f}</span></div>
            <div><span style="color:#5a5570;">High water:</span> <span style="color:#1aff8a;">${apex_status["high_water"]:,.2f}</span></div>
            <div><span style="color:#5a5570;">Today P&amp;L:</span> <span style="color:{"#1aff8a" if apex_status["daily_pnl"]>=0 else "#ff2d55"};">${apex_status["daily_pnl"]:+,.2f}</span></div>
            <div><span style="color:#5a5570;">Total profit:</span> <span style="color:{"#1aff8a" if apex_status["cumulative_pnl"]>=0 else "#ff2d55"};">${apex_status["cumulative_pnl"]:+,.2f}</span></div>
            <div><span style="color:#5a5570;">Trading days:</span> <span style="color:#c9a84c;">{apex_status["trading_days"]} / {APEX_CONFIG["min_trading_days"]}</span></div>
          </div>
        </div>""", unsafe_allow_html=True)
    with a0c2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#ff9500;margin-bottom:10px;">LIMIT GAUGES</div>', unsafe_allow_html=True)
        dl_pct=apex_status["daily_loss_pct"]
        dl_color="#ff2d55" if dl_pct>=100 else "#ff9500" if dl_pct>=70 else "#1aff8a"
        dl_used=abs(min(0,apex_status["daily_pnl"]))
        dl_left=APEX_CONFIG["daily_loss_limit"]-dl_used
        st.markdown(f"""
        <div class="panel" style="margin-bottom:10px;border-left:2px solid {dl_color};">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span style="font-family:Cinzel,serif;font-size:10px;color:#fff;">DAILY LOSS LIMIT</span>
            <span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{dl_color};">${dl_used:,.0f} / $1,000</span>
          </div>
          <div class="apex-progress-track"><div class="apex-progress-fill" style="width:{dl_pct:.1f}%;background:{dl_color};"></div></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:3px;">${dl_left:,.0f} remaining - {"LOCKED" if dl_pct>=100 else "CAUTION" if dl_pct>=70 else "CLEAR"}</div>
        </div>""", unsafe_allow_html=True)
        td_pct=apex_status["trailing_dd_pct"]
        td_color="#ff2d55" if td_pct>=100 else "#ff9500" if td_pct>=70 else "#1aff8a"
        td_left=APEX_CONFIG["trailing_drawdown"]-apex_status["trailing_dd"]
        st.markdown(f"""
        <div class="panel" style="margin-bottom:10px;border-left:2px solid {td_color};">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span style="font-family:Cinzel,serif;font-size:10px;color:#fff;">TRAILING DRAWDOWN</span>
            <span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{td_color};">${apex_status["trailing_dd"]:,.0f} / $2,500</span>
          </div>
          <div class="apex-progress-track"><div class="apex-progress-fill" style="width:{td_pct:.1f}%;background:{td_color};"></div></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:3px;">${max(0,td_left):,.0f} buffer from peak ${apex_status["high_water"]:,.0f}</div>
        </div>""", unsafe_allow_html=True)
        pt_pct=apex_status["pct_to_target"]
        pt_color="#1aff8a" if pt_pct>=100 else "#c9a84c" if pt_pct>=50 else "#5a5570"
        pt_left=max(0,APEX_CONFIG["profit_target"]-apex_status["cumulative_pnl"])
        st.markdown(f"""
        <div class="panel" style="margin-bottom:10px;border-left:2px solid {pt_color};">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span style="font-family:Cinzel,serif;font-size:10px;color:#fff;">PROFIT TARGET</span>
            <span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{pt_color};">${apex_status["cumulative_pnl"]:,.0f} / $3,000</span>
          </div>
          <div class="apex-progress-track"><div class="apex-progress-fill" style="width:{pt_pct:.1f}%;background:{pt_color};"></div></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:3px;">{"EVALUATION PASSED" if pt_pct>=100 else f"${pt_left:,.0f} to go - {pt_pct:.0f}% complete"}</div>
        </div>""", unsafe_allow_html=True)
        td_days=apex_status["trading_days"]; td_need=APEX_CONFIG["min_trading_days"]
        td_pct2=min(100,td_days/td_need*100); td_col2="#1aff8a" if td_days>=td_need else "#c9a84c"
        st.markdown(f"""
        <div class="panel" style="border-left:2px solid {td_col2};">
          <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
            <span style="font-family:Cinzel,serif;font-size:10px;color:#fff;">TRADING DAYS</span>
            <span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{td_col2};">{td_days} / {td_need}</span>
          </div>
          <div class="apex-progress-track"><div class="apex-progress-fill" style="width:{td_pct2:.1f}%;background:{td_col2};"></div></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;margin-top:3px;">{"Minimum days met" if td_days>=td_need else f"{td_need-td_days} more unique days needed"}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#ff9500;margin:22px 0 10px;">FUTURES PROXY TABLE</div>', unsafe_allow_html=True)
    proxy_rows=[]
    for mk in SEL:
        sig=market_signals[mk]; m=MARKETS[mk]; cv=council_per_market[mk]; tqs=tqs_per_market[mk]
        proxy_rows.append({"Signal":mk,"Direction":sig.get("signal","HOLD"),"TQS":tqs,
            "Council":cv["verdict"],"Apex Contract":m["apex_proxy"],"Contract Info":m["apex_note"],
            "Price":fmt_price(mk,sig.get("price",0)),"Max Risk 1%":f"${APEX_CONFIG['account_size']*0.01:,.0f}"})
    st.dataframe(pd.DataFrame(proxy_rows),use_container_width=True,hide_index=True)

    daily_hist=st.session_state.get("apex_daily_history",[])
    if len(daily_hist)>=2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#ff9500;margin:20px 0 10px;">DAILY P&L HISTORY</div>', unsafe_allow_html=True)
        dh_df=pd.DataFrame(daily_hist)
        bar_c=["#1aff8a" if p>=0 else "#ff2d55" for p in dh_df["pnl"]]
        fig_dh=go.Figure(go.Bar(x=dh_df["date"],y=dh_df["pnl"],marker=dict(color=bar_c,opacity=0.8),
            text=[f"${p:+,.0f}" for p in dh_df["pnl"]],textposition="outside",
            textfont=dict(family="JetBrains Mono",size=10,color="#d4cfc0")))
        fig_dh.add_hline(y=-APEX_CONFIG["daily_loss_limit"],line=dict(color="#ff2d55",width=1,dash="dash"),annotation_text="Daily Limit")
        fig_dh.update_layout(height=240,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
            margin=dict(l=0,r=0,t=10,b=0),showlegend=False,
            xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"),
            font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
        st.plotly_chart(fig_dh,use_container_width=True,key="apex_daily_chart")

# ==============================================================
# TAB 1 - PULSE
# ==============================================================
with t1:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:8px;">PULSE - LIVE OPPORTUNITY GRID</div>', unsafe_allow_html=True)
    tqs_cols=st.columns(len(SEL))
    sorted_mk=sorted(SEL,key=lambda x:tqs_per_market[x],reverse=True)
    for i,(col,mk) in enumerate(zip(tqs_cols,sorted_mk)):
        tqs=tqs_per_market[mk]; sig=market_signals[mk]; cv=council_per_market[mk]
        tc="#1aff8a" if tqs>=70 else "#c9a84c" if tqs>=45 else "#ff2d55" if tqs<30 else "#5a5570"
        vc="#1aff8a" if cv["verdict"]=="LONG" else "#ff2d55" if cv["verdict"]=="SHORT" else "#5a5570"
        rank="1" if i==0 else "2" if i==1 else "3" if i==2 else str(i+1)
        with col:
            st.markdown(f"""
            <div class="tqs-cell" style="border-top:2px solid {tc};">
              <div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#3a3550;margin-bottom:2px;">RANK {rank}</div>
              <div style="font-family:Cinzel,serif;font-size:1rem;font-weight:700;color:#fff;margin-bottom:4px;">{mk}</div>
              <div class="tqs-score" style="color:{tc};">{tqs}</div>
              <div class="tqs-label">TRADE QUALITY</div>
              <div class="meter-track" style="margin-top:8px;height:4px;"><div class="meter-fill" style="width:{tqs}%;background:{tc};"></div></div>
              <div style="margin-top:6px;font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;">
                <div>{sig.get("signal","HOLD")} - {sig.get("conf",0)}%</div>
                <div style="color:{vc};margin-top:2px;font-weight:700;">{cv["verdict"]}</div>
                <div style="margin-top:3px;"><span class="proxy-tag">{MARKETS[mk]["apex_proxy"]}</span></div>
              </div>
            </div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    p1l,p1r=st.columns([3,2])
    with p1l:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#c9a84c;margin-bottom:10px;">COUNCIL VOTING</div>', unsafe_allow_html=True)
        for mk in SEL:
            cv=council_per_market[mk]; total=cv["long"]+cv["short"]+cv["hold"]
            lp=cv["long"]/total*100; sp=cv["short"]/total*100; hp=cv["hold"]/total*100
            vc="#1aff8a" if cv["verdict"]=="LONG" else "#ff2d55" if cv["verdict"]=="SHORT" else "#5a5570"
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div><span style="font-family:Cinzel,serif;font-weight:700;color:#fff;">{mk}</span>
                <span style="font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;margin-left:6px;">{MARKETS[mk]['label']}</span>
                <span class="proxy-tag" style="margin-left:6px;">{MARKETS[mk]["apex_proxy"]}</span></div>
                <div style="font-family:Cinzel,serif;font-size:11px;font-weight:700;color:{vc};">{cv["verdict"]} - {cv["strength"]:.0f}%</div>
              </div>
              <div class="council-bar">
                <div class="council-long" style="width:{lp}%;"></div>
                <div class="council-short" style="width:{sp}%;"></div>
                <div class="council-hold" style="width:{hp}%;"></div>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;font-family:JetBrains Mono,monospace;font-size:9px;margin-top:3px;">
                <div style="color:#1aff8a;">L {cv["long"]}</div>
                <div style="color:#ff2d55;">S {cv["short"]}</div>
                <div style="color:#5a5570;">H {cv["hold"]}</div>
              </div>
            </div>""", unsafe_allow_html=True)
    with p1r:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#c9a84c;margin-bottom:10px;">TOP SETUP</div>', unsafe_allow_html=True)
        best_mk=sorted_mk[0]; btqs=tqs_per_market[best_mk]; bsig=market_signals[best_mk]; bcv=council_per_market[best_mk]
        bvc="#1aff8a" if bcv["verdict"]=="LONG" else "#ff2d55" if bcv["verdict"]=="SHORT" else "#5a5570"
        bm=MARKETS[best_mk]
        reasons_html="".join(f'<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570;">- {r}</div>' for r in bsig.get("reasons",[])[:4])
        st.markdown(f"""
        <div class="panel" style="border-top:2px solid {bvc};">
          <div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#5a5570;margin-bottom:6px;">HIGHEST TQS</div>
          <div style="font-family:Cinzel,serif;font-size:2rem;font-weight:900;color:#fff;">{best_mk}</div>
          <div style="font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;">{bm['label']}</div>
          <div style="margin:5px 0;"><span class="proxy-tag">{bm['apex_proxy']}</span> <span style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:11px;color:#5a5570;">{bm['apex_note']}</span></div>
          <div style="font-family:JetBrains Mono,monospace;font-size:11px;line-height:1.8;margin-top:8px;">
            <div style="color:#5a5570;">Signal: <span style="color:#fff;">{bsig.get("signal","HOLD")} ({bsig.get("conf",0)}%)</span></div>
            <div style="color:#5a5570;">Price: <span style="color:#fff;">{fmt_price(best_mk,live_prices[best_mk])}</span></div>
            <div style="color:#ff2d55;">SL: ${bsig.get("stop",0):,.2f}</div>
            <div style="color:#1aff8a;">TP: ${bsig.get("target",0):,.2f}</div>
          </div>
          <div style="margin-top:10px;border-top:1px solid #12101e;padding-top:10px;">{reasons_html}</div>
        </div>""", unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.14em;color:#c9a84c;margin:22px 0 10px;">LIVE EQUITY RACE</div>', unsafe_allow_html=True)
    race=sorted([(tr["name"],tr["balance"],tr["balance"]-STARTING_BALANCE) for tr in TRADERS],key=lambda x:x[1],reverse=True)
    fig_race=go.Figure(go.Bar(x=[p for _,_,p in race],y=[n for n,_,_ in race],orientation="h",
        marker=dict(color=["#1aff8a" if p>0 else "#ff2d55" for _,_,p in race],opacity=0.8),
        text=[f"${p:+,.0f}" for _,_,p in race],textposition="outside",
        textfont=dict(family="JetBrains Mono",size=11,color="#d4cfc0")))
    fig_race.update_layout(height=220,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
        margin=dict(l=0,r=60,t=10,b=0),showlegend=False,
        xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"),
        font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
    st.plotly_chart(fig_race,use_container_width=True,key="eq_race")

# ==============================================================
# TAB 2 - INTELLIGENCE
# ==============================================================
with t2:
    ni1,ni2=st.columns([3,2])
    with ni1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">INTELLIGENCE BRIEF</div>', unsafe_allow_html=True)
        notes=st.session_state["notes"]
        if not notes:
            st.markdown('<div class="nigel-note note-info"><div class="note-head">AWAITING ANALYSIS</div><div class="note-body">Nigel is observing the markets. Notes appear on next data cycle.</div></div>', unsafe_allow_html=True)
        icons = {"watch":"WATCH","buy":"LONG BIAS","sell":"SHORT BIAS","info":"OBSERVE"}
        colors = {"watch":"#c9a84c","buy":"#1aff8a","sell":"#ff2d55","info":"#00c4ff"}
        for n in notes[:8]:
            cls=f"note-{n['type']}"; ic=icons.get(n['type'],"OBSERVE"); cl=colors.get(n['type'],"#c9a84c")
            mk_name=MARKETS.get(n['market'],{}).get('label',n['market'])
            st.markdown(f'<div class="nigel-note {cls}"><div class="note-head" style="color:{cl};">{ic} - {mk_name} <span style="color:#3a3550;font-weight:400;float:right;">{n["time"]}</span></div><div class="note-body">{n["text"]}</div></div>', unsafe_allow_html=True)
    with ni2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">MARKET OVERVIEW</div>', unsafe_allow_html=True)
        rows=[]
        for mk in SEL:
            sig=market_signals[mk]; div=sig.get("divergence",{})
            divs="Bull" if (div.get("bull_div") or div.get("macd_bull")) else "Bear" if (div.get("bear_div") or div.get("macd_bear")) else "--"
            rows.append({"Market":mk,"Signal":sig["signal"],"Conf":f"{sig['conf']}%",
                "TQS":tqs_per_market.get(mk,0),"Council":council_per_market[mk]["verdict"],
                "RSI":f"{sig['rsi']:.0f}","Mom":f"{sig['mom']:+.1f}%",
                "Regime":sig['regime'].get('regime','?'),"Div":divs,
                "Proxy":MARKETS[mk]["apex_proxy"]})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ==============================================================
# TAB 3 - TRADERS
# ==============================================================
with t3:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">THE SIX DESKS</div>', unsafe_allow_html=True)
    if apex_status["locked"]:
        st.markdown(f'<div class="shield-banner">APEX LOCK - {apex_status["lock_reason"]}</div>', unsafe_allow_html=True)
    sb_rows=[]
    for tr in TRADERS:
        pnl=tr["balance"]-STARTING_BALANCE
        wins=sum(1 for t in tr["trades"] if t.get("result")=="win"); tot=len(tr["trades"])
        wr=round(wins/tot*100) if tot else 0
        dd=round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1) if tr["peak"] else 0
        streak=(f"+{tr.get('win_streak',0)}" if tr.get('win_streak',0)>0
                else f"-{tr.get('loss_streak',0)}" if tr.get('loss_streak',0)>0 else "--")
        sb_rows.append({"Desk":tr["name"],"Fitness":tr.get("fitness",0),"Balance":tr["balance"],
            "PnL":pnl,"Win%":wr,"Trades":tot,"DD%":dd,"Streak":streak,
            "Best":tr.get("best_market") or "--","Status":"PAUSED" if tr.get("paused") else "ACTIVE"})
    sb_df=pd.DataFrame(sb_rows).sort_values("Fitness",ascending=False).reset_index(drop=True)
    sb_df.index+=1
    st.dataframe(sb_df.style
        .format({"Balance":"${:,.0f}","PnL":"${:+,.0f}","Win%":"{}%","DD%":"{}%","Fitness":"{:.1f}"})
        .map(lambda v:"color:#1aff8a;font-weight:600" if isinstance(v,(int,float)) and v>0
             else "color:#ff2d55;font-weight:600" if isinstance(v,(int,float)) and v<0 else "",
             subset=["PnL"]),use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    tr_tabs=st.tabs([f"{tr['name']}" for tr in TRADERS])
    for tab,tr in zip(tr_tabs,TRADERS):
        with tab:
            pnl=tr["balance"]-STARTING_BALANCE
            wins=sum(1 for t in tr["trades"] if t.get("result")=="win"); tot=len(tr["trades"])
            wr=round(wins/tot*100) if tot else 0
            pnl_c="#1aff8a" if pnl>=0 else "#ff2d55"
            fit=tr.get("fitness",0); fc="#1aff8a" if fit>=60 else "#c9a84c" if fit>=35 else "#ff2d55"
            paused_html='<div style="font-family:Cinzel,serif;font-size:10px;color:#ff9500;margin-top:10px;">PAUSED - APEX LOCK ACTIVE</div>' if tr.get("paused") else ""
            st.markdown(f"""
            <div class="panel panel-gold" style="margin-bottom:14px;">
              <div class="trader-header">
                <div><div class="trader-name">{tr['name']}</div><div class="trader-style">{tr['style']}</div></div>
                <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570;">{tr.get('philosophy','')}</div>
              </div>
              <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;">
                <div><div class="stat-val" style="color:#fff;">${tr['balance']:,.0f}</div><div class="stat-lbl">Balance</div></div>
                <div><div class="stat-val" style="color:{pnl_c};">${pnl:+,.0f}</div><div class="stat-lbl">P&amp;L</div></div>
                <div><div class="stat-val">{wr}%</div><div class="stat-lbl">Win Rate</div></div>
                <div><div class="stat-val">{tot}</div><div class="stat-lbl">Trades</div></div>
                <div><div class="stat-val" style="color:#ff2d55;">{round(max(0,(tr["peak"]-tr["balance"])/tr["peak"]*100),1)}%</div><div class="stat-lbl">Drawdown</div></div>
                <div><div class="stat-val" style="color:{fc};">{fit:.1f}</div><div class="stat-lbl">Fitness</div></div>
              </div>
              {paused_html}
            </div>""", unsafe_allow_html=True)
            pos=tr.get("open_pos")
            if pos and _is_valid_position(pos):
                mk=pos.get("market",""); sig=market_signals.get(mk,{}); cur=sig.get("price",pos.get("entry",0))
                is_long=pos.get("dir")=="long"; cls2="pos-long" if is_long else "pos-short"
                unr=(cur-pos["entry"])*pos["units"] if is_long else (pos["entry"]-cur)*pos["units"]
                uc="#1aff8a" if unr>=0 else "#ff2d55"
                trail=" TRAILED" if pos.get("trailed") else ""
                st.markdown(f'<div class="{cls2} pos-panel">{"LONG" if is_long else "SHORT"} - {MARKETS.get(mk,{}).get("label",mk)}{trail} - {pos.get("bars_in_trade",0)} bars<br>Entry ${pos["entry"]:,.2f} - Now ${cur:,.2f} - SL <span style="color:#ff2d55;">${pos["stop"]:,.2f}</span> - TP <span style="color:#1aff8a;">${pos["tp"]:,.2f}</span><br>Unrealized <span style="color:{uc};font-weight:700;">${unr:+,.2f}</span></div>', unsafe_allow_html=True)
            else:
                if pos: tr["open_pos"]=None; state_save()
                st.markdown('<div class="pos-flat pos-panel">No open position - scanning for entry</div>', unsafe_allow_html=True)
            recent=tr["trades"][-5:][::-1]
            if recent:
                st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.1em;color:#5a5570;margin:10px 0 4px;">RECENT TRADES</div>', unsafe_allow_html=True)
                for t in recent:
                    is_w=t.get("result")=="win"; tc2="#1aff8a" if is_w else "#ff2d55"
                    pc="trade-pip-w" if is_w else "trade-pip-l"
                    proxy=MARKETS.get(t.get("market",""),{}).get("apex_proxy","--")
                    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #12101e;"><div><span class="{pc}">*</span><span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#d4cfc0;margin-left:8px;">{t.get("market","")} {"L" if t.get("dir")=="long" else "S"}</span><span style="font-family:JetBrains Mono,monospace;font-size:9px;color:#5a5570;margin-left:6px;">{t.get("reason","")} [{proxy}]</span></div><span style="font-family:JetBrains Mono,monospace;font-size:11px;color:{tc2};font-weight:600;">${t.get("pnl",0):+,.2f}</span></div>', unsafe_allow_html=True)
    colors_tr={"CONSERVATEUR":"#00c4ff","MOMENTUM":"#1aff8a","CONTRARIAN":"#ff2d55","SCALPER":"#c9a84c","MACRO":"#f7931a","ALGOBOT":"#a855f7"}
    fig_eq=go.Figure()
    for tr in TRADERS:
        if len(tr.get("history",[]))>1:
            fig_eq.add_trace(go.Scatter(y=tr["history"],mode="lines",name=tr["name"],
                line=dict(color=colors_tr.get(tr["name"],"#c9a84c"),width=2)))
    fig_eq.add_hline(y=STARTING_BALANCE,line=dict(color="#3a3550",width=1,dash="dot"))
    fig_eq.update_layout(height=280,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
        margin=dict(l=0,r=0,t=10,b=0),xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"),
        legend=dict(orientation="h",y=1.05,font=dict(family="JetBrains Mono",size=10)),
        font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
    st.plotly_chart(fig_eq,use_container_width=True,key="eq_curves")

# ==============================================================
# TAB 4 - SIGNAL FEED
# ==============================================================
with t4:
    sf1,sf2=st.columns([2,1])
    with sf1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">LIVE SIGNAL FEED</div>', unsafe_allow_html=True)
        feed=st.session_state["signal_feed"]
        if not feed:
            st.markdown('<div class="nigel-note note-info"><div class="note-body">Awaiting signals above 55% confidence...</div></div>', unsafe_allow_html=True)
        for item in feed[:30]:
            s=item["signal"]; is_b="BUY" in s or s=="OVERSOLD"
            dc="#1aff8a" if is_b else "#ff2d55"; bc="badge-long" if is_b else "badge-short"
            sfmt2=f'${item["stop"]:,.2f}' if item.get("stop") else "--"
            tfmt2=f'${item["target"]:,.2f}' if item.get("target") else "--"
            tqs_v=item.get("tqs",0); tqs_c="#1aff8a" if tqs_v>=70 else "#c9a84c" if tqs_v>=45 else "#5a5570"
            proxy=item.get("apex_proxy","--")
            div_parts=[]
            if item.get("div_bull"): div_parts.append('<span style="color:#1aff8a;font-size:9px;">RSI BULL</span>')
            if item.get("div_bear"): div_parts.append('<span style="color:#ff2d55;font-size:9px;">RSI BEAR</span>')
            if item.get("macd_bull"): div_parts.append('<span style="color:#1aff8a;font-size:9px;">MACD BULL</span>')
            if item.get("macd_bear"): div_parts.append('<span style="color:#ff2d55;font-size:9px;">MACD BEAR</span>')
            div_str=" ".join(div_parts)
            reasons_str=" - ".join(item.get("reasons",[])[:2])
            st.markdown(f"""
            <div style="display:flex;gap:12px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #12101e;">
              <div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#3a3550;min-width:58px;padding-top:2px;">{item['time']}</div>
              <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;flex-wrap:wrap;">
                  <span style="font-family:Cinzel,serif;font-weight:700;color:#fff;">{item['mk']}</span>
                  <span class="badge {bc}">{s}</span>
                  <span style="font-family:JetBrains Mono,monospace;font-size:10px;color:{dc};">{item['conf']}%</span>
                  <span class="proxy-tag">{proxy}</span>
                  <span style="font-family:JetBrains Mono,monospace;font-size:9px;color:{tqs_c};">TQS {tqs_v}</span>
                  {div_str}
                </div>
                <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#3a3550;">SL <span style="color:#ff2d55;">{sfmt2}</span> &nbsp; TP <span style="color:#1aff8a;">{tfmt2}</span></div>
                <div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:12px;color:#5a5570;">{reasons_str}</div>
              </div>
            </div>""", unsafe_allow_html=True)
    with sf2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">STATISTICS</div>', unsafe_allow_html=True)
        if feed:
            tot=len(feed); longs=sum(1 for x in feed if "BUY" in x["signal"] or x["signal"]=="OVERSOLD")
            avg_conf=np.mean([x["conf"] for x in feed]); avg_tqs=np.mean([x.get("tqs",0) for x in feed])
            st.markdown(f'<div class="panel panel-gold" style="margin-bottom:8px;"><div class="stat-val" style="color:#00c4ff;">{tot}</div><div class="stat-lbl">Total Signals</div></div>', unsafe_allow_html=True)
            c1a,c1b=st.columns(2)
            with c1a: st.markdown(f'<div class="panel panel-em"><div class="stat-val" style="color:#1aff8a;">{longs}</div><div class="stat-lbl">Long</div></div>', unsafe_allow_html=True)
            with c1b: st.markdown(f'<div class="panel panel-cr"><div class="stat-val" style="color:#ff2d55;">{tot-longs}</div><div class="stat-lbl">Short</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="panel" style="margin-top:8px;"><div class="stat-val" style="color:#c9a84c;">{avg_conf:.0f}%</div><div class="stat-lbl">Avg Conf</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="panel" style="margin-top:8px;"><div class="stat-val" style="color:#c9a84c;">{avg_tqs:.0f}</div><div class="stat-lbl">Avg TQS</div></div>', unsafe_allow_html=True)

# ==============================================================
# TAB 5 - LIVE CHARTS
# ==============================================================
with t5:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">LIVE CHARTS</div>', unsafe_allow_html=True)
    mk=st.selectbox("Instrument",SEL,key="charts_mk")
    sig=market_signals[mk]; closes=raw_data[mk]["closes"]
    if len(closes)>=30:
        _,bb_u,bb_l,_=bb_bands(closes)
        e8=ema_series(closes,8); e21=ema_series(closes,21)
        e50=ema_series(closes,50) if len(closes)>=50 else ema_series(closes,21)
        rsi_arr=rsi_full(closes,14)
        macd_vals=[]
        for i in range(26,len(closes)+1):
            sl=closes[:i]; macd_vals.append(ema_series(sl,12)[-1]-ema_series(sl,26)[-1])
        macd_sv=ema_series(macd_vals,9) if len(macd_vals)>=9 else macd_vals
        x_vals=list(range(len(closes)))
        fig=make_subplots(rows=4,cols=1,shared_xaxes=True,vertical_spacing=0.04,row_heights=[0.5,0.18,0.16,0.16])
        fig.add_trace(go.Scatter(x=x_vals,y=closes,mode="lines",name="Price",line=dict(color="#fff",width=2)),row=1,col=1)
        fig.add_trace(go.Scatter(x=x_vals,y=e8,mode="lines",name="EMA8",line=dict(color="#c9a84c",width=1,dash="dot")),row=1,col=1)
        fig.add_trace(go.Scatter(x=x_vals,y=e21,mode="lines",name="EMA21",line=dict(color="#1aff8a",width=1,dash="dot")),row=1,col=1)
        fig.add_trace(go.Scatter(x=x_vals,y=e50,mode="lines",name="EMA50",line=dict(color="#ff2d55",width=1,dash="dot")),row=1,col=1)
        bx=list(range(len(bb_u)))
        fig.add_trace(go.Scatter(x=bx,y=bb_u,mode="lines",name="BB Upper",line=dict(color="rgba(201,168,76,0.3)",width=1)),row=1,col=1)
        fig.add_trace(go.Scatter(x=bx,y=bb_l,mode="lines",name="BB Lower",fill='tonexty',fillcolor="rgba(201,168,76,0.04)",line=dict(color="rgba(201,168,76,0.3)",width=1)),row=1,col=1)
        if sig.get("stop"): fig.add_hline(y=sig["stop"],line=dict(color="#ff2d55",width=1,dash="dash"),annotation_text="SL",row=1,col=1)
        if sig.get("target"): fig.add_hline(y=sig["target"],line=dict(color="#1aff8a",width=1,dash="dash"),annotation_text="TP",row=1,col=1)
        if macd_vals:
            mx=list(range(26,26+len(macd_vals)))
            mc_c=["#1aff8a" if v>=0 else "#ff2d55" for v in macd_vals]
            fig.add_trace(go.Bar(x=mx,y=macd_vals,name="MACD",marker=dict(color=mc_c,opacity=0.4)),row=2,col=1)
            sx=list(range(26,26+len(macd_sv)))
            fig.add_trace(go.Scatter(x=sx,y=macd_sv,mode="lines",name="Signal",line=dict(color="#00c4ff",width=1)),row=2,col=1)
        rsi_clean=[v if v is not None else 50 for v in rsi_arr]
        fig.add_trace(go.Scatter(x=x_vals,y=rsi_clean,mode="lines",name="RSI",line=dict(color="#a855f7",width=2)),row=3,col=1)
        fig.add_hline(y=70,line=dict(color="#ff2d55",width=1,dash="dot"),row=3,col=1)
        fig.add_hline(y=30,line=dict(color="#1aff8a",width=1,dash="dot"),row=3,col=1)
        bar_changes=[abs((closes[i]-closes[i-1])/closes[i-1]*100) if i>0 else 0 for i in range(len(closes))]
        fig.add_trace(go.Bar(x=x_vals,y=bar_changes,name="Delta%",marker=dict(color="#c9a84c",opacity=0.4)),row=4,col=1)
        fig.update_layout(height=680,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
            margin=dict(l=0,r=0,t=10,b=0),showlegend=True,
            legend=dict(orientation="h",y=1.05,font=dict(family="JetBrains Mono",size=9)),
            font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
        for i in range(1,5): fig.update_xaxes(gridcolor="#12101e",row=i,col=1); fig.update_yaxes(gridcolor="#12101e",row=i,col=1)
        st.plotly_chart(fig,use_container_width=True,key=f"chart_{mk}")
    else: st.warning(f"Not enough data for {mk}")

# ==============================================================
# TAB 6 - RULES ENGINE
# ==============================================================
with t6:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">RULES ENGINE - APEX EDITION</div>', unsafe_allow_html=True)
    qp1,qp2,qp3,qp4,qp5=st.columns(5)
    with qp1:
        if st.button("Trend-Only"):
            st.session_state["rule_set"].append({"type":"trend_only","value":1,"active":True,"name":"Trend Only","desc":"Only trade with EMA stack alignment"})
            state_save(); st.rerun()
    with qp2:
        if st.button("Skip Lunch"):
            st.session_state["rule_set"].append({"type":"no_trade_hours","h_from":12,"h_to":13,"value":0,"active":True,"name":"Lunch Lockout","desc":"No trades 12:00-13:00 ET"})
            state_save(); st.rerun()
    with qp3:
        if st.button("Vol Min 1.2x"):
            st.session_state["rule_set"].append({"type":"vol_min","value":1.2,"active":True,"name":"Volume Floor","desc":"Require 1.2x avg volume"})
            state_save(); st.rerun()
    with qp4:
        if st.button("Cap ATR 6%"):
            st.session_state["rule_set"].append({"type":"atr_max","value":6.0,"active":True,"name":"ATR Cap","desc":"Block when ATR% > 6%"})
            state_save(); st.rerun()
    with qp5:
        if st.button("Apex $200 Guard"):
            st.session_state["rule_set"].append({"type":"apex_daily_guard","value":200,"active":True,"name":"Apex Daily Guard","desc":"Block when less than $200 daily headroom"})
            state_save(); st.rerun()
    st.divider()
    rl1,rl2=st.columns([2,1])
    with rl1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin-bottom:8px;">ACTIVE RULES</div>', unsafe_allow_html=True)
        if not st.session_state["rule_set"]:
            st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;">No rules. Desks trade on raw signal alone.</div>', unsafe_allow_html=True)
        for i,rule in enumerate(st.session_state["rule_set"]):
            active=rule.get("active",True)
            rc2="rule-on" if active else "rule-off"
            bc2="badge-long" if active else "badge-hold"
            al2="ACTIVE" if active else "OFF"
            cols=st.columns([5,1,1])
            with cols[0]:
                st.markdown(f'<div class="rule-row {rc2}"><div><div class="rule-name">{rule.get("name",rule.get("type",""))}</div><div class="rule-desc">{rule.get("desc","")}</div></div><span class="badge {bc2}">{al2}</span></div>', unsafe_allow_html=True)
            with cols[1]:
                if st.button("Toggle",key=f"tog_{i}"): st.session_state["rule_set"][i]["active"]=not active; state_save(); st.rerun()
            with cols[2]:
                if st.button("X",key=f"del_{i}"): st.session_state["rule_set"].pop(i); state_save(); st.rerun()
    with rl2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:9px;letter-spacing:.12em;color:#5a5570;margin-bottom:8px;">RULE IMPACT</div>', unsafe_allow_html=True)
        for mk,sig in market_signals.items():
            blocked=sig.get("rule_block",False); ic="#ff2d55" if blocked else "#1aff8a"; lbl="BLOCKED" if blocked else "OPEN"
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 12px;background:#0d0c16;border:1px solid #12101e;border-left:2px solid {ic};border-radius:1px;margin-bottom:4px;font-family:JetBrains Mono,monospace;font-size:11px;"><span style="color:#fff;">{mk}</span><span style="color:{ic};font-weight:600;">{lbl}</span></div>', unsafe_allow_html=True)

# ==============================================================
# TAB 7 - BACKTEST
# ==============================================================
with t7:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:8px;">BACKTEST - APEX RULES APPLIED</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570;margin-bottom:16px;">Respects Apex daily loss limit - days where $1K is hit get no further trades.</div>', unsafe_allow_html=True)
    bc=st.columns(5)
    with bc[0]: bt_mk=st.selectbox("Instrument",SEL,key="bt_mk")
    with bc[1]: bt_rr=st.slider("RR",1.0,5.0,2.0,0.25,key="bt_rr")
    with bc[2]: bt_risk=st.slider("Risk %",0.25,2.0,1.0,0.25,key="bt_risk")/100
    with bc[3]: bt_rules=st.checkbox("Apply rules",value=True,key="bt_rules")
    with bc[4]: run_bt=st.button("RUN",type="primary",key="bt_run")
    if run_bt:
        with st.spinner("Running backtest..."):
            result=run_backtest_nigel(raw_data[bt_mk]["closes"],bt_mk,bt_risk,bt_rr,
                                      st.session_state["rule_set"] if bt_rules else [])
            st.session_state["bt_cache"][f"{bt_mk}_{bt_rr}_{bt_risk}"]=result; state_save()
    if st.session_state["bt_cache"]:
        result=list(st.session_state["bt_cache"].values())[-1]
        if "error" in result: st.error(result["error"])
        else:
            r1=st.columns(5); rc2="#1aff8a" if result["return_pct"]>0 else "#ff2d55"
            with r1[0]: st.markdown(f'<div class="panel panel-gold"><div class="stat-val" style="color:{rc2};">${result["total_pnl"]:+,.0f}</div><div class="stat-lbl">Total P&L</div></div>', unsafe_allow_html=True)
            with r1[1]: st.markdown(f'<div class="panel"><div class="stat-val" style="color:{rc2};">{result["return_pct"]:+.1f}%</div><div class="stat-lbl">Return</div></div>', unsafe_allow_html=True)
            with r1[2]: st.markdown(f'<div class="panel"><div class="stat-val">{result["win_rate"]:.0f}%</div><div class="stat-lbl">Win Rate</div></div>', unsafe_allow_html=True)
            with r1[3]: st.markdown(f'<div class="panel"><div class="stat-val">{result["pf"]:.2f}</div><div class="stat-lbl">Profit Factor</div></div>', unsafe_allow_html=True)
            with r1[4]: st.markdown(f'<div class="panel"><div class="stat-val" style="color:#ff2d55;">{result["max_dd"]:.1f}%</div><div class="stat-lbl">Max DD</div></div>', unsafe_allow_html=True)
            fig_bt=go.Figure()
            fig_bt.add_trace(go.Scatter(y=result["equity"],mode="lines",line=dict(color="#c9a84c",width=2),fill='tozeroy',fillcolor="rgba(201,168,76,0.04)"))
            fig_bt.add_hline(y=result["start"],line=dict(color="#3a3550",width=1,dash="dot"))
            fig_bt.update_layout(height=260,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
                margin=dict(l=0,r=0,t=10,b=0),showlegend=False,
                xaxis=dict(gridcolor="#12101e"),yaxis=dict(gridcolor="#12101e"),
                font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
            st.plotly_chart(fig_bt,use_container_width=True,key="bt_chart")
            with st.expander(f"Trade Log ({result['total_trades']} trades)"):
                if isinstance(result["trades"],pd.DataFrame): st.dataframe(result["trades"],use_container_width=True,hide_index=True)

# ==============================================================
# TAB 8 - AI ANALYST
# ==============================================================
with t8:
    st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:8px;">AI ANALYST - APEX AWARE</div>', unsafe_allow_html=True)
    if not CLKEY:
        st.warning("Add a Claude API key in the sidebar to enable the AI Analyst.")
    else:
        ac1,ac2,ac3,ac4=st.columns(4)
        question=None
        with ac1:
            if st.button("Full Brief"): question="Give me a complete brief on every instrument. Include which Apex futures contract to use and risk sizing for a $50K account with $1K daily limit."
        with ac2:
            if st.button("Best Trade"): question="What is the single best trade idea right now? Give exact entry, stop, target, Apex contract, and how many contracts at 1% risk on $50K."
        with ac3:
            if st.button("Risk Check"): question="Audit my Apex account risk. Check trailing drawdown, daily P&L, and whether I should still be trading today."
        with ac4:
            if st.button("Divergence"): question="Walk through every active divergence. Which is most actionable for an Apex futures trader?"
        custom=st.text_area("Custom question:",key="ai_q",height=80)
        if st.button("Ask Nigel",type="primary"): question=custom or question
        if question:
            with st.spinner("Thinking..."):
                ctx=build_ai_context(market_signals,live_prices,diag,apex_status)
                resp,err=call_claude(f"Context:\n{ctx}\n\nQuestion: {question}",AI_ANALYST_SYSTEM,CLKEY,1200)
                if resp:
                    st.session_state["ai_feed"].insert(0,{"q":question,"a":resp,"time":datetime.now().strftime("%H:%M:%S")})
                    st.session_state["ai_feed"]=st.session_state["ai_feed"][:10]; state_save()
                if err: st.error(err)
        for entry in st.session_state["ai_feed"][:5]:
            st.markdown(f'<div class="ai-response" style="margin-bottom:12px;"><div class="ai-header">NIGEL - {entry["time"]}</div><div style="font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;font-size:13px;margin-bottom:10px;">Q: {entry["q"]}</div><div>{entry["a"].replace(chr(10),"<br>")}</div></div>', unsafe_allow_html=True)

# ==============================================================
# TAB 9 - EDGE TOOLS
# ==============================================================
with t9:
    et1,et2,et3=st.tabs(["RISK OF RUIN","CORRELATIONS","REGIME & VOL"])
    with et1:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">RISK OF RUIN - KELLY ENGINE - APEX CALIBRATED</div>', unsafe_allow_html=True)
        rc1,rc2=st.columns(2)
        with rc1:
            wr_=st.slider("Win Rate %",30,80,55,1,key="ror_wr")
            rr_=st.slider("Reward:Risk",1.0,5.0,2.0,0.25,key="ror_rr")
            risk_=st.slider("Risk per trade %",0.25,2.0,1.0,0.25,key="ror_risk")/100
            kdata=risk_of_ruin(wr_,rr_,risk_)
            ec="#1aff8a" if kdata["edge"]>0 else "#ff2d55"
            risk_dollar=APEX_CONFIG["account_size"]*risk_
            max_daily_trades=int(APEX_CONFIG["daily_loss_limit"]/max(risk_dollar,1))
            st.markdown(f"""
            <div class="kelly-panel">
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div><div class="stat-val" style="color:{ec};">{kdata['edge']:+.2f}%</div><div class="stat-lbl">Edge/Trade</div></div>
                <div><div class="stat-val" style="color:#c9a84c;">{kdata['half_kelly']:.2f}%</div><div class="stat-lbl">Half-Kelly</div></div>
                <div><div class="stat-val" style="color:#ff2d55;">{kdata['ror']:.1f}%</div><div class="stat-lbl">Risk of Ruin</div></div>
                <div><div class="stat-val">${risk_dollar:,.0f}</div><div class="stat-lbl">$ Per Trade</div></div>
              </div>
              <hr>
              <div style="font-family:JetBrains Mono,monospace;font-size:10px;color:#5a5570;line-height:1.8;">
                <div>Max losing trades before Apex daily lock: <span style="color:{"#ff2d55" if max_daily_trades<=2 else "#c9a84c"};">{max_daily_trades}</span></div>
                <div>{"Over Half-Kelly - high variance risk" if kdata["vs_half_kelly"]=="OVER" else "Under Half-Kelly - disciplined sizing"}</div>
              </div>
            </div>""", unsafe_allow_html=True)
        with rc2:
            wrs=list(range(35,76,5)); rrs=[1.0,1.5,2.0,2.5,3.0,4.0]
            heat=[[risk_of_ruin(wr_h,rr_h,risk_)["ror"] for rr_h in rrs] for wr_h in wrs]
            fig_h=go.Figure(go.Heatmap(z=heat,x=[f"{r}:1" for r in rrs],y=[f"{w}%" for w in wrs],
                colorscale=[[0,"#1aff8a"],[0.4,"#c9a84c"],[1,"#ff2d55"]],
                hovertemplate="WR %{y} - RR %{x} - RoR %{z:.1f}%<extra></extra>"))
            fig_h.update_layout(height=300,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
                margin=dict(l=0,r=0,t=10,b=0),font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
            st.plotly_chart(fig_h,use_container_width=True,key="ror_heat")
    with et2:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">CROSS-INSTRUMENT CORRELATIONS</div>', unsafe_allow_html=True)
        if len(SEL)>=2:
            min_len=min(min(len(raw_data[mk]["closes"]) for mk in SEL),30)
            ret_df=pd.DataFrame({mk:[math.log(raw_data[mk]["closes"][-min_len:][i]/raw_data[mk]["closes"][-min_len:][i-1]) for i in range(1,min_len)] for mk in SEL})
            corr=ret_df.corr().round(2)
            fig_c=go.Figure(go.Heatmap(z=corr.values,x=corr.columns,y=corr.index,
                colorscale=[[0,"#ff2d55"],[0.5,"#0d0c16"],[1,"#1aff8a"]],zmid=0,
                text=corr.values,texttemplate="%{text:.2f}",textfont=dict(family="JetBrains Mono",size=12,color="#fff")))
            fig_c.update_layout(height=360,template="plotly_dark",paper_bgcolor="#05040a",plot_bgcolor="#09080f",
                margin=dict(l=0,r=0,t=10,b=0),font=dict(family="JetBrains Mono",size=10,color="#5a5570"))
            st.plotly_chart(fig_c,use_container_width=True,key="corr_heat")
            st.markdown('<div style="font-family:Cormorant Garamond,serif;font-style:italic;font-size:13px;color:#5a5570;margin-top:8px;">SOL/AVAX and TQQQ/SOXL are SMT pairs - divergence between them creates high-conviction signals.</div>', unsafe_allow_html=True)
        else: st.info("Select at least 2 instruments.")
    with et3:
        st.markdown('<div style="font-family:Cinzel,serif;font-size:10px;letter-spacing:.18em;color:#c9a84c;margin-bottom:16px;">REGIME AND VOLATILITY</div>', unsafe_allow_html=True)
        for mk in SEL:
            sig=market_signals[mk]; reg=sig.get("regime",{}); vr=sig.get("vol_regime",{})
            rn=reg.get("regime","?"); rc3="#1aff8a" if rn=="TRENDING" else "#c9a84c" if rn=="RANGING" else "#ff2d55"
            fc2=vr.get("forecast","?"); fcc="#1aff8a" if fc2=="CONTRACTING" else "#c9a84c" if fc2=="STABLE" else "#ff2d55"
            st.markdown(f"""
            <div class="panel" style="margin-bottom:8px;border-left:2px solid {rc3};">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div><span style="font-family:Cinzel,serif;font-weight:700;color:#fff;">{mk}</span>
                <span style="font-family:Cormorant Garamond,serif;font-style:italic;color:#5a5570;margin-left:6px;">{MARKETS[mk]['label']}</span>
                <span class="proxy-tag" style="margin-left:6px;">{MARKETS[mk]['apex_proxy']}</span></div>
                <span class="badge" style="background:{rc3}22;color:{rc3};border:1px solid {rc3}55;">{rn}</span>
              </div>
              <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px;">
                <div><div style="font-family:JetBrains Mono,monospace;color:#fff;">{reg.get('adx_lite',0)}</div><div class="stat-lbl">ADX-lite</div></div>
                <div><div style="font-family:JetBrains Mono,monospace;color:#fff;">{reg.get('bb_width_pct',0):.1f}%</div><div class="stat-lbl">BB Width</div></div>
                <div><div style="font-family:JetBrains Mono,monospace;color:#fff;">{vr.get('rv',0):.1f}%</div><div class="stat-lbl">Realised Vol</div></div>
                <div><div style="font-family:JetBrains Mono,monospace;color:{fcc};">{fc2}</div><div class="stat-lbl">Forecast</div></div>
              </div>
            </div>""", unsafe_allow_html=True)

# ==============================================================
# ALWAYS-ON BAR + AUTO-REFRESH
# ==============================================================
state_kb=PERSIST_PATH.stat().st_size/1024 if PERSIST_PATH.exists() else 0
secs_til=max(0,int(st.session_state["refresh_interval"]-(time.time()-st.session_state["last_refresh"])))
if apex_status["locked"]: apex_bar_color="#ff2d55"; apex_bar_text=f"LOCKED - {apex_status['lock_reason'][:50]}"
elif apex_status["warnings"]: apex_bar_color="#ff9500"; apex_bar_text=f"Daily left ${APEX_CONFIG['daily_loss_limit']+apex_status['daily_pnl']:,.0f}"
else: apex_bar_color="#1aff8a"; apex_bar_text=f"APEX CLEAR - daily ${APEX_CONFIG['daily_loss_limit']+apex_status['daily_pnl']:,.0f} left"
sessions_str=" - ".join([s for s,_ in sessions_now])
st.markdown(f"""
<div class="always-on-bar">
  <div><span class="live-dot"></span>NIGEL v5.3 APEX - {sessions_str}</div>
  <div style="color:{apex_bar_color};"><span class="apex-dot" style="background:{apex_bar_color};"></span>{apex_bar_text}</div>
  <div>State {state_kb:.1f} KB - Refresh {secs_til}s</div>
</div>
<div style="height:44px;"></div>
""", unsafe_allow_html=True)

if st.session_state["always_on"]:
    remaining=st.session_state["refresh_interval"]-(time.time()-st.session_state["last_refresh"])
    if remaining<=0: st.cache_data.clear(); state_save(); time.sleep(1); st.rerun()
    else: time.sleep(min(remaining,5)); st.rerun()
