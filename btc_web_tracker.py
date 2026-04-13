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
        .map(_ss, subset=["Signal"]).map(_sd, subset=["Dir"])
        .format({"Entry $":"${:,.2f}","Stop $":"${:,.2f}","T1 $":"${:,.2f}","T2 $":"${:,.2f}","R:R":"1:{}","Conf %":"{}%"}),
        use_container_width=True, hide_index=True)
    st.caption(f"{len(log)} signal(s) this session.")
else:
    st.info("Signals appear here as they are detected on each refresh.")
st.divider()
st.subheader("Market detail and backtests")
tab_btc, tab_nq, tab_gold, tab_sessions, tab_alpha = st.tabs(["BTC / USD", "NASDAQ (QQQ)", "Gold (GLD)", "Trading Sessions", "⚡ Alpha Trader Lab"])
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
                tdf.style.map(_sp, subset=["PnL $"])
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
# ALPHA TRADER LAB TAB  — v2
# MT5 lots • live signals • session timing • continuous AI data collection
# ─────────────────────────────────────────────
with tab_alpha:
    st.markdown("## ⚡ Alpha Trader Lab — Live Multi-Market Engine")
    st.caption("MT5-style lot sizing • swing H/L detection • session entry timing • continuous AI data collection • Alpha Firm rules")

    # ── MT5 LOT SIZE REFERENCE (always visible) ─────────────────────────────
    with st.expander("📐 MT5 lot size guide — what to type on your broker", expanded=False):
        st.markdown("""
| Lot size | What it means | BTC value approx | QQQ value approx | GLD value approx |
|---|---|---|---|---|
| **0.01** | Micro lot — 1% of a standard | ~$840 notional | ~$49 | ~$320 |
| **0.05** | 5 micro lots | ~$4,200 | ~$245 | ~$1,600 |
| **0.10** | Mini lot | ~$8,400 | ~$490 | ~$3,200 |
| **0.20** | 2 mini lots | ~$16,800 | ~$980 | ~$6,400 |
| **0.50** | Half standard | ~$42,000 | ~$2,450 | ~$16,000 |
| **1.00** | Standard lot | ~$84,000 | ~$4,900 | ~$32,000 |

**How the lab calculates your lot:** `Risk $ ÷ Stop distance in price = raw units → converted to nearest 0.01 lot`

For BTC: 1 lot = 1 BTC. For QQQ/GLD: 1 lot = 100 shares (standard equity contract).
At **1% account risk** on $25,000 = **$250 risk per trade** — the lab sizes every position to this.
""")

    # ── SESSION STATE INIT ──────────────────────────────────────────────────
    _alpha_keys = {
        "alpha_account":       25000.0,
        "alpha_peak":          25000.0,
        "alpha_daily_start":   25000.0,
        "alpha_trades":        [],
        "alpha_open":          {},
        "alpha_signal_data":   [],
        "alpha_session_stats": {},
        "alpha_hour_stats":    {},
        "alpha_ticks":         0,
        "alpha_prices":        {"BTC": [], "NQ": [], "GOLD": []},
        "alpha_swings":        {"BTC": {"highs":[],"lows":[]}, "NQ": {"highs":[],"lows":[]}, "GOLD": {"highs":[],"lows":[]}},
        "alpha_notifications": [],
        "alpha_live_running":  False,
        "alpha_live_ticks":    0,
        "alpha_ai_log":        [],
        "alpha_equity_curve":  [25000.0],
        "alpha_last_live_fetch": 0.0,
    }
    for k, v in _alpha_keys.items():
        if k not in st.session_state:
            import copy
            st.session_state[k] = copy.deepcopy(v)

    ALPHA_ASSETS = {
        "BTC":  {
            "label": "BTC/USD", "mt5_symbol": "BTCUSD",
            "base": btc_price or 84000, "vol": 900,
            "color": "#f2a900", "is_crypto": True,
            "lot_unit": 1.0,          # 1 lot = 1 BTC
            "pip_val": 1.0,           # $1 per $1 move per lot
            "decimals": 0,
        },
        "NQ":   {
            "label": "NASDAQ (QQQ)", "mt5_symbol": "QQQ",
            "base": nq_price or 490, "vol": 5,
            "color": "#378ADD", "is_crypto": False,
            "lot_unit": 100.0,        # 1 lot = 100 shares
            "pip_val": 100.0,
            "decimals": 2,
        },
        "GOLD": {
            "label": "Gold (GLD)", "mt5_symbol": "XAUUSD",
            "base": gld_price or 3200, "vol": 14,
            "color": "#BA7517", "is_crypto": False,
            "lot_unit": 100.0,
            "pip_val": 100.0,
            "decimals": 2,
        },
    }
    ALPHA_START     = 25000.0
    ALPHA_MAX_DD    = 0.10
    ALPHA_MAX_DAILY = 0.03
    ALPHA_RISK_PCT  = 0.01     # 1% risk per trade
    SWING_N         = 5
    RR_RATIO        = 2.5

    # ── HELPERS ─────────────────────────────────────────────────────────────
    def a_dd():
        pk = st.session_state["alpha_peak"]
        ac = st.session_state["alpha_account"]
        return (pk - ac) / pk if pk > 0 else 0.0

    def a_daily():
        ds = st.session_state["alpha_daily_start"]
        ac = st.session_state["alpha_account"]
        return max(0.0, (ds - ac) / ds) if ds > 0 else 0.0

    def a_can_trade(mkey):
        return (
            a_dd() < ALPHA_MAX_DD and
            a_daily() < ALPHA_MAX_DAILY and
            mkey not in st.session_state["alpha_open"]
        )

    def detect_swings(arr, n=SWING_N):
        highs, lows = [], []
        for i in range(n, len(arr) - n):
            window = arr[i-n:i+n+1]
            if arr[i] == max(window):
                highs.append({"idx": i, "price": arr[i]})
            if arr[i] == min(window):
                lows.append({"idx": i, "price": arr[i]})
        return highs, lows

    def get_structure_signal(highs, lows, prices):
        if len(highs) < 2 or len(lows) < 2:
            return "hold", "No structure yet"
        lh, ph = highs[-1]["price"], highs[-2]["price"]
        ll, pl = lows[-1]["price"],  lows[-2]["price"]
        price  = prices[-1]
        if lh > ph and ll > pl and price > lows[-1]["price"] * 1.001:
            return "long",  "HH + HL — bullish structure confirmed"
        if lh < ph and ll < pl and price < highs[-1]["price"] * 0.999:
            return "short", "LH + LL — bearish structure confirmed"
        if lh > ph:
            return "hold", "Higher highs forming — watching for HL confirmation"
        if lh < ph:
            return "hold", "Lower highs forming — watching for LL confirmation"
        return "hold", "Choppy — no clean structure"

    def calc_mt5_lots(account, entry, stop, asset):
        risk_usd  = account * ALPHA_RISK_PCT
        stop_dist = abs(entry - stop)
        if stop_dist == 0:
            return 0.01
        # raw units needed
        raw_units = risk_usd / stop_dist
        # convert to lots
        lots = raw_units / asset["lot_unit"]
        # round to nearest 0.01
        lots = max(0.01, round(lots / 0.01) * 0.01)
        return lots

    def push_notification(msg, kind="signal"):
        st.session_state["alpha_notifications"].insert(0, {
            "time": datetime.now(ZoneInfo("UTC")).strftime("%H:%M:%S UTC"),
            "msg":  msg,
            "kind": kind,
        })
        st.session_state["alpha_notifications"] = st.session_state["alpha_notifications"][:50]

    def add_ai_log(msg):
        st.session_state["alpha_ai_log"].insert(0, {
            "time": datetime.now(ZoneInfo("UTC")).strftime("%H:%M:%S"),
            "msg":  msg,
        })
        st.session_state["alpha_ai_log"] = st.session_state["alpha_ai_log"][:100]

    def update_stats(mkey, session_name, hour_utc, outcome, pnl):
        ss = st.session_state["alpha_session_stats"]
        ss.setdefault(session_name, {}).setdefault(mkey, {"wins":0,"losses":0,"total":0,"pnl":0.0})
        hs = st.session_state["alpha_hour_stats"]
        hs.setdefault(hour_utc, {}).setdefault(mkey, {"wins":0,"losses":0,"total":0,"pnl":0.0})
        for store, key in [(ss[session_name], mkey), (hs[hour_utc], mkey)]:
            store[key]["total"] += 1
            store[key]["pnl"]   += pnl
            store[key]["wins" if outcome == "win" else "losses"] += 1

    # ── CORE TICK (simulated price + real structure logic) ───────────────────
    def alpha_tick(use_real_prices=False):
        utc_now      = datetime.now(ZoneInfo("UTC"))
        hour_utc     = utc_now.hour
        active_sess, _ = get_current_session()
        session_name   = active_sess[0] if active_sess else "Off-hours"
        account        = st.session_state["alpha_account"]
        peak           = st.session_state["alpha_peak"]
        open_trades    = st.session_state["alpha_open"]
        st.session_state["alpha_ticks"] += 1

        for mkey, asset in ALPHA_ASSETS.items():
            prices = st.session_state["alpha_prices"][mkey]

            # price generation
            if use_real_prices:
                # use last known real price seeded from live data
                last = prices[-1] if prices else asset["base"]
            else:
                last = prices[-1] if prices else asset["base"]

            drift = (np.random.random() - 0.478) * asset["vol"]
            mom   = (prices[-1] - prices[-2]) * 0.25 if len(prices) >= 2 else 0
            price = max(asset["base"] * 0.2, last + drift + mom)
            prices.append(price)
            if len(prices) > 400:
                prices.pop(0)

            highs, lows = detect_swings(prices)
            st.session_state["alpha_swings"][mkey] = {"highs": highs, "lows": lows}

            # ── close open trades ──
            if mkey in open_trades:
                tr = open_trades[mkey]
                hit_stop = (tr["dir"]=="long"  and price <= tr["stop"]) or \
                           (tr["dir"]=="short" and price >= tr["stop"])
                hit_tp   = (tr["dir"]=="long"  and price >= tr["tp"])   or \
                           (tr["dir"]=="short" and price <= tr["tp"])
                if hit_stop or hit_tp:
                    pnl = (price - tr["entry"]) * tr["lots"] * asset["lot_unit"] \
                          if tr["dir"] == "long" \
                          else (tr["entry"] - price) * tr["lots"] * asset["lot_unit"]
                    account      = max(0, account + pnl)
                    outcome      = "win" if pnl > 0 else "loss"
                    tr["exit"]   = price
                    tr["pnl"]    = round(pnl, 2)
                    tr["outcome"]= outcome
                    tr["closed_at"] = utc_now.strftime("%H:%M:%S")
                    tr["reason"] = "TP hit" if hit_tp else "SL hit"
                    st.session_state["alpha_trades"].append(dict(tr))
                    update_stats(mkey, tr["entry_session"], tr["entry_hour"], outcome, pnl)
                    st.session_state["alpha_equity_curve"].append(round(account, 2))
                    emoji = "✅" if outcome=="win" else "❌"
                    push_notification(
                        f"{emoji} {asset['label']} {tr['dir'].upper()} closed — {tr['reason']} | "
                        f"P&L: {'+'if pnl>=0 else ''}{pnl:.2f} | Lots: {tr['lots']:.2f} | "
                        f"Entry {tr['entry']:.{asset['decimals']}f} → Exit {price:.{asset['decimals']}f}",
                        "close"
                    )
                    add_ai_log(
                        f"{asset['label']} {tr['dir'].upper()} {outcome.upper()} — "
                        f"{tr['reason']} at {price:.{asset['decimals']}f} | "
                        f"P&L ${pnl:+.2f} | Session: {tr['entry_session']} | "
                        f"Lots: {tr['lots']:.2f} (MT5: type '{tr['lots']:.2f}' in volume field)"
                    )
                    del open_trades[mkey]

            # ── open new trades ──
            if a_can_trade(mkey) and len(highs) >= 2 and len(lows) >= 2:
                sig, reason = get_structure_signal(highs, lows, prices)
                if sig in ("long", "short"):
                    if sig == "long":
                        stop = lows[-1]["price"] * 0.997
                        tp   = price + (price - stop) * RR_RATIO
                    else:
                        stop = highs[-1]["price"] * 1.003
                        tp   = price - (stop - price) * RR_RATIO
                    lots      = calc_mt5_lots(account, price, stop, asset)
                    risk_usd  = abs(price - stop) * lots * asset["lot_unit"]
                    reward_usd= risk_usd * RR_RATIO
                    open_trades[mkey] = {
                        "market":        mkey,
                        "label":         asset["label"],
                        "mt5_symbol":    asset["mt5_symbol"],
                        "dir":           sig,
                        "entry":         round(price, asset["decimals"]),
                        "stop":          round(stop,  asset["decimals"]),
                        "tp":            round(tp,    asset["decimals"]),
                        "lots":          lots,
                        "risk_usd":      round(risk_usd, 2),
                        "reward_usd":    round(reward_usd, 2),
                        "entry_session": session_name,
                        "entry_hour":    hour_utc,
                        "entry_time":    utc_now.strftime("%H:%M:%S"),
                        "reason":        reason,
                    }
                    st.session_state["alpha_signal_data"].append({
                        "ts": utc_now.strftime("%H:%M:%S"),
                        "market": mkey, "signal": sig, "price": price,
                        "session": session_name, "hour": hour_utc,
                    })
                    dir_arrow = "🟢 LONG" if sig=="long" else "🔴 SHORT"
                    push_notification(
                        f"🔔 SIGNAL: {asset['label']} {dir_arrow} | "
                        f"Entry: {price:.{asset['decimals']}f} | "
                        f"Stop: {stop:.{asset['decimals']}f} | TP: {tp:.{asset['decimals']}f} | "
                        f"Lots: {lots:.2f} | Risk: ${risk_usd:.0f} | {reason} | Session: {session_name}",
                        "signal"
                    )
                    add_ai_log(
                        f"NEW SIGNAL — {asset['label']} {sig.upper()} @ {price:.{asset['decimals']}f} | "
                        f"MT5 symbol: {asset['mt5_symbol']} | Volume: {lots:.2f} lots | "
                        f"SL: {stop:.{asset['decimals']}f} | TP: {tp:.{asset['decimals']}f} | "
                        f"Risk $: {risk_usd:.2f} | Reward $: {reward_usd:.2f} | "
                        f"Structure: {reason} | {session_name} session | UTC {hour_utc:02d}:xx"
                    )

        st.session_state["alpha_account"] = account
        st.session_state["alpha_peak"]    = max(peak, account)
        st.session_state["alpha_open"]    = open_trades

    # ── LIVE SESSION SIGNAL CHECKER (uses real Polygon/CG prices) ────────────
    def live_signal_check():
        """Check real live prices for signals — runs on each page refresh."""
        utc_now  = datetime.now(ZoneInfo("UTC"))
        hour_utc = utc_now.hour
        active_sess, _ = get_current_session()
        session_name   = active_sess[0] if active_sess else "Off-hours"
        found = []

        # BTC — use real CoinGecko price seeded into sim prices
        if btc_price:
            prices = st.session_state["alpha_prices"]["BTC"]
            if not prices or abs(prices[-1] - btc_price) / btc_price > 0.005:
                prices.append(btc_price)
                if len(prices) > 400: prices.pop(0)
            highs, lows = detect_swings(prices)
            if len(highs) >= 2 and len(lows) >= 2:
                sig, reason = get_structure_signal(highs, lows, prices)
                if sig != "hold":
                    found.append(("BTC", sig, btc_price, reason, session_name, hour_utc))

        # NQ / GOLD — use real Polygon close
        for mkey, price in [("NQ", nq_price), ("GOLD", gld_price)]:
            if not price:
                continue
            prices = st.session_state["alpha_prices"][mkey]
            if not prices or abs(prices[-1] - price) / price > 0.003:
                prices.append(price)
                if len(prices) > 400: prices.pop(0)
            highs, lows = detect_swings(prices)
            if len(highs) >= 2 and len(lows) >= 2:
                sig, reason = get_structure_signal(highs, lows, prices)
                if sig != "hold":
                    found.append((mkey, sig, price, reason, session_name, hour_utc))

        for mkey, sig, price, reason, sess, hour in found:
            asset = ALPHA_ASSETS[mkey]
            if a_can_trade(mkey):
                account = st.session_state["alpha_account"]
                if sig == "long":
                    highs_l = st.session_state["alpha_swings"][mkey]["highs"]
                    lows_l  = st.session_state["alpha_swings"][mkey]["lows"]
                    stop = (lows_l[-1]["price"] * 0.997) if lows_l else price * 0.975
                    tp   = price + (price - stop) * RR_RATIO
                else:
                    highs_l = st.session_state["alpha_swings"][mkey]["highs"]
                    lows_l  = st.session_state["alpha_swings"][mkey]["lows"]
                    stop = (highs_l[-1]["price"] * 1.003) if highs_l else price * 1.025
                    tp   = price - (stop - price) * RR_RATIO
                lots     = calc_mt5_lots(account, price, stop, asset)
                risk_usd = abs(price - stop) * lots * asset["lot_unit"]
                rwd_usd  = risk_usd * RR_RATIO
                open_trades = st.session_state["alpha_open"]
                open_trades[mkey] = {
                    "market": mkey, "label": asset["label"],
                    "mt5_symbol": asset["mt5_symbol"],
                    "dir": sig,
                    "entry": round(price, asset["decimals"]),
                    "stop":  round(stop,  asset["decimals"]),
                    "tp":    round(tp,    asset["decimals"]),
                    "lots":  lots, "risk_usd": round(risk_usd,2),
                    "reward_usd": round(rwd_usd,2),
                    "entry_session": sess, "entry_hour": hour,
                    "entry_time": utc_now.strftime("%H:%M:%S"),
                    "reason": reason,
                }
                push_notification(
                    f"🔔 LIVE SIGNAL: {asset['label']} {'🟢 LONG' if sig=='long' else '🔴 SHORT'} | "
                    f"Entry: {price:.{asset['decimals']}f} | SL: {stop:.{asset['decimals']}f} | "
                    f"TP: {tp:.{asset['decimals']}f} | Lots: {lots:.2f} | Risk: ${risk_usd:.0f} | {sess}",
                    "live"
                )
                add_ai_log(
                    f"LIVE — {asset['label']} {sig.upper()} @ {price:.{asset['decimals']}f} | "
                    f"MT5: symbol={asset['mt5_symbol']} volume={lots:.2f} SL={stop:.{asset['decimals']}f} TP={tp:.{asset['decimals']}f} | "
                    f"Risk ${risk_usd:.2f} → Reward ${rwd_usd:.2f} | {reason}"
                )
        return found

    # run live check on every page load
    live_found = live_signal_check()
    st.session_state["alpha_last_live_fetch"] = time.time()

    # ── SESSION ENTRY TIMING GUIDE ───────────────────────────────────────────
    utc_now_disp = datetime.now(ZoneInfo("UTC"))
    cur_hour     = utc_now_disp.hour + utc_now_disp.minute / 60
    active_sess_now, _ = get_current_session()

    SESSION_WINDOWS = {
        "Tokyo":   {"open": (0,9),   "best": (3,8),   "markets":["BTC"],           "quality":"Medium",   "color":"#7C3AED"},
        "London":  {"open": (8,17),  "best": (8,10),  "markets":["BTC","GOLD"],    "quality":"High",     "color":"#2563EB"},
        "NY":      {"open": (13,22), "best": (13.5,16),"markets":["NQ","GOLD","BTC"],"quality":"High",   "color":"#059669"},
        "Overlap": {"open": (13,17), "best": (13,15),  "markets":["BTC","NQ","GOLD"],"quality":"Peak",   "color":"#D97706"},
    }

    st.markdown("### 🕐 Session entry timing — right now")
    sess_cols = st.columns(4)
    for ci, (sname, sw) in enumerate(SESSION_WINDOWS.items()):
        with sess_cols[ci]:
            in_best  = sw["best"][0] <= cur_hour < sw["best"][1]
            in_open  = sw["open"][0] <= cur_hour < sw["open"][1]
            bg       = sw["color"] if in_best else ("#1a1a2e" if in_open else "#111")
            badge    = "🟢 BEST TIME NOW" if in_best else ("🟡 SESSION OPEN" if in_open else "⚫ CLOSED")
            best_s   = f"{int(sw['best'][0]):02d}:{int((sw['best'][0]%1)*60):02d}"
            best_e   = f"{int(sw['best'][1]):02d}:{int((sw['best'][1]%1)*60):02d}"
            st.markdown(
                f'<div style="border:1.5px solid {sw["color"]};border-radius:10px;padding:12px;text-align:center">'
                f'<div style="font-size:14px;font-weight:600;color:{sw["color"]}">{sname}</div>'
                f'<div style="font-size:11px;color:#aaa;margin:4px 0">{badge}</div>'
                f'<div style="font-size:11px;color:#888">Best: {best_s}–{best_e} UTC</div>'
                f'<div style="font-size:11px;color:#888">Quality: {sw["quality"]}</div>'
                f'<div style="font-size:10px;color:#555;margin-top:4px">{" • ".join(sw["markets"])}</div>'
                f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── ACCOUNT METRICS ─────────────────────────────────────────────────────
    account_now = st.session_state["alpha_account"]
    profit_now  = account_now - ALPHA_START
    dd_pct      = a_dd() * 100
    dl_pct      = a_daily() * 100
    all_trades  = st.session_state["alpha_trades"]
    wins_all    = [t for t in all_trades if t.get("outcome")=="win"]
    losses_all  = [t for t in all_trades if t.get("outcome")=="loss"]
    win_rate    = len(wins_all)/len(all_trades)*100 if all_trades else 0.0

    mc = st.columns(7)
    mc[0].metric("Balance",         f"${account_now:,.2f}", delta=f"{profit_now:+.2f}")
    mc[1].metric("Net P&L",         f"${profit_now:+,.2f}")
    mc[2].metric("Your 80% split",  f"${max(0,profit_now)*0.8:,.2f}")
    mc[3].metric("Smart DD",        f"{dd_pct:.1f}%",  delta=f"{10-dd_pct:.1f}% left", delta_color="off")
    mc[4].metric("Daily loss",      f"{dl_pct:.1f}%",  delta=f"{3-dl_pct:.1f}% left",  delta_color="off")
    mc[5].metric("Win rate",        f"{win_rate:.0f}%")
    mc[6].metric("Total trades",    len(all_trades))

    st.progress(min(1.0, dd_pct/10),  text=f"Smart drawdown  {dd_pct:.1f}% of 10% max")
    st.progress(min(1.0, dl_pct/3),   text=f"Daily loss       {dl_pct:.1f}% of 3% max")

    if dd_pct >= 10 or dl_pct >= 3:
        st.error("🛑 Alpha Firm risk limits breached — no new trades. Reset account or wait for next day.")

    st.divider()

    # ── LIVE OPEN POSITIONS + MT5 TICKET DETAILS ─────────────────────────────
    st.markdown("### 📋 Open positions — MT5 ticket details")
    open_trades = st.session_state["alpha_open"]
    if not open_trades:
        st.info("No open positions. Run ticks or wait for live signals to populate.")
    else:
        for mkey, tr in open_trades.items():
            asset     = ALPHA_ASSETS[mkey]
            cur_p     = st.session_state["alpha_prices"][mkey][-1] if st.session_state["alpha_prices"][mkey] else tr["entry"]
            unreal    = (cur_p - tr["entry"]) * tr["lots"] * asset["lot_unit"] \
                        if tr["dir"]=="long" \
                        else (tr["entry"] - cur_p) * tr["lots"] * asset["lot_unit"]
            ur_color  = "#22c55e" if unreal >= 0 else "#ef4444"
            dir_color = "#22c55e" if tr["dir"]=="long" else "#ef4444"
            st.markdown(
                f'<div style="border:2px solid {dir_color};border-radius:10px;padding:14px 18px;margin-bottom:10px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
                f'  <span style="font-size:15px;font-weight:600;color:{asset["color"]}">{asset["label"]}</span>'
                f'  <span style="background:{dir_color};color:#fff;border-radius:4px;padding:3px 10px;font-size:12px;font-weight:600">'
                f'    {"LONG ▲" if tr["dir"]=="long" else "SHORT ▼"}</span>'
                f'</div>'
                f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;font-size:12px">'
                f'  <div><span style="color:#aaa">MT5 Symbol</span><br><b>{tr["mt5_symbol"]}</b></div>'
                f'  <div><span style="color:#aaa">Volume (lots)</span><br>'
                f'    <b style="color:#facc15;font-size:15px">{tr["lots"]:.2f}</b></div>'
                f'  <div><span style="color:#aaa">Entry price</span><br><b>{tr["entry"]:.{asset["decimals"]}f}</b></div>'
                f'  <div><span style="color:#aaa">Current price</span><br><b>{cur_p:.{asset["decimals"]}f}</b></div>'
                f'  <div><span style="color:#aaa">Stop loss (SL)</span><br>'
                f'    <b style="color:#ef4444">{tr["stop"]:.{asset["decimals"]}f}</b></div>'
                f'  <div><span style="color:#aaa">Take profit (TP)</span><br>'
                f'    <b style="color:#22c55e">{tr["tp"]:.{asset["decimals"]}f}</b></div>'
                f'  <div><span style="color:#aaa">Risk $</span><br><b>${tr["risk_usd"]:.2f}</b></div>'
                f'  <div><span style="color:#aaa">Reward $</span><br><b>${tr["reward_usd"]:.2f}</b></div>'
                f'</div>'
                f'<div style="margin-top:10px;padding-top:8px;border-top:0.5px solid #333;font-size:12px">'
                f'  Unrealized P&L: <b style="color:{ur_color}">${unreal:+.2f}</b> &nbsp;|&nbsp; '
                f'  R:R 1:{RR_RATIO} &nbsp;|&nbsp; {tr["reason"]} &nbsp;|&nbsp; '
                f'  Opened: {tr["entry_time"]} {tr["entry_session"]}'
                f'</div>'
                f'<div style="margin-top:6px;font-size:11px;color:#555">'
                f'  MT5 order: New Order → Symbol: <b>{tr["mt5_symbol"]}</b> | '
                f'  Type: {"Buy" if tr["dir"]=="long" else "Sell"} | Volume: <b>{tr["lots"]:.2f}</b> | '
                f'  SL: {tr["stop"]:.{asset["decimals"]}f} | TP: {tr["tp"]:.{asset["decimals"]}f}'
                f'</div>'
                f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── NOTIFICATIONS FEED ──────────────────────────────────────────────────
    st.markdown("### 🔔 Live signal notifications")
    notifs = st.session_state["alpha_notifications"]
    if notifs:
        for n in notifs[:20]:
            kind_color = {"signal":"#2563EB","live":"#7C3AED","close":"#059669"}.get(n["kind"],"#555")
            st.markdown(
                f'<div style="border-left:3px solid {kind_color};padding:6px 12px;margin-bottom:4px;'
                f'background:rgba(0,0,0,0.15);border-radius:0 6px 6px 0;font-size:12px">'
                f'<span style="color:#888;font-size:10px">{n["time"]}</span>  {n["msg"]}</div>',
                unsafe_allow_html=True)
    else:
        st.info("No notifications yet. Run ticks or wait for live signal detection.")

    st.divider()

    # ── CONTROLS ────────────────────────────────────────────────────────────
    st.markdown("### ⚙️ Simulation controls")
    ctrl_c = st.columns([1,1,1,1,1,2])
    with ctrl_c[0]:
        if st.button("▶ 100 ticks", key="a100"):
            for _ in range(100):  alpha_tick()
            st.rerun()
    with ctrl_c[1]:
        if st.button("▶▶ 500", key="a500"):
            for _ in range(500):  alpha_tick()
            st.rerun()
    with ctrl_c[2]:
        if st.button("▶▶▶ 2000", key="a2000"):
            for _ in range(2000): alpha_tick()
            st.rerun()
    with ctrl_c[3]:
        if st.button("▶▶▶▶ 5000", key="a5000"):
            for _ in range(5000): alpha_tick()
            st.rerun()
    with ctrl_c[4]:
        if st.button("🔄 Reset", key="ares"):
            import copy
            for k, v in _alpha_keys.items():
                st.session_state[k] = copy.deepcopy(v)
            st.session_state["alpha_account"]     = 25000.0
            st.session_state["alpha_peak"]        = 25000.0
            st.session_state["alpha_daily_start"] = 25000.0
            st.session_state["alpha_equity_curve"]= [25000.0]
            st.rerun()
    with ctrl_c[5]:
        ticks = st.session_state["alpha_ticks"]
        st.caption(f"Ticks: **{ticks:,}** | Closed trades: **{len(all_trades)}** | Open: **{len(open_trades)}** | Signals fired: **{len(st.session_state['alpha_signal_data'])}**")

    st.divider()

    # ── LIVE PRICE ACTION CHARTS ─────────────────────────────────────────────
    st.markdown("### 📈 Price action — swing highs & lows (all 3 markets)")
    chart_cols = st.columns(3)
    for cidx, (mkey, asset) in enumerate(ALPHA_ASSETS.items()):
        with chart_cols[cidx]:
            prices = st.session_state["alpha_prices"][mkey]
            swings = st.session_state["alpha_swings"][mkey]
            highs  = swings["highs"]
            lows   = swings["lows"]
            open_tr= open_trades.get(mkey)

            if len(prices) < 2:
                st.info(f"{asset['label']}: run ticks")
                continue

            disp = prices[-120:]
            offset = max(0, len(prices)-120)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(len(disp))), y=disp,
                line=dict(color=asset["color"], width=1.5),
                name="Price", showlegend=False))

            h_x = [h["idx"]-offset for h in highs if h["idx"] >= offset and h["idx"]-offset < len(disp)]
            h_y = [h["price"] for h in highs if h["idx"] >= offset and h["idx"]-offset < len(disp)]
            l_x = [l["idx"]-offset for l in lows  if l["idx"] >= offset and l["idx"]-offset < len(disp)]
            l_y = [l["price"] for l in lows  if l["idx"] >= offset and l["idx"]-offset < len(disp)]

            if h_x: fig.add_trace(go.Scatter(x=h_x, y=h_y, mode="markers",
                marker=dict(symbol="triangle-down", color="#ef4444", size=9),
                name="H", showlegend=False))
            if l_x: fig.add_trace(go.Scatter(x=l_x, y=l_y, mode="markers",
                marker=dict(symbol="triangle-up", color="#22c55e", size=9),
                name="L", showlegend=False))

            if open_tr:
                fig.add_hline(y=open_tr["entry"], line=dict(color="#fff",    width=1, dash="dot"),  annotation_text="Entry")
                fig.add_hline(y=open_tr["stop"],  line=dict(color="#ef4444", width=1, dash="dash"), annotation_text=f"SL {open_tr['stop']:.{asset['decimals']}f}")
                fig.add_hline(y=open_tr["tp"],    line=dict(color="#22c55e", width=1, dash="dash"), annotation_text=f"TP {open_tr['tp']:.{asset['decimals']}f}")

            fig.update_layout(
                height=220, template="plotly_dark",
                title=dict(text=asset["label"], font=dict(size=12)),
                margin=dict(l=0,r=0,t=28,b=0),
                xaxis=dict(visible=False),
                yaxis=dict(tickfont=dict(size=9)),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            if prices:
                lp = prices[-1]
                fmt = f"${lp:,.0f}" if asset["is_crypto"] else f"${lp:,.2f}"
                status = ""
                if open_tr:
                    unreal = (lp - open_tr["entry"]) * open_tr["lots"] * asset["lot_unit"] \
                             if open_tr["dir"]=="long" \
                             else (open_tr["entry"] - lp) * open_tr["lots"] * asset["lot_unit"]
                    uc = "#22c55e" if unreal>=0 else "#ef4444"
                    status = f' | <span style="color:{uc}">${unreal:+.2f} unrealized</span>'
                sig_now, reason_now = get_structure_signal(highs, lows, prices) if len(highs)>=2 and len(lows)>=2 else ("hold","")
                sig_col = "#22c55e" if sig_now=="long" else "#ef4444" if sig_now=="short" else "#888"
                st.markdown(
                    f'<div style="font-size:11px;text-align:center;margin-top:-8px">'
                    f'<span style="color:{asset["color"]}">{fmt}</span>'
                    f' | <span style="color:{sig_col}">{sig_now.upper()}</span>{status}'
                    f'</div>', unsafe_allow_html=True)

    st.divider()

    # ── AI CONTINUOUS DATA COLLECTION LOG ───────────────────────────────────
    st.markdown("### 🤖 AI continuous data collection — live trade log")
    st.caption("Every signal, entry, exit and decision is logged here in real time. This is the AI's running memory of what it's seeing.")
    ai_log = st.session_state["alpha_ai_log"]
    if ai_log:
        for entry in ai_log[:30]:
            st.markdown(
                f'<div style="border-left:2px solid #7C3AED;padding:5px 10px;margin-bottom:3px;'
                f'font-size:11px;color:var(--color-text-secondary);background:rgba(124,58,237,0.04);border-radius:0 4px 4px 0">'
                f'<span style="color:#7C3AED;font-size:10px">{entry["time"]}</span>  {entry["msg"]}'
                f'</div>', unsafe_allow_html=True)
    else:
        st.info("AI log populates as trades are detected and closed.")

    st.divider()

    # ── DATA INTELLIGENCE ───────────────────────────────────────────────────
    st.markdown("### 📊 Data intelligence — best time to trade")
    session_stats = st.session_state["alpha_session_stats"]
    hour_stats    = st.session_state["alpha_hour_stats"]
    signal_data   = st.session_state["alpha_signal_data"]

    if not signal_data:
        st.info("Run ticks to collect data. The engine records every signal by session and UTC hour, then maps where win rate is highest.")
    else:
        # heatmap
        st.markdown("#### Session × market win rate")
        sess_order = ["Tokyo","London","NY","Overlap","Off-hours"]
        mkt_order  = ["BTC","NQ","GOLD"]
        heat_z, heat_text = [], []
        for sess in sess_order:
            row_z, row_t = [], []
            for mkt in mkt_order:
                s = session_stats.get(sess,{}).get(mkt,{})
                tot = s.get("total",0)
                wr  = s.get("wins",0)/tot*100 if tot>0 else None
                row_z.append(wr)
                row_t.append(f"{wr:.0f}%\n({tot}t)" if wr is not None else "—")
            heat_z.append(row_z)
            heat_text.append(row_t)

        fig_heat = go.Figure(data=go.Heatmap(
            z=heat_z,
            x=[ALPHA_ASSETS[m]["label"] for m in mkt_order],
            y=sess_order,
            colorscale=[[0,"#7f1d1d"],[0.5,"#854F0B"],[1,"#166534"]],
            zmin=0, zmax=100,
            text=heat_text, texttemplate="%{text}",
            textfont=dict(size=12), showscale=True,
            colorbar=dict(title="Win %", tickfont=dict(size=10)),
        ))
        fig_heat.update_layout(
            height=260, template="plotly_dark",
            margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # hourly bar
        if hour_stats:
            st.markdown("#### Win rate by UTC hour — all markets combined")
            hour_rows = []
            for h in sorted(hour_stats.keys()):
                tot_h  = sum(v.get("total",0) for v in hour_stats[h].values())
                wins_h = sum(v.get("wins", 0) for v in hour_stats[h].values())
                pnl_h  = sum(v.get("pnl",  0) for v in hour_stats[h].values())
                wr_h   = (wins_h/tot_h*100) if tot_h>0 else 0
                hour_rows.append({"hour": f"{h:02d}:00","win_rate":wr_h,"trades":tot_h,"pnl":pnl_h})
            df_h = pd.DataFrame(hour_rows)
            bar_col = ["#22c55e" if w>=55 else "#BA7517" if w>=45 else "#ef4444" for w in df_h["win_rate"]]
            fig_h = go.Figure()
            fig_h.add_trace(go.Bar(
                x=df_h["hour"], y=df_h["win_rate"],
                marker_color=bar_col,
                text=[f"{w:.0f}%\n({t}t)" for w,t in zip(df_h["win_rate"],df_h["trades"])],
                textposition="outside", textfont=dict(size=9),
            ))
            fig_h.add_hline(y=50, line=dict(color="#888",width=1,dash="dot"), annotation_text="50% breakeven")
            fig_h.update_layout(
                height=260, template="plotly_dark",
                yaxis=dict(range=[0,110], title="Win rate %"),
                xaxis=dict(title="UTC hour"),
                margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_h, use_container_width=True)

        # per-market verdict
        st.markdown("#### Best time to trade — verdict cards")
        v_cols = st.columns(3)
        for ci, mkey in enumerate(mkt_order):
            with v_cols[ci]:
                asset  = ALPHA_ASSETS[mkey]
                bs, bswr = "—", 0.0
                for sess, mkts in session_stats.items():
                    if mkey in mkts and mkts[mkey].get("total",0)>=3:
                        wr = mkts[mkey]["wins"]/mkts[mkey]["total"]*100
                        if wr > bswr: bswr=wr; bs=sess
                bh, bhwr = "—", 0.0
                for h, mkts in hour_stats.items():
                    if mkey in mkts and mkts[mkey].get("total",0)>=3:
                        wr = mkts[mkey]["wins"]/mkts[mkey]["total"]*100
                        if wr > bhwr: bhwr=wr; bh=f"{h:02d}:00 UTC"
                tot_m  = sum(v.get("total",0) for s in session_stats.values() for k,v in s.items() if k==mkey)
                wins_m = sum(v.get("wins", 0) for s in session_stats.values() for k,v in s.items() if k==mkey)
                pnl_m  = sum(v.get("pnl",  0) for s in session_stats.values() for k,v in s.items() if k==mkey)
                owr    = (wins_m/tot_m*100) if tot_m>0 else 0
                wr_col = "#22c55e" if owr>=50 else "#ef4444"
                pnl_col= "#22c55e" if pnl_m>=0 else "#ef4444"
                st.markdown(
                    f'<div style="border:1.5px solid {asset["color"]};border-radius:10px;padding:14px">'
                    f'<div style="font-size:13px;font-weight:600;color:{asset["color"]};margin-bottom:8px">{asset["label"]}</div>'
                    f'<div style="font-size:12px;color:#aaa;margin-bottom:3px">Best session: <b style="color:#fff">{bs}</b> ({bswr:.0f}% WR)</div>'
                    f'<div style="font-size:12px;color:#aaa;margin-bottom:3px">Best hour UTC: <b style="color:#fff">{bh}</b> ({bhwr:.0f}% WR)</div>'
                    f'<div style="font-size:12px;color:#aaa;margin-bottom:3px">Overall WR: <b style="color:{wr_col}">{owr:.0f}%</b></div>'
                    f'<div style="font-size:12px;color:#aaa;margin-bottom:3px">Trades: {tot_m}</div>'
                    f'<div style="font-size:12px;color:#aaa">Net P&L: <b style="color:{pnl_col}">${pnl_m:+,.2f}</b></div>'
                    f'</div>', unsafe_allow_html=True)

        st.divider()

        # equity curve
        st.markdown("#### Equity curve")
        eq = st.session_state["alpha_equity_curve"]
        if len(eq) > 1:
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(
                y=eq, mode="lines",
                line=dict(color="#22c55e" if eq[-1]>=eq[0] else "#ef4444", width=2),
                fill="tozeroy", fillcolor="rgba(34,197,94,0.07)" if eq[-1]>=eq[0] else "rgba(239,68,68,0.07)",
            ))
            fig_eq.add_hline(y=ALPHA_START, line=dict(color="#888",width=1,dash="dot"), annotation_text="$25k start")
            fig_eq.update_layout(
                height=220, template="plotly_dark",
                yaxis=dict(title="Account $"),
                margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_eq, use_container_width=True)

        st.divider()

        # full trade log
        st.markdown("#### Full trade log")
        if all_trades:
            df_tl = pd.DataFrame(all_trades)
            show_cols = [c for c in ["entry_time","label","dir","lots","entry","exit","stop","tp","pnl","outcome","reason","entry_session","entry_hour"] if c in df_tl.columns]
            rmap = {
                "entry_time":"Time","label":"Market","dir":"Dir","lots":"Lots",
                "entry":"Entry","exit":"Exit","stop":"SL","tp":"TP","pnl":"P&L",
                "outcome":"Result","reason":"Reason","entry_session":"Session","entry_hour":"Hr UTC"
            }
            def _cr(v): return "color:#22c55e;font-weight:600" if v=="win" else "color:#ef4444;font-weight:600"
            def _cp(v): return "color:#22c55e" if v>0 else "color:#ef4444"
            disp = df_tl[show_cols].rename(columns=rmap)
            sty  = disp.style
            if "Result" in disp.columns: sty = sty.map(_cr, subset=["Result"])
            if "P&L"    in disp.columns: sty = sty.map(_cp, subset=["P&L"])
            num_cols = {c: "${:,.2f}" for c in ["Entry","Exit","SL","TP","P&L"] if c in disp.columns}
            if "Lots" in disp.columns: num_cols["Lots"] = "{:.2f}"
            if num_cols: sty = sty.format(num_cols)
            st.dataframe(sty, use_container_width=True, hide_index=True)
        else:
            st.info("No closed trades yet.")

# ─────────────────────────────────────────────
# AUTO REFRESH
# ─────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.cache_data.clear()
    st.rerun()
