#!/usr/bin/env python3
"""Upload a short to TikTok via the Content Posting API.

TWO MODES (TikTok's rules, not ours):
  - DRAFT (default, no app audit needed): pushes the video to your TikTok
    "inbox"/drafts. You open the app and tap post. Needs scope video.upload.
  - DIRECT (set TIKTOK_DIRECT=1, requires passing TikTok's Content Posting
    audit): posts straight to your profile. Needs scope video.publish. Until
    audited, direct posts are forced SELF_ONLY (only you can see them).

Creds (env / .env / Actions secrets):
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
Untested until real creds exist — built to TikTok's documented v2 flow.
"""
import os, json, urllib.request, urllib.parse

OAUTH = "https://open.tiktokapis.com/v2/oauth/token/"
INBOX = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
DIRECT = "https://open.tiktokapis.com/v2/post/publish/video/init/"

def _have():
    return all(os.environ.get(k) for k in
               ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"))

def _access_token():
    data = urllib.parse.urlencode({
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
    }).encode()
    req = urllib.request.Request(OAUTH, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    if "access_token" not in r:
        raise RuntimeError(f"TikTok token refresh failed: {r}")
    return r["access_token"]

def upload(path, title="", privacy="SELF_ONLY"):
    if not _have():
        print("TikTok creds not set — skipping TikTok."); return None
    direct = os.environ.get("TIKTOK_DIRECT") == "1"
    tok = _access_token()
    size = os.path.getsize(path)
    # single-chunk upload is allowed when the file is <= 64MB (our shorts are ~1MB)
    body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                            "chunk_size": size, "total_chunk_count": 1}}
    if direct:
        body["post_info"] = {"title": title[:150], "privacy_level": privacy,
                             "disable_comment": False, "disable_duet": False,
                             "disable_stitch": False}
    init_url = DIRECT if direct else INBOX
    req = urllib.request.Request(init_url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    d = (r or {}).get("data", {})
    upload_url = d.get("upload_url"); pid = d.get("publish_id")
    if not upload_url:
        print(f"TikTok init failed: {r}"); return None
    with open(path, "rb") as f:
        vid = f.read()
    put = urllib.request.Request(upload_url, data=vid, method="PUT",
        headers={"Content-Type": "video/mp4",
                 "Content-Range": f"bytes 0-{size-1}/{size}"})
    urllib.request.urlopen(put, timeout=120)
    print(f"TikTok: {'posted (direct)' if direct else 'sent to your drafts — open the app to post'} "
          f"(publish_id={pid})")
    return pid

if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "output/short.mp4"
    upload(p, "Check any Hyperliquid wallet before you copy it — @vett_hl_bot")
