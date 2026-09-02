"""Optional: upload a generated short to YouTube. Env-gated — reads creds from
environment only (never hardcoded). Set YT_CLIENT_ID / YT_CLIENT_SECRET /
YT_REFRESH_TOKEN (in .env or GitHub Actions Secrets)."""
import os,sys
def upload(path,title,description,tags=None,privacy="public"):
    cid=os.environ.get("YT_CLIENT_ID"); csec=os.environ.get("YT_CLIENT_SECRET")
    rtok=os.environ.get("YT_REFRESH_TOKEN")
    if not all([cid,csec,rtok]):
        print("YT creds not set (YT_CLIENT_ID/SECRET/REFRESH_TOKEN) — skipping upload."); return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds=Credentials(None,refresh_token=rtok,client_id=cid,client_secret=csec,
        token_uri="https://oauth2.googleapis.com/token")
    yt=build("youtube","v3",credentials=creds)
    body={"snippet":{"title":title[:100],"description":description[:4900],
            "tags":(tags or ["hyperliquid","crypto","copytrading"])[:15],"categoryId":"28"},
          "status":{"privacyStatus":privacy,"selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(path,mimetype="video/mp4",resumable=True)
    req=yt.videos().insert(part="snippet,status",body=body,media_body=media)
    resp=None
    while resp is None:
        status,resp=req.next_chunk()
    vid=resp["id"]; print(f"uploaded: https://youtube.com/shorts/{vid}")
    return vid
if __name__=='__main__':
    upload(sys.argv[1],"Vett demo","Auto-generated.",None)
