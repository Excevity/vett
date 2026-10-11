"""Backtest "near-sure bets" (buy the favourite at 90c+ and hold) on real
resolved Polymarket markets, with current taker fees applied.

Data: the honest-odds study sample (2,946 resolved binary markets, 2023-2026).
    curl -o polymarket/data/sample.parquet \
      https://raw.githubusercontent.com/CH4RL3I/honest-odds/main/data/sample.parquet
    pip install pandas pyarrow
    python3 polymarket/backtests/bonding.py polymarket/data/sample.parquet

Prices are last-traded snapshots (12-hourly), not guaranteed fills, and fees
did not exist for most of this period; we apply today's fees as if they did.
"""
import math
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fees import taker_fee  # noqa: E402

# category -> taker fee rate; categories without a published rate assume 0.05
RATES = {"Crypto": 0.07, "Sports": 0.05, "Politics": 0.04}
BANDS = [(0.90, 0.95), (0.95, 0.97), (0.97, 0.99), (0.99, 1.001)]
WORSE_FILL = 0.01  # taker pays ~1c above the last price (crossing the spread)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def roi(win, price, fee):
    return ((win - price - fee) / (price + fee)).mean()


def main(path):
    df = pd.read_parquet(path)
    df["fav"] = df.price.where(df.price >= 0.5, 1 - df.price)
    df["win"] = (((df.price >= 0.5) & (df.outcome == 1))
                 | ((df.price < 0.5) & (df.outcome == 0))).astype(float)
    df["r"] = df.category.map(RATES).fillna(0.05)

    for h in (30, 7, 1):
        print(f"\n{h} days before resolution")
        print("band | bets | avg price | win % (95% CI) | losses | "
              "maker | taker fee only | taker +1c fill")
        for lo, hi in BANDS:
            s = df[(df.horizon_days == h) & (df.fav >= lo) & (df.fav < hi)]
            n, k = len(s), int(s.win.sum())
            if not n:
                continue
            ci = wilson(k, n)
            pt = (s.fav + WORSE_FILL).clip(upper=0.999)
            print(f"{lo:.2f}-{min(hi, 1):.2f} | {n} | {s.fav.mean():.3f} | "
                  f"{100*k/n:.1f} ({100*ci[0]:.1f}-{100*ci[1]:.1f}) | {n-k} | "
                  f"{100*roi(s.win, s.fav, 0):+.2f}% | "
                  f"{100*roi(s.win, s.fav, taker_fee(1, s.fav, s.r)):+.2f}% | "
                  f"{100*roi(s.win, pt, taker_fee(1, pt, s.r)):+.2f}%")


if __name__ == "__main__":
    main(sys.argv[1])
