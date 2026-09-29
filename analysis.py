import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

KRAKEN_BASE = "https://api.kraken.com/0/public"

def kraken_ohlc(pair="XBTUSD", interval=1440, since=None):
    """Fetch daily OHLC from Kraken. interval=1440 -> daily."""
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

def compute_indicators(df):
    df = df.copy()
    df["ma50"] = df["close"].rolling(50).mean()
    df["ma200"] = df["close"].rolling(200).mean()
    df["rsi"] = rsi(df["close"], 14)
    df["high90"] = df["high"].rolling(90).max()
    df["pct_from_high90"] = (df["close"] / df["high90"] - 1) * 100
    return df

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def conservative_signal(row):
    """Returns 'BUY', 'SELL', or 'HOLD' using strict rules."""
    if pd.isna(row["ma200"]) or pd.isna(row["rsi"]):
        return "HOLD"
    price = row["close"]
    # BUY: all must be true
    if (price > row["ma200"]
        and row["ma50"] > row["ma200"]
        and 30 <= row["rsi"] <= 50
        and row["pct_from_high90"] < -5):
        return "BUY"
    # SELL/CAUTION
    if (price < row["ma200"]
        or row["rsi"] > 75
        or (row["ma50"] < row["ma200"] and row["ma50"] < row["ma200"] * 0.98)):
        return "SELL"
    return "HOLD"

def analyze_asset(pair="XBTUSD"):
    df = kraken_ohlc(pair)
    df = compute_indicators(df)
    last = df.iloc[-1]
    signal = conservative_signal(last)
    return {
        "pair": pair,
        "price": last["close"],
        "ma50": last["ma50"],
        "ma200": last["ma200"],
        "rsi": last["rsi"],
        "pct_from_high90": last["pct_from_high90"],
        "signal": signal,
        "history": df,
    }
