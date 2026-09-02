#!/usr/bin/env python3
"""Upload output/short.mp4 to YouTube using output/meta.json for title/desc/tags.
Reads YT_* from environment (.env locally, Actions Secrets in CI).
Usage: python3 code/publish.py [public|private|unlisted]  (default public)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from upload import upload

def load_dotenv():
    p = os.path.join(HERE, "..", ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k, v)

def main():
    load_dotenv()
    privacy = sys.argv[1] if len(sys.argv) > 1 else "public"
    out = os.path.join(HERE, "..", "output")
    vid = os.path.join(out, "short.mp4")
    meta_p = os.path.join(out, "meta.json")
    if not os.path.exists(vid):
        print("no output/short.mp4 — run generate.py first"); return 1
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {
        "title": "Vett — check any Hyperliquid wallet", "description": "@vett_hl_bot on Telegram",
        "tags": ["hyperliquid", "crypto", "copytrading"]}
    r = upload(vid, meta["title"], meta["description"], meta.get("tags"), privacy=privacy)
    if r:
        print(f"published to YouTube ({privacy}): https://youtube.com/shorts/{r}")
    else:
        print("YouTube upload skipped/failed (check YT_* creds)")
    # TikTok (optional; skips if TIKTOK_* not set). Draft mode unless audited.
    try:
        from tiktok_upload import upload as tt_upload
        tt_priv = "PUBLIC_TO_EVERYONE" if privacy == "public" else "SELF_ONLY"
        tt_upload(vid, meta["title"], privacy=tt_priv)
    except Exception as e:
        print(f"TikTok step error (non-fatal): {e}")
    return 0 if r else 1

if __name__ == "__main__":
    sys.exit(main())
