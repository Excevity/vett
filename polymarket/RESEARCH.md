# Polymarket trading bots: research notes (Oct 2026)

Plain-language notes on the ways people try to make money with bots on
Polymarket, and how likely each one is to work for a small, solo trader.

> Warning about sources: most "Polymarket bot" articles online are written by
> people selling bots, servers, or courses. Their win rates are not checked by
> anyone. The numbers below that come from independent or official sources are
> marked as such. Everything else should be treated as a claim, not a fact.

---

## 1. Quick basics (words you'll see a lot)

- **Prediction market**: you buy "YES" or "NO" shares on a question
  ("Will X happen by date Y?"). A winning share pays **$1.00**, a losing share
  pays **$0**. The price (say 63¢) is roughly the crowd's guess of the chance.
- **Order book (CLOB)**: the list of everyone's buy and sell offers at each
  price. Polymarket's is called the CLOB ("central limit order book").
- **Maker**: you place an order that *waits* in the book (a "limit order").
  You add liquidity. On Polymarket, **makers pay no fees** and can get paid
  rewards.
- **Taker**: you trade *immediately* against someone's waiting order. You
  remove liquidity. **Takers pay the fees.**
- **Spread**: the gap between the best buy price and the best sell price.
- **Arbitrage ("arb")**: buying and selling related things at the same time so
  you lock in a profit no matter what happens.
- **Slippage**: when your order fills at a worse price than you expected
  because there weren't enough shares at the price you saw.
- **Resolution**: how and when a market is officially decided. Polymarket uses
  a system called **UMA** where results can be **disputed**, which can delay or
  change an outcome.

---

## 2. The hard truth first

- An on-chain study of ~95 million Polymarket transactions (Apr 2024 to Dec
  2025) reportedly found that only **about 0.5% of wallets made more than
  $1,000 profit**. (Seen via secondary write-ups, not the original study.)
- A one-week look at the 15-minute crypto markets found only **about 37% of
  wallets were profitable, before fees**. After fees it's worse.
  ([Telonex](https://telonex.io/research/top-crypto-traders-polymarket-15m))
- The easy "free money" tricks from 2024 have mostly been competed away by
  faster, better-funded bots, and Polymarket added fees specifically to kill
  some of them.

So: **the default result for a new bot is losing money.** Any plan has to
explain *why we'd be the ones who win*.

---

## 3. Costs (fees) in 2026

This matters because most bot strategies make tiny profits per trade, and fees
can wipe them out.

- **Makers pay 0%.** Only takers pay.
- The reported taker fee formula is:
  `fee = shares × feeRate × price × (1 − price)`
  This means fees are **biggest at 50¢** and shrink to near zero at 1¢ or 99¢.
- Reported `feeRate` by category: **crypto 0.07, sports 0.05** (raised from
  0.03), **politics 0.04, geopolitics 0 (free)**, and other categories have
  their own rates.
  ([changelog](https://docs.polymarket.com/changelog/predictions),
  [fees page](https://docs.polymarket.com/trading/fees))
- Example if that's right: buying 100 crypto shares at 50¢ = 100 × 0.07 × 0.5 ×
  0.5 = **$1.75 fee on a $50 trade (3.5%)**. That's huge for a bot.
- **Don't hardcode fees.** They change often and third-party sites disagree.
  The bot should ask the API for each market's fee rate at run time.
- The old `py-clob-client` Python library **no longer works**. Use
  `py-clob-client-v2` (CLOB V2 went live in 2026).
  ([V2 migration](https://docs.polymarket.com/v2-migration))

---

## 4. Strategies, ranked by how realistic they are for us

### A. Market making + liquidity rewards — **most realistic**
**What it is:** the bot keeps a buy order a bit below the fair price and a sell
order a bit above it. When both fill, you keep the gap (the spread).

**Why it's attractive in 2026:**
- Makers pay no fees.
- **Liquidity rewards**: Polymarket pays makers daily (midnight UTC) just for
  keeping qualifying orders close to the middle price in selected markets. Each
  market sets a minimum order size and max distance from the middle.
  ([liquidity rewards](https://docs.polymarket.com/programs/liquidity-rewards))
- **Maker rebates**: part of the taker fees is given back to makers. Official
  docs listed 20% for 5/15-minute crypto markets and 25% for some sports
  markets, but this changes.
  ([maker rebates](https://docs.polymarket.com/polymarket-learn/trading/maker-rebates-program))

**The catch — "adverse selection":** this fancy term means *the people who
trade against you often know something you don't*. If news breaks and your
old order is still sitting there, a faster trader buys it from you at a bad
price. Market makers lose money this way. The bot must cancel/move orders
fast when prices jump, and avoid markets right before big news.

**Other risk — inventory:** if only one side of your orders fills, you're left
holding shares. If the market resolves against you, those go to $0.

**Verdict:** best starting point. Earn rewards in quiet, slow markets where
speed matters less. Start tiny.

### B. "Rebalancing" arbitrage (prices that don't add up) — **mostly taken**
**What it is:** in a market, YES + NO should cost $1. In a market with many
outcomes (e.g. "Who wins the election?"), all the YES prices should add up to
$1. If they add up to 97¢, buy all of them and you're guaranteed $1 back.

**Evidence:** an academic paper estimates **about $40 million** was made this
way on Polymarket from Apr 2024 to Apr 2025.
([arXiv 2508.03474](https://arxiv.org/abs/2508.03474v1),
[Decrypt](https://decrypt.co/339958/40-million-free-money-glitch-crypto-prediction-markets))

**The catch:** that money is exactly why lots of fast bots now hunt for it.
The gaps last seconds, are usually tiny, and taker fees can eat the whole
profit. You also often can't buy *all* legs at the price you saw (slippage).

**Verdict:** good as a **scanner to learn from** (cheap to build, no risk if
read-only). Unlikely to be our money maker on its own.

### C. Combinatorial / logic arbitrage across related markets — **interesting**
**What it is:** two *different* markets that are logically linked but priced
inconsistently. Example: "Candidate wins state X" priced higher than "Party
wins state X" (impossible, the first implies the second).

**Why interesting:** harder to spot automatically, so fewer bots do it. An AI
model (like Claude) could help find linked market pairs.

**The catch:** resolution rules differ in small print. Two markets that look
linked might resolve differently. Read the rules for every pair.

**Verdict:** worth researching. Our possible edge = smarter matching, not speed.

### D. Cross-platform arbitrage (Polymarket vs Kalshi) — **medium**
**What it is:** same question, different price on two sites. Buy YES on one,
NO on the other, total under $1, guaranteed profit... in theory.

**The catch:** the two sites can word or resolve the "same" question
differently, so you can lose *both* sides. You need money on both platforms,
and the gaps are shrinking. Fees on both sides.

**Verdict:** possible later. Resolution-wording risk is the big danger.

### E. Speed ("latency") arbitrage on 5/15-minute crypto markets — **dead for us**
**What it is:** Polymarket has "Will BTC be up in 15 minutes?" markets. When BTC
jumps on Binance, Polymarket prices can lag a few seconds. Bots raced to buy
before the price caught up.

**What happened:** Polymarket added **dynamic taker fees** to these markets in
Jan 2026 *specifically to stop this*. Pure taker bots lost most of their edge.
The remaining players use rented servers next to the exchange.
([Coinspectator](https://coinspectator.com/mainstream/2026/01/07/polymarket-introduces-dynamic-fees-to-curb-latency-arbitrage-in-short-term-crypto-markets/),
[DeFi Rate](https://defirate.com/?p=3210))

**Verdict:** skip. We can't win a speed race from a laptop or a free cloud box.

### F. "Bonding" (buying near-certain outcomes at 95–99¢) — **small, with rare big losses**
**What it is:** buy outcomes that are almost surely winning, collect the last
1–5¢ when it resolves. Like a short-term bond.

**The catch:** "almost certain" isn't certain. One surprise or a resolution
dispute wipes out the gains of dozens of wins. Your money is also locked up
until resolution.
([guide](https://startpolymarket.com/strategies/bonding/),
[resolution risk](https://orrery.me/learn/polymarket-resolution-risk))

**Verdict:** only with strict rules (avoid markets with vague wording, cap size
per market). Needs a backtest on past resolved markets first.

### G. Copy trading whale wallets — **this is Vett's home turf**
**What it is:** follow wallets with good track records and copy their trades.

**The catch (same as Vett found on Hyperliquid):** high win rates often come
from buying 95¢ outcomes (lots of small wins hiding rare big losses), and by
the time you copy, the price has moved. A trade that was good for the whale
can be bad for the follower.
([pm.wiki listings](https://pm.wiki/projects/polymaster-2))

**Verdict:** copying is weak as a strategy, **but a Vett-style "is this wallet
actually worth copying?" scanner for Polymarket could be a product.** Vett
already does exactly this for Hyperliquid, and Polymarket wallet data is public.
That's a way to make money *from* the Polymarket bot craze without needing to
out-trade the pros.

### H. Information / forecasting edge (news bots, AI forecasting) — **hard but open**
**What it is:** the bot reads news or data and decides the market price is
wrong, then bets.

**The catch:** you're betting against everyone else's opinion, including
professionals. You need to *prove* your forecasts beat the market price on
past data before trusting them.

**Verdict:** a long-term research idea, not a first project.

---

## 5. Legal / access question (must answer first)

Where you live decides which Polymarket you can use.

- **Polymarket (global)** runs on the Polygon blockchain using a crypto
  dollar (pUSD). **US users are blocked from opening new trades** there
  (close-only for US IPs). Using a VPN to get around this breaks their terms
  and can get funds frozen. Don't.
- **Polymarket US** is a separate, US-regulated exchange (CFTC-licensed, after
  Polymarket bought QCEX in 2025). It has **its own API** for bots: you verify
  your identity in the app, then create API keys at `polymarket.us/developer`.
  Official Python SDK: `polymarket-us`. Reported limit: ~20 requests/second.
  Different markets, different IDs, US dollars instead of crypto.
  ([CoinDesk](https://www.coindesk.com/business/2025/11/25/polymarket-secures-cftc-approval-for-regulated-u-s-return),
  [developer page](https://polymarket.us/developer),
  [QuantVPS](https://www.quantvps.com/blog/polymarket-us-api-available))
- Some US states are fighting prediction markets in court, so check your
  state too.
- Rewards programs and fees above are for the **global** platform. Polymarket
  US may have different (or no) maker rewards — needs checking.
- **Taxes:** winnings are taxable income in most countries. Keep records.

---

## 6. Suggested plan

1. **Decide the platform** (global vs US) based on where you live.
2. **Build a read-only scanner** (no keys, no money): pull live prices and
   flag (a) markets where prices don't add up to $1 after fees, and
   (b) markets with liquidity rewards and wide spreads. This teaches us how
   the market really behaves.
3. **Backtest** (test a strategy on past data) for bonding and market making.
4. **Paper trade** (pretend trades with fake money, real prices) for 2+ weeks.
5. Only then, **real money in tiny amounts** with hard limits: max $ per
   market, max total, auto-stop on a daily loss.
6. Side track: a **Polymarket version of the Vett wallet scanner**, which fits
   what this repo already does well.

---

## 7. Open questions / to check
- Exact current fee rates per category (read from the API, not blogs).
- Which markets currently have liquidity rewards, and how big they are.
- Whether Polymarket US offers maker rewards/rebates.
- Polymarket API hosts (`gamma-api.polymarket.com`, `clob.polymarket.com`)
  are **blocked by this cloud session's network settings**, so live data
  can't be pulled from here yet.

## Sources
- [Polymarket fees docs](https://docs.polymarket.com/trading/fees) ·
  [changelog](https://docs.polymarket.com/changelog/predictions) ·
  [V2 migration](https://docs.polymarket.com/v2-migration) ·
  [liquidity rewards](https://docs.polymarket.com/programs/liquidity-rewards) ·
  [maker rebates](https://docs.polymarket.com/polymarket-learn/trading/maker-rebates-program)
- [Arbitrage paper, arXiv 2508.03474](https://arxiv.org/abs/2508.03474v1) ·
  [Decrypt on the $40M](https://decrypt.co/339958/40-million-free-money-glitch-crypto-prediction-markets)
- [Telonex 15m crypto trader study](https://telonex.io/research/top-crypto-traders-polymarket-15m)
- [Coinspectator on dynamic fees](https://coinspectator.com/mainstream/2026/01/07/polymarket-introduces-dynamic-fees-to-curb-latency-arbitrage-in-short-term-crypto-markets/) ·
  [DeFi Rate](https://defirate.com/?p=3210) ·
  [DEV: Feb 2026 bot numbers](https://dev.to/lkto1m/february-2026-changed-polymarket-forever-heres-what-happened-to-my-bots-numbers-2fi5)
- [Simple Mondays: are bots profitable?](https://simplemondays.com/technology/are-polymarket-trading-bots-actually-profitable-the-math-behind-2026-s-predictio/) ·
  [Medium: 4 strategies](https://medium.com/illumination/beyond-simple-arbitrage-4-polymarket-strategies-bots-actually-profit-from-in-2026-ddacc92c5b4f)
- [CoinDesk: Polymarket US approval](https://www.coindesk.com/business/2025/11/25/polymarket-secures-cftc-approval-for-regulated-u-s-return) ·
  [Polymarket US developer](https://polymarket.us/developer) ·
  [QuantVPS: US API](https://www.quantvps.com/blog/polymarket-us-api-available)
- [Bonding guide](https://startpolymarket.com/strategies/bonding/) ·
  [Resolution risk](https://orrery.me/learn/polymarket-resolution-risk) ·
  [pm.wiki copy-trading listings](https://pm.wiki/projects/polymaster-2)
