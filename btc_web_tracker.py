import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import json

st.set_page_config(page_title="Multi-Market Trader", layout="wide", page_icon="📈")

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
.trader-card {
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 8px;
    border: 1px solid rgba(0,0,0,0.1);
}
.note-card {
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size: 14px;
    line-height: 1.6;
}
.note-watch { background: #fff8e1; border-left: 4px solid #f0a500; color: #4a3500; }
.note-buy   { background: #f0faf2; border-left: 4px solid #3a9d4e; color: #1a4024; }
.note-sell  { background: #fdf2f2; border-left: 4px solid #c0392b; color: #4a1010; }
.note-info  { background: #f0f4ff; border-left: 4px solid #4a6fa5; color: #1a2a4a; }
.metric-row { display: flex; gap: 12px; margin-bottom: 10px; }
.big-price { font-size: 28px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# API KEY GATE
# ─────────────────────────────────────────────
def get_keys():
    poly  = st.secrets.get("POLYGON_KEY",   "") if hasattr(st, "secrets") else ""
    anth  = st.secrets.get("ANTHROPIC_KEY", "") if hasattr(st, "secrets") else ""
    return (
        st.session_state.get("POLYGON_KEY",   poly),
        st.session_state.get("ANTHROPIC_KEY", anth),
    )

POLYGON_KEY, ANTHROPIC_KEY = get_keys()

if not POLYGON_KEY:
    st.title("📈 Multi-Market Trader — Setup")
    st.info("Enter your API keys to get started. They're only stored for this session unless you add them to `.streamlit/secrets.toml`.")
    with st.form("key_form"):
        pk = st.text_input("Polygon.io API Key", type="password", help="Free key at polygon.io")
        ak = st.text_input("Anthropic API Key (for plain-English notes)", type="password")
        if st.form_submit_button("Start App"):
            if not pk:
                st.error("Polygon.io key is required.")
            else:
                st.session_state["POLYGON_KEY"]   = pk
                st.session_state["ANTHROPIC_KEY"] = ak
                st.rerun()
    st.markdown("""
---
### How to set up permanent keys (recommended)
Create a file called `.streamlit/secrets.toml` in your project folder:
```toml
POLYGON_KEY   = "your_polygon_key_here"
ANTHROPIC_KEY = "your_anthropic_key_here"
```
Then push to GitHub — Streamlit Cloud will use these automatically.
""")
    st.stop()

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
def init_trader(name, emoji, style, risk_pct, rr, min_conf, wait_strong):
    return {
        "name": name, "emoji": emoji, "style": style,
        "risk_pct": risk_pct, "rr": rr, "min_conf": min_conf,
        "wait_strong": wait_strong,
        "balance": 25000.0, "peak": 25000.0,
        "trades": [], "open_pos": None, "history": [25000.0],
    }

if "traders" not in st.session_state:
    st.session_state["traders"] = [
        init_trader("Safe Sam",    "🔵", "Low risk — only trades strong signals",         0.005, 2.0, 70, True),
        init_trader("Swing Steve", "🟢", "Medium risk — rides the bigger moves",           0.015, 2.5, 55, False),
        init_trader("Risky Rick",  "🔴", "High risk — jumps in on almost every signal",   0.030, 1.5, 40, False),
    ]

if "notes" not in st.session_state:
    st.session_state["notes"] = []

if "signal_log" not in st.session_state:
    st.session_state["signal_log"] = []

if "last_ai_call" not in st.session_state:
    st.session_state["last_ai_call"] = 0.0

TRADERS = st.session_state["traders"]

# ─────────────────────────────────────────────
# SESSIONS
# ─────────────────────────────────────────────
SESSION_TIPS = {
    "Tokyo":    "BTC is the main one to watch. Gold and stocks are pretty quiet right now.",
    "London":   "Gold can make big moves this session. Keep an eye on BTC too.",
    "New York": "Best time for everything — stocks, gold, and BTC all moving.",
    "Overlap":  "Peak time! London and NY both open. Strongest signals happen right now.",
    "Off-hours":"Things are slow. Better to watch than trade.",
}

def get_session():
    h = datetime.now(ZoneInfo("UTC"))
    hf = h.hour + h.minute / 60
    sessions = []
    if 0  <= hf < 9:  sessions.append(("Tokyo",    "#7C3AED"))
    if 8  <= hf < 17: sessions.append(("London",   "#2563EB"))
    if 13 <= hf < 22: sessions.append(("New York", "#059669"))
    if 13 <= hf < 17: sessions.append(("Overlap",  "#D97706"))
    if not sessions:  sessions.append(("Off-hours","#888888"))
    return sessions

def session_banner():
    sessions = get_session()
    utc = datetime.now(ZoneInfo("UTC"))
    ny  = utc.astimezone(ZoneInfo("America/New_York"))
    lon = utc.astimezone(ZoneInfo("Europe/London"))

    badges = " ".join(
        f'<span style="display:inline-block;background:{c};color:#fff;border-radius:6px;'
        f'padding:3px 12px;font-size:13px;font-weight:600;margin-right:6px">{n}</span>'
        for n, c in sessions
    )
    tip = SESSION_TIPS.get(sessions[0][0], "")
    st.markdown(
        f'<div style="background:#1a1a2e;border-radius:10px;padding:14px 18px;margin-bottom:16px">'
        f'<div style="margin-bottom:8px">{badges}</div>'
        f'<div style="font-size:13px;color:#ccc;margin-bottom:6px">{tip}</div>'
        f'<div style="font-size:12px;color:#888">'
        f'UTC {utc.strftime("%H:%M")} | ET {ny.strftime("%H:%M")} | LDN {lon.strftime("%H:%M")}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    return [n for n, _ in sessions]

# ─────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_btc():
    try:
        d = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            "?vs_currency=usd&days=30&interval=daily", timeout=15
        ).json()
        closes = [p[1] for p in d["prices"]]
        price  = closes[-1]
        chg    = (price - closes[-2]) / closes[-2] * 100
        return {"closes": closes, "price": price, "chg": chg, "label": "BTC / USD", "crypto": True}
    except:
        p = 84000
        return {"closes": [p]*30, "price": p, "chg": 0.5, "label": "BTC / USD", "crypto": True}

@st.cache_data(ttl=300)
def fetch_polygon(ticker, key, days=45):
    try:
        from datetime import timedelta
        to   = datetime.today().strftime("%Y-%m-%d")
        frm  = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        url  = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
                f"{frm}/{to}?adjusted=true&sort=asc&limit={days}&apiKey={key}")
        d    = requests.get(url, timeout=15).json()
        if "results" not in d or len(d["results"]) < 5:
            raise ValueError("no data")
        closes = [r["c"] for r in d["results"]]
        price  = closes[-1]
        chg    = (price - closes[-2]) / closes[-2] * 100
        return {"closes": closes, "price": price, "chg": chg}
    except:
        base = {"QQQ": 490, "GLD": 320}[ticker]
        p = base
        return {"closes": [p]*30, "price": p, "chg": 0.3, "label": ticker, "crypto": False}

# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def ema(arr, n):
    if len(arr) < n:
        return arr[-1]
    k, e = 2/(n+1), sum(arr[:n])/n
    for v in arr[n:]:
        e = v*k + e*(1-k)
    return e

def rsi(closes, n=14):
    if len(closes) < n+1:
        return 50.0
    gains = losses = 0.0
    for i in range(len(closes)-n, len(closes)):
        d = closes[i] - closes[i-1]
        if d > 0: gains += d
        else:     losses -= d
    rs = (gains/n) / max(losses/n, 1e-10)
    return 100 - 100/(1+rs)

def ma(closes, n):
    return sum(closes[-n:]) / n if len(closes) >= n else closes[-1]

def compute_signal(closes):
    if len(closes) < 22:
        return {"signal": "HOLD", "conf": 50, "rsi": 50, "ma_bull": False, "macd_bull": False, "price": closes[-1]}
    r    = rsi(closes)
    ma8  = ma(closes, 8)
    ma21 = ma(closes, 21)
    macd = ema(closes, 12) - ema(closes, 26)
    ma_bull   = ma8 > ma21
    macd_bull = macd > 0

    if r < 30:
        sig, conf = "OVERSOLD",    72
    elif r > 72:
        sig, conf = "OVERBOUGHT",  70
    elif ma_bull and macd_bull and 40 < r < 60:
        sig, conf = "STRONG BUY",  80
    elif ma_bull and macd_bull and r < 68:
        sig, conf = "BUY",         65
    elif not ma_bull and not macd_bull and r > 55:
        sig, conf = "STRONG SELL", 77
    elif not ma_bull and not macd_bull and r > 35:
        sig, conf = "SELL",        62
    else:
        sig, conf = "HOLD",        50

    return {"signal": sig, "conf": conf, "rsi": r, "ma_bull": ma_bull,
            "macd_bull": macd_bull, "price": closes[-1]}

# ─────────────────────────────────────────────
# TRADER SIMULATION
# ─────────────────────────────────────────────
MARKETS = {
    "BTC":  {"label": "BTC / USD",    "stop_mult": 0.025, "crypto": True},
    "NQ":   {"label": "NASDAQ (QQQ)", "stop_mult": 0.010, "crypto": False},
    "GOLD": {"label": "Gold (GLD)",   "stop_mult": 0.008, "crypto": False},
}

def simulate_trader(tr, market_signals):
    """Check if open position should close, then maybe open new one."""
    # --- close open position ---
    if tr["open_pos"]:
        pos = tr["open_pos"]
        mk  = pos["market"]
        sig = market_signals.get(mk, {})
        if not sig:
            return
        p      = sig["price"]
        is_long = pos["dir"] == "long"
        hit_sl  = is_long and p <= pos["stop"]
        hit_tp  = is_long and p >= pos["tp"]
        hit_sl2 = not is_long and p >= pos["stop"]
        hit_tp2 = not is_long and p <= pos["tp"]
        if hit_sl or hit_tp or hit_sl2 or hit_tp2:
            pnl = (p - pos["entry"]) * pos["units"] if is_long else (pos["entry"] - p) * pos["units"]
            tr["balance"] = max(0, tr["balance"] + pnl)
            tr["peak"]    = max(tr["peak"], tr["balance"])
            tr["trades"].append({
                "market":  mk, "dir": pos["dir"],
                "entry":   pos["entry"], "exit": p,
                "pnl":     round(pnl, 2),
                "result":  "win" if pnl > 0 else "loss",
                "reason":  "TP hit" if (hit_tp or hit_tp2) else "SL hit",
                "time":    datetime.now().strftime("%H:%M:%S"),
            })
            tr["history"].append(round(tr["balance"], 2))
            tr["open_pos"] = None

    # --- open new position ---
    if tr["open_pos"]:
        return
    for mk, sig in market_signals.items():
        if sig["conf"] < tr["min_conf"]:
            continue
        is_buy  = sig["signal"] in ("BUY", "STRONG BUY", "OVERSOLD")
        is_sell = sig["signal"] in ("SELL", "STRONG SELL", "OVERBOUGHT")
        if tr["wait_strong"] and sig["signal"] not in ("STRONG BUY", "STRONG SELL", "OVERSOLD"):
            continue
        if not is_buy and not is_sell:
            continue
        direction  = "long" if is_buy else "short"
        p          = sig["price"]
        stop_dist  = p * MARKETS[mk]["stop_mult"]
        stop       = p - stop_dist if is_buy else p + stop_dist
        tp         = p + stop_dist * tr["rr"] if is_buy else p - stop_dist * tr["rr"]
        risk_amt   = tr["balance"] * tr["risk_pct"]
        units      = risk_amt / stop_dist
        tr["open_pos"] = {
            "market": mk, "dir": direction,
            "entry":  round(p, 2 if not MARKETS[mk]["crypto"] else 0),
            "stop":   round(stop, 2 if not MARKETS[mk]["crypto"] else 0),
            "tp":     round(tp,   2 if not MARKETS[mk]["crypto"] else 0),
            "units":  units, "risk_amt": round(risk_amt, 2),
            "time":   datetime.now().strftime("%H:%M:%S"),
        }
        break

# ─────────────────────────────────────────────
# PLAIN-ENGLISH NOTES (AI or fallback)
# ─────────────────────────────────────────────
def push_note(ntype, market, text):
    st.session_state["notes"].insert(0, {
        "type": ntype, "market": market, "text": text,
        "time": datetime.now().strftime("%H:%M:%S"),
    })
    if len(st.session_state["notes"]) > 40:
        st.session_state["notes"].pop()

def fallback_notes(market_signals):
    labels = {"BTC": "BTC / USD", "NQ": "NASDAQ (QQQ)", "GOLD": "Gold (GLD)"}
    for mk, sig in market_signals.items():
        r, s = sig["rsi"], sig["signal"]
        label = labels[mk]
        if s == "OVERBOUGHT" or r > 72:
            push_note("watch", mk,
                f"**{label}:** Price is really high up right now — don't chase it. "
                f"Watch out for a drop. If you're already in, think about taking some profit.")
        elif s == "OVERSOLD" or r < 30:
            push_note("buy", mk,
                f"**{label}:** Price got beaten down pretty low. "
                f"Wait for one green candle to close, then it might be a good spot to get in small.")
        elif s == "STRONG BUY":
            push_note("buy", mk,
                f"**{label}:** Trend is pointing up — the short average crossed above the longer one (good sign). "
                f"Wait for the next candle to close green, then consider buying.")
        elif s == "STRONG SELL":
            push_note("sell", mk,
                f"**{label}:** Trend flipped down. Avoid buying right now. "
                f"If you have a position open, tighten your stop-loss.")
        elif s == "BUY":
            push_note("info", mk,
                f"**{label}:** Slowly building upward momentum. Nothing urgent — just keep watching. "
                f"If the next 15-min candle closes green, that's your entry signal.")

def ai_notes(market_signals, anthropic_key, sessions):
    if not anthropic_key:
        fallback_notes(market_signals)
        return
    cooldown = 60
    if time.time() - st.session_state["last_ai_call"] < cooldown:
        return
    st.session_state["last_ai_call"] = time.time()
    labels = {"BTC": "BTC / USD", "NQ": "NASDAQ (QQQ)", "GOLD": "Gold (GLD)"}
    summaries = ". ".join(
        f"{labels[k]}: RSI {v['rsi']:.0f}, signal {v['signal']}, "
        f"{'uptrend' if v['ma_bull'] else 'downtrend'}"
        for k, v in market_signals.items()
    )
    sess = ", ".join(sessions)
    prompt = (
        f"You are a friendly trading coach texting a complete beginner who loves the idea of trading. "
        f"Current markets: {summaries}. Session: {sess}. "
        f"Write 3-4 very short plain-English notes — like texting a friend. "
        f"Examples of tone: 'BTC is dropping like it forgot its keys — stay out for now', "
        f"'Gold looks like it wants to bounce — wait for one green candle then sneak in small', "
        f"'Nasdaq is running hot — watch out for a pullback before buying'. "
        f"NO jargon, no RSI, no MACD, no 'bullish divergence'. Just vibes and candle shapes. "
        f"Format as JSON array: "
        f'[{{"type":"watch|buy|sell|info","market":"BTC|NQ|GOLD","text":"..."}}]. '
        f"Return ONLY valid JSON, no extra text."
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": "claude-sonnet-4-5", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        raw    = resp.json()["content"][0]["text"].strip()
        parsed = json.loads(raw.replace("```json","").replace("```","").strip())
        for n in parsed:
            push_note(n.get("type","info"), n.get("market","BTC"), n.get("text",""))
    except:
        fallback_notes(market_signals)

# ─────────────────────────────────────────────
# RENDER HELPERS
# ─────────────────────────────────────────────
def render_price_cards(market_signals):
    cols = st.columns(3)
    config = [
        ("BTC",  "#f2a900", "BTC / USD"),
        ("NQ",   "#378ADD", "NASDAQ (QQQ)"),
        ("GOLD", "#BA7517", "Gold (GLD)"),
    ]
    for col, (mk, color, label) in zip(cols, config):
        with col:
            sig = market_signals.get(mk, {})
            p   = sig.get("price", 0)
            chg = market_data.get(mk, {}).get("chg", 0)
            s   = sig.get("signal", "HOLD")
            c   = sig.get("conf", 50)
            r   = sig.get("rsi", 50)
            is_buy  = "BUY"  in s or s == "OVERSOLD"
            is_sell = "SELL" in s or s == "OVERBOUGHT"
            border  = "#3a9d4e" if is_buy else "#c0392b" if is_sell else "#888"
            px_fmt  = f"${p:,.0f}" if mk == "BTC" else f"${p:,.2f}"
            chg_col = "#3a9d4e" if chg >= 0 else "#c0392b"
            st.markdown(
                f'<div style="border:2px solid {border};border-radius:12px;padding:14px;margin-bottom:4px">'
                f'<div style="font-size:12px;color:#888;margin-bottom:4px">{label}</div>'
                f'<div style="font-size:24px;font-weight:600;color:{color}">{px_fmt}</div>'
                f'<div style="font-size:12px;color:{chg_col};margin-bottom:8px">{chg:+.2f}% today</div>'
                f'<div style="font-size:16px;font-weight:600">{s}</div>'
                f'<div style="font-size:12px;color:#888">Confidence: {c}% | RSI: {r:.0f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

def render_notes(market_filter="ALL"):
    notes = st.session_state["notes"]
    if market_filter != "ALL":
        notes = [n for n in notes if n["market"] == market_filter]
    if not notes:
        st.info("Watching the markets... notes will appear here on the next refresh.")
        return
    icons = {"watch": "👀 Watch out", "buy": "🟢 Possible buy", "sell": "🔴 Consider selling", "info": "💡 Heads up"}
    for n in notes[:8]:
        cls = {"watch":"note-watch","buy":"note-buy","sell":"note-sell","info":"note-info"}.get(n["type"],"note-info")
        st.markdown(
            f'<div class="note-card {cls}">'
            f'<div style="font-size:10px;color:#666;margin-bottom:3px">{n["time"]}</div>'
            f'<div style="font-weight:600;font-size:12px;margin-bottom:4px">'
            f'{icons.get(n["type"],"💡")} — {MARKETS.get(n["market"],{}).get("label",n["market"])}</div>'
            f'{n["text"]}</div>',
            unsafe_allow_html=True,
        )

def render_trader_card(tr, market_signals):
    pnl  = tr["balance"] - 25000
    wins = sum(1 for t in tr["trades"] if t["result"] == "win")
    tot  = len(tr["trades"])
    wr   = round(wins/tot*100) if tot else 0
    dd   = round(max(0, (tr["peak"] - tr["balance"]) / tr["peak"] * 100), 1) if tr["peak"] else 0
    pnl_col = "#3a9d4e" if pnl >= 0 else "#c0392b"

    st.markdown(f"#### {tr['emoji']} {tr['name']}")
    st.caption(tr["style"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", f"${tr['balance']:,.0f}", delta=f"{pnl:+,.0f}")
    c2.metric("Win rate", f"{wr}%")
    c3.metric("Trades",   tot)
    c4.metric("Drawdown", f"{dd}%")

    # open position
    pos = tr["open_pos"]
    if pos:
        mk    = pos["market"]
        sig   = market_signals.get(mk, {})
        cur_p = sig.get("price", pos["entry"])
        unreal = (cur_p - pos["entry"]) * pos["units"] if pos["dir"]=="long" \
                 else (pos["entry"] - cur_p) * pos["units"]
        u_col = "#3a9d4e" if unreal >= 0 else "#c0392b"
        mk_label = MARKETS[mk]["label"]
        fmt = "0f" if MARKETS[mk]["crypto"] else ".2f"
        st.markdown(
            f'<div style="background:{"#f0faf2" if pos["dir"]=="long" else "#fdf2f2"};'
            f'border-left:3px solid {"#3a9d4e" if pos["dir"]=="long" else "#c0392b"};'
            f'border-radius:8px;padding:10px 14px;font-size:13px;margin:8px 0">'
            f'<b>{mk_label} — {pos["dir"].upper()}</b><br>'
            f'Entered at <b>${pos["entry"]:{fmt}}</b> &nbsp;|&nbsp; '
            f'Now at <b>${cur_p:{fmt}}</b><br>'
            f'Stop: <span style="color:#c0392b">${pos["stop"]:{fmt}}</span> &nbsp;|&nbsp; '
            f'Target: <span style="color:#3a9d4e">${pos["tp"]:{fmt}}</span><br>'
            f'Unrealized P&L: <span style="color:{u_col}"><b>${unreal:+,.0f}</b></span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#f5f5f5;border-radius:8px;padding:10px 14px;'
            'font-size:13px;margin:8px 0;color:#888">No open position right now</div>',
            unsafe_allow_html=True,
        )

    # last 3 trades
    recent = tr["trades"][-3:][::-1]
    if recent:
        for t in recent:
            col = "#3a9d4e" if t["result"]=="win" else "#c0392b"
            mk_label = MARKETS.get(t["market"],{}).get("label", t["market"])
            pnl_str = f"${t['pnl']:+,.2f}"
            st.markdown(
                f'<div style="font-size:11px;padding:2px 0">'
                f'<span style="background:{"#f0faf2" if t["result"]=="win" else "#fdf2f2"};'
                f'color:{col};border-radius:4px;padding:1px 6px;font-weight:600">'
                f'{t["result"].upper()}</span> &nbsp;'
                f'{mk_label} {t["dir"]} — {pnl_str} ({t["reason"]})'
                f'</div>',
                unsafe_allow_html=True,
            )

def render_scoreboard():
    rows = []
    for tr in TRADERS:
        pnl  = tr["balance"] - 25000
        wins = sum(1 for t in tr["trades"] if t["result"]=="win")
        tot  = len(tr["trades"])
        wr   = round(wins/tot*100) if tot else 0
        dd   = round(max(0, (tr["peak"] - tr["balance"]) / tr["peak"] * 100), 1) if tr["peak"] else 0
        rows.append({"Trader": f"{tr['emoji']} {tr['name']}", "Strategy": tr["style"],
                     "Balance": tr["balance"], "P&L ($)": pnl,
                     "Win %": wr, "Trades": tot, "Max Drawdown %": dd})
    df = pd.DataFrame(rows).sort_values("P&L ($)", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    st.dataframe(
        df.style
          .format({"Balance": "${:,.0f}", "P&L ($)": "${:+,.0f}", "Win %": "{}%", "Max Drawdown %": "{}%"})
          .map(lambda v: "color:#3a9d4e;font-weight:600" if v > 0 else "color:#c0392b;font-weight:600", subset=["P&L ($)"]),
        use_container_width=True,
    )

def render_equity_chart():
    fig = go.Figure()
    colors = {"Safe Sam": "#185fa5", "Swing Steve": "#3a9d4e", "Risky Rick": "#c0392b"}
    for tr in TRADERS:
        if len(tr["history"]) > 1:
            fig.add_trace(go.Scatter(
                y=tr["history"], mode="lines",
                name=f"{tr['emoji']} {tr['name']}",
                line=dict(color=colors.get(tr["name"],"#888"), width=2),
            ))
    fig.add_hline(y=25000, line=dict(color="#888", width=1, dash="dot"), annotation_text="$25k start")
    fig.update_layout(
        height=300, template="plotly_dark",
        title="Equity curves — all 3 traders",
        yaxis_title="Balance ($)", xaxis_title="Trade #",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    with st.expander("Update API keys", expanded=False):
        np_ = st.text_input("Polygon.io Key", value=POLYGON_KEY, type="password")
        na_ = st.text_input("Anthropic Key",  value=ANTHROPIC_KEY, type="password")
        if st.button("Save and reload"):
            st.session_state["POLYGON_KEY"]   = np_
            st.session_state["ANTHROPIC_KEY"] = na_
            st.cache_data.clear()
            st.rerun()

    st.divider()
    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)
    market_filter = st.selectbox("Filter notes by market", ["ALL", "BTC", "NQ", "GOLD"])

    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

    if st.button("🗑 Clear notes"):
        st.session_state["notes"] = []
        st.rerun()

    if st.button("♻️ Reset traders"):
        st.session_state["traders"] = [
            init_trader("Safe Sam",    "🔵", "Low risk — only trades strong signals",        0.005, 2.0, 70, True),
            init_trader("Swing Steve", "🟢", "Medium risk — rides the bigger moves",          0.015, 2.5, 55, False),
            init_trader("Risky Rick",  "🔴", "High risk — jumps in on almost every signal",  0.030, 1.5, 40, False),
        ]
        st.rerun()

    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# ─────────────────────────────────────────────
# FETCH DATA
# ─────────────────────────────────────────────
with st.spinner("Fetching live prices..."):
    btc_data  = fetch_btc()
    nq_raw    = fetch_polygon("QQQ", POLYGON_KEY)
    gld_raw   = fetch_polygon("GLD", POLYGON_KEY)

market_data = {
    "BTC":  btc_data,
    "NQ":   {**nq_raw,  "label": "NASDAQ (QQQ)", "crypto": False},
    "GOLD": {**gld_raw, "label": "Gold (GLD)",   "crypto": False},
}

market_signals = {
    mk: compute_signal(d["closes"])
    for mk, d in market_data.items()
}
for mk, sig in market_signals.items():
    sig["price"] = market_data[mk]["price"]

# run trader simulation
for tr in TRADERS:
    simulate_trader(tr, market_signals)

# generate notes
ai_notes(market_signals, ANTHROPIC_KEY, [s for s, _ in get_session()])

# ─────────────────────────────────────────────
# PAGE LAYOUT
# ─────────────────────────────────────────────
st.title("📈 Multi-Market Trader")
active_sessions = session_banner()

# ── Price cards ──
st.subheader("Live prices & signals")
render_price_cards(market_signals)
st.divider()

# ── Plain-English notes ──
st.subheader("📝 Your plain-English alerts")
st.caption("Written in plain language — no jargon, just what to watch for.")
render_notes(market_filter)
st.divider()

# ── 3 AI Traders ──
st.subheader("🤖 The 3 AI traders")
st.caption("Each uses different rules. Watch the scoreboard to see which strategy is working best right now.")

tabs = st.tabs([f"{tr['emoji']} {tr['name']}" for tr in TRADERS])
for tab, tr in zip(tabs, TRADERS):
    with tab:
        render_trader_card(tr, market_signals)

st.divider()

# ── Scoreboard ──
st.subheader("🏆 Scoreboard")
render_scoreboard()
st.divider()

# ── Equity chart ──
st.subheader("📈 Equity curves")
render_equity_chart()
st.divider()

# ── Signal log ──
with st.expander("📋 Full signal log"):
    log = []
    for tr in TRADERS:
        for t in tr["trades"]:
            log.append({
                "Trader":  tr["name"],
                "Market":  MARKETS.get(t["market"],{}).get("label", t["market"]),
                "Dir":     t["dir"],
                "Entry":   t["entry"],
                "Exit":    t["exit"],
                "P&L ($)": t["pnl"],
                "Result":  t["result"],
                "Reason":  t["reason"],
                "Time":    t.get("time",""),
            })
    if log:
        df_log = pd.DataFrame(log)
        st.dataframe(
            df_log.style
                  .format({"Entry": "${:,.2f}", "Exit": "${:,.2f}", "P&L ($)": "${:+,.2f}"})
                  .map(lambda v: "color:#3a9d4e" if v=="win" else "color:#c0392b", subset=["Result"]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No closed trades yet.")

# ── Auto-refresh ──
if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
