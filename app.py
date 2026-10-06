import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import requests

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
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 780px;}

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

/* Header card */
.header-card {
    display: flex; align-items: center; gap: 14px;
    background-color: #1c1c21;
    border: 1px solid #2a2a30;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.header-sigil-img {
    width: 56px; height: 56px; flex-shrink: 0;
    object-fit: cover; object-position: 60% center;
    border-radius: 10px;
}
.header-title {
    margin: 0; font-size: 1.8rem; font-weight: 800;
    color: #ededf0; letter-spacing: -0.03em; line-height: 1;
}
.header-sub {
    color: #8b8b95; font-size: 0.78rem; margin-top: 4px; letter-spacing: 0.02em;
}

/* Coin card */
.coin-card {
    background-color: #1c1c21; border: 1px solid #2a2a30;
    border-radius: 14px; padding: 12px 14px; transition: all 0.15s ease;
}
.coin-card:hover { border-color: #3a3a42; }
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

def fmt_amount(n):
    if n is None:
        return "—"
    if n >= 1000:
        return f"{n:,.2f}"
    if n >= 1:
        return f"{n:,.4f}".rstrip("0").rstrip(".")
    return f"{n:.6f}".rstrip("0").rstrip(".")

# ---------------- HEADER ----------------
st.markdown(f"""
<div class="header-card">
    <img src="{SIGIL_URL}" class="header-sigil-img" />
    <div>
        <div class="header-title">Balerion</div>
        <div class="header-sub">By Chioua Investment Group</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- TABS ----------------
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Market"

tab_options = ["Market", "Ledger"]
tab_icons = {
    "Market": ":material/dashboard:",
    "Ledger": ":material/receipt_long:",
}

selected = st.segmented_control(
    "Navigation",
    options=tab_options,
    format_func=lambda x: tab_icons[x],
    selection_mode="single",
    default=st.session_state.active_tab,
    key="main_tabs",
    label_visibility="collapsed"
)

if selected:
    st.session_state.active_tab = selected

# ---------------- TAB CONTENT ----------------

# ============ MARKET ============
if st.session_state.active_tab == "Market":
    st.markdown('<div class="section-label">Top 15</div>', unsafe_allow_html=True)

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

    st.caption("Data: CoinGecko · refresh every 2 min")

# ============ LEDGER ============
elif st.session_state.active_tab == "Ledger":
    trades = load_trades()
    buys = [t for t in trades if t["type"] == "Buy"]
    sells = [t for t in trades if t["type"] == "Sell"]

    # BUYS
    st.markdown('<div class="section-label">Buys</div>', unsafe_allow_html=True)
    if buys:
        for i, t in enumerate(trades):
            if t["type"] != "Buy":
                continue
            with st.expander(f"{t['coin']} · €{t['amount_eur']:,.2f} · {t.get('date','')}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    new_coin = st.text_input("Coin", t["coin"], key=f"coin_b_{i}").upper()
                with c2:
                    try:
                        default_date = datetime.fromisoformat(t["date"]).date()
                    except Exception:
                        default_date = datetime.now().date()
                    new_date = st.date_input("Date", default_date, key=f"date_b_{i}")

                c3, c4 = st.columns(2)
                with c3:
                    new_amount_eur = st.number_input("Buy amount (€)", value=float(t["amount_eur"]), min_value=0.0, step=1.0, format="%.2f", key=f"eur_b_{i}")
                with c4:
                    new_fee = st.number_input("Fee (€)", value=float(t["fee"]), min_value=0.0, step=0.01, format="%.2f", key=f"fee_b_{i}")

                new_amount = st.number_input("Amount (coins)", value=float(t["amount"]), min_value=0.0, step=0.0001, format="%.6f", key=f"amt_b_{i}")

                c5, c6 = st.columns(2)
                with c5:
                    if st.button("💾 Save", key=f"save_b_{i}", use_container_width=True):
                        trades[i] = {"type": "Buy", "coin": new_coin, "amount_eur": new_amount_eur, "fee": new_fee, "amount": new_amount, "date": str(new_date)}
                        save_trades(trades)
                        st.rerun()
                with c6:
                    if st.button("✕ Delete", key=f"del_b_{i}", use_container_width=True):
                        trades.pop(i)
                        save_trades(trades)
                        st.rerun()
    else:
        st.caption("No buys recorded yet.")

    # SELLS
    st.markdown('<div class="section-label">Sells</div>', unsafe_allow_html=True)
    if sells:
        for i, t in enumerate(trades):
            if t["type"] != "Sell":
                continue
            with st.expander(f"{t['coin']} · €{t['amount_eur']:,.2f} · {t.get('date','')}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    new_coin = st.text_input("Coin", t["coin"], key=f"coin_s_{i}").upper()
                with c2:
                    try:
                        default_date = datetime.fromisoformat(t["date"]).date()
                    except Exception:
                        default_date = datetime.now().date()
                    new_date = st.date_input("Date", default_date, key=f"date_s_{i}")

                c3, c4 = st.columns(2)
                with c3:
                    new_amount_eur = st.number_input("Sell amount (€)", value=float(t["amount_eur"]), min_value=0.0, step=1.0, format="%.2f", key=f"eur_s_{i}")
                with c4:
                    new_fee = st.number_input("Fee (€)", value=float(t["fee"]), min_value=0.0, step=0.01, format="%.2f", key=f"fee_s_{i}")

                new_amount = st.number_input("Amount (coins)", value=float(t["amount"]), min_value=0.0, step=0.0001, format="%.6f", key=f"amt_s_{i}")

                c5, c6 = st.columns(2)
                with c5:
                    if st.button("💾 Save", key=f"save_s_{i}", use_container_width=True):
                        trades[i] = {"type": "Sell", "coin": new_coin, "amount_eur": new_amount_eur, "fee": new_fee, "amount": new_amount, "date": str(new_date)}
                        save_trades(trades)
                        st.rerun()
                with c6:
                    if st.button("✕ Delete", key=f"del_s_{i}", use_container_width=True):
                        trades.pop(i)
                        save_trades(trades)
                        st.rerun()
    else:
        st.caption("No sells recorded yet.")

    # ADD
    st.markdown('<div class="section-label">Add transaction</div>', unsafe_allow_html=True)
    with st.form("add_trade", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ttype = st.selectbox("Type", ["Buy", "Sell"])
        with c2:
            coin = st.text_input("Coin", "BTC").upper()

        amount_label = "Buy amount (€)" if ttype == "Buy" else "Sell amount (€)"
        c3, c4 = st.columns(2)
        with c3:
            amount_eur = st.number_input(amount_label, min_value=0.0, step=1.0, format="%.2f")
        with c4:
            fee = st.number_input("Fee (€)", min_value=0.0, step=0.01, format="%.2f")

        c5, c6 = st.columns(2)
        with c5:
            amount = st.number_input("Amount (coins)", min_value=0.0, step=0.0001, format="%.6f")
        with c6:
            date = st.date_input("Date", datetime.now())

        submitted = st.form_submit_button("Add")
        if submitted:
            if not coin or amount_eur <= 0 or amount <= 0:
                st.error("Fill coin, amount and coins.")
            else:
                trades = load_trades()
                trades.append({"type": ttype, "coin": coin, "amount_eur": amount_eur, "fee": fee, "amount": amount, "date": str(date)})
                save_trades(trades)
                st.rerun()

    # EXPORT
    if trades:
        st.markdown('<div class="section-label">Backup</div>', unsafe_allow_html=True)
        df_export = pd.DataFrame(trades)
        csv = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇  Export CSV",
            data=csv,
            file_name=f"balerion_trades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
)
