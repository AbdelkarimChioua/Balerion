import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from analysis import analyze_asset, conservative_signal

st.set_page_config(page_title="Kraken Analyst", page_icon="📊", layout="centered")

DATA_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return []

def save_portfolio(p):
    with open(DATA_FILE, "w") as f:
        json.dump(p, f, indent=2)

st.title("📊 Kraken Analyst")

tab1, tab2, tab3, tab4 = st.tabs(["Portfolio", "Analyze", "Add Trade", "Backtest"])

# ---------- TAB 1: PORTFOLIO ----------
with tab1:
    st.subheader("My Portfolio")
    portfolio = load_portfolio()
    if not portfolio:
        st.info("No positions yet. Go to **Add Trade** tab.")
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
                pnl_pct = (pnl / cost) * 100
                total_value += value
                total_cost += cost
                rows.append({
                    "Asset": pos["pair"],
                    "Amount": pos["amount"],
                    "Buy": round(pos["price"], 2),
                    "Now": round(a["price"], 2),
                    "Value €": round(value, 2),
                    "P&L €": round(pnl, 2),
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
            c1.metric("Value", f"€{total_value:,.2f}")
            c2.metric("Cost", f"€{total_cost:,.2f}")
            c3.metric("P&L", f"€{pnl_total:,.2f}",
                      f"{(pnl_total/total_cost*100):.1f}%" if total_cost else "0%")

            st.subheader("Allocation")
            alloc = pd.DataFrame({
                "Asset": [r["Asset"] for r in rows],
                "Value": [r["Value €"] for r in rows],
            })
            st.bar_chart(alloc.set_index("Asset"))

# ---------- TAB 2: ANALYZE ----------
with tab2:
    st.subheader("Analyze an asset")
    pair = st.text_input("Kraken pair (e.g. XBTUSD, ETHUSD, SOLUSD)", "XBTUSD")
    if st.button("Analyze"):
        try:
            a = analyze_asset(pair)
            colors = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
            st.markdown(f"### {colors[a['signal']]} {a['signal']} — {pair}")
            c1, c2 = st.columns(2)
            c1.metric("Price", f"${a['price']:,.2f}")
            c2.metric("RSI(14)", f"{a['rsi']:.1f}")
            c1.metric("MA50", f"${a['ma50']:,.2f}")
            c2.metric("MA200", f"${a['ma200']:,.2f}")
            st.metric("Distance from 90d high", f"{a['pct_from_high90']:.1f}%")

            st.subheader("Why this signal?")
            r = a["history"].iloc[-1]
            reasons = []
            reasons.append(f"Price {'above' if r['close'] > r['ma200'] else 'below'} MA200")
            reasons.append(f"MA50 {'above' if r['ma50'] > r['ma200'] else 'below'} MA200")
            reasons.append(f"RSI = {r['rsi']:.1f} ({'oversold' if r['rsi']<30 else 'overbought' if r['rsi']>70 else 'neutral'})")
            for reason in reasons:
                st.write("• " + reason)

            st.subheader("Last 90 days")
            chart_df = a["history"].tail(90).set_index("time")[["close", "ma50", "ma200"]]
            st.line_chart(chart_df)
        except Exception as e:
            st.error(f"Error: {e}")

# ---------- TAB 3: ADD TRADE ----------
with tab3:
    st.subheader("Add a trade")
    with st.form("add_trade"):
        pair = st.text_input("Pair (e.g. XBTUSD)", "XBTUSD")
        amount = st.number_input("Amount (coins)", min_value=0.0, step=0.0001, format="%.6f")
        price = st.number_input("Buy price (USD)", min_value=0.0, step=1.0)
        date = st.date_input("Date", datetime.now())
        submitted = st.form_submit_button("Add")
        if submitted and amount > 0 and price > 0:
            p = load_portfolio()
            p.append({"pair": pair.upper(), "amount": amount, "price": price, "date": str(date)})
            save_portfolio(p)
            st.success(f"Added {amount} {pair} @ ${price}")
            st.rerun()

    st.subheader("Current positions")
    portfolio = load_portfolio()
    if portfolio:
        for i, pos in enumerate(portfolio):
            col1, col2 = st.columns([4, 1])
            col1.write(f"{pos['amount']} {pos['pair']} @ ${pos['price']} ({pos['date']})")
            if col2.button("🗑", key=f"del_{i}"):
                portfolio.pop(i)
                save_portfolio(portfolio)
                st.rerun()

# ---------- TAB 4: BACKTEST ----------
with tab4:
    st.subheader("BTC Signal Backtest")
    st.caption("Uses Kraken's full BTC history. Full = 2010+, Modern = 2018+.")
    if st.button("Run BTC backtest (~30s)"):
        with st.spinner("Fetching history and simulating..."):
            from backtest import run_backtest
            res, _ = run_backtest()
        if not res:
            st.error("No data returned.")
        else:
            for era in ["full", "modern"]:
                if era in res:
                    st.markdown(f"### {era.upper()} history")
                    tbl = []
                    for h, s in res[era].items():
                        if s["winrate"] is None:
                            tbl.append({"Horizon": f"{h}d", "Signals": 0, "Winrate": "—", "Avg return": "—"})
                        else:
                            tbl.append({
                                "Horizon": f"{h}d",
                                "Signals": s["count"],
                                "Winrate": f"{s['winrate']}%",
                                "Avg return": f"{s['avg_ret']}%",
                                "Median": f"{s['median_ret']}%",
                            })
                    st.dataframe(pd.DataFrame(tbl), hide_index=True, use_container_width=True)
            st.info("⚠️ Winrate ≠ profitability. Check avg return and sample size (need 20+ signals to trust).")
