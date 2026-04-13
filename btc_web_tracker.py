import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import numpy as np
from datetime import datetime, timedelta
import time
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Multi-Market Trader", layout="wide")
# ─────────────────────────────────────────────
# API KEY GATE
# ─────────────────────────────────────────────
def get_keys():
    poly_key = st.secrets.get("POLYGON_KEY", "") if hasattr(st, "secrets") else ""
    anth_key = st.secrets.get("ANTHROPIC_KEY", "") if hasattr(st, "secrets") else ""
    return (
        st.session_state.get("POLYGON_KEY", poly_key),
        st.session_state.get("ANTHROPIC_KEY", anth_key),
    )
POLYGON_KEY, ANTHROPIC_KEY = get_keys()
if not POLYGON_KEY:
    st.title("Multi-Market Trader — Setup")
    st.info("Enter your API keys to get started. Stored in session only unless added to `.streamlit/secrets.toml`.")
    with st.form("key_form"):
        pk = st.text_input("Polygon.io API Key", type="password", help="Free key at polygon.io")
        ak = st.text_input("Anthropic API Key (optional — for AI analysis)", type="password")
        if st.form_submit_button("Start App"):
            if not pk:
                st.error("Polygon.io key is required.")
            else:
                st.session_state["POLYGON_KEY"]   = pk
                st.session_state["ANTHROPIC_KEY"] = ak
                st.rerun()
    st.stop()
# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "signal_log" not in st.session_state:
    st.session_state["signal_log"] = []
# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    with st.expander("Update API keys", expanded=False):
        new_poly = st.text_input("Polygon.io Key", value=POLYGON_KEY, type="password")
        new_anth = st.text_input("Anthropic Key (optional)", value=ANTHROPIC_KEY, type="password")
        if st.button("Save and reload"):
            st.session_state["POLYGON_KEY"]   = new_poly
            st.session_state["ANTHROPIC_KEY"] = new_anth
            st.cache_data.clear()
            st.rerun()
        st.caption("Session only.")
    st.divider()
    auto_refresh = st.toggle("Auto-refresh (60s)", value=True)
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.rerun()
    if st.button("Clear signal log"):
        st.session_state["signal_log"] = []
        st.rerun()
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
# ─────────────────────────────────────────────
# TRADING SESSIONS
# ─────────────────────────────────────────────
SESSIONS = {
    "Tokyo":   {"start": 0,  "end": 9,  "color": "#7C3AED", "markets": ["BTC/USD"],                          "desc": "Thin liquidity. BTC can drift or spike. Gold quiet."},
    "London":  {"start": 8,  "end": 17, "color": "#2563EB", "markets": ["BTC/USD", "Gold (GLD)"],             "desc": "High volatility open. Best for Gold breakouts. BTC often trends."},
    "NY":      {"start": 13, "end": 22, "color": "#059669", "markets": ["NASDAQ (QQQ)", "Gold (GLD)", "BTC/USD"], "desc": "Highest volume. NASDAQ most active. Key US data at 13:30 UTC."},
    "Overlap": {"start": 13, "end": 17, "color": "#D97706", "markets": ["All"],                               "desc": "London/NY overlap. Peak volume and volatility across all markets."},
}
def get_current_session():
    utc_now  = datetime.now(ZoneInfo("UTC"))
    utc_hour = utc_now.hour + utc_now.minute / 60
    active   = [name for name, s in SESSIONS.items() if s["start"] <= utc_hour < s["end"]]
    return (active if active else ["Off-hours"]), utc_now
def session_banner():
    active, utc_now = get_current_session()
    utc_str = utc_now.strftime("%H:%M UTC")
    ny_str  = utc_now.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M ET")
    lon_str = utc_now.astimezone(ZoneInfo("Europe/London")).strftime("%H:%M LDN")
    tok_str = utc_now.astimezone(ZoneInfo("Asia/Tokyo")).strftime("%H:%M TKY")
    badges = ""
    best_mkts = []
    for sess in active:
        color = SESSIONS[sess]["color"] if sess in SESSIONS else "#6B7280"
        badges += f'<span style="display:inline-block;background:{color};color:#fff;border-radius:6px;padding:4px 12px;font-size:13px;font-weight:600;margin-right:8px;">{sess} Session</span>'
        best_mkts.extend(SESSIONS.get(sess, {}).get("markets", []))
    best_mkts = list(dict.fromkeys(best_mkts))
    desc_text = " | ".join(SESSIONS[s]["desc"] for s in active if s in SESSIONS) or "Markets are quiet. Lower volume, wider spreads."
    mkt_line  = f'<div style="font-size:12px;color:#facc15;margin-top:6px;">Best markets now: {", ".join(best_mkts)}</div>' if best_mkts else ""
    st.markdown(
        f'<div style="background:#1a1a2e;border-radius:10px;padding:14px 18px;margin-bottom:12px;">'
        f'<div style="margin-bottom:8px;">{badges}</div>'
        f'<div style="font-size:13px;color:#ccc;margin-bottom:6px;">{desc_text}</div>'
        f'<div style="font-size:12px;color:#888;">Clock: {utc_str} | {ny_str} | {lon_str} | {tok_str}</div>'
        f'{mkt_line}</div>',
        unsafe_allow_html=True,
    )
    return active
# ─────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_btc_price():
    try:
        url = ("https://api.coingecko.com/api/v3/simple/price"
               "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true")
        d = requests.get(url, timeout=10).json()
        return d["bitcoin"]["usd"], d["bitcoin"].get("usd_24h_change", 0), d["bitcoin"].get("usd_24h_vol", 0)
    except Exception as e:
        st.warning(f"BTC price error: {e}")
        return None, None, None
@st.cache_data(ttl=120)
def fetch_btc_chart():
    try:
        url = ("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
               "?vs_currency=usd&days=90&interval=daily")
        d   = requests.get(url, timeout=20).json()
        df  = pd.DataFrame(d["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df.set_index("timestamp")
    except Exception as e:
        st.warning(f"BTC chart error: {e}")
        return pd.DataFrame()
@st.cache_data(ttl=300)
def fetch_polygon_stock(ticker: str, _key: str, days: int = 90):
    try:
        to_date   = datetime.today().strftime("%Y-%m-%d")
        from_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
               f"{from_date}/{to_date}?adjusted=true&sort=asc&limit={days}&apiKey={_key}")
        d = requests.get(url, timeout=15).json()
        if "results" not in d or len(d["results"]) < 2:
            st.warning(f"No Polygon data for {ticker}. Check API key or plan.")
            return pd.DataFrame()
        df = pd.DataFrame(d["results"])
        df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={"c": "close", "o": "open", "h": "high", "l": "low", "v": "volume"})
        return df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        st.warning(f"Polygon {ticker} error: {e}")
        return pd.DataFrame()
@st.cache_data(ttl=60)
def fetch_polygon_snapshot(ticker: str, _key: str):
    try:
        url = (f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
               f"/{ticker}?apiKey={_key}")
        return requests.get(url, timeout=10).json().get("ticker", {})
    except Exception as e:
        st.warning(f"Snapshot error: {e}")
        return {}
@st.cache_data(ttl=60)
def fetch_btc_polygon_rsi(_key: str):
    try:
        url  = (f"https://api.polygon.io/v1/indicators/rsi/X:BTCUSD"
                f"?timespan=hour&window=14&series_type=close&order=desc&limit=1&apiKey={_key}")
        d    = requests.get(url, timeout=10).json()
        vals = d.get("results", {}).get("values", [])
        return vals[0]["value"] if vals else None
    except Exception as e:
        st.warning(f"Polygon RSI error: {e}")
        return None
@st.cache_data(ttl=120)
def fetch_polymarket_btc():
    try:
        url  = "https://clob.polymarket.com/markets?active=true&closed=false&limit=20&keyword=bitcoin"
        resp = requests.get(url, timeout=10).json()
        results = []
        for m in resp.get("data", [])[:5]:
            tokens    = m.get("tokens", [])
            yes_token = next((t for t in tokens if t.get("outcome", "").upper() == "YES"), None)
            no_token  = next((t for t in tokens if t.get("outcome", "").upper() == "NO"),  None)
            if yes_token and no_token:
                results.append({
                    "question": m.get("question", "Unknown"),
                    "yes_pct":  round(float(yes_token.get("price", 0)) * 100, 1),
                    "no_pct":   round(float(no_token.get("price",  0)) * 100, 1),
                    "volume":   m.get("volume", 0),
                })
        return results
    except Exception as e:
        st.warning(f"Polymarket error: {e}")
        return []
# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 30:
        return df
    df = df.copy()
    df["ma8"]  = df["close"].rolling(8).mean()
    df["ma21"] = df["close"].rolling(21).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]        = exp1 - exp2
    df["signal_line"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["signal_line"]
    delta = df["close"].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + gain / loss))
    df["bb_mid"]   = df["close"].rolling(20).mean()
    df["bb_std"]   = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    if "high" in df.columns and "low" in df.columns:
        hl   = df["high"] - df["low"]
        df["atr"] = hl.rolling(14).mean()
    else:
        df["atr"] = df["close"] * 0.02
    bull_ma        = df["ma8"] > df["ma21"]
    bull_macd      = df["macd"] > df["signal_line"]
    macd_cross_up  = bull_macd & ~bull_macd.shift(1).fillna(False)
    macd_cross_dn  = ~bull_macd & bull_macd.shift(1).fillna(False)
    df["signal"] = np.where(
        bull_ma & macd_cross_up  & df["rsi"].between(40, 72), "STRONG BUY",
        np.where(bull_ma & bull_macd & df["rsi"].between(40, 68), "BUY",
        np.where(~bull_ma & macd_cross_dn & (df["rsi"] > 30),    "STRONG SELL",
        np.where(~bull_ma & ~bull_macd & (df["rsi"] > 32),       "SELL",
        np.where(df["rsi"] < 30, "OVERSOLD",
        np.where(df["rsi"] > 70, "OVERBOUGHT", "HOLD"))))))
    return df
def get_signal_meta(signal, rsi, is_bull, macd_bull):
    if signal == "STRONG BUY":
        conf  = min(94, round(65 + (rsi - 45) * 0.4 + (8 if is_bull else 0)))
        emoji = "🟢"
    elif signal == "BUY":
        conf  = min(85, round(55 + (8 if is_bull else 0) + (7 if macd_bull else 0)))
        emoji = "🟢"
    elif signal == "STRONG SELL":
        conf  = min(94, round(65 + (8 if not is_bull else 0)))
        emoji = "🔴"
    elif signal == "SELL":
        conf  = min(85, round(55 + (8 if not is_bull else 0) + (7 if not macd_bull else 0)))
        emoji = "🔴"
    elif signal == "OVERSOLD":
        conf  = min(88, round(62 + (30 - rsi)))
        emoji = "🟡"
    elif signal == "OVERBOUGHT":
        conf  = min(88, round(62 + (rsi - 70)))
        emoji = "🟡"
    else:
        conf, emoji = 50, "⚪"
    return max(42, conf), emoji
def get_market_state(df):
    if df.empty:
        return None, None, 0, "HOLD", False, False
    price    = df["close"].iloc[-1]
    rsi      = df["rsi"].iloc[-1]    if "rsi"    in df.columns else None
    macd     = df["macd"].iloc[-1]   if "macd"   in df.columns else 0
    sig      = df["signal"].iloc[-1] if "signal" in df.columns else "HOLD"
    is_bull  = bool(df["ma8"].iloc[-1] > df["ma21"].iloc[-1]) if "ma8" in df.columns else False
    mcd_bull = bool(macd > 0)
    return price, rsi, macd, sig, is_bull, mcd_bull
# ─────────────────────────────────────────────
# TRADE LEVELS
# ─────────────────────────────────────────────
def calc_trade_levels(price, signal, is_crypto, atr=None):
    if atr and atr > 0:
        stop_dist = atr * 1.5
    else:
        stop_dist = price * (0.025 if is_crypto else 0.008)
    t1_dist = stop_dist * 1.5
    t2_dist = stop_dist * 3.0
    is_buy  = "BUY" in signal or signal == "OVERSOLD"
    fmt     = 0 if is_crypto else 2
    if is_buy:
        stop, t1, t2 = price - stop_dist, price + t1_dist, price + t2_dist
    else:
        stop, t1, t2 = price + stop_dist, price - t1_dist, price - t2_dist
    return {
        "direction": "LONG" if is_buy else "SHORT",
        "entry":    round(price, fmt),
        "stop":     round(stop,  fmt),
        "target_1": round(t1,    fmt),
        "target_2": round(t2,    fmt),
        "rr":       1.5,
    }
# ─────────────────────────────────────────────
# BACKTESTING ENGINE
# ─────────────────────────────────────────────
def run_backtest(df, is_crypto=False):
    if df.empty or "signal" not in df.columns or len(df) < 30:
        return {}
    df = df.copy().dropna(subset=["close", "signal", "rsi"])
    initial_capital = 10_000.0
    cash = initial_capital
    position = 0.0
    entry_px = 0.0
    trades   = []
    equity   = []
    stop_pct = 0.025 if is_crypto else 0.010
    t1_pct   = 0.040 if is_crypto else 0.015
    for i in range(1, len(df)):
        row      = df.iloc[i]
        prev_sig = df.iloc[i - 1]["signal"]
        price    = row["close"]
        val      = cash + position * price
        equity.append({"date": df.index[i], "equity": val})
        if position > 0 and entry_px > 0 and price <= entry_px * (1 - stop_pct):
            pnl  = (price - entry_px) * position
            cash += position * price
            trades.append({"type": "Long SL", "entry": entry_px, "exit": price, "pnl": pnl})
            position = 0; entry_px = 0
            continue
        if position < 0 and entry_px > 0 and price >= entry_px * (1 + stop_pct):
            pnl  = (entry_px - price) * abs(position)
            cash += abs(position) * price
            trades.append({"type": "Short SL", "entry": entry_px, "exit": price, "pnl": -abs(pnl)})
            position = 0; entry_px = 0
            continue
        if prev_sig in ("STRONG BUY", "BUY") and position == 0:
            units = (cash * 0.95) / price
            position = units; cash -= units * price; entry_px = price
        elif prev_sig in ("STRONG SELL", "SELL") and position == 0:
            units = (cash * 0.95) / price
            position = -units; cash += units * price; entry_px = price
        elif prev_sig in ("STRONG SELL", "SELL", "OVERBOUGHT") and position > 0:
            pnl  = (price - entry_px) * position
            cash += position * price
            trades.append({"type": "Long", "entry": entry_px, "exit": price, "pnl": pnl})
            position = 0; entry_px = 0
        elif prev_sig in ("STRONG BUY", "BUY", "OVERSOLD") and position < 0:
            pnl  = (entry_px - price) * abs(position)
            cash += abs(position) * price
            trades.append({"type": "Short", "entry": entry_px, "exit": price, "pnl": pnl})
            position = 0; entry_px = 0
    final_price = df.iloc[-1]["close"]
    if position != 0:
        pnl  = (final_price - entry_px) * position if position > 0 else (entry_px - final_price) * abs(position)
        cash += abs(position) * final_price
        trades.append({"type": "Open@end", "entry": entry_px, "exit": final_price, "pnl": pnl})
    if not trades:
        return {"error": "No trades generated."}
    eq_df    = pd.DataFrame(equity)
    trade_df = pd.DataFrame(trades)
    wins     = trade_df[trade_df["pnl"] > 0]
    losses   = trade_df[trade_df["pnl"] <= 0]
    total_ret    = (cash - initial_capital) / initial_capital * 100
    win_rate     = len(wins) / len(trade_df) * 100
    avg_win      = wins["pnl"].mean()   if not wins.empty   else 0
    avg_loss     = losses["pnl"].mean() if not losses.empty else 0
    pf_denom     = losses["pnl"].sum()
    profit_factor = abs(wins["pnl"].sum() / pf_denom) if pf_denom != 0 else 99.0
    bh_ret       = (df.iloc[-1]["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"] * 100
    if not eq_df.empty:
        roll_max = eq_df["equity"].cummax()
        max_dd   = ((eq_df["equity"] - roll_max) / roll_max * 100).min()
    else:
        max_dd = 0
    return {
        "total_return":  round(total_ret,          2),
        "bh_return":     round(bh_ret,             2),
        "win_rate":      round(win_rate,           1),
        "total_trades":  len(trade_df),
        "wins":          len(wins),
        "losses":        len(losses),
        "avg_win":       round(avg_win,            2),
        "avg_loss":      round(avg_loss,           2),
        "profit_factor": round(min(profit_factor, 99.0), 2),
        "max_drawdown":  round(max_dd,             2),
        "equity_curve":  eq_df,
        "trade_list":    trade_df,
        "final_equity":  round(cash,               2),
    }
# ─────────────────────────────────────────────
# SIGNAL LOG
# ─────────────────────────────────────────────
def maybe_log_signal(market, signal, price, conf, levels, active_sessions):
    log  = st.session_state["signal_log"]
    last = next((e for e in reversed(log) if e["market"] == market), None)
    price_moved = (abs(price - last["entry_price"]) / last["entry_price"] > 0.005 if last else False)
    if not last or last["signal"] != signal or price_moved:
        st.session_state["signal_log"].append({
            "time":        datetime.now().strftime("%H:%M:%S"),
            "session":     " / ".join(active_sessions),
            "market":      market,
            "signal":      signal,
            "direction":   levels["direction"],
            "entry_price": price,
            "stop":        levels["stop"],
            "target_1":    levels["target_1"],
            "target_2":    levels["target_2"],
            "rr":          levels["rr"],
            "conf":        conf,
        })
# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────
def ai_analysis(market_name, price, change, rsi, macd, is_bull, macd_bull, signal, conf, anth_key, sessions):
    sess_ctx = ", ".join(sessions) if sessions else "Off-hours"
    if not anth_key:
        return (
            f"[{sess_ctx}] RSI {rsi:.1f}, MA8 {'above' if is_bull else 'below'} MA21 — "
            f"{'bullish' if is_bull else 'bearish'} momentum. MACD {'bullish' if macd_bull else 'bearish'}. "
            f"{signal} at {conf}% confidence. Always use stop-losses. Not financial advice."
        )
    try:
        prompt = (
            f"Professional market analyst. Live data for {market_name}:\n"
            f"Price: ${price:,.2f} | 24h: {change:+.2f}% | RSI: {rsi:.1f}\n"
            f"MACD: {macd:.4f} ({'bullish' if macd_bull else 'bearish'}) | "
            f"MA8 vs MA21: {'bullish' if is_bull else 'bearish'}\n"
            f"Signal: {signal} | Confidence: {conf}% | Session: {sess_ctx}\n\n"
            "Write 3-4 direct sentences: technicals, key price level, "
            "whether session supports this trade, and the primary risk."
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": anth_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-5", "max_tokens": 350,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        return resp.json()["content"][0]["text"]
    except Exception as e:
        return f"AI analysis unavailable: {e}"
# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
def build_chart(df, title, color="#f2a900", levels=None):
    if df.empty:
        return None
    fig = go.Figure()
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], line=dict(color="#444", width=1), showlegend=False, name="BB Upper"))
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], line=dict(color="#444", width=1),
                                 fill="tonexty", fillcolor="rgba(100,100,100,0.08)", showlegend=False, name="BB Lower"))
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Price", line=dict(color=color, width=2.5)))
    if "ma8"  in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df["ma8"],  name="MA8",  line=dict(color="#5DCAA5", width=1.2, dash="dot")))
    if "ma21" in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df["ma21"], name="MA21", line=dict(color="#ED93B1", width=1.2, dash="dot")))
    if "ma50" in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df["ma50"], name="MA50", line=dict(color="#F59E0B", width=1.0, dash="dash")))
    if "signal" in df.columns:
        buys      = df[df["signal"].isin(["BUY", "STRONG BUY", "OVERSOLD"])]
        str_buys  = df[df["signal"] == "STRONG BUY"]
        sells     = df[df["signal"].isin(["SELL", "STRONG SELL", "OVERBOUGHT"])]
        str_sells = df[df["signal"] == "STRONG SELL"]
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers",
                                     marker=dict(symbol="triangle-up", size=12, color="lime"), name="Buy"))
        if not str_buys.empty:
            fig.add_trace(go.Scatter(x=str_buys.index, y=str_buys["close"], mode="markers",
                                     marker=dict(symbol="star", size=16, color="#00ff88"), name="Strong Buy"))
        if not sells.empty:
            fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers",
                                     marker=dict(symbol="triangle-down", size=12, color="red"), name="Sell"))
        if not str_sells.empty:
            fig.add_trace(go.Scatter(x=str_sells.index, y=str_sells["close"], mode="markers",
                                     marker=dict(symbol="x", size=14, color="#ff4444"), name="Strong Sell"))
    if levels:
        fig.add_hline(y=levels["entry"],    line=dict(color="#fff",    width=1, dash="dot"),  annotation_text="Entry")
        fig.add_hline(y=levels["stop"],     line=dict(color="#ef4444", width=1, dash="dash"), annotation_text="Stop")
        fig.add_hline(y=levels["target_1"], line=dict(color="#22c55e", width=1, dash="dash"), annotation_text="T1")
        fig.add_hline(y=levels["target_2"], line=dict(color="#16a34a", width=1, dash="dash"), annotation_text="T2")
    fig.update_layout(height=500, template="plotly_dark", title=title,
                      xaxis_title="Date", yaxis_title="Price (USD)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig
def build_equity_chart(eq_df, title):
    if eq_df.empty:
        return None
    fig = px.area(eq_df, x="date", y="equity", title=title, color_discrete_sequence=["#22c55e"])
    fig.add_hline(y=10000, line=dict(color="#888", width=1, dash="dot"), annotation_text="$10k start")
    fig.update_layout(height=300, template="plotly_dark", xaxis_title="", yaxis_title="Portfolio Value ($)")
    return fig
def build_macd_chart(df, color):
    if df.empty or "macd" not in df.columns:
        return None
    bar_colors = ["#22c55e" if v >= 0 else "#ef4444" for v in df["macd_hist"].fillna(0)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], name="Histogram", marker_color=bar_colors))
    fig.add_trace(go.Scatter(x=df.index, y=df["macd"],        name="MACD",   line=dict(color=color,    width=1.5)))
    fig.add_trace(go.Scatter(x=df.index, y=df["signal_line"], name="Signal", line=dict(color="#ED93B1", width=1.5)))
    fig.update_layout(height=220, template="plotly_dark", title="MACD",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig
def build_rsi_chart(df):
    if df.empty or "rsi" not in df.columns:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], name="RSI", line=dict(color="#7C3AED", width=2)))
    fig.add_hline(y=70, line=dict(color="#ef4444", width=1, dash="dash"), annotation_text="OB 70")
    fig.add_hline(y=30, line=dict(color="#22c55e", width=1, dash="dash"), annotation_text="OS 30")
    fig.add_hline(y=50, line=dict(color="#888",    width=1, dash="dot"))
    fig.update_layout(height=200, template="plotly_dark", title="RSI (14)", yaxis=dict(range=[0, 100]))
    return fig
# ─────────────────────────────────────────────
# FUNDED SIMULATOR
# ─────────────────────────────────────────────
def funded_sim(price, signal, is_crypto=True):
    target_pct = 0.04 if is_crypto else 0.015
    stop_pct   = 0.025 if is_crypto else 0.008
    sizes  = [0.1, 0.2, 0.3] if is_crypto else [1, 5, 10]
    unit   = "BTC" if is_crypto else "shares"
    is_buy = "BUY" in signal or signal == "OVERSOLD"
    results = []
    for size in sizes:
        target = price * (1 + target_pct) if is_buy else price * (1 - target_pct)
        stop   = price * (1 - stop_pct)   if is_buy else price * (1 + stop_pct)
        pnl    = (target - price) * size   if is_buy else (price - target) * size
        risk   = abs(price - stop) * size
        results.append((size, unit, "Long" if is_buy else "Short", pnl, target_pct * 100, risk))
    return results
# ─────────────────────────────────────────────
# FETCH ALL DATA
# ─────────────────────────────────────────────
btc_price, btc_chg, btc_vol = fetch_btc_price()
df_btc    = compute_indicators(fetch_btc_chart())
df_nasdaq = compute_indicators(fetch_polygon_stock("QQQ", POLYGON_KEY, days=90))
df_gold   = compute_indicators(fetch_polygon_stock("GLD", POLYGON_KEY, days=90))
_,         btc_rsi,  btc_macd,  btc_sig,  btc_bull,  btc_mcd_bull = get_market_state(df_btc)
nq_price,  nq_rsi,   nq_macd,   nq_sig,   nq_bull,   nq_mcd_bull  = get_market_state(df_nasdaq)
gld_price, gld_rsi,  gld_macd,  gld_sig,  gld_bull,  gld_mcd_bull = get_market_state(df_gold)
nq_prev  = df_nasdaq["close"].iloc[-2] if len(df_nasdaq) > 1 else nq_price
gld_prev = df_gold["close"].iloc[-2]   if len(df_gold)   > 1 else gld_price
nq_chg   = ((nq_price  / nq_prev  - 1) * 100) if nq_price  and nq_prev  else None
gld_chg  = ((gld_price / gld_prev - 1) * 100) if gld_price and gld_prev else None
nq_vol   = df_nasdaq["volume"].iloc[-1] if not df_nasdaq.empty and "volume" in df_nasdaq else None
gld_vol  = df_gold["volume"].iloc[-1]   if not df_gold.empty   and "volume" in df_gold   else None
btc_atr  = df_btc["atr"].iloc[-1]    if not df_btc.empty    and "atr" in df_btc.columns    else None
nq_atr   = df_nasdaq["atr"].iloc[-1] if not df_nasdaq.empty and "atr" in df_nasdaq.columns else None
gld_atr  = df_gold["atr"].iloc[-1]   if not df_gold.empty   and "atr" in df_gold.columns   else None
btc_conf, btc_emoji = get_signal_meta(btc_sig, btc_rsi or 50, btc_bull, btc_mcd_bull)
nq_conf,  nq_emoji  = get_signal_meta(nq_sig,  nq_rsi  or 50, nq_bull,  nq_mcd_bull)
gld_conf, gld_emoji = get_signal_meta(gld_sig, gld_rsi or 50, gld_bull, gld_mcd_bull)
btc_levels  = calc_trade_levels(btc_price, btc_sig, True,  btc_atr) if btc_price else None
nq_levels   = calc_trade_levels(nq_price,  nq_sig,  False, nq_atr)  if nq_price  else None
gld_levels  = calc_trade_levels(gld_price, gld_sig, False, gld_atr) if gld_price else None
active_sessions, _ = get_current_session()
if btc_price  and btc_levels:  maybe_log_signal("BTC/USD",      btc_sig, btc_price,  btc_conf,  btc_levels,  active_sessions)
if nq_price   and nq_levels:   maybe_log_signal("NASDAQ (QQQ)", nq_sig,  nq_price,   nq_conf,   nq_levels,   active_sessions)
if gld_price  and gld_levels:  maybe_log_signal("Gold (GLD)",   gld_sig, gld_price,  gld_conf,  gld_levels,  active_sessions)
# ─────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────
st.title("Multi-Market Trader  BTC  NASDAQ  Gold")
active_sessions = session_banner()
st.subheader("Live signals")
sig_cols = st.columns(3)
markets_meta = [
    ("BTC / USD",    btc_price, btc_chg, btc_sig, btc_conf, btc_emoji, btc_levels, "#f2a900", True),
    ("NASDAQ (QQQ)", nq_price,  nq_chg,  nq_sig,  nq_conf,  nq_emoji,  nq_levels,  "#378ADD", False),
    ("Gold (GLD)",   gld_price, gld_chg, gld_sig, gld_conf, gld_emoji, gld_levels, "#BA7517", False),
]
for col, (name, price, chg, sig, conf, emoji, levels, accent, is_crypto) in zip(sig_cols, markets_meta):
    with col:
        is_buy  = "BUY"  in sig or sig == "OVERSOLD"
        is_sell = "SELL" in sig or sig == "OVERBOUGHT"
        border  = "#22c55e" if is_buy else "#ef4444" if is_sell else "#555"
        px_fmt  = f"${price:,.0f}" if (price and is_crypto) else (f"${price:,.2f}" if price else "N/A")
        chg_fmt = f"{chg:+.2f}% today" if chg else "N/A"
        sess_match = any(
            name.split(" ")[0] in SESSIONS.get(s, {}).get("markets", []) or
            "All" in SESSIONS.get(s, {}).get("markets", [])
            for s in active_sessions if s != "Off-hours"
        )
        sess_badge = (' <span style="background:#D97706;color:#fff;border-radius:4px;padding:1px 7px;font-size:10px;">ACTIVE SESSION</span>' if sess_match else "")
        st.markdown(
            f'<div style="border:2px solid {border};border-radius:10px;padding:14px 16px;margin-bottom:6px;">'
            f'<div style="font-size:12px;color:#aaa;">{name}{sess_badge}</div>'
            f'<div style="font-size:22px;font-weight:600;color:{accent};">{px_fmt}</div>'
            f'<div style="font-size:12px;color:#aaa;margin-bottom:8px;">{chg_fmt}</div>'
            f'<div style="font-size:18px;font-weight:600;">{emoji} {sig}</div>'
            f'<div style="font-size:12px;color:#aaa;">Confidence: {conf}%</div>'
            f'<div style="font-size:11px;color:#555;margin-top:4px;">{datetime.now().strftime("%H:%M:%S")}</div>'
            f'</div>', unsafe_allow_html=True)
        if levels and price:
            dc = "#22c55e" if levels["direction"] == "LONG" else "#ef4444"
            st.markdown(
                f'<div style="background:#111;border-radius:8px;padding:10px 14px;font-size:13px;line-height:2;">'
                f'<span style="background:{dc};color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;">{levels["direction"]}</span><br>'
                f'<b>Entry:</b> ${levels["entry"]:,}<br>'
                f'<b>Stop:</b> <span style="color:#ef4444;">${levels["stop"]:,}</span> (ATR-based)<br>'
                f'<b>Target 1:</b> <span style="color:#22c55e;">${levels["target_1"]:,}</span><br>'
                f'<b>Target 2:</b> <span style="color:#22c55e;">${levels["target_2"]:,}</span><br>'
                f'<b>R:R:</b> 1:{levels["rr"]}'
                f'</div>', unsafe_allow_html=True)
st.divider()
# Signal log
st.subheader("Signal history (this session)")
log = st.session_state["signal_log"]
if log:
    df_log = pd.DataFrame(list(reversed(log)))
    def _ss(v):
        if "BUY"  in str(v): return "color:#22c55e;font-weight:600"
        if "SELL" in str(v): return "color:#ef4444;font-weight:600"
        if v == "OVERBOUGHT": return "color:#f97316;font-weight:600"
        if v == "OVERSOLD":   return "color:#facc15;font-weight:600"
        return ""
    def _sd(v):
        return "color:#22c55e;font-weight:600" if v == "LONG" else "color:#ef4444;font-weight:600" if v == "SHORT" else ""
    cols_show  = ["time","session","market","signal","direction","entry_price","stop","target_1","target_2","rr","conf"]
    rename_map = {"time":"Time","session":"Session","market":"Market","signal":"Signal","direction":"Dir",
                  "entry_price":"Entry $","stop":"Stop $","target_1":"T1 $","target_2":"T2 $","rr":"R:R","conf":"Conf %"}
    st.dataframe(
        df_log[cols_show].rename(columns=rename_map).style
        .applymap(_ss, subset=["Signal"]).applymap(_sd, subset=["Dir"])
        .format({"Entry $":"${:,.2f}","Stop $":"${:,.2f}","T1 $":"${:,.2f}","T2 $":"${:,.2f}","R:R":"1:{}","Conf %":"{}%"}),
        use_container_width=True, hide_index=True)
    st.caption(f"{len(log)} signal(s) this session.")
else:
    st.info("Signals appear here as they are detected on each refresh.")
st.divider()
st.subheader("Market detail and backtests")
tab_btc, tab_nq, tab_gold, tab_sessions = st.tabs(["BTC / USD", "NASDAQ (QQQ)", "Gold (GLD)", "Trading Sessions"])
def render_market_tab(name, df, price, chg, vol, rsi, macd, sig, conf, emoji,
                      is_bull, macd_bull, levels, is_crypto, chart_color,
                      active_sessions, snap=None, poly_rsi=None):
    if not price:
        st.warning("No data available.")
        return
    st.markdown(f"### {emoji} {sig}  |  Confidence {conf}%")
    st.progress(conf / 100)
    if levels:
        ca, cb, cc, cd, ce = st.columns(5)
        ca.metric("Direction", levels["direction"])
        cb.metric("Entry",     f"${levels['entry']:,}")
        cc.metric("Stop loss", f"${levels['stop']:,}",
                  delta=f"-{abs(price - levels['stop']) / price * 100:.1f}%", delta_color="inverse")
        cd.metric("Target 1",  f"${levels['target_1']:,}",
                  delta=f"+{abs(levels['target_1'] - price) / price * 100:.1f}%")
        ce.metric("Target 2",  f"${levels['target_2']:,}",
                  delta=f"+{abs(levels['target_2'] - price) / price * 100:.1f}%")
        st.caption(f"ATR-based stop  |  R:R 1:{levels['rr']}  |  {datetime.now().strftime('%H:%M:%S')}  |  Session: {', '.join(active_sessions)}")
    st.divider()
    st.subheader("Price chart")
    fig_price = build_chart(df, name, chart_color, levels)
    if fig_price: st.plotly_chart(fig_price, use_container_width=True)
    fig_macd  = build_macd_chart(df, chart_color)
    if fig_macd:  st.plotly_chart(fig_macd,  use_container_width=True)
    fig_rsi   = build_rsi_chart(df)
    if fig_rsi:   st.plotly_chart(fig_rsi,   use_container_width=True)
    st.divider()
    st.subheader("Backtest results (90 days)")
    bt = run_backtest(df, is_crypto)
    if "error" in bt:
        st.warning(bt["error"])
    elif bt:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Strategy return",   f"{bt['total_return']:+.1f}%")
        m2.metric("Buy & hold return", f"{bt['bh_return']:+.1f}%")
        m3.metric("Win rate",          f"{bt['win_rate']:.0f}%")
        m4.metric("Total trades",      bt["total_trades"])
        m5.metric("Profit factor",     bt["profit_factor"])
        m6.metric("Max drawdown",      f"{bt['max_drawdown']:.1f}%")
        col_eq, col_tr = st.columns([2, 1])
        with col_eq:
            fig_eq = build_equity_chart(bt["equity_curve"], f"{name}  Equity curve ($10k start)")
            if fig_eq: st.plotly_chart(fig_eq, use_container_width=True)
        with col_tr:
            st.markdown("**Recent trades**")
            tdf = bt["trade_list"].tail(10)[["type","entry","exit","pnl"]].copy()
            tdf.columns = ["Type","Entry","Exit","PnL $"]
            def _sp(v):
                return "color:#22c55e" if v > 0 else "color:#ef4444"
            st.dataframe(
                tdf.style.applymap(_sp, subset=["PnL $"])
                         .format({"Entry":"${:,.2f}","Exit":"${:,.2f}","PnL $":"${:+,.2f}"}),
                use_container_width=True, hide_index=True)
        with st.expander("Backtest disclaimer"):
            st.caption("Past results do not guarantee future performance. No slippage, commissions, or fees modelled. Do not trade based solely on backtest results.")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Indicators")
        if rsi:
            rsi_lbl = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            st.markdown(f"- **RSI 14:** {rsi:.1f} ({rsi_lbl})")
            st.markdown(f"- **MACD:** {macd:.4f} ({'Bullish' if macd_bull else 'Bearish'})")
            if "ma8" in df.columns:
                st.markdown(f"- **MA8:** ${df['ma8'].iloc[-1]:,.2f}  vs  **MA21:** ${df['ma21'].iloc[-1]:,.2f}")
            if "bb_upper" in df.columns:
                bb_pos = (price - df["bb_lower"].iloc[-1]) / (df["bb_upper"].iloc[-1] - df["bb_lower"].iloc[-1]) * 100
                st.markdown(f"- **Bollinger position:** {bb_pos:.0f}%")
            if "atr" in df.columns:
                st.markdown(f"- **ATR (14):** ${df['atr'].iloc[-1]:,.2f}")
            st.markdown(f"- **Trend:** {'Uptrend' if is_bull else 'Downtrend'}")
    with c2:
        st.subheader("Crowd and sentiment")
        if is_crypto:
            if vol: st.markdown(f"- **24h Volume:** ${vol/1e9:.2f}B")
            if poly_rsi: st.markdown(f"- **Polygon RSI (live):** {poly_rsi:.1f}")
            if rsi:
                bull_pct = round(rsi)
                st.markdown(f"- **Bullish proxy:** {bull_pct}%  |  Bearish: {100 - bull_pct}%")
            poly_markets = fetch_polymarket_btc()
            if poly_markets:
                st.markdown("**Polymarket odds**")
                for m in poly_markets:
                    with st.expander(m["question"]):
                        pa, pb = st.columns(2)
                        pa.metric("YES", f"{m['yes_pct']}%")
                        pb.metric("NO",  f"{m['no_pct']}%")
                        if m["volume"]: st.caption(f"Volume: ${float(m['volume']):,.0f}")
        elif snap:
            day  = snap.get("day",     {})
            prev = snap.get("prevDay", {})
            if day.get("v"):  st.markdown(f"- **Day volume:** {day['v']/1e6:.1f}M shares")
            if day.get("c") and day.get("o"):
                st.markdown(f"- **Intraday change:** {(day['c'] - day['o']) / day['o'] * 100:+.2f}%")
            if prev.get("c"): st.markdown(f"- **Prev close:** ${prev['c']:.2f}")
            if rsi: st.markdown(f"- **RSI sentiment:** {'Bullish' if rsi > 60 else 'Bearish' if rsi < 40 else 'Neutral'}")
    st.subheader("Funded account simulator")
    for size, unit, direction, pnl, pct, risk in funded_sim(price, sig, is_crypto):
        label = f"{size} {unit}  {direction}"
        info  = f"Risk: ${risk:,.2f}"
        if pnl >= 0:
            st.success(f"{label}  ->  ${pnl:+,.2f} (+{pct:.1f}%)  |  {info}")
        else:
            st.error(f"{label}  ->  ${pnl:+,.2f} ({pct:.1f}%)  |  {info}")
    st.caption("Not financial advice.")
    st.subheader("AI analysis (Claude)")
    with st.spinner("Analyzing..."):
        analysis = ai_analysis(name, price, chg or 0, rsi or 50, macd,
                               is_bull, macd_bull, sig, conf, ANTHROPIC_KEY, active_sessions)
    st.info(analysis)
    if not ANTHROPIC_KEY:
        st.caption("Add ANTHROPIC_KEY to secrets.toml for live Claude analysis.")
with tab_btc:
    render_market_tab("BTC / USD", df_btc, btc_price, btc_chg, btc_vol,
                      btc_rsi, btc_macd, btc_sig, btc_conf, btc_emoji,
                      btc_bull, btc_mcd_bull, btc_levels, True, "#f2a900",
                      active_sessions, poly_rsi=fetch_btc_polygon_rsi(POLYGON_KEY))
with tab_nq:
    render_market_tab("NASDAQ (QQQ)", df_nasdaq, nq_price, nq_chg, nq_vol,
                      nq_rsi, nq_macd, nq_sig, nq_conf, nq_emoji,
                      nq_bull, nq_mcd_bull, nq_levels, False, "#378ADD",
                      active_sessions, snap=fetch_polygon_snapshot("QQQ", POLYGON_KEY))
with tab_gold:
    render_market_tab("Gold (GLD)", df_gold, gld_price, gld_chg, gld_vol,
                      gld_rsi, gld_macd, gld_sig, gld_conf, gld_emoji,
                      gld_bull, gld_mcd_bull, gld_levels, False, "#BA7517",
                      active_sessions, snap=fetch_polygon_snapshot("GLD", POLYGON_KEY))
with tab_sessions:
    st.subheader("Trading session guide")
    st.markdown("All times in **UTC**.")
    session_data = [
        ("Tokyo",    "00:00 to 09:00 UTC", "03:00 to 08:00 UTC", "BTC / USD",                "Low volatility. BTC consolidates or slowly trends. Avoid NASDAQ and Gold."),
        ("London",   "08:00 to 17:00 UTC", "08:00 to 10:00 UTC", "Gold (GLD), BTC / USD",    "Strong breakout potential at open. Gold reacts to EU data. BTC picks up momentum."),
        ("New York", "13:00 to 22:00 UTC", "13:30 to 16:00 UTC", "NASDAQ, Gold, BTC",         "Highest volume. NASDAQ most active. US data at 13:30 UTC spikes all markets."),
        ("Overlap",  "13:00 to 17:00 UTC", "13:00 to 15:00 UTC", "All markets",              "PRIME TIME. London + NY both active. Tightest spreads, strongest signals."),
        ("Off-hours","22:00 to 00:00 UTC", "Avoid",              "None",                      "Very low liquidity. Avoid new positions. BTC gaps on news but risk is high."),
    ]
    for sess_name, hours, best_time, best_markets, desc in session_data:
        is_active  = sess_name in active_sessions or any(sess_name in s for s in active_sessions)
        border     = "#D97706" if is_active else "#333"
        active_lbl = " NOW ACTIVE" if is_active else ""
        st.markdown(
            f'<div style="border:1.5px solid {border};border-radius:10px;padding:14px 18px;margin-bottom:10px;">'
            f'<div style="font-size:16px;font-weight:600;">{sess_name}{active_lbl}</div>'
            f'<div style="font-size:13px;color:#aaa;margin-top:4px;">Hours: {hours} | Best entry: {best_time} | Markets: {best_markets}</div>'
            f'<div style="font-size:13px;color:#ccc;margin-top:6px;">{desc}</div>'
            f'</div>', unsafe_allow_html=True)
    st.divider()
    st.subheader("Best entry times by market")
    st.markdown("""
| Market | Best Session | Ideal Entry Window (UTC) | Why |
|---|---|---|---|
| BTC / USD | London open or NY overlap | 08:00-10:00 or 13:00-16:00 | Highest momentum and volume |
| NASDAQ (QQQ) | New York | 13:30-16:00 | After US open, peak liquidity |
| Gold (GLD) | London open + NY overlap | 08:00-10:00 or 13:30-15:00 | Reacts to EU/US data releases |
| All markets | London/NY overlap | 13:00-17:00 | Tightest spreads, strongest signals |
""")
    st.divider()
    st.subheader("Current session signal quality")
    quality_map = {"Overlap": "Very High", "NY": "High", "London": "Medium-High",
                   "Tokyo": "Medium", "Off-hours": "Low"}
    for name in ["Tokyo", "London", "NY", "Overlap", "Off-hours"]:
        is_now = name in active_sessions
        marker = "  <-- YOU ARE HERE" if is_now else ""
        q      = quality_map.get(name, "Medium")
        st.markdown(f"**{name}:** Signal quality = {q}{marker}")
# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
