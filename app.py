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
.stApp { background-color: #16161a; }
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 780px;}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background-color: #1c1c21; border-radius: 14px;
    padding: 6px; border: 1px solid #2a2a30;
}
.stTabs [data-baseweb="tab"] {
    height: 40px; background-color: transparent; border-radius: 10px;
    color: #8b8b95; font-weight: 600; font-size: 14px; padding: 0 16px;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important; color: #16161a !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {display: none;}

/* Buttons */
.stButton > button {
    background-color: #ffffff; color: #16161a; border: none;
    border-radius: 10px; font-weight: 600; padding: 0.5rem 1rem;
    transition: all 0.15s ease;
}
.stButton > button:hover { background-color: #ededf0; transform: translateY(-1px); }

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    background-color: #1c1c21 !important;
    border: 1px solid #2a2a30 !important;
    border-radius: 10px !important;
    color: #ededf0 !important;
}

/* Metrics */
[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; color: #ededf0; }
[data-testid="stMetricLabel"] {
    color: #8b8b95; font-size: 0.8rem;
    text-transform: uppercase; letter-spacing: 0.05em;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: 12px; overflow: hidden; border: 1px solid #2a2a30;
}

/* Coin card */
.coin-card {
    background-color: #1c1c21; border: 1px solid #2a2a30;
    border-radius: 14px; padding: 12px 14px; transition: all 0.15s ease;
}
.coin-card:hover { border-color: #3a3a42; transform: translateY(-1px); }
.coin-symbol { font-size: 0.95rem; font-weight: 700; color: #ededf0; letter-spacing: 0.02em; }
.coin-name { font-size: 0.7rem; color: #8b8b95; margin-top: -2px; }
.coin-price { font-size: 1.05rem; font-weight: 700; color: #ededf0; margin: 6px 0 4px 0; }
.coin-pct-row {
    display: flex; flex-direction: column; gap: 2px;
    font-size: 0.7rem; font-weight: 600; margin-top: 4px;
}
.pct-up { color: #4ade80; }
.pct-down { color: #f87171; }
.pct-label { color: #55555c; font-weight: 500; }
.pct-lbl { margin-left: 4px; color: #55555c; font-weight: 500; }

/* Grid */
.coin-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px; margin-top: 6px;
}

/* Section labels */
.section-label {
    color: #8b8b95; font-size: 0.75rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 20px 0 10px 0;
}

/* Header */
.header-wrap {
    display: flex; align-items: center; gap: 14px; margin-bottom: 8px;
}
.header-sigil-img {
    width: 56px; height: 56px; flex-shrink: 0;
    object-fit: cover; object-position: 60% center;
    border-radius: 8px;
}
.header-title {
    margin: 0; font-size: 2rem; font-weight: 800;
    color: #ededf0; letter-spacing: -0.03em; line-height: 1;
}
.header-sub {
    color: #8b8b95; font-size: 0.8rem; margin-top: 4px; letter-spacing: 0.02em;
}

/* Ledger table */
.ledger {
    width: 100%; border-collapse: collapse;
    background-color: #1c1c21;
    border: 1px solid #2a2a30; border-radius: 12px;
    overflow: hidden; font-size: 0.82rem;
    margin-bottom: 4px;
}
.ledger th {
    background-color: #14141a; color: #8b8b95;
    font-weight: 600; font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 0.05em;
    padding: 8px 6px; text-align: left;
    border-bottom: 1px solid #2a2a30;
}
.ledger td {
    padding: 10px 6px; color: #ededf0;
    border-bottom: 1px solid #23232a;
}
.ledger tr:last-child td { border-bottom: none; }
.ledger .buy-tag { color: #4ade80; font-weight: 700; }
.ledger .sell-tag { color: #f87171; font-weight: 700; }
.ledger .coin-cell { font-weight: 700; color: #ededf0; }
.ledger .muted { color: #8b8b95; }
.ledger .date-cell { color: #55555c; font-size: 0.75rem; }

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

SIGIL_URL = "https://raw.githubusercontent.com/AbdelkarimChioua/Balerion/main/sigil.jpeg"

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

def load_trades():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_trades(trades):
    with open(DATA_FILE, "w") as f:
        json.dump(trades, f, indent=2)

# ---------------- HEADER ----------------
st.markdown(f"""
<div class="header-wrap">
    <img src="{SIGIL_URL}" class="header-sigil-img" />
    <div>
        <div class="header-title">Balerion</div>
        <div class="header-sub">By Chioua Investment Group</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- TABS ----------------
tab_home, tab_analyze, tab_ledger, tab_backtest = st.tabs(
    ["Market", "Analyze", "Ledger", "Backtest"]
)

# ============ TAB: MARKET ============
with tab_home:
    st.markdown('<div class="section-label">Top 15 · tap a coin to analyze</div>', unsafe_allow_html=True)

    try:
        coins = fetch_top15()
    except Exception as e:
        st.error(f"Couldn't fetch market data: {e}")
        coins = []

    cards = ['<div class="coin-grid">']
    for c in coins:
        sym = SYMBOL_MAP.get(c["id"], c["symbol"].upper())
        name = c.get("name", sym)
        price = c.get("current_price")
        pct24 = c.get("price_change_percentage_24h_in_currency")
        pct7d = c.get("price_change_percentage_7d_in_currency")

        card = (
            '<div class="coin-card">'
            f'<div class="coin-symbol">{sym}</div>'
            f'<div class="coin-name">{name}</div>'
            f'<div class="coin-price">{fmt_price(price)}</div>'
            f'<div class="coin-pct-row">{pct_span(pct24, "24h")}{pct_span(pct7d, "7d")}</div>'
            '</div>'
        )
        cards.append(card)
    cards.append('</div>')
    st.markdown("".join(cards), unsafe_allow_html=True)

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

# ============ TAB: LEDGER ============
with tab_ledger:
    trades = load_trades()

    buys = [t for t in trades if t["type"] == "Buy"]
    sells = [t for t in trades if t["type"] == "Sell"]

    # ---------- BUYS ----------
    st.markdown('<div class="section-label">Buys</div>', unsafe_allow_html=True)
    if buys:
        rows = ['<table class="ledger"><thead><tr>'
                '<th>Coin</th><th>Price</th><th>Fee</th><th>Amount</th><th>Date</th>'
                '</tr></thead><tbody>']
        for t in buys:
            rows.append(
                '<tr>'
                f'<td class="coin-cell">{t["coin"]}</td>'
                f'<td>€{t["price"]:,.2f}</td>'
                f'<td class="muted">{t["fee"]}</td>'
                f'<td>{t["amount"]} {t["coin"]}</td>'
                f'<td class="date-cell">{t.get("date","")}</td>'
                '</tr>'
            )
        rows.append('</tbody></table>')
        st.markdown("".join(rows), unsafe_allow_html=True)
    else:
        st.caption("No buys recorded yet.")

    # ---------- SELLS ----------
    st.markdown('<div class="section-label">Sells</div>', unsafe_allow_html=True)
    if sells:
        rows = ['<table class="ledger"><thead><tr>'
                '<th>Coin</th><th>Price</th><th>Fee</th><th>Amount</th><th>Date</th>'
                '</tr></thead><tbody>']
        for t in sells:
            rows.append(
                '<tr>'
                f'<td class="coin-cell">{t["coin"]}</td>'
                f'<td>€{t["price"]:,.2f}</td>'
                f'<td class="muted">{t["fee"]}</td>'
                f'<td>{t["amount"]} {t["coin"]}</td>'
                f'<td class="date-cell">{t.get("date","")}</td>'
                '</tr>'
            )
        rows.append('</tbody></table>')
        st.markdown("".join(rows), unsafe_allow_html=True)
    else:
        st.caption("No sells recorded yet.")

    # ---------- ADD ----------
    st.markdown('<div class="section-label">Add transaction</div>', unsafe_allow_html=True)
    with st.form("add_trade", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ttype = st.selectbox("Type", ["Buy", "Sell"])
        with c2:
            coin = st.text_input("Coin", "BTC").upper()

        c3, c4 = st.columns(2)
        with c3:
            price = st.number_input("Price (€)", min_value=0.0, step=1.0, format="%.2f")
        with c4:
            fee = st.text_input("Fee (e.g. €5 or 0.0001 BTC)", "")

        c5, c6 = st.columns(2)
        with c5:
            amount = st.number_input("Amount (coins)", min_value=0.0, step=0.0001, format="%.6f")
        with c6:
            date = st.date_input("Date", datetime.now())

        submitted = st.form_submit_button("Add")
        if submitted:
            if not coin or price <= 0 or amount <= 0:
                st.error("Fill coin, price and amount.")
            else:
                trades = load_trades()
                trades.append({
                    "type": ttype,
                    "coin": coin,
                    "price": price,
                    "fee": fee,
                    "amount": amount,
                    "date": str(date),
                })
                save_trades(trades)
                st.success(f"Added {ttype} {amount} {coin}")
                st.rerun()

    # ---------- EXPORT / DELETE ----------
    if trades:
        st.markdown('<div class="section-label">Manage</div>', unsafe_allow_html=True)

        df_export = pd.DataFrame(trades)
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇  Export CSV (backup)",
            data=csv,
            file_name=f"balerion_trades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown('<div class="section-label">Delete a transaction</div>', unsafe_allow_html=True)
        for i, t in enumerate(trades):
            col1, col2 = st.columns([5, 1])
            col1.write(f"**{t['type']}** · {t['coin']} · €{t['price']:,.2f} · {t['amount']} {t['coin']} · {t.get('date','')}")
            if col2.button("✕", key=f"del_{i}"):
                trades.pop(i)
                save_trades(trades)
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
