import pandas as pd
from analysis import kraken_ohlc, compute_indicators, SIGNALS

def run_backtest(pair="XBTUSD", horizons=(7, 30, 90)):
    """
    Runs every strategy in SIGNALS over full BTC history.
    Reports winrate + avg return for full and modern (2018+) eras.
    """
    df = kraken_ohlc(pair)
    if df.empty:
        return None, None
    df = compute_indicators(df)

    # Compute signal column for each strategy
    for name, fn in SIGNALS.items():
        df[name] = df.apply(fn, axis=1)

    results = {}  # results[era][strategy][horizon] = stats

    for era, start in [("full", None), ("modern", "2018-01-01")]:
        sub = df if start is None else df[df["time"] >= start].copy()
        # IMPORTANT: also apply shift within the SAME slice (sub), not global df
        if sub.empty:
            continue
        results[era] = {}

        for name in SIGNALS.keys():
            results[era][name] = {}
            buys = sub[sub[name] == "BUY"].copy()
            for h in horizons:
                if buys.empty:
                    results[era][name][h] = {
                        "count": 0, "winrate": None,
                        "avg_ret": None, "median_ret": None
                    }
                    continue
                # future price within this era's slice
                future = sub["close"].shift(-h)
                ret = (future.loc[buys.index] / buys["close"] - 1) * 100
                ret = ret.dropna()
                if len(ret) == 0:
                    results[era][name][h] = {
                        "count": 0, "winrate": None,
                        "avg_ret": None, "median_ret": None
                    }
                else:
                    results[era][name][h] = {
                        "count": int(len(ret)),
                        "winrate": round((ret > 0).mean() * 100, 1),
                        "avg_ret": round(ret.mean(), 2),
                        "median_ret": round(ret.median(), 2),
                    }

    return results, df

if __name__ == "__main__":
    res, _ = run_backtest()
    for era, strategies in res.items():
        print(f"\n=== {era.upper()} ===")
        for strat, horizons in strategies.items():
            print(f"\n  {strat}:")
            for h, stats in horizons.items():
                print(f"    {h}d: {stats}")
