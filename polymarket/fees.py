"""Polymarket taker-fee math, copied from the official client.

Source: py-clob-client-v2 1.2.0, fees.py:
    fee = shares * rate * (price * (1 - price)) ** exponent
`rate` and `exponent` come per market from the CLOB market info ("fd": {"r", "e"}).
Makers pay 0. Always read r/e from the API at run time; the defaults below are
the published category rates (Oct 2026) and assume exponent 1.

Run `python3 polymarket/fees.py` to print the tables used in STRATEGIES.md.
"""

RATES = {"crypto": 0.07, "sports": 0.05, "politics": 0.04, "geopolitics": 0.0}


def taker_fee(shares, price, rate, exponent=1.0):
    """Fee in dollars for taking `shares` at `price`."""
    return shares * rate * (price * (1 - price)) ** exponent


def basket_arb(prices, rate, exponent=1.0, payout=1.0):
    """Buy one share of every outcome (they should sum to $1) as a taker.
    Returns (gross edge, fees, net edge) per basket, in dollars."""
    cost = sum(prices)
    fees = sum(taker_fee(1, p, rate, exponent) for p in prices)
    return payout - cost, fees, payout - cost - fees


def bond(price, rate, win_prob, exponent=1.0):
    """Buy the favourite at `price` as a taker and hold to resolution.
    Returns (profit per $ if it wins, fee per $, expected profit per $)."""
    fee = taker_fee(1, price, rate, exponent)
    spent = price + fee
    return (1 - spent) / spent, fee / spent, (win_prob - spent) / spent


def copy_edge(leader_edge, drift, price, rate, builder_rate=0.0, exponent=1.0):
    """Edge per share left for a copier who buys `drift` dollars worse than the
    leader and pays the taker fee plus any copy-app builder fee (% of notional)."""
    p = price + drift
    return leader_edge - drift - taker_fee(1, p, rate, exponent) - builder_rate * p


if __name__ == "__main__":
    print("== Fee per share and per $ spent, by price ==")
    print("price | " + " | ".join(f"{c} ({r})" for c, r in RATES.items()))
    for p in (0.05, 0.10, 0.30, 0.50, 0.70, 0.90, 0.95, 0.97, 0.99):
        cells = [f"{100*taker_fee(1,p,r):.2f}c ({100*taker_fee(1,p,r)/p:.2f}%)" for r in RATES.values()]
        print(f"{p:.2f} | " + " | ".join(cells))

    print("\n== Basket arbitrage: how big must the gap be just to break even? ==")
    cases = {
        "YES/NO at 50/50": [0.5, 0.5],
        "YES/NO at 90/10": [0.9, 0.1],
        "3 outcomes 60/30/10": [0.6, 0.3, 0.1],
        "5 equal outcomes": [0.2] * 5,
        "10 equal outcomes": [0.1] * 10,
        "1 favourite 80% + 9 x 2.2%": [0.8] + [0.2 / 9] * 9,
    }
    print("market | " + " | ".join(RATES))
    for name, ps in cases.items():
        cells = [f"{100*basket_arb(ps, r)[1]:.2f}c" for r in RATES.values()]
        print(f"{name} | " + " | ".join(cells))

    print("\n== Near-sure bet (taker): win rate needed to break even ==")
    for p in (0.90, 0.95, 0.97, 0.99):
        cells = [f"{100*(p + taker_fee(1,p,r)):.2f}%" for r in RATES.values()]
        print(f"buy at {p:.2f} | " + " | ".join(cells))

    print("\n== Copy trading: leader has 4c edge at 50c, politics fees ==")
    for drift in (0.0, 0.01, 0.02, 0.03):
        for b in (0.0, 0.01):
            e = copy_edge(0.04, drift, 0.50, RATES["politics"], b)
            print(f"copier fills {100*drift:.0f}c worse, builder fee {100*b:.0f}% -> copier edge {100*e:+.2f}c/share")
