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

chrome.alarms.onAlarm.addListener(async (a) => {
  if (a.name !== ALARM) return;
  const watch = await getWatch();
  const addrs = Object.keys(watch);
  if (!addrs.length) return;
  for (const addr of addrs) {
    try {
      const an = await analyze(addr);
      if (!an || an.tooFew) continue;
      const nv = verdict(an).v;
      const ov = watch[addr];
      if (ov && ov !== nv) {
        chrome.notifications.create("vett-" + addr + Date.now(), {
          type: "basic", iconUrl: "icons/128.png",
          title: "Vett alert — verdict changed",
          message: `${addr.slice(0, 8)}…${addr.slice(-4)}\n${ov} → ${nv}`,
          priority: 2,
        });
      }
      watch[addr] = nv;
    } catch (e) {}
    await new Promise((r) => setTimeout(r, 300));
  }
  await setWatch(watch);
});
