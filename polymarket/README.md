# polymarket/ — Polymarket trading bot research

A separate project that lives inside the vett repo. It has nothing to do with
the video pipeline in `code/` and does not touch it.

## What's here
- `RESEARCH.md` — first pass: ways people try to make money with Polymarket
  bots, the costs, and the legal/access questions.
- `STRATEGIES.md` — deep dive on 3 strategies (basket arbitrage, near-sure
  bets, copy trading) with fees worked into every number.
- `fees.py` — Polymarket's official taker-fee formula + break-even tables.
  Run: `python3 polymarket/fees.py`
- `backtests/bonding.py` — near-sure-bet backtest on 2,946 real resolved
  markets (see the file for how to get the data).

## Status
- [x] First research pass (Oct 2026)
- [x] Deep dive on #2, #6, #7 with fees + near-sure-bet backtest
- [x] Market making ruled out
- [ ] Decide which platform we can legally use (Polymarket global vs Polymarket US)
- [ ] Read-only data scanner (no money, no keys) to test ideas on real prices
- [ ] Paper trading (pretend trades, track results) before any real money

## Rules for this folder
- No API keys or wallet private keys in code. Use `.env` (already gitignored).
- Nothing trades real money until a strategy has been paper-tested.
