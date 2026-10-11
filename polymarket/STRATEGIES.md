# Deep dive: 3 strategies, with fees (Oct 2026)

The three we picked from `RESEARCH.md`:
- **#2 Prices that don't add up** (basket / "rebalancing" arbitrage)
- **#6 Near-sure bets** ("bonding": buy at 90–99¢, hold to the end)
- **#7 Copy trading** (follow good wallets)

Market making is ruled out (already researched separately).

Every number about fees below comes from `fees.py`, which uses **the exact
formula from Polymarket's own Python library**. Run `python3 polymarket/fees.py`
to reproduce the tables.

---

## 0. The fee rule (read this first)

From Polymarket's official client code (`py-clob-client-v2`, `fees.py`):

```
fee = shares × rate × (price × (1 − price)) ^ exponent
```

- **Only takers pay.** A taker is someone whose order fills *right away*
  against an order already waiting. If your order waits in the book (a
  "limit order" that someone else fills), you're a **maker** and pay **0**.
- `rate` and `exponent` are set **per market**. Our bot must read them from
  the API for every market (the market-info call returns them as `fd.r` and
  `fd.e`). Don't trust blog tables.
- Published rates (Oct 2026, exponent 1): **crypto 0.07, sports 0.05,
  politics 0.04, geopolitics 0 (free)**. Other categories have their own rates.
- Fees are **biggest at 50¢** and tiny near 1¢ or 99¢.
- Apps built on Polymarket (like copy-trading apps) can add a **"builder fee"**
  of up to 1% on top. Polymarket's code has a slot for this.
- Holding a winning share until the end and cashing it in has **no fee**.

**Fee per share (and as a % of what you paid):**

| price | crypto | sports | politics | geopolitics |
|---|---|---|---|---|
| 10¢ | 0.63¢ (6.3%) | 0.45¢ (4.5%) | 0.36¢ (3.6%) | 0 |
| 30¢ | 1.47¢ (4.9%) | 1.05¢ (3.5%) | 0.84¢ (2.8%) | 0 |
| 50¢ | 1.75¢ (3.5%) | 1.25¢ (2.5%) | 1.00¢ (2.0%) | 0 |
| 70¢ | 1.47¢ (2.1%) | 1.05¢ (1.5%) | 0.84¢ (1.2%) | 0 |
| 90¢ | 0.63¢ (0.7%) | 0.45¢ (0.5%) | 0.36¢ (0.4%) | 0 |
| 97¢ | 0.20¢ (0.21%) | 0.15¢ (0.15%) | 0.12¢ (0.12%) | 0 |
| 99¢ | 0.07¢ (0.07%) | 0.05¢ (0.05%) | 0.04¢ (0.04%) | 0 |

Two other costs that aren't "fees" but act like them:
- **The spread**: as a taker you buy at the *ask* (seller's price), which is
  usually 1¢ or more above the last trade price.
- **Slippage**: big orders eat through several price levels.

---

## #2. Prices that don't add up (basket arbitrage)

### How it works
- In a YES/NO market, 1 YES + 1 NO always pays exactly $1. So if you can buy
  both for less than $1 total, you lock in profit.
- You don't even have to wait for the end: Polymarket lets you **"merge"**
  1 YES + 1 NO back into $1 at any time. And the reverse, **"split"**, turns
  $1 into 1 YES + 1 NO. So if YES + NO can be **sold** for more than $1,
  split $1 and sell both.
- Markets with many outcomes ("Who wins the election?") are called
  **NegRisk** markets. Only one outcome can win, so all the YES prices
  should add up to $1. Polymarket also has a "convert" tool there that turns
  a set of NO shares into YES shares on the other outcomes plus cash.

### What the research says
- **The famous $40 million**: a 2025 paper estimated ~$40M of arbitrage
  profit on Polymarket from Apr 2024 to Apr 2025: about **$10.6M** from
  YES/NO pairs and **$29M** from many-outcome (NegRisk) markets. Secondary
  write-ups say the top wallet made ~$2M over ~4,000 trades and the top 10
  took ~20% of all profit (not verified against the paper).
  ([paper](https://arxiv.org/abs/2508.03474),
  [Medium summary](https://medium.com/@navnoorbawa/negrisk-market-rebalancing-how-29m-was-extracted-from-multi-condition-prediction-markets-2f1f91644c5b),
  [dev.to summary](https://dev.to/abrownfox001/polymarket-arbitrage-analysis-2026-40m-extracted-via-market-rebalancing-combinatorial-3lb5))
- **But a stricter 2026 paper disagrees hugely.** It only counts arbitrage
  that could *actually be done* (enough shares available at those prices,
  fees included, and only using moves the system really allows). For the
  same period it finds about **$291,000**, not $40M. It also found most
  "violations" are on the side you **can't** easily exploit (prices adding to
  *more* than $1 on YES), and the exploitable side closes faster.
  ([Executable Arbitrage paper](https://arxiv.org/abs/2608.00666))
- **NBA study (75M order book snapshots, 173 games):** only **7** real
  YES/NO arbitrage moments, lasting a **median of 3.6 seconds**. Most
  multi-market chances were in the last minutes of games and averaged only
  **~15 shares** you could actually buy. Conclusion: "highly efficient."
  ([NBA paper](https://arxiv.org/abs/2605.00864))

### Fees: how big the gap must be just to break even (taker on every leg)
For a full basket, total fee = `rate × Σ p(1 − p)`. More outcomes and
prices nearer 50¢ = bigger fees.

| market shape | crypto | sports | politics | geopolitics |
|---|---|---|---|---|
| YES/NO at 50/50 | 3.50¢ | 2.50¢ | 2.00¢ | 0 |
| YES/NO at 90/10 | 1.26¢ | 0.90¢ | 0.72¢ | 0 |
| 3 outcomes 60/30/10 | 3.78¢ | 2.70¢ | 2.16¢ | 0 |
| 5 equal outcomes | 5.60¢ | 4.00¢ | 3.20¢ | 0 |
| 10 equal outcomes | 6.30¢ | 4.50¢ | 3.60¢ | 0 |
| 1 favourite 80% + 9 small | 2.49¢ | 1.78¢ | 1.42¢ | 0 |

Read it like this: in a 10-outcome politics market, the YES prices must add
up to **less than 96.4¢** before buying all of them makes any money. The
research above says gaps that big basically don't last.

### Ways around the fee
1. **Fee-free categories (geopolitics).** No taker fee, so tiny gaps can
   count. This is the most interesting lead. (Still have to beat other bots
   and pay the spread.)
2. **Be a maker on some legs.** Put limit orders on the legs and only take
   the last one. No fee on maker legs, but **"legging risk"**: if only some
   legs fill and prices move, you're left holding a normal bet.
3. **Lopsided markets.** Fees are smallest when one outcome is near 100%,
   so baskets with one big favourite cost less in fees.

### Verdict
**Weak as a money maker for us.** The big profits were mostly in 2024, are
now hunted by fast bots, and the stricter study says the real amount was
~100× smaller than the headline. **Still worth building as a read-only
scanner**: it's cheap, risk-free, and the only realistic lead is
fee-free geopolitics markets. We'd log every gap with its fee-adjusted size
and how long it lasted before trusting it with money.

---

## #6. Near-sure bets ("bonding")

### How it works
Buy outcomes priced 90–99¢ and hold to the end to collect the last few cents.
Small win most of the time; rarely you lose the whole stake.

### Fees: nice for this strategy
Because fees shrink near 99¢, they barely matter here:
- Fee eats `rate × price` of your possible profit. At 97¢ in politics:
  0.04 × 0.97 ≈ **4% of the profit**. In crypto ≈ 7%.
- **Win rate needed to break even** as a taker:

| buy at | crypto | sports | politics | geopolitics |
|---|---|---|---|---|
| 90¢ | 90.63% | 90.45% | 90.36% | 90.00% |
| 95¢ | 95.33% | 95.24% | 95.19% | 95.00% |
| 97¢ | 97.20% | 97.15% | 97.12% | 97.00% |
| 99¢ | 99.07% | 99.05% | 99.04% | 99.00% |

**The real killer is the spread, not the fee.** At 99¢ the whole profit is
1¢. If you buy 1¢ above the last price (normal for a taker), the profit is
gone. So this strategy only makes sense with **limit orders (maker, 0 fee)**.

### Our own backtest (real data)
We ran `backtests/bonding.py` on **2,946 real resolved Polymarket markets
(2023–2026)** from the open honest-odds study. For each market we "bought" the
favourite 30, 7 and 1 days before the end and applied today's fees.
([dataset](https://github.com/CH4RL3I/honest-odds))

Columns: **maker** = got our limit order filled at the last price, no fee.
**taker fee only** = paid the fee. **taker +1¢** = paid the fee *and*
bought 1¢ above the last price (the realistic taker case).

**30 days before the end**

| band | bets | avg price | win % (95% range) | losses | maker | taker fee only | taker +1¢ |
|---|---|---|---|---|---|---|---|
| 90–95¢ | 358 | 92.6¢ | 93.3 (90.2–95.5) | 24 | +0.78% | +0.43% | −0.59% |
| 95–97¢ | 238 | 96.0¢ | 96.6 (93.5–98.3) | 8 | +0.69% | +0.49% | −0.50% |
| 97–99¢ | 468 | 98.1¢ | 98.5 (96.9–99.3) | 7 | +0.38% | +0.29% | −0.68% |
| 99¢+ | 704 | 99.7¢ | 99.7 (99.0–99.9) | 2 | +0.04% | +0.02% | −0.19% |

**7 days before the end**

| band | bets | avg price | win % (95% range) | losses | maker | taker fee only | taker +1¢ |
|---|---|---|---|---|---|---|---|
| 90–95¢ | 273 | 92.7¢ | 89.7 (85.6–92.8) | 28 | −3.25% | −3.58% | −4.56% |
| 95–97¢ | 193 | 96.1¢ | 98.4 (95.5–99.5) | 3 | +2.50% | +2.31% | +1.30% |
| 97–99¢ | 436 | 98.1¢ | 98.9 (97.3–99.5) | 5 | +0.73% | +0.64% | −0.33% |
| 99¢+ | 1232 | 99.7¢ | 99.4 (98.8–99.7) | 7 | −0.25% | −0.27% | −0.47% |

**1 day before the end**

| band | bets | avg price | win % (95% range) | losses | maker | taker fee only | taker +1¢ |
|---|---|---|---|---|---|---|---|
| 90–95¢ | 205 | 92.8¢ | 89.8 (84.8–93.2) | 21 | −3.29% | −3.62% | −4.60% |
| 95–97¢ | 151 | 96.1¢ | 95.4 (90.7–97.7) | 7 | −0.78% | −0.96% | −1.94% |
| 97–99¢ | 351 | 98.2¢ | 99.1 (97.5–99.7) | 3 | +0.96% | +0.87% | −0.10% |
| 99¢+ | 1618 | 99.7¢ | 99.6 (99.2–99.8) | 6 | −0.12% | −0.13% | −0.28% |

**What this tells us:**
- **Prices are honest.** A 96¢ favourite wins about 96% of the time. There is
  no big hidden edge. The "95% range" column always includes the price paid.
- **Taker = lose.** With a realistic 1¢ worse fill, almost every row is
  negative. The one positive row (7 days, 95–97¢) comes from only 3 losses
  out of 193 bets, which is luck-sized, not proof.
- **Maker results are around zero**, slightly positive 30 days out. That
  matches a bigger study of 588 million Polymarket trades, which found
  buying at 90¢+ earned only **+0.83¢ per dollar** (before fees), while
  buying at under 10¢ lost 19.3¢ per dollar.
  ([FLB paper](https://arxiv.org/abs/2609.12878))
- **Losses come from everywhere**: politics, sports, economics. No category
  was "safe".
- **Time cost**: money sits locked until the end. +0.5% over 30 days is
  ~6% a year at best, and only if the edge is real.

Limits of our test: prices are 12-hourly last trades (not guaranteed fills);
only markets with $20k+ volume that ran 31+ days; fees didn't exist for most
of this period (we applied them anyway); disputed results were taken as final.

### Something that helps: holding rewards
Polymarket pays a **4% yearly reward** on positions held in certain
long-term markets (mostly big elections), paid daily. A near-sure position
in an eligible market earns this on top. Check the live list before relying
on it.
([holding rewards](https://docs.polymarket.com/polymarket-learn/trading/holding-rewards))

### Verdict
**Break-even at best.** If we try it: limit orders only (never take),
30-ish days out, skip markets with vague rules (dispute risk), cap the size
per market, and prefer markets with the 4% holding reward. Expect a few %
a year, not a money machine.

---

## #7. Copy trading

### How it works
Find wallets that make money, copy their trades. All Polymarket wallet data
is public and free (Data API: positions, trades/activity, leaderboard; no
key needed).
([Data API docs](https://docs.polymarket.com/api-reference/data-api/overview.md))

### Fees: the follower always pays more than the leader
The leader often trades with limit orders (maker, 0 fee). The copier sees the
trade *after* it happens, so the copier:
1. **Buys worse** (the price already moved: "drift"),
2. **Pays the taker fee** (to get filled fast),
3. Often **pays a copy app's builder fee** (up to 1%) plus a subscription,
4. Pays fees **again on the way out** if the leader sells before the end.

Example (made-up leader with a 4¢ edge per share at 50¢, politics fees,
entry only):

| copier fills | no app fee | 1% app fee |
|---|---|---|
| same price | +3.00¢ | +2.50¢ |
| 1¢ worse | +2.00¢ | +1.49¢ |
| 2¢ worse | +1.00¢ | +0.48¢ |
| 3¢ worse | 0.00¢ | −0.53¢ |

A **4¢ edge is already a very good trader**. A copy bot that is a couple of
seconds late can easily lose 2–3¢, so most of the edge is gone before any
exit fees. The more people copy the same wallet, the worse the drift gets.

### What the research says
- No independent study measures how copiers actually do. Every copy-trading
  "result" online is from a company selling the tool.
  ([Tradox model](https://tradoxvps.com/polymarket-copy-trading/))
- Most wallets lose: estimates range from **~84% unprofitable** (2.5M
  wallets) to only **~7.6% profitable**. Picking from the top is easy to
  get fooled by luck (**"survivorship bias"**: you only see the winners who
  are still around, not the many who did the same thing and lost).
  ([Dropstab](https://news.dropstab.com/research/polymarket-how-to-make-money))
- High win rates often come from near-sure bets (see #6): lots of tiny wins
  hiding a rare big loss. A 95% win rate can still lose money.
- **Insider risk**: in April 2026 Polymarket audited copy-trading apps in its
  Builders Program (Polycool, Kreo) after they were marketing tools to copy
  wallets suspected of trading on secret information (e.g. one wallet won 93%
  of bets on military strikes). Copying an insider can count as joining in.
  ([Unchained](https://unchainedcrypto.com/polymarket-audits-builders-program-startups-over-insider-trading-concerns/))

### The better money idea: Vett for Polymarket
Copying is a weak *trading* strategy, but there's a real *product* here, and
it's exactly what this repo already does for Hyperliquid:
- **Score wallets by what a copier would actually earn**, after drift, the
  taker fee and the exit fee, not by the leader's own P&L. Flag
  "fake good" wallets whose wins are all near-sure bets. That's Vett's
  "it advertises green, but a copier would lose" angle, and fees make the gap
  even bigger on Polymarket.
- **Ways it earns money:** Polymarket's **Builders Program** pays app
  makers a fee (up to 1% taker / 0.5% maker) on trades sent through their
  app, plus a weekly reward pool split by volume. Or subscriptions, or the
  same TikTok/YouTube content engine Vett already runs.
  ([Builder fees](https://docs.polymarket.com/programs/builders/fees),
  [Builders Program guide](https://polymart.app/blog/polymarket-builders-program))
- **Stay clean**: don't promote copying suspected-insider wallets (that's
  what got the other apps audited). An honest "don't copy this" scanner is
  the opposite of that, which is a selling point.

### Verdict
**Don't copy-trade with our own money.** **Do consider building a Polymarket
"copyability" scanner** as a Vett product. It uses free public data, needs no
trading keys, and doesn't need us to beat professional bots.

---

## Overall ranking after the deep dive

| strategy | after fees | risk | effort | recommendation |
|---|---|---|---|---|
| #7 as a product (Vett scanner) | not trading, so fees hit the *users*, which is the selling point | low | medium | **best lead** |
| #6 near-sure bets (maker only) | ~0 to slightly + | rare total losses | low | maybe, small, with strict rules |
| #2 basket arb | − in fee categories; maybe tiny + in geopolitics | legging, speed | high | read-only scanner only |
| #7 copying with our money | − after drift + fees | insider/rules risk | low | no |

## Next steps
1. Allow `gamma-api.polymarket.com`, `clob.polymarket.com` and
   `data-api.polymarket.com` in this cloud session's network settings so we
   can pull live data.
2. Build the read-only **Polymarket copyability scanner** (reuse Vett's
   analyzer ideas): pull top wallets, rebuild their trades, simulate a
   follower with drift + real per-market fees.
3. Build the read-only **basket-gap scanner**, focused on geopolitics.
4. Re-run the near-sure-bet backtest on a bigger dataset (the 36 GB
   [prediction-market-analysis](https://github.com/jon-becker/prediction-market-analysis)
   dataset) once we have somewhere with room for it.

## Sources
- Fee formula: [py-clob-client-v2 on PyPI](https://pypi.org/project/py-clob-client-v2/) (`fees.py`) ·
  [Polymarket fees docs](https://docs.polymarket.com/trading/fees) ·
  [changelog](https://docs.polymarket.com/changelog/predictions)
- Arbitrage: [Saguillo et al. 2025](https://arxiv.org/abs/2508.03474) ·
  [Executable Arbitrage 2026](https://arxiv.org/abs/2608.00666) ·
  [NBA arbitrage 2026](https://arxiv.org/abs/2605.00864) ·
  [NegRisk adapter](https://github.com/polymarket/neg-risk-ctf-adapter) ·
  [Medium: NegRisk $29M](https://medium.com/@navnoorbawa/negrisk-market-rebalancing-how-29m-was-extracted-from-multi-condition-prediction-markets-2f1f91644c5b) ·
  [dev.to summary](https://dev.to/abrownfox001/polymarket-arbitrage-analysis-2026-40m-extracted-via-market-rebalancing-combinatorial-3lb5)
- Near-sure bets: [honest-odds dataset](https://github.com/CH4RL3I/honest-odds) ·
  [FLB paper, 588M trades](https://arxiv.org/abs/2609.12878) ·
  [holding rewards](https://docs.polymarket.com/polymarket-learn/trading/holding-rewards) ·
  [bonding guide](https://startpolymarket.com/strategies/bonding/)
- Copy trading: [Data API](https://docs.polymarket.com/api-reference/data-api/overview.md) ·
  [Builder fees](https://docs.polymarket.com/programs/builders/fees) ·
  [Builders guide](https://polymart.app/blog/polymarket-builders-program) ·
  [Unchained: builders audit](https://unchainedcrypto.com/polymarket-audits-builders-program-startups-over-insider-trading-concerns/) ·
  [Tradox copy math](https://tradoxvps.com/polymarket-copy-trading/) ·
  [Dropstab wallet stats](https://news.dropstab.com/research/polymarket-how-to-make-money)
