# Vett — Browser Extension

Everything the Telegram bot does, right in your browser — no login, no server,
no keys. All analysis runs locally against Hyperliquid's public API.

## Features
- **🔍 Check** — paste a wallet (or it auto-fills from the current tab) → honest verdict.
- **⚖️ Compare** — two wallets side by side.
- **📈 Positions** — a wallet's current open longs/shorts, size, leverage, uPnL.
- **👁 Watchlist + alerts** — watch wallets; get a **desktop notification** when a
  verdict changes (checked every 30 min by the background worker).
- **🏆 Top** — scans the live leaderboard and shows the genuinely copyable wallets.
- **On-page badges** — every wallet address on app.hyperliquid.xyz gets a 🔍 Vett badge.
- **4 languages** (EN / ES / 中文 / PT), auto-detected.

## Install (no Web Store needed)
See **https://excevity.github.io/vett/install.html** for click-by-click steps, or:
1. Download `vett_extension.zip` and unzip it.
2. Open `chrome://extensions` → turn on **Developer mode** (top-right).
3. Click **Load unpacked** → pick the unzipped folder.
4. Pin the Vett icon. Done.

## Files
- `manifest.json` (MV3), `analyzer.js` (mirror of analyzer.py + leaderboard/positions),
  `background.js` (off-page analysis + watchlist alerts), `content.js` (on-page badges),
  `popup.{html,css,js}` (the 5-tab UI), `i18n.js` (translations).
