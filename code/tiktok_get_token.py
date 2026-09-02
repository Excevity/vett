"""One-time helper: mint a TikTok refresh token with the video.upload scope.
Run on your machine. Reads TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / your
registered TIKTOK_REDIRECT_URI from ../.env (or env), prints the auth URL,
you approve in a browser, then paste the `code` from the redirected URL back.

TikTok requires the redirect URI to be HTTPS and registered in your app. It's
fine if the redirect page itself 404s — you only need the ?code=... it lands on.
"""
import os, sys, json, urllib.request, urllib.parse
from pathlib import Path

envp = Path(__file__).resolve().parent.parent / ".env"
if envp.exists():
    for line in envp.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k, v)

ck = os.environ.get("TIKTOK_CLIENT_KEY")
cs = os.environ.get("TIKTOK_CLIENT_SECRET")
redirect = os.environ.get("TIKTOK_REDIRECT_URI")
if not (ck and cs and redirect):
    sys.exit("Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET and TIKTOK_REDIRECT_URI in .env first.")

scope = "video.upload"   # add ,video.publish once you pursue the audit
auth = ("https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
    "client_key": ck, "scope": scope, "response_type": "code",
    "redirect_uri": redirect, "state": "vett"}))
print("\n1) Open this URL, approve, and let it redirect:\n\n" + auth + "\n")
print("2) Copy the `code` value from the redirected URL (…?code=XXXX&…).")
code = input("\nPaste the code here: ").strip()

data = urllib.parse.urlencode({
    "client_key": ck, "client_secret": cs, "code": code,
    "grant_type": "authorization_code", "redirect_uri": redirect}).encode()
req = urllib.request.Request("https://open.tiktokapis.com/v2/oauth/token/", data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"})
r = json.load(urllib.request.urlopen(req, timeout=30))
if "refresh_token" not in r:
    sys.exit(f"Failed: {r}")
print("\n=== TIKTOK_REFRESH_TOKEN (paste this back) ===")
print(r["refresh_token"])
print("scope granted:", r.get("scope"))
