"""Vett content generator — turns a scanner story into a vertical data-driven short.
Pure data visuals (no stock footage), Piper narration, burned captions.
Numbers are templated straight from real scanner output — never invented."""
import os,sys,json,subprocess,shutil,math,textwrap,random,urllib.request,urllib.parse
from io import BytesIO
sys.path.insert(0,os.path.dirname(__file__))
from paths import FFMPEG,FFPROBE,FONT_DIR,KOKORO_MODEL,KOKORO_VOICES,VOICE,SPEED,SCANNER_DATA
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

# ---- optional photo background (Pexels, free + commercial-use). OFF unless PEXELS_KEY is set. ----
_BGIMG = None
def bg(img):
    """Fill a frame: darkened photo if one was fetched, else the solid brand BG."""
    if _BGIMG is not None: img.paste(_BGIMG, (0, 0))
    else: img.paste(BG, (0, 0, W, H))
def _cover(im):
    iw, ih = im.size; scale = max(W/iw, H/ih)
    im = im.resize((int(iw*scale), int(ih*scale)))
    x = (im.size[0]-W)//2; y = (im.size[1]-H)//2
    return im.crop((x, y, x+W, y+H))
def _pexels(query):
    key = os.environ.get("PEXELS_KEY")
    if not key: return None
    u = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page=20&orientation=portrait"
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"Authorization": key}), timeout=20))
    photos = r.get("photos", [])
    if not photos: return None
    src = random.choice(photos)["src"]
    return src.get("portrait") or src["large"]

def _pixabay(query):
    key = os.environ.get("PIXABAY_KEY")
    if not key: return None
    u = (f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(query)}"
         f"&image_type=photo&orientation=vertical&per_page=20&safesearch=true")
    r = json.load(urllib.request.urlopen(u, timeout=20))
    hits = r.get("hits", [])
    if not hits: return None
    h = random.choice(hits)
    return h.get("largeImageURL") or h.get("webformatURL")

def fetch_bg(query):
    for provider in (_pixabay, _pexels):        # Pixabay first (works), Pexels fallback
        try:
            url = provider(query)
            if not url: continue
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=20).read()
            im = _cover(Image.open(BytesIO(raw)).convert("RGB"))
            im = Image.eval(im, lambda p: int(p*0.15))     # heavy darken -> subtle texture
            # tint toward the brand background so it reads as one piece, not a photo
            base = Image.new("RGB", (W, H), BG)
            return Image.blend(im, base, 0.45)
        except Exception:
            continue
    return None

def chart_bg(rng=None, up_bias=0.0):
    """Draw a subtle, ON-TOPIC candlestick chart as the backdrop — always relevant
    and clean, unlike random stock photos. Dark/desaturated so data stays the focus."""
    rng = rng or random
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    for gy in range(0, H, 150):                      # faint grid
        d.line([(0, gy), (W, gy)], fill=(15, 19, 26), width=2)
    n = 24; cw = W // n; price = H * 0.5
    for i in range(n):
        o = price
        price += rng.uniform(-70, 70) - up_bias      # up_bias<0 trends up, >0 trends down
        price = max(H*0.2, min(H*0.85, price))
        c = price
        hi = min(o, c) - rng.uniform(15, 70); lo = max(o, c) + rng.uniform(15, 70)
        x = i*cw + cw//2
        col = (24, 56, 42) if c < o else (58, 26, 26)   # green up / red down, very dark
        d.line([(x, hi), (x, lo)], fill=col, width=3)
        d.rectangle([x-cw//3, min(o, c), x+cw//3, max(o, c)], fill=col)
    return img

CAPTIONS = True   # burn narration subtitles at the bottom (retention on silent autoplay)
def _wrap(d, text, fnt, maxw):
    words=text.split(); lines=[]; cur=""
    for w in words:
        test=(cur+" "+w).strip()
        if d.textlength(test,font=fnt)<=maxw: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines
def draw_caption(img,d,text,t=1.0,speech_frac=1.0):
    """Dynamic captions: white fill + teal outline, words popping in paced to the
    actual spoken audio (reveal finishes right when the narration ends)."""
    if not (CAPTIONS and text): return
    fnt=font(48,mono=False,bold=True)
    lines=_wrap(d,text,fnt,W-180)[:3]
    words=[ln.split() for ln in lines]
    total=sum(len(w) for w in words) or 1
    sf=max(speech_frac,0.05)
    shown=total if t>=sf else max(1,int((t/sf)*total)+1)     # tracks the speech pace
    lh=66; total_h=lh*len(lines); y0=1850-total_h
    d.rectangle([0,y0-30,W,1898],fill=(6,8,11))              # subtle band for contrast
    idx=0; yy=y0
    for wl in words:
        vis=[]
        for w in wl:
            idx+=1
            if idx<=shown: vis.append(w)
        if vis:
            s=" ".join(vis)
            bb=d.textbbox((0,0),s,font=fnt); wpx=bb[2]-bb[0]
            # white fill, teal (green) outline — pops off any background
            d.text(((W-wpx)//2,yy),s,font=fnt,fill=(255,255,255),
                   stroke_width=6,stroke_fill=TEAL)
        yy+=lh

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
        bg(img)
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
        bg(img)
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
            bg(img)
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
            bg(img)
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
        bg(img)
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
        bg(img)
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
    s,sr=_kok().create(text,voice=VOICE,speed=SPEED,lang="en-us")
    sf.write(dest,s,sr)
    return dest
def dur(wav):
    r=subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration","-of","csv=p=0",wav],
        capture_output=True,text=True)
    return float(r.stdout.strip())

HASHTAGS="#vett #trading #crypto #hyperliquid #bitcoin"
VETT_TAGS=["vett","trading","crypto","hyperliquid","bitcoin"]
CTA_LINE="Check any wallet free before you copy it → @vett_hl_bot on Telegram (t.me/vett_hl_bot)."

def _scan():
    try: return json.load(open(SCANNER_DATA))
    except Exception: return []

# ---- alternate template: TOP 3 copyable wallets ----
def top3_scenes(rows, rng):
    pick=lambda o: rng.choice(o); scenes=[]
    def title_scene(img,d,t):
        bg(img)
        ctext(d,360,"HYPERLIQUID",font(46,mono=True),INK3)
        ctext(d,430,"3 WALLETS YOU CAN",font(80),INK)
        ctext(d,540,"ACTUALLY COPY",font(80),GREEN)
        ctext(d,760,"(after real fees + slippage)",font(44,mono=True),INK2)
    scenes.append((pick([
        "Most Hyperliquid 'winners' would lose you money. But not these three.",
        "I checked the whole leaderboard. These three actually survive copying."]), title_scene))
    for idx,a in enumerate(rows,1):
        def card(img,d,t,a=a,idx=idx):
            bg(img)
            ctext(d,280,f"#{idx}",font(120),TEAL)
            d.rounded_rectangle([120,500,W-120,1040],36,fill=PANEL)
            ctext(d,560,"A COPIER REALLY GETS",font(38,mono=True),INK2)
            val=int(ease(min(t*1.6,1))*a['copier_pnl'])
            ctext(d,630,f"+${val:,.0f}",font(120,mono=True),GREEN)
            ctext(d,840,f"{a['maker_pct']:.0f}% maker · {a['coins']} coins · {a['span_days']:.0f} days",font(38,mono=True),INK2)
            ctext(d,1160,f"{a['addr'][:6]}…{a['addr'][-4:]}",font(40,mono=True),INK3)
        scenes.append((pick([
            f"Number {idx}. A copier nets {say_money(a['copier_pnl'])}, and it holds up even when you drop the luckiest trades.",
            f"Number {idx}. After every real cost, you'd still make {say_money(a['copier_pnl'])}."]), card))
    def cta(img,d,t):
        bg(img)
        ctext(d,540,"CHECK ANY WALLET",font(72),INK)
        ctext(d,640,"BEFORE YOU COPY",font(72),INK)
        d.rounded_rectangle([150,780,W-150,1050],40,fill=(15,42,34))
        ctext(d,830,"@vett_hl_bot",font(78,mono=True),TEAL)
        ctext(d,950,"t.me/vett_hl_bot",font(48,mono=True),INK2)
    scenes.append((pick([
        "Want the full list? Check any wallet free with Vett on Telegram.",
        "Vet any wallet yourself, free. Vett, on Telegram."]), cta))
    return scenes

# ---- alternate template: LEADERBOARD TRUTH-CHECK ----
def truth_scenes(n, pct, rng):
    pick=lambda o: rng.choice(o); scenes=[]
    def s1(img,d,t):
        bg(img)
        ctext(d,420,"I CHECKED",font(70),INK2)
        ctext(d,540,f"{int(ease(min(t*1.6,1))*n)}",font(220,mono=True),INK)
        ctext(d,820,"HYPERLIQUID 'TOP' WALLETS",font(46,mono=True),INK2)
    scenes.append((pick([
        f"I ran every one of Hyperliquid's top {n} wallets through Vett.",
        f"I checked {n} of the best-looking wallets on Hyperliquid."]), s1))
    def s2(img,d,t):
        bg(img)
        d.rounded_rectangle([100,600,W-100,980],40,fill=(28,16,15))
        ctext(d,660,f"{int(ease(min(t*1.5,1))*pct)}%",font(200,mono=True),RED)
        ctext(d,920,"WOULD LOSE A COPIER MONEY",font(44,mono=True),INK2)
    scenes.append((pick([
        f"{pct:.0f} percent of them would actually lose you money if you copied them.",
        f"{pct:.0f} percent are traps. You'd lose money copying them."]), s2))
    def s3(img,d,t):
        bg(img)
        ctext(d,400,"WHY?",font(90),INK)
        for i,(a,b) in enumerate([("Taker fees","you cross the spread, they don't"),
                                  ("Slippage","you enter later and worse"),
                                  ("Luck","a few trades you can't catch")]):
            y=600+i*230
            d.rounded_rectangle([110,y,W-110,y+200],28,fill=PANEL)
            ctext(d,y+40,a,font(58),RED,center=False,x=170)
            ctext(d,y+118,b,font(38,mono=False,bold=False),INK2,center=False,x=170)
    scenes.append((pick([
        "Fees, slippage, and luck. The advertised number is never what a copier gets.",
        "Real fees, worse fills, and lucky trades you could never catch."]), s3))
    def cta(img,d,t):
        bg(img)
        ctext(d,560,"KNOW BEFORE",font(76),INK)
        ctext(d,660,"YOU COPY",font(76),INK)
        d.rounded_rectangle([150,820,W-150,1090],40,fill=(15,42,34))
        ctext(d,870,"@vett_hl_bot",font(78,mono=True),TEAL)
        ctext(d,990,"t.me/vett_hl_bot",font(48,mono=True),INK2)
    scenes.append((pick([
        "Check any wallet free before you copy it. Vett, on Telegram.",
        "Don't be the one who finds out the hard way. Vett, free on Telegram."]), cta))
    return scenes

# ---- template dispatchers: each returns (scenes, meta, label) or None ----
def trap_template(rng):
    s=story_mod.pick()
    if not s: return None
    scenes=build_scenes(s,rng)
    if s.get('trap_type')=='maker':
        title=f"This Hyperliquid 'top trader' made {money(s['raw_pnl'])} — but you CAN'T copy it 🚩"
        desc=(f"They advertise {money(s['raw_pnl'])} profit, but {s['maker_pct']:.0f}% is market-maker fills. "
              f"Copy them by taking and you get the worse side of every trade.\n\n{CTA_LINE}\n\n{HASHTAGS}")
    else:
        title=f"This Hyperliquid 'top trader' would LOSE you {money(s['copier_pnl']).lstrip('-')} 🚩"
        desc=(f"They advertise {money(s['raw_pnl'])} at {s['win_rate']:.0f}% win rate. Copy them and after "
              f"real fees + slippage you'd get {money(s['copier_pnl'])}.\n\n{CTA_LINE}\n\n{HASHTAGS}")
    return scenes, dict(kind='trap',addr=s['addr'],title=title,description=desc,tags=VETT_TAGS), f"trap {s['addr'][:10]}"

def top3_template(rng):
    good=[a for a in _scan() if a.get('final_verdict')=='COPYABLE' and a.get('copier_pnl',0)>0]
    good.sort(key=lambda a:-a.get('score',0))
    if len(good)<3: return None
    rows=good[:3]
    title="3 Hyperliquid wallets a copier could ACTUALLY follow ✅"
    desc=("Most 'winners' would lose a copier money — these three pass every honesty check "
          f"(real fees, slippage, no maker rebate, luck test).\n\nVet any wallet free → @vett_hl_bot "
          f"on Telegram (t.me/vett_hl_bot).\n\n{HASHTAGS}")
    return top3_scenes(rows,rng), dict(kind='top3',addr=rows[0]['addr'],title=title,description=desc,tags=VETT_TAGS), "top3"

def truth_template(rng):
    d=_scan(); n=len(d)
    if n<20: return None
    pct=100*sum(1 for a in d if a.get('final_verdict')=='DO NOT COPY')/n
    title=f"I checked {n} Hyperliquid 'top' wallets — {pct:.0f}% would lose you money 🚩"
    desc=(f"{pct:.0f}% of the leaderboard's 'winners' would lose a copier money after real fees, "
          f"slippage and luck.\n\n{CTA_LINE}\n\n{HASHTAGS}")
    return truth_scenes(n,pct,rng), dict(kind='truth',addr='',title=title,description=desc,tags=VETT_TAGS), "truthcheck"

# ---- alternate template: SPOTLIGHT a genuinely copyable wallet (positive tone) ----
def spotlight_scenes(a, rng):
    pick=lambda o: rng.choice(o); scenes=[]
    tag=f"{a['addr'][:6]}…{a['addr'][-4:]}"
    def s1(img,d,t):
        bg(img)
        ctext(d,360,"HYPERLIQUID",font(46,mono=True),INK3)
        ctext(d,430,"A WALLET YOU CAN",font(80),INK)
        ctext(d,540,"ACTUALLY COPY",font(80),GREEN)
        ctext(d,760,"(rare — most can't be)",font(44,mono=True),INK2)
    scenes.append((pick([
        "Almost every 'top' Hyperliquid wallet is a trap. This one isn't.",
        "I check the leaderboard every day. Genuinely copyable wallets are rare — here's one."]), s1))
    def s2(img,d,t):
        bg(img)
        ctext(d,300,"✅ COPYABLE",font(88),GREEN)
        d.rounded_rectangle([120,520,W-120,1050],36,fill=PANEL)
        ctext(d,580,"A COPIER REALLY GETS",font(38,mono=True),INK2)
        val=int(ease(min(t*1.6,1))*a['copier_pnl'])
        ctext(d,650,f"+${val:,.0f}",font(120,mono=True),GREEN)
        ctext(d,860,f"{a['maker_pct']:.0f}% maker · {a['coins']} coins · {a['span_days']:.0f} days",font(38,mono=True),INK2)
        ctext(d,1180,tag,font(40,mono=True),INK3)
    scenes.append((pick([
        f"After real fees and slippage, a copier still nets {say_money(a['copier_pnl'])}.",
        f"Even paying every real cost, you'd make {say_money(a['copier_pnl'])} copying this one."]), s2))
    def s3(img,d,t):
        bg(img)
        ctext(d,340,"WHY IT PASSES",font(60),INK)
        for i,(x,y) in enumerate([("Takes, not makes","you can replicate its fills"),
                                  ("Not luck","edge survives dropping its best trades"),
                                  ("Beats the fees","real profit after every cost")]):
            yy=620+i*230
            d.rounded_rectangle([110,yy,W-110,yy+200],28,fill=PANEL)
            ctext(d,yy+40,x,font(56),GREEN,center=False,x=170)
            ctext(d,yy+118,y,font(36,mono=False,bold=False),INK2,center=False,x=170)
    scenes.append((pick([
        "It takes trades you can actually copy, the edge survives a luck check, and it beats the fees.",
        "You can replicate its fills, the profit isn't a few lucky trades, and it clears every cost."]), s3))
    def s4(img,d,t):
        bg(img)
        ctext(d,470,"FIND THEM YOURSELF",font(66),INK)
        ctext(d,560,"BEFORE YOU COPY",font(66),INK)
        d.rounded_rectangle([150,760,W-150,1030],40,fill=(15,42,34))
        ctext(d,810,"@vett_hl_bot",font(78,mono=True),TEAL)
        ctext(d,930,"t.me/vett_hl_bot",font(48,mono=True),INK2)
    scenes.append((pick([
        "Vett finds the rare copyable ones for you, free, on Telegram.",
        "Don't guess. Vett surfaces the real ones — free on Telegram."]), s4))
    return scenes

# ---- alternate template: EDUCATIONAL "3 signs a wallet will lose you money" ----
def signs_scenes(rng):
    pick=lambda o: rng.choice(o); scenes=[]
    def s1(img,d,t):
        bg(img)
        ctext(d,420,"3 SIGNS A WALLET",font(80),INK)
        ctext(d,530,"WILL LOSE YOU MONEY",font(66),RED)
        ctext(d,760,"before you copy it",font(46,mono=True),INK2)
    scenes.append((pick([
        "Three signs a Hyperliquid wallet will lose you money, even though it looks green.",
        "Before you copy any wallet, check for these three red flags."]), s1))
    signs=[("1. It's a market maker","You can't copy the spread edge"),
           ("2. A few lucky trades","Drop 5 trades, the profit's gone"),
           ("3. Fees beat the edge","Fees cost more than it earns")]
    for i,(a,b) in enumerate(signs):
        def sc(img,d,t,a=a,b=b):
            bg(img)
            ctext(d,360,a.split('. ',1)[0]+".",font(160,mono=True),RED)
            d.rounded_rectangle([110,620,W-110,900],28,fill=PANEL)
            ctext(d,680,a.split('. ',1)[1],font(60),INK,center=False,x=160)
            ctext(d,780,b,font(40,mono=False,bold=False),INK2,center=False,x=160)
        scenes.append((pick([f"{a[3:]}. {b}.", f"Sign {a[0]}. {a[3:]} — {b.lower()}."]), sc))
    def cta(img,d,t):
        bg(img)
        ctext(d,470,"VETT CHECKS",font(72),INK)
        ctext(d,560,"ALL THREE FOR YOU",font(66),INK)
        d.rounded_rectangle([150,760,W-150,1030],40,fill=(15,42,34))
        ctext(d,810,"@vett_hl_bot",font(78,mono=True),TEAL)
        ctext(d,930,"t.me/vett_hl_bot",font(48,mono=True),INK2)
    scenes.append((pick([
        "Vett checks all three for you in seconds. Free, on Telegram.",
        "Paste any wallet and Vett checks all three instantly. Free on Telegram."]), cta))
    return scenes

def spotlight_template(rng):
    good=[a for a in _scan() if a.get('final_verdict')=='COPYABLE' and a.get('copier_pnl',0)>0 and a.get('maker_pct',100)<40]
    good.sort(key=lambda a:-a.get('score',0))
    if not good: return None
    a=good[0]
    title=f"A Hyperliquid wallet you can ACTUALLY copy (+{money(a['copier_pnl']).lstrip('+')}) ✅"
    desc=("Rare: this wallet passes every honesty check — taker-executable, survives a luck test, "
          f"and beats the fees.\n\nVet any wallet free → @vett_hl_bot on Telegram (t.me/vett_hl_bot).\n\n{HASHTAGS}")
    return spotlight_scenes(a,rng), dict(kind='spotlight',addr=a['addr'],title=title,description=desc,tags=VETT_TAGS), "spotlight"

def signs_template(rng):
    title="3 signs a Hyperliquid wallet will LOSE you money 🚩"
    desc=("Market-maker fills, luck-concentrated profit, and fees bigger than the edge — the three "
          f"reasons a 'green' wallet loses a copier money.\n\n{CTA_LINE}\n\n{HASHTAGS}")
    return signs_scenes(rng), dict(kind='signs',addr='',title=title,description=desc,tags=VETT_TAGS), "signs"

def render_and_write(scenes, out):
    tmp="output/_tmp"; shutil.rmtree(tmp,ignore_errors=True); os.makedirs(tmp)
    durs=[]; sfr=[]
    for i,(narr,_) in enumerate(scenes):
        tts(narr,f"{tmp}/a{i}.wav")
        nd=dur(f"{tmp}/a{i}.wav"); sd=max(nd,1.2)+0.35
        durs.append(sd); sfr.append(min(1.0, nd/sd) if sd else 1.0)   # speech fraction of scene
    fi=0
    for i,(narr,draw_fn) in enumerate(scenes):
        n=max(1,int(round(durs[i]*FPS)))
        for k in range(n):
            img=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(img)
            prog=k/max(1,n-1)
            draw_fn(img,d,prog)
            draw_caption(img,d,narr,prog,sfr[i])  # captions paced to the spoken audio
            img.save(f"{tmp}/f{fi:05d}.png"); fi+=1
    with open(f"{tmp}/alist.txt","w") as f:
        for i in range(len(scenes)):
            subprocess.run([FFMPEG,"-y","-i",f"{tmp}/a{i}.wav","-af",
                f"apad=pad_dur={durs[i]}","-t",str(durs[i]),f"{tmp}/p{i}.wav"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            f.write(f"file 'p{i}.wav'\n")
    subprocess.run([FFMPEG,"-y","-f","concat","-safe","0","-i",f"{tmp}/alist.txt","-c","copy",
        f"{tmp}/audio.wav"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run([FFMPEG,"-y","-framerate",str(FPS),"-i",f"{tmp}/f%05d.png","-i",f"{tmp}/audio.wav",
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest",
        "-vf","format=yuv420p",out],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    shutil.rmtree(tmp,ignore_errors=True)
    return sum(durs), fi

def generate(out="output/short.mp4"):
    rng=random.Random()
    # trap is the core; top3 and truth add variety. Weighted, with fallback.
    order=[trap_template, trap_template, top3_template, truth_template,
           spotlight_template, signs_template]
    rng.shuffle(order)
    res=None
    for tf in order:
        res=tf(rng)
        if res: break
    if not res: res=trap_template(rng)
    if not res: print("no story available"); return None
    scenes, meta, label = res
    print(f"template: {label}")
    # optional darkened photo backdrop (only if PEXELS_KEY is set)
    global _BGIMG
    # Default backdrop = a procedurally-drawn candlestick chart: always on-topic
    # and clean. (Stock-photo search kept returning irrelevant junk — candles,
    # cell towers — so photos are now opt-in via VETT_PHOTOS=1.)
    if os.environ.get("VETT_PHOTOS") == "1":
        _BGIMG = fetch_bg(random.choice(["forex trading graph","bitcoin price chart","market data screen"]))
        print(f"  backdrop: photo {'on' if _BGIMG is not None else 'failed→chart'}")
    if _BGIMG is None:
        bias = -30 if meta.get("kind") == "top3" else 30   # top3 trends up, traps trend down
        _BGIMG = chart_bg(rng, up_bias=bias)
        print("  backdrop: candlestick chart")
    total, fi = render_and_write(scenes, out)
    _BGIMG = None
    json.dump(meta, open(os.path.join(os.path.dirname(out),"meta.json"),"w"))
    print(f"done -> {out}  ({total:.0f}s, {fi} frames)")
    return out

if __name__=='__main__':
    generate()
