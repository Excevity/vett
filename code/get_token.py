"""One-time helper: mint a YouTube refresh token with the UPLOAD scope.
Run this on your own machine (it opens a browser for the Google consent screen).
Reads YT_CLIENT_ID / YT_CLIENT_SECRET from ../.env, prints a refresh token.
Paste that token back and it goes into .env as YT_REFRESH_TOKEN."""
import os,sys
from pathlib import Path

# load ../.env
envp=Path(__file__).resolve().parent.parent/".env"
if envp.exists():
    for line in envp.read_text().splitlines():
        line=line.strip()
        if line and not line.startswith("#") and "=" in line:
            k,v=line.split("=",1); os.environ.setdefault(k,v)

cid=os.environ.get("YT_CLIENT_ID"); csec=os.environ.get("YT_CLIENT_SECRET")
if not (cid and csec):
    sys.exit("Set YT_CLIENT_ID and YT_CLIENT_SECRET in .env first.")

from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
cfg={"installed":{"client_id":cid,"client_secret":csec,
    "auth_uri":"https://accounts.google.com/o/oauth2/auth",
    "token_uri":"https://oauth2.googleapis.com/token",
    "redirect_uris":["http://localhost"]}}
flow=InstalledAppFlow.from_client_config(cfg,SCOPES)
try:
    creds=flow.run_local_server(port=0, prompt="consent")
except Exception:
    # headless fallback: prints a URL to paste into any browser
    creds=flow.run_console()
print("\n=== YOUR REFRESH TOKEN (paste this back) ===")
print(creds.refresh_token)
print("============================================")
