#!/usr/bin/env python3
"""Self-contained scanner for the content pipeline (so CI needs no other repo).
Fetches the HL leaderboard, deep-analyzes copyable-size winners, writes
data/leaderboard_scan.json in the format story.py expects. Trimmed twin of the
bot's scanner — same analyzer, same verdict logic."""
import os, sys, json, time, urllib.request, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
exec(open(os.path.join(HERE, "analyzer.py")).read().split("if __name__")[0])  # analyze(), verdict()
OUT = os.path.join(HERE, "..", "data", "leaderboard_scan.json")

BUDGET = 900.0; _sp = collections.deque()
def pace(w=20):
    while True:
        n = time.time()
        while _sp and n - _sp[0][0] > 60: _sp.popleft()
        if sum(x[1] for x in _sp) + w <= BUDGET: _sp.append((n, w)); return
        time.sleep(0.5)

def wperf(r, w):
    for k, d in r["windowPerformances"]:
        if k == w: return float(d["pnl"]), float(d["roi"]), float(d["vlm"])
    return 0, 0, 0

def score(a):
    if a["maker_pct"] > 50 or a["copier_pnl"] <= 0: return -1
    s = 0
    s += min(a["copier_roi"] * 100, 50)
    s += min(a["profit_factor"] * 8, 40)
    s += (100 - a["top5_share"]) * 0.3
    s += min(a["coins"] * 2, 30)
    s += min(a["span_days"] * 0.1, 30)
    if a["span_days"] < 14: s -= 40
    return s

def run(deep_n=200):
    print("fetching leaderboard...", flush=True)
    url = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
    lb = json.load(urllib.request.urlopen(url, timeout=40))["leaderboardRows"]
    print(f"{len(lb)} wallets. pre-filtering...", flush=True)
    cands = []
    for r in lb:
        av = float(r["accountValue"])
        mp, _, _ = wperf(r, "month"); ap, _, mvlm = wperf(r, "allTime")
        if 2000 < av < 500000 and mp > 1000 and ap > 0 and mvlm > 50000:
            cands.append((mp, r["ethAddress"]))
    cands.sort(reverse=True); cands = cands[:deep_n]
    print(f"{len(cands)} candidates -> analyzing...", flush=True)
    results = []
    for i, (_, addr) in enumerate(cands):
        try:
            pace()
            a = analyze(addr)
            if not a or "verdict" in a: continue
            v, flags = verdict(a); a["final_verdict"] = v; a["flags"] = flags; a["score"] = score(a)
            results.append(a)
            if (i + 1) % 25 == 0: print(f"  ...{i+1}/{len(cands)}", flush=True)
        except Exception:
            pass
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(results, open(OUT, "w"))
    nope = sum(1 for a in results if a["final_verdict"] == "DO NOT COPY")
    n = len(results) or 1
    print(f"saved {len(results)} wallets -> {OUT}  ({100*nope//n}% DO NOT COPY)")
    return results

if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
