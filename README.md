# vett_content — auto-generated data shorts for @vett_hl_bot

Turns the Vett scanner's findings into vertical shorts for TikTok/YouTube.
**Pure data-driven visuals** (no stock footage, no copyrighted clips), free
Piper TTS, numbers templated straight from real scanner output — never invented.

## Why it looks like this
Every "trap exposé" is built from a real wallet: it advertises green, but the
scanner shows a copier would lose money. The video shows that gap. The honesty
is the hook, and it's un-fakeable because the numbers are real.

## Pipeline (code/)
- `story.py`    — picks the best unused wallet story from the scanner output
- `generate.py` — script (template) -> Piper narration -> PIL animated frames -> ffmpeg
- `paths.py`    — tool locations

## Run
    python3 code/generate.py        # -> output/short.mp4 (~33s, 1080x1920)

## Setup (no root needed) — see setup.sh
Installs ffmpeg (static), Piper TTS + voice, Pillow/numpy into user space.

## Secrets / public-repo safety
- Video generation needs **NO API keys**. Safe to run and open-source as-is.
- Only the OPTIONAL YouTube auto-upload stage needs keys — put them in `.env`
  (gitignored) or GitHub Actions Secrets. Never in code. See `.env.example`.
- `.gitignore` excludes .env, tokens, voice models, and generated media.

## Status
- [x] story selection, script, TTS, data-driven render -> working MP4
- [ ] YouTube auto-upload stage (env-gated)
- [ ] scheduler (local cron or GitHub Actions) for daily auto-posting
