# TikTok Content Posting API — Audit Submission (copy-paste ready)

Use this when you submit the Vett app for the Content Posting audit (to unlock
`video.publish` / direct public posting so you stop posting drafts by hand).

---

## Field: "Explain how each product and scope works within your app or website"
(Paste this — it's ~880 characters, under the 1000 limit.)

```
Vett is an automated content tool that publishes short, data-driven videos about
public Hyperliquid trading wallets to the account owner's own TikTok.

Login Kit (user.info.basic): used only to authenticate the account owner (me, the
operator) so the app can identify the connected account and upload to it. No other
user data is accessed.

Content Posting API (video.upload): used to upload my own auto-generated videos to
my own TikTok account. Each day a pipeline renders a short from public on-chain
data and uploads it via video.upload, where it lands in my TikTok inbox/drafts for
me to review and post. No content from other users is accessed or posted.

We do not collect data about other TikTok users, do not post on anyone else's
behalf, and comply with TikTok's Developer Terms and Community Guidelines. Website:
https://excevity.github.io/vett/
```

---

## Field: Demo video (record a ~40–60s screen recording showing the full flow)

TikTok requires the demo to show the **complete end-to-end integration**, on the
**same domain** as your app website (`excevity.github.io/vett`). Record this order:

1. **Show the website** — open `https://excevity.github.io/vett/` for ~2s (proves the domain matches).
2. **Show the authorization (Login Kit)** — open the TikTok auth link, sign in,
   and approve the `user.info.basic` + `video.upload` scopes. (You can reuse the
   auth flow we already did; just screen-record it once.)
3. **Show the upload (Content Posting API)** — run the pipeline (or trigger the
   GitHub Action) so a video is uploaded, and show the terminal/log line
   `TikTok: sent to your drafts …` OR the resulting draft appearing in the TikTok app.
4. **Show the result** — open the TikTok app → inbox/drafts → the uploaded video is
   there, ready to post. Tapping through to post it is a nice finish.

Tips TikTok looks for:
- The website domain in the demo must match the URL you entered in app settings.
- Every product/scope you selected (Login Kit, Content Posting API, user.info.basic,
  video.upload) must be visibly demonstrated — if you don't use one, remove it first.
- Clear UI + user interactions; no fast cuts.
- mp4 or mov, ≤50MB.

## After approval
Tell me and I'll set the repo variable `TIKTOK_DIRECT=1` — the pipeline then posts
straight to public instead of drafts. (Until then, drafts + you tapping post works fine.)
```
