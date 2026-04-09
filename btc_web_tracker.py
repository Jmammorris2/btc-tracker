import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Multi-Market Trader", layout="wide")

# ─────────────────────────────────────────────
# STARTUP: API KEY GATE
# Keys are loaded from Streamlit secrets if present, otherwise user enters them.
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
    st.info("Enter your API keys to get started. They are only stored for this session unless you add them to `.streamlit/secrets.toml`.")
    with st.form("key_form"):
        pk = st.text_input("Polygon.io API Key", type="password", help="Get a free key at polygon.io")
        ak = st.text_input("Anthropic API Key (optional — for AI analysis)", type="password", help="Get a key at console.anthropic.com")
        submitted = st.form_submit_button("Start App")
        if submitted:
            if not pk:
                st.error("Polygon.io key is required.")
            else:
                st.session_state["POLYGON_KEY"] = pk
                st.session_state["ANTHROPIC_KEY"] = ak
                st.rerun()
    st.stop()

# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

st.title("Multi-Market Trader — BTC · NASDAQ · Gold")

# ─────────────────────────────────────────────
# DATA FETCHERS
# ─────────────────────────────────────────────

@st.cache_data(ttl=30)
def fetch_btc_price():
    try:
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
        )
        d = requests.get(url, timeout=10).json()
        return (
            d["bitcoin"]["usd"],
            d["bitcoin"].get("usd_24h_change", 0),
            d["bitcoin"].get("usd_24h_vol", 0),
        )
    except Exception as e:
        st.warning(f"BTC price error: {e}")
        return None, None, None


@st.cache_data(ttl=120)
def fetch_btc_chart():
    try:
        url = (
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            "?vs_currency=usd&days=30&interval=hourly"
        )
        d = requests.get(url, timeout=20).json()
        df = pd.DataFrame(d["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df.set_index("timestamp")
    except Exception as e:
        st.warning(f"BTC chart error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_polygon_stock(ticker: str, _key: str):
    """Fetch daily OHLCV for a stock/ETF via Polygon.io."""
    try:
        to_date = datetime.today().strftime("%Y-%m-%d")
        from_date = (datetime.today() - timedelta(days=60)).strftime("%Y-%m-%d")
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
            f"{from_date}/{to_date}?adjusted=true&sort=asc&limit=60&apiKey={_key}"
        )
        d = requests.get(url, timeout=15).json()
        if "results" not in d or len(d["results"]) < 2:
            st.warning(f"No Polygon data for {ticker}. Check your API key or plan.")
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
    """Real-time snapshot from Polygon.io."""
    try:
        url = (
            f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
            f"/{ticker}?apiKey={_key}"
        )
        return requests.get(url, timeout=10).json().get("ticker", {})
    except Exception as e:
        st.warning(f"Polygon snapshot error: {e}")
        return {}


@st.cache_data(ttl=60)
def fetch_btc_polygon_rsi(_key: str):
    """Polygon crypto RSI for BTC."""
    try:
        url = (
            f"https://api.polygon.io/v1/indicators/rsi/X:BTCUSD"
            f"?timespan=hour&window=14&series_type=close&order=desc&limit=1&apiKey={_key}"
        )
        d = requests.get(url, timeout=10).json()
        vals = d.get("results", {}).get("values", [])
        return vals[0]["value"] if vals else None
    except Exception as e:
        st.warning(f"Polygon RSI error: {e}")
        return None


# ─────────────────────────────────────────────
# POLYMARKET CROWD DATA
# ─────────────────────────────────────────────

@st.cache_data(ttl=120)
def fetch_polymarket_btc():
    """
    Fetch Polymarket crowd odds for BTC-related markets.
    Uses the public CLOB API — no API key required.
    Returns a list of dicts: {question, yes_pct, no_pct, volume}
    """
    try:
        # Search for active BTC markets
        url = "https://clob.polymarket.com/markets?active=true&closed=false&limit=20&keyword=bitcoin"
        resp = requests.get(url, timeout=10).json()
        markets = resp.get("data", [])
        results = []
        for m in markets[:5]:  # cap at 5 to keep UI clean
            tokens = m.get("tokens", [])
            yes_token = next((t for t in tokens if t.get("outcome", "").upper() == "YES"), None)
            no_token  = next((t for t in tokens if t.get("outcome", "").upper() == "NO"), None)
            if yes_token and no_token:
                yes_price = float(yes_token.get("price", 0)) * 100
                no_price  = float(no_token.get("price", 0)) * 100
                results.append({
                    "question": m.get("question", "Unknown"),
                    "yes_pct": round(yes_price, 1),
                    "no_pct":  round(no_price, 1),
                    "volume":  m.get("volume", 0),
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
    # MACD
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]        = exp1 - exp2
    df["signal_line"] = df["macd"].ewm(span=9, adjust=False).mean()
    # RSI (guard against zero loss)
    delta = df["close"].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 1e-10)
    df["rsi"] = 100 - (100 / (1 + gain / loss))
    # Signal
    bull_ma   = df["ma8"] > df["ma21"]
    bull_macd = df["macd"] > df["signal_line"]
    df["signal"] = np.where(
        bull_ma & bull_macd & df["rsi"].between(45, 72), "STRONG BUY",
        np.where(bull_ma & (df["rsi"] < 68),             "BUY",
        np.where(~bull_ma & (df["rsi"] > 32),            "SELL",
        np.where(df["rsi"] < 30,                         "OVERSOLD",
        np.where(df["rsi"] > 70,                         "OVERBOUGHT", "HOLD")))))
    return df


def get_signal_meta(signal: str, rsi: float, is_bull: bool, macd_bull: bool):
    if signal == "STRONG BUY":
        conf  = min(94, round(62 + (rsi - 45) * 0.4 + (8 if is_bull else 0)))
        color, emoji = "green", "🟢"
    elif signal == "BUY":
        conf  = min(88, round(55 + (8 if is_bull else 0) + (7 if macd_bull else 0)))
        color, emoji = "green", "🟢"
    elif signal == "SELL":
        conf  = min(88, round(55 + (8 if not is_bull else 0) + (7 if not macd_bull else 0)))
        color, emoji = "red", "🔴"
    elif signal == "OVERSOLD":
        conf  = min(90, round(62 + (30 - rsi)))
        color, emoji = "green", "🟡"
    elif signal == "OVERBOUGHT":
        conf  = min(90, round(62 + (rsi - 70)))
        color, emoji = "red", "🔴"
    else:
        conf, color, emoji = 50, "gray", "🟡"
    return max(42, conf), color, emoji


def get_market_state(df: pd.DataFrame):
    """Extract the latest indicator values from a computed dataframe."""
    if df.empty:
        return None, None, 0, "HOLD", False, False
    price   = df["close"].iloc[-1] if not df.empty else None
    rsi     = df["rsi"].iloc[-1]   if "rsi"  in df.columns else None
    macd    = df["macd"].iloc[-1]  if "macd" in df.columns else 0
    sig     = df["signal"].iloc[-1] if "signal" in df.columns else "HOLD"
    is_bull = (df["ma8"].iloc[-1] > df["ma21"].iloc[-1]) if "ma8" in df.columns else False
    mcd_bull = macd > 0
    return price, rsi, macd, sig, is_bull, mcd_bull


# ─────────────────────────────────────────────
# AI ANALYSIS (Claude)
# ─────────────────────────────────────────────

def ai_analysis(market_name, price, change, rsi, macd, is_bull, macd_bull, signal, conf, anth_key):
    if not anth_key:
        return (
            f"RSI at {rsi:.1f} with MA8 {'above' if is_bull else 'below'} MA21 indicates "
            f"{'bullish' if is_bull else 'bearish'} short-term momentum. "
            f"MACD is {'positive' if macd_bull else 'negative'}, "
            f"{'confirming upward pressure' if macd_bull else 'confirming downward pressure'}. "
            f"The {signal} signal at {conf}% confidence suggests "
            f"{'a potential long entry' if 'BUY' in signal else 'caution or a short setup'}. "
            "Always use stop-losses and proper position sizing."
        )
    try:
        prompt = (
            f"You are a market analyst. Given this live data for {market_name}, "
            f"write a concise 3-4 sentence analysis:\n"
            f"Price: ${price:,.2f}\n24h Change: {change:+.2f}%\nRSI(14): {rsi:.1f}\n"
            f"MACD: {macd:.2f} ({'bullish' if macd_bull else 'bearish'})\n"
            f"MA8 vs MA21: {'MA8 above — bullish' if is_bull else 'MA8 below — bearish'}\n"
            f"Signal: {signal} — Confidence: {conf}%\n"
            "Be direct: what do the indicators say, what price level matters, and the main risk."
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anth_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        return resp.json()["content"][0]["text"]
    except Exception as e:
        return f"AI analysis unavailable: {e}"


# ─────────────────────────────────────────────
# CHART
# ─────────────────────────────────────────────

def build_chart(df: pd.DataFrame, title: str, color: str = "#f2a900"):
    if df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Price",
                             line=dict(color=color, width=2.5)))
    if "ma8" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["ma8"], name="MA8",
                                 line=dict(color="#5DCAA5", width=1.2, dash="dot")))
        fig.add_trace(go.Scatter(x=df.index, y=df["ma21"], name="MA21",
                                 line=dict(color="#ED93B1", width=1.2, dash="dot")))
    if "signal" in df.columns:
        buys  = df[df["signal"].str.contains("BUY",  na=False)]
        sells = df[df["signal"].str.contains("SELL", na=False)]
        if not buys.empty:
            fig.add_trace(go.Scatter(x=buys.index, y=buys["close"], mode="markers",
                                     marker=dict(symbol="triangle-up", size=14, color="lime"),
                                     name="Long entry"))
        if not sells.empty:
            fig.add_trace(go.Scatter(x=sells.index, y=sells["close"], mode="markers",
                                     marker=dict(symbol="triangle-down", size=14, color="red"),
                                     name="Short / exit"))
    fig.update_layout(height=480, template="plotly_dark", title=title,
                      xaxis_title="Date", yaxis_title="Price (USD)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    return fig


# ─────────────────────────────────────────────
# FUNDED SIMULATOR
# ─────────────────────────────────────────────

def funded_sim(price: float, signal: str, is_crypto: bool = True):
    # Target % varies by asset — BTC is volatile, Gold is not
    target_pct = 0.03 if is_crypto else 0.008
    sizes  = [0.1, 0.2, 0.3] if is_crypto else [1, 5, 10]
    unit   = "BTC" if is_crypto else "shares"
    is_buy = "BUY" in signal or signal == "OVERSOLD"
    results = []
    for size in sizes:
        target = price * (1 + target_pct) if is_buy else price * (1 - target_pct)
        pnl    = (target - price) * size if is_buy else (price - target) * size
        pct    = target_pct * 100 if is_buy else -target_pct * 100
        results.append((size, unit, "Long" if is_buy else "Short", pnl, pct))
    return results


# ─────────────────────────────────────────────
# FETCH ALL MARKET DATA
# ─────────────────────────────────────────────

btc_price, btc_chg, btc_vol = fetch_btc_price()
df_btc    = compute_indicators(fetch_btc_chart())
df_nasdaq = compute_indicators(fetch_polygon_stock("QQQ", POLYGON_KEY))
df_gold   = compute_indicators(fetch_polygon_stock("GLD", POLYGON_KEY))

_, btc_rsi,  btc_macd,  btc_sig,  btc_bull,  btc_mcd_bull  = get_market_state(df_btc)
nq_price, nq_rsi,  nq_macd,  nq_sig,  nq_bull,  nq_mcd_bull   = get_market_state(df_nasdaq)
gld_price, gld_rsi, gld_macd, gld_sig, gld_bull, gld_mcd_bull  = get_market_state(df_gold)

nq_prev  = df_nasdaq["close"].iloc[-2] if len(df_nasdaq) > 1 else nq_price
gld_prev = df_gold["close"].iloc[-2]   if len(df_gold)   > 1 else gld_price
nq_chg   = ((nq_price  / nq_prev  - 1) * 100) if nq_price  and nq_prev  else None
gld_chg  = ((gld_price / gld_prev - 1) * 100) if gld_price and gld_prev else None
nq_vol   = df_nasdaq["volume"].iloc[-1] if not df_nasdaq.empty and "volume" in df_nasdaq else None
gld_vol  = df_gold["volume"].iloc[-1]   if not df_gold.empty   and "volume" in df_gold   else None

btc_conf,  btc_color,  btc_emoji  = get_signal_meta(btc_sig,  btc_rsi  or 50, btc_bull,  btc_mcd_bull)
nq_conf,   nq_color,   nq_emoji   = get_signal_meta(nq_sig,   nq_rsi   or 50, nq_bull,   nq_mcd_bull)
gld_conf,  gld_color,  gld_emoji  = get_signal_meta(gld_sig,  gld_rsi  or 50, gld_bull,  gld_mcd_bull)

# ─────────────────────────────────────────────
# TOP METRICS ROW
# ─────────────────────────────────────────────

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("BTC / USD",   f"${btc_price:,.0f}" if btc_price else "—",
              f"{btc_chg:+.2f}%" if btc_chg else "—")
    st.markdown(f"{btc_emoji} **{btc_sig}** ({btc_conf}%)")

with col2:
    st.metric("NASDAQ / QQQ", f"${nq_price:,.2f}" if nq_price else "—",
              f"{nq_chg:+.2f}%" if nq_chg else "—")
    st.markdown(f"{nq_emoji} **{nq_sig}** ({nq_conf}%)")

with col3:
    st.metric("Gold / GLD",  f"${gld_price:,.2f}" if gld_price else "—",
              f"{gld_chg:+.2f}%" if gld_chg else "—")
    st.markdown(f"{gld_emoji} **{gld_sig}** ({gld_conf}%)")

st.divider()

# ─────────────────────────────────────────────
# MARKET SELECTOR
# ─────────────────────────────────────────────

market_choice = st.radio("Market", ["BTC / USD", "NASDAQ (QQQ)", "Gold (GLD)"], horizontal=True)

if market_choice == "BTC / USD":
    df, price, chg, vol = df_btc, btc_price, btc_chg, btc_vol
    rsi, macd, sig, conf = btc_rsi, btc_macd, btc_sig, btc_conf
    is_bull, macd_bull, emoji = btc_bull, btc_mcd_bull, btc_emoji
    chart_color, is_crypto = "#f2a900", True
    poly_rsi = fetch_btc_polygon_rsi(POLYGON_KEY)
    snap = None

elif market_choice == "NASDAQ (QQQ)":
    df, price, chg, vol = df_nasdaq, nq_price, nq_chg, nq_vol
    rsi, macd, sig, conf = nq_rsi, nq_macd, nq_sig, nq_conf
    is_bull, macd_bull, emoji = nq_bull, nq_mcd_bull, nq_emoji
    chart_color, is_crypto, poly_rsi = "#378ADD", False, None
    snap = fetch_polygon_snapshot("QQQ", POLYGON_KEY)

else:
    df, price, chg, vol = df_gold, gld_price, gld_chg, gld_vol
    rsi, macd, sig, conf = gld_rsi, gld_macd, gld_sig, gld_conf
    is_bull, macd_bull, emoji = gld_bull, gld_mcd_bull, gld_emoji
    chart_color, is_crypto, poly_rsi = "#BA7517", False, None
    snap = fetch_polygon_snapshot("GLD", POLYGON_KEY)

# ─────────────────────────────────────────────
# SIGNAL BANNER
# ─────────────────────────────────────────────

st.subheader(f"📢 {market_choice} — Current signal")
st.markdown(f"### {emoji} **{sig}** — Confidence **{conf}%**")
st.progress(conf / 100)

# ─────────────────────────────────────────────
# INDICATORS + CROWD
# ─────────────────────────────────────────────

c1, c2 = st.columns(2)

with c1:
    st.subheader("📊 Technical indicators")
    if rsi:
        rsi_lbl = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
        st.markdown(f"- **RSI 14:** {rsi:.1f} — {rsi_lbl}")
        st.markdown(f"- **MACD:** {macd:.2f} — {'Bullish' if macd_bull else 'Bearish'}")
        ma8v  = df["ma8"].iloc[-1]  if "ma8"  in df.columns else None
        ma21v = df["ma21"].iloc[-1] if "ma21" in df.columns else None
        if ma8v and ma21v:
            st.markdown(f"- **MA8:** ${ma8v:,.2f} vs **MA21:** ${ma21v:,.2f} — {'Bullish cross' if is_bull else 'Bearish cross'}")
        st.markdown(f"- **Trend:** {'Uptrend 📈' if is_bull else 'Downtrend 📉'}")
    else:
        st.info("Fetching indicators...")

with c2:
    st.subheader("👥 Crowd & sentiment")
    if is_crypto:
        if btc_vol:
            st.markdown(f"- **24h Volume:** ${btc_vol/1e9:.2f}B")
        if poly_rsi:
            st.markdown(f"- **Polygon RSI (live):** {poly_rsi:.1f}")
        if rsi:
            bull_pct = round(rsi)
            st.markdown(f"- **Bullish sentiment proxy:** {bull_pct}% | **Bearish:** {100-bull_pct}%")
        st.markdown("- **Source:** Polygon.io + CoinGecko")
    elif snap:
        day  = snap.get("day",     {})
        prev = snap.get("prevDay", {})
        if day.get("v"):
            st.markdown(f"- **Day volume:** {day['v']/1e6:.1f}M shares")
        if day.get("c") and day.get("o"):
            day_chg = (day["c"] - day["o"]) / day["o"] * 100
            st.markdown(f"- **Intraday change:** {day_chg:+.2f}%")
        if prev.get("c"):
            st.markdown(f"- **Prev close:** ${prev['c']:.2f}")
        if rsi:
            st.markdown(f"- **RSI sentiment:** {'Bullish' if rsi > 60 else 'Bearish' if rsi < 40 else 'Neutral'}")
        st.markdown("- **Source:** Polygon.io live snapshot")
    else:
        st.info("Polygon snapshot unavailable")

# ─────────────────────────────────────────────
# POLYMARKET CROWD DATA (BTC only)
# ─────────────────────────────────────────────

if is_crypto:
    st.subheader("🎲 Polymarket crowd odds (BTC)")
    poly_markets = fetch_polymarket_btc()
    if poly_markets:
        for m in poly_markets:
            with st.expander(m["question"]):
                pa, pb = st.columns(2)
                with pa:
                    st.metric("YES (crowd bullish)", f"{m['yes_pct']}%")
                with pb:
                    st.metric("NO  (crowd bearish)", f"{m['no_pct']}%")
                if m["volume"]:
                    st.caption(f"Volume: ${float(m['volume']):,.0f}")
    else:
        st.info("No active BTC Polymarket markets found right now.")

# ─────────────────────────────────────────────
# FUNDED ACCOUNT SIMULATOR
# ─────────────────────────────────────────────

st.subheader("💰 Funded account simulator")
if price:
    sims = funded_sim(price, sig, is_crypto)
    for size, unit, direction, pnl, pct in sims:
        label = f"{size} {unit} — {direction}"
        if pnl >= 0:
            st.success(f"{label} → **${pnl:+,.2f}** ({pct:+.1f}%)")
        else:
            st.error(f"{label} → **${pnl:+,.2f}** ({pct:+.1f}%)")
    st.caption("Directional targets only. Not financial advice.")

# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────

st.subheader("🤖 AI analysis (Claude)")
if price and rsi:
    with st.spinner("Claude is analyzing..."):
        analysis = ai_analysis(
            market_choice, price, chg or 0, rsi, macd,
            is_bull, macd_bull, sig, conf, ANTHROPIC_KEY
        )
    st.info(analysis)
    if not ANTHROPIC_KEY:
        st.caption("Add ANTHROPIC_KEY to .streamlit/secrets.toml for live Claude analysis.")

# ─────────────────────────────────────────────
# PRICE CHART
# ─────────────────────────────────────────────

st.subheader(f"📈 {market_choice} — Price chart with signals")
if not df.empty:
    fig = build_chart(df, market_choice, chart_color)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

st.caption(
    f"Last updated: {datetime.now().strftime('%H:%M:%S')} · "
    "Polygon.io + CoinGecko + Polymarket + Claude AI"
)
