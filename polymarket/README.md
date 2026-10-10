# polymarket/ — Polymarket trading bot research

A separate project that lives inside the vett repo. It has nothing to do with
the video pipeline in `code/` and does not touch it.

## What's here
- `RESEARCH.md` — ways people try to make money with Polymarket bots, what
  actually works in 2026, the costs, and the legal/access questions.

## Status
- [x] First research pass (Oct 2026)
- [ ] Decide which platform we can legally use (Polymarket global vs Polymarket US)
- [ ] Read-only data scanner (no money, no keys) to test ideas on real prices
- [ ] Paper trading (pretend trades, track results) before any real money

## Rules for this folder
- No API keys or wallet private keys in code. Use `.env` (already gitignored).
- Nothing trades real money until a strategy has been paper-tested.
