// Vett analyzer — self-contained JS port of the Python analyzer.
// Talks straight to Hyperliquid's public API. No backend, no keys.
const HL_API = "https://api.hyperliquid.xyz/info";
const TAKER = 0.00045;  // copier pays taker fee, both legs
const SLIP  = 0.0004;   // copier enters later / worse

async function hlPost(body) {
  const r = await fetch(HL_API, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("HL API " + r.status);
  return r.json();
}

// Mirror of analyze() in analyzer.py — keep the two in sync.
async function analyze(addr) {
  const fills = await hlPost({ type: "userFills", user: addr });
  if (!fills || !fills.length) return null;
  const num = (x) => parseFloat(x) || 0;
  const closes = fills.filter(
    (f) => (f.dir || "").includes("Close") || ("closedPnl" in f && num(f.closedPnl) !== 0)
  );
  if (closes.length < 10) return { addr, tooFew: true, n: closes.length };

  const raw_pnl = fills.reduce((s, f) => s + num(f.closedPnl), 0);
  const their_fees = fills.reduce((s, f) => s + num(f.fee), 0);
  const gross_pnl = raw_pnl + their_fees;
  const wins = closes.filter((f) => num(f.closedPnl) > 0);
  const win_rate = (100 * wins.length) / closes.length;

  const tot_vol = fills.reduce((s, f) => s + num(f.px) * num(f.sz), 0);
  const maker_vol = fills
    .filter((f) => f.crossed === false)
    .reduce((s, f) => s + num(f.px) * num(f.sz), 0);
  const maker_pct = tot_vol ? (100 * maker_vol) / tot_vol : 0;

  const copier_cost = fills.reduce(
    (s, f) => s + num(f.px) * num(f.sz) * (TAKER + SLIP), 0
  );
  const copier_pnl = gross_pnl - copier_cost;

  const pnls = closes.map((f) => num(f.closedPnl)).sort((a, b) => b - a);
  const top5 = pnls.slice(0, 5).reduce((s, x) => s + x, 0);
  const pnl_ex_top5 = pnls.slice(5).reduce((s, x) => s + x, 0);
  const top5_share = raw_pnl > 0 ? (100 * top5) / raw_pnl : 0;

  const times = fills.map((f) => f.time);
  const span_days = (Math.max(...times) - Math.min(...times)) / 86400000;
  const coins = new Set(fills.map((f) => f.coin)).size;
  const copier_roi = tot_vol ? (100 * copier_pnl) / tot_vol : 0;
  const truncated = fills.length >= 2000; // HL caps userFills ~2000
  const cw = pnls.filter((p) => p > 0).reduce((s, x) => s + x, 0);
  const cl = Math.abs(pnls.filter((p) => p < 0).reduce((s, x) => s + x, 0));
  const profit_factor = cl > 0 ? cw / cl : 99;

  // avg hold: FIFO-pair each coin's Opens with subsequent Closes (mirror of analyzer.py)
  const opensByCoin = {}; const holds = [];
  for (const f of fills.slice().sort((a, b) => a.time - b.time)) {
    const d = f.dir || "", c = f.coin;
    if (d.includes("Open")) (opensByCoin[c] = opensByCoin[c] || []).push(f.time);
    else if (d.includes("Close") && opensByCoin[c] && opensByCoin[c].length)
      holds.push(f.time - opensByCoin[c].shift());
  }
  const avg_hold_hours = holds.length ? holds.reduce((s, x) => s + x, 0) / holds.length / 3600000 : 0;

  const a = { addr, raw_pnl, gross_pnl, win_rate, maker_pct, tot_vol,
    copier_pnl, copier_cost, top5_share, pnl_ex_top5, span_days, coins, copier_roi,
    profit_factor, n_closes: closes.length, truncated, avg_hold_hours };
  a.score = score(a); a.grade = grade(a.score);
  return a;
}

function score(a) {
  if (a.maker_pct > 50 || a.copier_pnl <= 0) return 0;
  let s = 0;
  s += Math.min(a.copier_roi * 100, 50); s += Math.min(a.profit_factor * 8, 40);
  s += (100 - a.top5_share) * 0.3; s += Math.min(a.coins * 2, 30); s += Math.min(a.span_days * 0.1, 30);
  if (a.span_days < 14) s -= 40;
  return Math.max(0, s);
}
function grade(s) {
  return s >= 140 ? "A+" : s >= 115 ? "A" : s >= 90 ? "B" : s >= 65 ? "C" : s >= 35 ? "D" : "F";
}

// Mirror of verdict() in analyzer.py
function verdict(a) {
  if (a.tooFew) return { v: "TOO FEW TRADES", flags: [] };
  const flags = [];
  if (a.maker_pct > 60)
    flags.push(`MAKER-DEPENDENT: ${a.maker_pct.toFixed(0)}% maker volume — a taker copier can't replicate the spread edge`);
  if (a.copier_pnl < 0)
    flags.push(`UNCOPYABLE: profitable for them but a copier paying fees+slippage nets ${money(a.copier_pnl)}`);
  if (a.top5_share > 80)
    flags.push(`LUCK-CONCENTRATED: ${a.top5_share.toFixed(0)}% of profit is in 5 trades — drop them and it's ${money(a.pnl_ex_top5)}`);
  if (a.span_days < 14)
    flags.push(`TOO NEW: only ${a.span_days.toFixed(0)} days of history`);
  if (a.coins < 3) flags.push(`UNDIVERSIFIED: only ${a.coins} coin(s)`);
  if (a.truncated) flags.push("PARTIAL DATA: only the most-recent ~2000 trades are visible");
  if (a.maker_pct > 50) return { v: "DO NOT COPY", flags };
  if (a.copier_pnl <= 0) return { v: "DO NOT COPY", flags };
  if (flags.length) return { v: "RISKY", flags };
  return { v: "COPYABLE", flags: [] };
}

function money(x) {
  const s = x < 0 ? "-" : "+";
  return s + "$" + Math.abs(x).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

// Current perps account value (for the copy calculator).
async function accountValue(addr) {
  const cs = await hlPost({ type: "clearinghouseState", user: addr });
  return parseFloat((cs && cs.marginSummary && cs.marginSummary.accountValue) || 0) || 0;
}

// Current open positions for a wallet (for the Positions view).
async function positions(addr) {
  const cs = await hlPost({ type: "clearinghouseState", user: addr });
  const out = [];
  for (const p of (cs && cs.assetPositions) || []) {
    const pos = p.position || {};
    const szi = parseFloat(pos.szi) || 0;
    if (szi === 0) continue;
    out.push({
      coin: pos.coin, side: szi > 0 ? "LONG" : "SHORT",
      lev: (pos.leverage && pos.leverage.value) || "",
      value: parseFloat(pos.positionValue) || 0,
      upnl: parseFloat(pos.unrealizedPnl) || 0,
    });
  }
  return out;
}

// Pull leaderboard candidates (copyable-size winners) for Top / Random.
async function leaderboardCandidates() {
  const r = await fetch("https://stats-data.hyperliquid.xyz/Mainnet/leaderboard");
  if (!r.ok) throw new Error("leaderboard " + r.status);
  const rows = (await r.json()).leaderboardRows || [];
  const perf = (row, w) => {
    for (const [k, d] of row.windowPerformances) if (k === w) return [+d.pnl, +d.roi, +d.vlm];
    return [0, 0, 0];
  };
  const cands = [];
  for (const row of rows) {
    const av = +row.accountValue;
    const [mp] = perf(row, "month");
    const [ap, , avlm] = perf(row, "allTime");
    if (av > 2000 && av < 500000 && mp > 1000 && ap > 0 && avlm > 50000)
      cands.push([mp, row.ethAddress]);
  }
  cands.sort((a, b) => b[0] - a[0]);
  return cands.map((c) => c[1]);
}

// Analyze the top N candidates and return the copyable/risky ones, best first.
async function scanTop(n, onProgress) {
  const cands = (await leaderboardCandidates()).slice(0, n);
  const out = [];
  for (let i = 0; i < cands.length; i++) {
    try {
      const a = await analyze(cands[i]);
      if (a && !a.tooFew) {
        const res = verdict(a);
        if (res.v !== "DO NOT COPY" && a.copier_pnl > 0)
          out.push({ addr: cands[i], v: res.v, copier: a.copier_pnl, maker: a.maker_pct,
                     coins: a.coins, days: a.span_days });
      }
    } catch (e) {}
    if (onProgress) onProgress(i + 1, cands.length);
  }
  out.sort((a, b) => b.copier - a.copier);
  return out;
}

if (typeof module !== "undefined")
  module.exports = { analyze, verdict, money, positions, accountValue, leaderboardCandidates, scanTop };
