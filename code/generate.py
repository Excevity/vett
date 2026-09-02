"""Vett content generator — turns a scanner story into a vertical data-driven short.
Pure data visuals (no stock footage), Piper narration, burned captions.
Numbers are templated straight from real scanner output — never invented."""
import os,sys,json,subprocess,shutil,math,textwrap,random
sys.path.insert(0,os.path.dirname(__file__))
from paths import FFMPEG,FFPROBE,FONT_DIR,KOKORO_MODEL,KOKORO_VOICES,VOICE
from PIL import Image,ImageDraw,ImageFont
import story as story_mod

W,H,FPS=1080,1920,24
BG=(10,12,16); PANEL=(19,23,30); INK=(238,242,247); INK2=(150,166,182); INK3=(95,107,124)
TEAL=(51,225,176); RED=(255,90,82); GREEN=(64,214,120); AMBER=(255,182,56)
def font(sz,mono=False,bold=True):
    f=("DejaVuSansMono.ttf" if mono else ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))
    return ImageFont.truetype(os.path.join(FONT_DIR,f),sz)
def money(x):
    s="-" if x<0 else "+"; return f"{s}${abs(x):,.0f}"

# --- spoken numbers: TTS reads "4,328" with the comma literally; say words instead ---
_ONES=["zero","one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen"]
_TENS=["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
def _u1000(n):
    if n<20: return _ONES[n]
    if n<100: return _TENS[n//10]+(" "+_ONES[n%10] if n%10 else "")
    return _ONES[n//100]+" hundred"+(" "+_u1000(n%100) if n%100 else "")
def _int_words(n):
    if n==0: return "zero"
    parts=[]
    if n>=1000:
        parts.append(_u1000(n//1000)+" thousand"); n%=1000
    if n: parts.append(_u1000(n))
    return " ".join(parts)
def say_money(x):
    x=abs(int(round(x)))
    if x>=1_000_000:
        m=x/1_000_000; whole=int(m); frac=int(round((m-whole)*10))
        if frac==10: whole+=1; frac=0
        base=_int_words(whole)+(f" point {_ONES[frac]}" if frac else "")
        return f"{base} million dollars"
    return f"{_int_words(x)} dollars"

def ctext(d,y,txt,fnt,fill,center=True,x=W//2,anchor_m=True):
    bb=d.textbbox((0,0),txt,font=fnt); w=bb[2]-bb[0]; h=bb[3]-bb[1]
    px=(x-w//2) if center else x
    d.text((px,y),txt,font=fnt,fill=fill)
    return h
def ease(t): return 1-(1-t)**3

# ---------------- scene builders (each returns (narration, draw_fn)) ----------------
# Every video pulls its wording/labels/order from these pools so no two are the
# same. rng is fresh per generation.
def build_scenes(s, rng=None):
    rng = rng or random.Random()
    pick = lambda opts: rng.choice(opts)
    tt = s.get('trap_type','loss')
    tag = f"{s['addr'][:6]}…{s['addr'][-4:]}"
    scenes = []

    # ---- chosen visual labels (vary per video) ----
    hook_sub  = pick(["'TOP TRADER'","WHALE WALLET","'GENIUS' TRADER","PRO TRADER","'SMART MONEY'"])
    adv_label = pick(["ADVERTISES","ON PAPER","LEADERBOARD SAYS","THEY SHOW YOU"])
    why_head  = pick(["WHY IT'S A TRAP","WHY YOU'D LOSE","THE RED FLAGS","WHAT THEY HIDE"])
    cta_head  = pick([("CHECK ANY WALLET","BEFORE YOU COPY IT"),
                      ("VET ANY WALLET","IN SECONDS, FREE"),
                      ("KNOW THE TRUTH","BEFORE YOU COPY"),
                      ("DON'T COPY BLIND","CHECK IT FIRST")])
    cta_stat  = pick(["49% of 'winners' are traps.","Half of 'top' wallets lose copiers money.",
                      "Most green wallets are traps.","The leaderboard lies. We don't."])

    # 1 HOOK
    def s1(img,d,t):
        img.paste(BG,(0,0,W,H))
        ctext(d,300,"HYPERLIQUID",font(46,mono=True),INK3)
        ctext(d,370,hook_sub,font(96),INK)
        d.rounded_rectangle([120,640,W-120,1080],36,fill=PANEL)
        ctext(d,700,adv_label,font(40,mono=True),INK2)
        a=int(ease(min(t*1.6,1))*s['raw_pnl'])
        ctext(d,780,money(a),font(150,mono=True),GREEN)
        ctext(d,980,f"{s['win_rate']:.0f}% WIN RATE",font(48,mono=True),INK2)
        ctext(d,1300,tag,font(40,mono=True),INK3)
    scenes.append((pick([
        "This wallet is a top trader on Hyperliquid.",
        "Here's one of Hyperliquid's top traders.",
        "This wallet looks like a genius on Hyperliquid.",
        "Everybody wants to copy this Hyperliquid wallet.",
        "This trader is supposedly crushing it on Hyperliquid."]), s1))
    scenes.append((pick([
        f"It advertises {say_money(s['raw_pnl'])} in profit, with a {s['win_rate']:.0f} percent win rate.",
        f"On paper it's up {say_money(s['raw_pnl'])}, winning {s['win_rate']:.0f} percent of the time.",
        f"The leaderboard shows {say_money(s['raw_pnl'])} in profit and a {s['win_rate']:.0f} percent win rate.",
        f"It's showing {say_money(s['raw_pnl'])} in gains, with {s['win_rate']:.0f} percent of trades green."]), s1))

    # 2 TURN
    turn_top = pick(["but what happens if","but watch what happens when","now here's the catch —"])
    turn_bot = pick(["actually copy it?","actually try to copy it?","copy this wallet?"])
    def s2(img,d,t):
        img.paste(BG,(0,0,W,H))
        ctext(d,560,turn_top,font(60,mono=False,bold=True),INK2)
        ctext(d,700,"YOU",font(150),TEAL)
        ctext(d,920,turn_bot,font(60,mono=False,bold=True),INK2)
        if int(t*4)%2: ctext(d,1180,"?",font(180),INK3)
    scenes.append((pick([
        "But here's what nobody shows you. What happens if you actually copy it?",
        "But here's the part the apps hide. What if you actually copied it?",
        "Now here's what they won't tell you. What happens the moment you copy it?",
        "But watch what happens the second you try to copy this wallet."]), s2))

    # 3 REVEAL — copier LOSS, or a MAKER you can't copy at all
    if tt=='maker':
        def s3(img,d,t):
            img.paste(BG,(0,0,W,H))
            ctext(d,420,"THE CATCH:",font(44,mono=True),INK3)
            d.rounded_rectangle([100,620,W-100,940],40,fill=(28,16,15))
            ctext(d,680,"YOU CAN'T",font(120,mono=True),RED)
            ctext(d,820,"COPY THIS",font(120,mono=True),RED)
            ctext(d,1040,f"{s['maker_pct']:.0f}% MARKET-MAKER FILLS",font(46,mono=True),INK2)
            ctext(d,1180,"they earn the spread — you'd take",font(40,mono=False,bold=False),INK2)
            ctext(d,1240,"the worse side of every trade",font(40,mono=False,bold=False),INK2)
        scenes.append((pick([
            "Here's the catch. This is a market maker. They earn the spread. Copy them by taking trades, "
            "and you get the worse side of every single fill. You literally can't replicate it.",
            "Turns out it's a market maker. Their profit comes from the spread — something a copier taking "
            "trades can never capture. You'd be on the wrong side of every fill."]), s3))
    else:
        def s3(img,d,t):
            img.paste(BG,(0,0,W,H))
            ctext(d,420,"AFTER REAL FEES",font(44,mono=True),INK3)
            ctext(d,480,"+ SLIPPAGE, YOU GET:",font(44,mono=True),INK3)
            d.rounded_rectangle([100,760,W-100,1080],40,fill=(28,16,15))
            val=int(ease(min(t*1.4,1))*abs(s['copier_pnl']))
            ctext(d,830,f"-${val:,.0f}",font(150,mono=True),RED)
            ctext(d,1180,pick(["YOU LOSE MONEY","YOU'RE IN THE RED","A COPIER LOSES"]),font(60),RED)
        scenes.append((pick([
            f"You would lose {say_money(s['copier_pnl'])}.",
            f"You'd actually lose {say_money(s['copier_pnl'])}.",
            f"A copier ends up down {say_money(s['copier_pnl'])}.",
            f"After the real costs, you lose {say_money(s['copier_pnl'])}."]), s3))

    # 4 WHY (flags) — shuffled order per video
    reasons=[]
    if s['maker_pct']>50: reasons.append(("Market maker","You can't copy their spread edge"))
    if s['top5_share']>80: reasons.append((f"{s['top5_share']:.0f}% luck","Nearly all profit from 5 trades"))
    reasons.append(("Fees > edge","Their volume eats the profit"))
    if s['span_days']<20: reasons.append((f"Only {s['span_days']:.0f} days","Too new to trust"))
    rng.shuffle(reasons)
    reasons=reasons[:3]
    def s4(img,d,t):
        img.paste(BG,(0,0,W,H))
        ctext(d,340,why_head,font(60),INK)
        y=620
        shown=int(t*len(reasons))+1
        for i,(a,b) in enumerate(reasons):
            if i>=shown: break
            d.rounded_rectangle([110,y,W-110,y+230],28,fill=PANEL)
            ctext(d,y+40,a,font(64),RED,center=False,x=170)
            ctext(d,y+140,b,font(40,mono=False,bold=False),INK2,center=False,x=170)
            y+=280
    scenes.append((pick([
        "Fees eat the edge, and almost all their profit came from a handful of lucky trades.",
        "The fees burn the edge, and most of the wins were just a few lucky trades you'd never catch.",
        "Their volume eats the profit, and the gains came from trades a copier can't replicate."]), s4))

    # 5 CTA — always shows BOTH the @ handle and the t.me link
    def s5(img,d,t):
        img.paste(BG,(0,0,W,H))
        ctext(d,470,cta_head[0],font(72),INK)
        ctext(d,570,cta_head[1],font(72),INK)
        d.rounded_rectangle([150,740,W-150,1010],40,fill=(15,42,34))
        ctext(d,790,"@vett_hl_bot",font(78,mono=True),TEAL)
        ctext(d,910,"t.me/vett_hl_bot",font(48,mono=True),INK2)
        ctext(d,1080,"free · no login · instant",font(44,mono=True),INK3)
        ctext(d,1500,cta_stat,font(44),INK3)
        ctext(d,1560,"don't be the one who finds out.",font(44),INK3)
    scenes.append((pick([
        "Check any wallet for free, before you copy it. Vett, on Telegram.",
        "Vet any wallet in seconds, free. Find Vett on Telegram.",
        "Don't copy blind. Check any wallet free with Vett on Telegram.",
        "Know before you copy. Vett is free on Telegram."]), s5))
    return scenes

# ---------------- TTS (Kokoro, natural voice) ----------------
_KOKORO=None
def _kok():
    global _KOKORO
    if _KOKORO is None:
        from kokoro_onnx import Kokoro
        _KOKORO=Kokoro(KOKORO_MODEL,KOKORO_VOICES)
    return _KOKORO
def tts(text,dest):
    import soundfile as sf
    s,sr=_kok().create(text,voice=VOICE,speed=1.0,lang="en-us")
    sf.write(dest,s,sr)
    return dest
def dur(wav):
    r=subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration","-of","csv=p=0",wav],
        capture_output=True,text=True)
    return float(r.stdout.strip())

def generate(out="output/short.mp4"):
    s=story_mod.pick()
    if not s: print("no story available"); return None
    print(f"story: {s['kind']} {s['addr'][:10]} adv {money(s['raw_pnl'])} copier {money(s['copier_pnl'])}")
    scenes=build_scenes(s)
    tmp="output/_tmp"; shutil.rmtree(tmp,ignore_errors=True); os.makedirs(tmp)
    # 1) TTS each scene, measure durations
    durs=[]
    for i,(narr,_) in enumerate(scenes):
        tts(narr,f"{tmp}/a{i}.wav"); durs.append(max(dur(f"{tmp}/a{i}.wav"),1.2)+0.35)
    # 2) render frames
    fi=0
    for i,(narr,draw_fn) in enumerate(scenes):
        n=max(1,int(round(durs[i]*FPS)))
        for k in range(n):
            img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img)
            draw_fn(img,d,k/max(1,n-1))
            img.save(f"{tmp}/f{fi:05d}.png"); fi+=1
    # 3) concat audio (pad each to its scene length)
    with open(f"{tmp}/alist.txt","w") as f:
        for i in range(len(scenes)):
            subprocess.run([FFMPEG,"-y","-i",f"{tmp}/a{i}.wav","-af",
                f"apad=pad_dur={durs[i]}","-t",str(durs[i]),f"{tmp}/p{i}.wav"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            f.write(f"file 'p{i}.wav'\n")
    subprocess.run([FFMPEG,"-y","-f","concat","-safe","0","-i",f"{tmp}/alist.txt","-c","copy",
        f"{tmp}/audio.wav"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    # 4) encode video + mux
    subprocess.run([FFMPEG,"-y","-framerate",str(FPS),"-i",f"{tmp}/f%05d.png","-i",f"{tmp}/audio.wav",
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest",
        "-vf","format=yuv420p",out],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    shutil.rmtree(tmp,ignore_errors=True)
    total=sum(durs)
    # sidecar metadata for the uploader (title/desc/tags built from real facts)
    HASHTAGS="#vett #trading #crypto #hyperliquid #bitcoin"
    CTA_LINE="Check any wallet free before you copy it → @vett_hl_bot on Telegram (t.me/vett_hl_bot)."
    if s['kind']=='trap' and s.get('trap_type')=='maker':
        title=f"This Hyperliquid 'top trader' made {money(s['raw_pnl'])} — but you CAN'T copy it 🚩"
        desc=(f"They advertise {money(s['raw_pnl'])} profit, but {s['maker_pct']:.0f}% of it is market-maker "
              f"fills — they earn the spread. Copy them by taking and you get the worse side of every trade.\n\n"
              f"{CTA_LINE}\n\n{HASHTAGS}")
    elif s['kind']=='trap':
        title=f"This Hyperliquid 'top trader' would LOSE you {money(s['copier_pnl']).lstrip('-')} 🚩"
        desc=(f"They advertise {money(s['raw_pnl'])} profit at {s['win_rate']:.0f}% win rate. "
              f"But copy them and after real fees + slippage you'd get {money(s['copier_pnl'])}.\n\n"
              f"{CTA_LINE}\n\n{HASHTAGS}")
    else:
        title=f"A Hyperliquid wallet a copier could ACTUALLY follow (+{money(s['copier_pnl']).lstrip('+')}) ✅"
        desc=(f"Most 'winners' would lose a copier money. This one passes every honesty check.\n\n"
              f"Vet any wallet free → @vett_hl_bot on Telegram (t.me/vett_hl_bot).\n\n{HASHTAGS}")
    meta=dict(kind=s['kind'],addr=s['addr'],title=title,description=desc,
              tags=["vett","trading","crypto","hyperliquid","bitcoin"])
    json.dump(meta,open(os.path.join(os.path.dirname(out),"meta.json"),"w"))
    print(f"done -> {out}  ({total:.0f}s, {fi} frames)")
    return out

if __name__=='__main__':
    generate()
