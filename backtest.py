import pandas as pd
from analysis import kraken_ohlc, compute_indicators, conservative_signal

def run_backtest(pair="XBTUSD", horizons=(7, 30, 90)):
    """
    Fetch full BTC history from Kraken and evaluate signal winrate.
    Winrate = % of signals where price was higher N days later.
    """
    df = kraken_ohlc(pair)
    if df.empty:
        return None
    df = compute_indicators(df)
    df["signal"] = df.apply(conservative_signal, axis=1)

    results = {"full": {}, "modern": {}}

    for label, start in [("full", None), ("modern", "2018-01-01")]:
        sub = df if start is None else df[df["time"] >= start]
        if sub.empty:
            continue
        for h in horizons:
            buys = sub[sub["signal"] == "BUY"].copy()
            buys["future"] = sub["close"].shift(-h).reindex(buys.index)
            buys = buys.dropna(subset=["future"])
            if len(buys) == 0:
                results[label][h] = {"count": 0, "winrate": None, "avg_ret": None}
                continue
            ret = (buys["future"] / buys["close"] - 1) * 100
            winrate = (ret > 0).mean() * 100
            results[label][h] = {
                "count": len(buys),
                "winrate": round(winrate, 1),
                "avg_ret": round(ret.mean(), 2),
                "median_ret": round(ret.median(), 2),
            }

    return results, df

if __name__ == "__main__":
    res, df = run_backtest()
    print("=== BTC CONSERVATIVE SIGNAL BACKTEST ===\n")
    for era, data in res.items():
        print(f"--- {era.upper()} ---")
        for h, stats in data.items():
            print(f"  {h}d horizon: {stats}")
        print()
