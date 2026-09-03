// Service worker: runs analysis off-page (for content.js) AND runs watchlist
// alerts on a timer — re-vets watched wallets and fires a desktop notification
// when a verdict changes. No server; all local to the browser.
importScripts("analyzer.js");

// --- analysis requests from the content script ---
chrome.runtime.onMessage.addListener((msg, sender, send) => {
  if (msg && msg.type === "analyze") {
    analyze(msg.addr)
      .then((a) => {
        if (!a || a.tooFew) return send({ a, res: null, tooFew: !!(a && a.tooFew) });
        send({ a, res: verdict(a) });
      })
      .catch((e) => send({ error: String(e) }));
    return true;
  }
});

// --- watchlist alerts ---
const ALARM = "vett-watch";
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM, { periodInMinutes: 30 });
});
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(ALARM, { periodInMinutes: 30 });
});

async function getWatch() {
  const o = await chrome.storage.local.get("watch");
  return o.watch || {}; // { addrLower: lastVerdict|null }
}
async function setWatch(w) { await chrome.storage.local.set({ watch: w }); }

async function getWhaleMin() { const o = await chrome.storage.local.get("whaleMin"); return o.whaleMin != null ? o.whaleMin : 25000; }
async function getPos() { const o = await chrome.storage.local.get("bgpos"); return o.bgpos || {}; }
async function setPos(p) { await chrome.storage.local.set({ bgpos: p }); }

async function positionsNotional(addr) {
  const cs = await hlPost({ type: "clearinghouseState", user: addr });
  const out = {};
  for (const p of (cs && cs.assetPositions) || []) {
    const pos = p.position || {}; const szi = parseFloat(pos.szi) || 0;
    if (szi === 0) continue;
    out[pos.coin] = [parseFloat(pos.positionValue) || 0, szi > 0 ? "LONG" : "SHORT"];
  }
  return out;
}

chrome.alarms.onAlarm.addListener(async (a) => {
  if (a.name !== ALARM) return;
  const watch = await getWatch();
  const addrs = Object.keys(watch);
  if (!addrs.length) return;
  const allPos = await getPos();
  const whaleMin = await getWhaleMin();
  for (const addr of addrs) {
    try {
      const an = await analyze(addr);
      if (!an || an.tooFew) continue;
      const nv = verdict(an).v;
      const ov = watch[addr];
      if (ov && ov !== nv) {
        chrome.notifications.create("vett-v-" + addr + Date.now(), {
          type: "basic", iconUrl: "icons/128.png",
          title: "Vett — verdict changed",
          message: `${addr.slice(0, 8)}…${addr.slice(-4)}\n${ov} → ${nv}`, priority: 2,
        });
      }
      watch[addr] = nv;
      // whale alert: coin newly appears / grows by >= WHALE_MIN
      const np = await positionsNotional(addr); const op = allPos[addr] || {};
      for (const coin in np) {
        const [val, side] = np[coin]; const prev = (op[coin] || [0])[0];
        if (whaleMin > 0 && val >= whaleMin && val - prev >= whaleMin) {
          chrome.notifications.create("vett-w-" + addr + coin + Date.now(), {
            type: "basic", iconUrl: "icons/128.png",
            title: "🐋 Vett — whale move",
            message: `${addr.slice(0, 8)}… ${side} ${coin} ~$${val.toLocaleString("en-US", { maximumFractionDigits: 0 })}\nVerdict: ${nv}`,
            priority: 2,
          });
        }
      }
      allPos[addr] = np;
    } catch (e) {}
    await new Promise((r) => setTimeout(r, 300));
  }
  await setWatch(watch); await setPos(allPos);
});
