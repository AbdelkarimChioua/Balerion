import requests
import pandas as pd
import numpy as np

KRAKEN_BASE = "https://api.kraken.com/0/public"

def kraken_ohlc(pair="XBTUSD", interval=1440, since=None):
    params = {"pair": pair, "interval": interval}
    if since:
        params["since"] = since
    r = requests.get(f"{KRAKEN_BASE}/OHLC", params=params, timeout=30)
    data = r.json()
    if data.get("error"):
        raise Exception(f"Kraken error: {data['error']}")
    key = list(data["result"].keys())[0]
    rows = data["result"][key]
    df = pd.DataFrame(rows, columns=[
        "time", "open", "high", "low", "close", "vwap", "volume", "count"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="s")
    for c in ["open", "high", "low", "close", "vwap", "volume"]:
        df[c] = df[c].astype(float)
    return df.sort_values("time").reset_index(drop=True)

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_indicators(df):
    df = df.copy()
    df["ma50"] = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()
    df["rsi"] = rsi(df["close"], 14)
    df["high90"] = df["high"].rolling(90).max()
    df["pct_from_high90"] = (df["close"] / df["high90"] - 1) * 100
    # golden cross: MA50 crossed above MA200 today
    df["ma50_above_ma200"] = df["ma50"] > df["ma200"]
    df["golden_cross"] = (df["ma50_above_ma200"]) & (~df["ma50_above_ma200"].shift(1).fillna(False))
    # death cross
    df["death_cross"] = (~df["ma50_above_ma200"]) & (df["ma50_above_ma200"].shift(1).fillna(False))
    return df

# ---------- SIGNAL STRATEGIES ----------

def signal_conservative(row):
    """Original rules — kept for comparison."""
    if pd.isna(row["ma200"]) or pd.isna(row["rsi"]):
        return "HOLD"
    if (row["close"] > row["ma200"]
        and row["ma50"] > row["ma200"]
        and 30 <= row["rsi"] <= 50
        and row["pct_from_high90"] < -5):
        return "BUY"
    if (row["close"] < row["ma200"]
        or row["rsi"] > 75
        or row["death_cross"]):
        return "SELL"
    return "HOLD"

def signal_trend_follow(row):
    """Buy on golden cross in strong uptrend. Ride the trend."""
    if pd.isna(row["ma200"]) or pd.isna(row["rsi"]):
        return "HOLD"
    # Strong uptrend: price and MA50 both well above MA200
    strong_uptrend = row["close"] > row["ma200"] * 1.02 and row["ma50"] > row["ma200"]
    # Entry trigger: golden cross recently (within 10 days) OR strong uptrend + RSI rising
    if strong_uptrend and (row["golden_cross"] or (40 <= row["rsi"] <= 65)):
        return "BUY"
    if row["death_cross"] or row["close"] < row["ma200"] * 0.95:
        return "SELL"
    return "HOLD"

def signal_oversold_bounce(row):
    """Buy capitulation dips within a bull regime."""
    if pd.isna(row["ma200"]) or pd.isna(row["rsi"]):
        return "HOLD"
    # Only buy if still in bull regime (price above MA200)
    if row["close"] > row["ma200"] and row["rsi"] < 30:
        return "BUY"
    if row["close"] < row["ma200"] or row["rsi"] > 75:
        return "SELL"
    return "HOLD"

def signal_momentum_breakout(row):
    """Buy new highs with room left in RSI."""
    if pd.isna(row["ma200"]) or pd.isna(row["rsi"]):
        return "HOLD"
    # New 90-day high (within 1%) + RSI not yet overbought
    near_high = row["pct_from_high90"] > -1
    if (row["close"] > row["ma200"]
        and near_high
        and row["rsi"] < 70):
        return "BUY"
    if row["close"] < row["ma200"] * 0.95 or row["rsi"] > 80:
        return "SELL"
    return "HOLD"

SIGNALS = {
    "conservative": signal_conservative,
    "trend_follow": signal_trend_follow,
    "oversold_bounce": signal_oversold_bounce,
    "momentum_breakout": signal_momentum_breakout,
}

def analyze_asset(pair="XBTUSD", strategy="conservative"):
    df = kraken_ohlc(pair)
    df = compute_indicators(df)
    last = df.iloc[-1]
    fn = SIGNALS.get(strategy, signal_conservative)
    signal = fn(last)
    return {
        "pair": pair,
        "price": last["close"],
        "ma50": last["ma50"],
        "ma200": last["ma200"],
        "rsi": last["rsi"],
        "pct_from_high90": last["pct_from_high90"],
        "signal": signal,
        "strategy": strategy,
        "history": df,
    }
