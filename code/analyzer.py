#!/usr/bin/env python3
"""Honest Hyperliquid wallet analyzer — the core of the copy-vetting bot.

Given a wallet, it separates what the wallet ADVERTISES (raw PnL) from what a
COPIER would actually earn (taker fees, slippage, no maker rebate, latency).
Built from the hard lesson: an edge that describes a wallet's fills does not
transfer to someone copying by taking.
"""
import json,urllib.request,statistics,sys,time
API='https://api.hyperliquid.xyz/info'
TAKER=0.00045          # a copier pays taker fee both legs
SLIP=0.0004            # copier enters late/worse than the wallet
def post(p,retry=3):
    for i in range(retry):
        try:
            r=urllib.request.Request(API,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'})
            return json.load(urllib.request.urlopen(r,timeout=30))
        except Exception as e:
            if i==retry-1: raise
            time.sleep(2)

def analyze(addr):
    fills=post({'type':'userFills','user':addr})
    if not fills: return None
    closes=[f for f in fills if 'Close' in f.get('dir','') or 'closedPnl' in f and float(f['closedPnl'])!=0]
    if len(closes)<10: return {'addr':addr,'verdict':'TOO FEW TRADES','n':len(closes)}
    # RAW (what they'd advertise)
    raw_pnl=sum(float(f['closedPnl']) for f in fills)
    their_fees=sum(float(f['fee']) for f in fills)
    gross_pnl=raw_pnl+their_fees                       # pre-fee gross
    wins=[f for f in closes if float(f['closedPnl'])>0]
    win_rate=100*len(wins)/len(closes)
    # MAKER dependency: fraction of volume done as maker (crossed=False)
    tot_vol=sum(float(f['px'])*float(f['sz']) for f in fills)
    maker_vol=sum(float(f['px'])*float(f['sz']) for f in fills if not f.get('crossed',True))
    maker_pct=100*maker_vol/tot_vol if tot_vol else 0
    # COPIER-ADJUSTED: charge taker fee + slippage on the copier's version of every fill
    copier_cost=sum(float(f['px'])*float(f['sz'])*(TAKER+SLIP) for f in fills)
    copier_pnl=gross_pnl-copier_cost
    # CONCENTRATION: is it a few lucky trades? drop best 5 closes
    pnls=sorted((float(f['closedPnl']) for f in closes),reverse=True)
    pnl_ex_top5=sum(pnls[5:])
    top5_share=100*sum(pnls[:5])/raw_pnl if raw_pnl>0 else 0
    # time span
    span_days=(max(f['time'] for f in fills)-min(f['time'] for f in fills))/86400000
    # coins traded
    coins=len(set(f['coin'] for f in fills))
    # profit factor = gross wins / gross losses (on closer closedPnl)
    cw=sum(p for p in pnls if p>0); cl=abs(sum(p for p in pnls if p<0))
    profit_factor=cw/cl if cl>0 else 99.0
    copier_roi=100*copier_pnl/tot_vol if tot_vol else 0     # net return per $ traded
    truncated=len(fills)>=2000        # HL caps userFills ~2000 -> older history unseen
    return dict(addr=addr,n_fills=len(fills),n_closes=len(closes),span_days=span_days,coins=coins,
        raw_pnl=raw_pnl,gross_pnl=gross_pnl,their_fees=their_fees,win_rate=win_rate,
        maker_pct=maker_pct,tot_vol=tot_vol,copier_pnl=copier_pnl,copier_cost=copier_cost,
        top5_share=top5_share,pnl_ex_top5=pnl_ex_top5,profit_factor=profit_factor,copier_roi=copier_roi,
        truncated=truncated)

def verdict(a):
    if 'verdict' in a: return a['verdict'],[]
    flags=[]
    if a['maker_pct']>60: flags.append(f"MAKER-DEPENDENT: {a['maker_pct']:.0f}% of volume is maker fills — a taker copier can't replicate the spread edge")
    if a['copier_pnl']<0: flags.append(f"UNCOPYABLE: profitable for them (+${a['raw_pnl']:,.0f}) but a copier paying taker fees+slippage nets ${a['copier_pnl']:,.0f}")
    if a['top5_share']>80: flags.append(f"LUCK-CONCENTRATED: {a['top5_share']:.0f}% of profit is in just 5 trades — drop them and it's ${a['pnl_ex_top5']:,.0f}")
    if a['span_days']<14: flags.append(f"TOO NEW: only {a['span_days']:.0f} days of history — not enough to trust")
    if a['coins']<3: flags.append(f"UNDIVERSIFIED: only {a['coins']} coin(s)")
    if a.get('truncated'): flags.append("PARTIAL DATA: only the most-recent ~2000 trades are visible — older history hidden")
    # maker-dependent: copier CANNOT replicate spread capture by taking -> uncopyable, full stop
    if a['maker_pct']>50: return 'DO NOT COPY',flags
    if a['copier_pnl']<=0: return 'DO NOT COPY',flags
    if flags: return 'RISKY',flags
    return 'COPYABLE',[]

if __name__=='__main__':
    addr=sys.argv[1]
    a=analyze(addr)
    if not a: print('no data'); sys.exit()
    v,flags=verdict(a)
    print(f"\n{'='*64}\nWALLET {addr[:10]}...{addr[-6:]}\n{'='*64}")
    if 'verdict' in a: print(a['verdict']); sys.exit()
    print(f"  history: {a['span_days']:.0f} days, {a['n_closes']} closed trades, {a['coins']} coins, ${a['tot_vol']:,.0f} volume")
    print(f"\n  WHAT THEY ADVERTISE:")
    print(f"    reported PnL:   ${a['raw_pnl']:>+12,.0f}")
    print(f"    win rate:       {a['win_rate']:>13.0f}%")
    print(f"\n  WHAT A COPIER WOULD ACTUALLY GET:")
    print(f"    pre-fee gross:  ${a['gross_pnl']:>+12,.0f}")
    print(f"    copier costs:   ${a['copier_cost']:>12,.0f}  (taker fee + slippage, both legs)")
    print(f"    copier net:     ${a['copier_pnl']:>+12,.0f}   <-- the number that matters")
    print(f"    maker-fill %:   {a['maker_pct']:>13.0f}%  (copier can't get this edge)")
    print(f"\n  VERDICT: {v}")
    for f in flags: print(f"    ⚠  {f}")
    print()
