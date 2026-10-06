import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import requests

from analysis import analyze_asset, SIGNALS

st.set_page_config(page_title="Balerion", page_icon="◆", layout="centered")

# ---------------- THEME / CSS ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

.stApp {
    background-color: #16161a;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 780px;}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background-color: #1c1c21;
    border-radius: 14px;
    padding: 6px;
    border: 1px solid #2a2a30;
}
.stTabs [data-baseweb="tab"] {
    height: 40px;
    background-color: transparent;
    border-radius: 10px;
    color: #8b8b95;
    font-weight: 600;
    font-size: 14px;
    padding: 0 16px;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #16161a !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {display: none;}

/* Buttons */
.stButton > button {
    background-color: #ffffff;
    color: #16161a;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.5rem 1rem;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    background-color: #ededf0;
    transform: translateY(-1px);
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    background-color: #1c1c21 !important;
    border: 1px solid #2a2a30 !important;
    border-radius: 10px !important;
    color: #ededf0 !important;
}

/* Metrics */
[data-testid="stMetricValue"] {
    font-size: 1.6rem;
    font-weight: 700;
    color: #ededf0;
}
[data-testid="stMetricLabel"] {
    color: #8b8b95;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #2a2a30;
}

/* Custom coin card */
.coin-card {
    background-color: #1c1c21;
    border: 1px solid #2a2a30;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: all 0.15s ease;
}
.coin-card:hover {
    border-color: #3a3a42;
    transform: translateY(-1px);
}
.coin-symbol {
    font-size: 1rem;
    font-weight: 700;
    color: #ededf0;
    letter-spacing: 0.02em;
}
.coin-name {
    font-size: 0.72rem;
    color: #8b8b95;
    margin-top: -2px;
}
.coin-price {
    font-size: 1.25rem;
    font-weight: 700;
    color: #ededf0;
    margin: 8px 0 4px 0;
}
.coin-pct-row {
    display: flex;
    gap: 10px;
    font-size: 0.78rem;
    font-weight: 600;
}
.pct-up { color: #4ade80; }
.pct-down { color: #f87171; }
.pct-label { color: #55555c; font-weight: 500; }

/* 2-column coin grid — forced, works on mobile */
.coin-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 6px;
}
.coin-grid .coin-card {
    margin-bottom: 0;
    padding: 12px 14px;
}
.coin-grid .coin-price {
    font-size: 1.05rem;
    margin: 6px 0 4px 0;
}
.coin-grid .coin-symbol {
    font-size: 0.95rem;
}
.coin-grid .coin-name {
    font-size: 0.7rem;
}
.coin-grid .coin-pct-row {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.7rem;
    margin-top: 4px;
}
.coin-grid .pct-lbl {
    margin-left: 4px;
    color: #55555c;
    font-weight: 500;
}

/* Section labels */
.section-label {
    color: #8b8b95;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 20px 0 10px 0;
}

h1, h2, h3 { color: #ededf0; font-weight: 700; letter-spacing: -0.02em; }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "portfolio.json"

# ---------------- DATA ----------------
COINGECKO = "https://api.coingecko.com/api/v3"

TOP15_IDS = [
    "bitcoin", "ethereum", "binancecoin", "solana", "ripple",
    "dogecoin", "cardano", "tron", "avalanche-2", "chainlink",
    "the-open-network", "shiba-inu", "polkadot", "litecoin", "bitcoin-cash"
]

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "solana": "SOL", "ripple": "XRP", "dogecoin": "DOGE",
    "cardano": "ADA", "tron": "TRX", "avalanche-2": "AVAX",
    "chainlink": "LINK", "the-open-network": "TON",
    "shiba-inu": "SHIB", "polkadot": "DOT", "litecoin": "LTC",
    "bitcoin-cash": "BCH",
}

@st.cache_data(ttl=120)
def fetch_top15():
    ids = ",".join(TOP15_IDS)
    url = f"{COINGECKO}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ids,
        "order": "market_cap_desc",
        "price_change_percentage": "24h,7d",
        "sparkline": "false",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def fmt_price(p):
    if p is None:
        return "—"
    if p >= 1000:
        return f"${p:,.0f}"
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    return f"${p:.8f}"

def pct_span(v, lbl):
    if v is None:
        return f'<span class="pct-label">{lbl} —</span>'
    cls = "pct-up" if v >= 0 else "pct-down"
    arrow = "▲" if v >= 0 else "▼"
    return f'<span class="{cls}">{arrow}{v:+.2f}%<span class="pct-lbl">{lbl}</span></span>'

def load_portfolio():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_portfolio(p):
    with open(DATA_FILE, "w") as f:
        json.dump(p, f, indent=2)

# ---------------- HEADER ----------------
st.markdown(
    '<h1 style="margin-bottom:0.2rem;">Balerion</h1>'
    '<div style="color:#8b8b95;font-size:0.85rem;">Crypto analyst · your private board</div>',
    unsafe_allow_html=True
)

# ---------------- TABS ----------------
tab_home, tab_analyze, tab_portfolio, tab_add, tab_backtest = st.tabs(
    ["Market", "Analyze", "Portfolio", "Add", "Backtest"]
)

# ============ TAB: MARKET ============
with tab_home:
    st.markdown('<div class="section-label">Top 15 · tap a coin to analyze</div>', unsafe_allow_html=True)

    try:
        coins = fetch_top15()
    except Exception as e:
        st.error(f"Couldn't fetch market data: {e}")
        coins = []

    # Build the whole grid as one HTML block so it stays 2 columns on mobile
    cards_html = '<div class="coin-grid">'
    for c in coins:
        sym = SYMBOL_MAP.get(c["id"], c["symbol"].upper())
        name = c.get("name", sym)
        price = c.get("current_price")
        pct24 = c.get("price_change_percentage_24h_in_currency")
        pct7d = c.get("price_change_percentage_7d_in_currency")

        cards_html += f"""
        <div class="coin-card">
            <div class="coin-symbol">{sym}</div>
            <div class="coin-name">{name}</div>
            <div class="coin-price">{fmt_price(price)}</div>
            <div class="coin-pct-row">
                {pct_span(pct24, "24h")}
                {pct_span(pct7d, "7d")}
            </div>
        </div>
        """
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # Analyzer shortcut below the grid
    st.markdown('<div class="section-label">Quick analyze</div>', unsafe_allow_html=True)
    if coins:
        symbols = [SYMBOL_MAP.get(c["id"], c["symbol"].upper()) for c in coins]
        cols = st.columns([3, 1])
        with cols[0]:
            pick = st.selectbox("Pick a coin", symbols, label_visibility="collapsed")
        with cols[1]:
            if st.button("Go", use_container_width=True):
                st.session_state["analyze_pair_input_field"] = f"{pick}USD"
                st.rerun()

    st.caption("Data: CoinGecko · refresh every 2 min")

# ============ TAB: ANALYZE ============
with tab_analyze:
    st.markdown('<div class="section-label">Single asset analysis</div>', unsafe_allow_html=True)

    default_pair = st.session_state.get("analyze_pair_input_field", "XBTUSD")
    pair = st.text_input("Kraken pair", value=default_pair, key="analyze_pair_input_field")
    strategy = st.selectbox("Strategy", list(SIGNALS.keys()), index=0)

    if st.button("Run analysis"):
        try:
            a = analyze_asset(pair, strategy=strategy)
            colors = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
            st.markdown(
                f'<h2 style="margin-top:10px;">{colors[a["signal"]]} {a["signal"]} '
                f'<span style="color:#8b8b95;font-size:1rem;font-weight:500;">· {pair} · {strategy}</span></h2>',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns(2)
            c1.metric("Price", f"${a['price']:,.4f}")
            c2.metric("RSI(14)", f"{a['rsi']:.1f}")
            c1.metric("MA50", f"${a['ma50']:,.4f}")
            c2.metric("MA200", f"${a['ma200']:,.4f}")
            st.metric("Distance from 90d high", f"{a['pct_from_high90']:.1f}%")

            r = a["history"].iloc[-1]
            st.markdown('<div class="section-label">Context</div>', unsafe_allow_html=True)
            st.write(f"• Price is **{'above' if r['close'] > r['ma200'] else 'below'}** MA200")
            st.write(f"• MA50 is **{'above' if r['ma50'] > r['ma200'] else 'below'}** MA200")
            rsi_state = "oversold" if r["rsi"] < 30 else "overbought" if r["rsi"] > 70 else "neutral"
            st.write(f"• RSI = {r['rsi']:.1f} ({rsi_state})")

            st.markdown('<div class="section-label">Last 90 days</div>', unsafe_allow_html=True)
            chart_df = a["history"].tail(90).set_index("time")[["close", "ma50", "ma200"]]
            st.line_chart(chart_df)
        except Exception as e:
            st.error(f"Error: {e}")

# ============ TAB: PORTFOLIO ============
with tab_portfolio:
    st.markdown('<div class="section-label">My positions</div>', unsafe_allow_html=True)
    portfolio = load_portfolio()
    if not portfolio:
        st.info("No positions yet. Go to **Add** tab.")
    else:
        rows = []
        total_value = 0
        total_cost = 0
        for pos in portfolio:
            try:
                a = analyze_asset(pos["pair"])
                value = a["price"] * pos["amount"]
                cost = pos["price"] * pos["amount"]
                pnl = value - cost
                pnl_pct = (pnl / cost) * 100 if cost else 0
                total_value += value
                total_cost += cost
                rows.append({
                    "Asset": pos["pair"],
                    "Amount": pos["amount"],
                    "Buy": round(pos["price"], 4),
                    "Now": round(a["price"], 4),
                    "Value $": round(value, 2),
                    "P&L": round(pnl, 2),
                    "P&L %": round(pnl_pct, 1),
                    "Signal": a["signal"],
                })
            except Exception as e:
                st.warning(f"{pos['pair']}: {e}")

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            pnl_total = total_value - total_cost
            c1, c2, c3 = st.columns(3)
            c1.metric("Value", f"${total_value:,.2f}")
            c2.metric("Cost", f"${total_cost:,.2f}")
            c3.metric("P&L", f"${pnl_total:,.2f}",
                      f"{(pnl_total/total_cost*100):.1f}%" if total_cost else "0%")

            st.markdown('<div class="section-label">Allocation</div>', unsafe_allow_html=True)
            alloc = pd.DataFrame({
                "Asset": [r["Asset"] for r in rows],
                "Value": [r["Value $"] for r in rows],
            })
            st.bar_chart(alloc.set_index("Asset"))

# ============ TAB: ADD ============
with tab_add:
    st.markdown('<div class="section-label">Add a trade</div>', unsafe_allow_html=True)
    with st.form("add_trade"):
        pair = st.text_input("Pair (e.g. XBTUSD)", "XBTUSD")
        amount = st.number_input("Amount (coins)", min_value=0.0, step=0.0001, format="%.6f")
        price = st.number_input("Buy price (USD)", min_value=0.0, step=1.0)
        date = st.date_input("Date", datetime.now())
        submitted = st.form_submit_button("Add position")
        if submitted and amount > 0 and price > 0:
            p = load_portfolio()
            p.append({"pair": pair.upper(), "amount": amount, "price": price, "date": str(date)})
            save_portfolio(p)
            st.success(f"Added {amount} {pair} @ ${price}")
            st.rerun()

    st.markdown('<div class="section-label">Current positions</div>', unsafe_allow_html=True)
    portfolio = load_portfolio()
    if portfolio:
        for i, pos in enumerate(portfolio):
            col1, col2 = st.columns([5, 1])
            col1.write(f"**{pos['pair']}** · {pos['amount']} @ ${pos['price']} · {pos['date']}")
            if col2.button("✕", key=f"del_{i}"):
                portfolio.pop(i)
                save_portfolio(portfolio)
                st.rerun()

# ============ TAB: BACKTEST ============
with tab_backtest:
    st.markdown('<div class="section-label">BTC strategy backtest</div>', unsafe_allow_html=True)
    st.caption("Compares 4 strategies. Modern = 2018+ (trust this).")
    if st.button("Run BTC backtest (~30-60s)"):
        with st.spinner("Fetching history and running 4 strategies..."):
            from backtest import run_backtest
            res, _ = run_backtest()
        if not res:
            st.error("No data returned.")
        else:
            for era in ["full", "modern"]:
                if era not in res:
                    continue
                st.markdown(f"### {era.upper()}")
                for strat, horizons in res[era].items():
                    st.markdown(f"**{strat}**")
                    tbl = []
                    for h in sorted(horizons.keys()):
                        s = horizons[h]
                        if s["winrate"] is None:
                            tbl.append({"H": f"{h}d", "Signals": 0, "Winrate": "—", "Avg": "—"})
                        else:
                            tbl.append({
                                "H": f"{h}d",
                                "Signals": s["count"],
                                "Winrate": f"{s['winrate']}%",
                                "Avg": f"{s['avg_ret']}%",
                                "Median": f"{s['median_ret']}%",
                            })
                    st.dataframe(pd.DataFrame(tbl), hide_index=True, use_container_width=True)
