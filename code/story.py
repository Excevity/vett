"""Pick the most compelling UNUSED wallet story from the scanner output.
A 'trap' (advertises green, copier loses) is the best hook; falls back to a 'gem'."""
import os,json,hashlib
from paths import SCANNER_DATA
STATE=os.path.join(os.path.dirname(__file__),'..','state','used.json')
def _used():
    return set(json.load(open(STATE))) if os.path.exists(STATE) else set()
def _mark(k):
    os.makedirs(os.path.dirname(STATE),exist_ok=True)   # state/ is gitignored; create it in CI
    u=_used(); u.add(k); json.dump(sorted(u),open(STATE,'w'))
def pick():
    d=json.load(open(SCANNER_DATA))
    used=_used()
    def key(a): return a['addr']
    # rank traps: advertise positive, copier negative, biggest gap, not yet used
    # strong hook = large advertised profit AND large copier loss; require a punchy advertised #
    # Type A trap — advertises green, a copier literally LOSES money. Strongest hook.
    trapsA=[a for a in d if a.get('raw_pnl',0)>=2000 and a.get('copier_pnl',0)<0 and key(a) not in used]
    trapsA.sort(key=lambda a:-(a['raw_pnl']+abs(a['copier_pnl'])))
    if trapsA: return _story(trapsA[0],'trap','loss')
    # Type B trap — big advertised profit but MAKER-dependent: you can't copy it at all.
    trapsB=[a for a in d if a.get('maker_pct',0)>50 and a.get('raw_pnl',0)>=5000 and key(a) not in used]
    trapsB.sort(key=lambda a:-a['raw_pnl'])
    if trapsB: return _story(trapsB[0],'trap','maker')
    # Fallback — a genuinely copyable wallet (positive story).
    gems=[a for a in d if a.get('final_verdict')=='COPYABLE' and a.get('copier_pnl',0)>0 and key(a) not in used]
    gems.sort(key=lambda a:-a.get('score',0))
    if gems: return _story(gems[0],'gem','gem')
    return None
def _story(a,kind,trap_type):
    _mark(a['addr'])
    return dict(kind=kind,trap_type=trap_type,addr=a['addr'],raw_pnl=a['raw_pnl'],copier_pnl=a['copier_pnl'],
        win_rate=a['win_rate'],maker_pct=a['maker_pct'],coins=a['coins'],
        span_days=a['span_days'],top5_share=min(a.get('top5_share',0),99),
        profit_factor=a.get('profit_factor',0),verdict=a['final_verdict'],flags=a.get('flags',[]))
if __name__=='__main__':
    import pprint; pprint.pprint(pick())
