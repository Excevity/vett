let lang = localStorage.getItem("vett_lang") || pickLang();
const $ = (id) => document.getElementById(id);
const ADDR_RE = /0x[0-9a-fA-F]{40}/;
const money = (x) => (x < 0 ? "-" : "+") + "$" + Math.abs(x).toLocaleString("en-US", { maximumFractionDigits: 0 });

// ---------- watchlist storage (shared with the background alert worker) ----------
async function getWatch() { const o = await chrome.storage.local.get("watch"); return o.watch || {}; }
async function addWatch(addr, v) { const w = await getWatch(); w[addr.toLowerCase()] = v || null; await chrome.storage.local.set({ watch: w }); }
async function delWatch(addr) { const w = await getWatch(); delete w[addr.toLowerCase()]; await chrome.storage.local.set({ watch: w }); }
async function isWatched(addr) { return (await getWatch()).hasOwnProperty(addr.toLowerCase()); }

// ---------- shared rendering ----------
function verdictCard(a, res, addr, opts = {}) {
  const v = res.v, cls = v === "DO NOT COPY" ? "DONOT" : v;
  const icon = v === "COPYABLE" ? "✅" : v === "RISKY" ? "⚠️" : "🚫";
  const foot = v === "COPYABLE" ? T(lang, "foot_COPYABLE") : v === "RISKY" ? T(lang, "foot_RISKY") : T(lang, "foot");
  const flags = res.flags.slice(0, 3).map((f) => `<div class="flag">• ${f.split(":")[0]}</div>`).join("");
  const makerLine = a.maker_pct > 50 ? `<div class="flag">${T(lang, "maker", { p: a.maker_pct.toFixed(0) })}</div>` : "";
  const watchBtn = opts.watchBtn
    ? `<div style="margin-top:8px"><button class="wbtn" id="wtoggle" data-addr="${addr}">${opts.watching ? T(lang,"unwatch_btn") : T(lang,"watch_btn")}</button></div>` : "";
  return `<div class="card">
    <div class="vhead ${cls}">${icon} ${v}</div>
    <div class="sec">${T(lang, "adv")}</div>
    <div class="row"><span class="k">PnL</span><span class="v ${a.raw_pnl<0?'neg':'pos'}">${money(a.raw_pnl)}</span></div>
    <div class="row"><span class="k">${T(lang,"winrate")}</span><span class="v">${a.win_rate.toFixed(0)}%</span></div>
    <div class="sec">${T(lang, "copier")}</div>
    <div class="row"><span class="k">${T(lang,"afterfees")}</span><span class="v ${a.copier_pnl<0?'neg':'pos'}">${money(a.copier_pnl)}</span></div>
    <div class="row"><span class="k">${T(lang,"traded",{c:a.coins,d:a.span_days.toFixed(0)})}</span><span class="v"></span></div>
    ${makerLine}
    ${flags ? `<div class="sec">${T(lang,"flags")}</div>${flags}` : ""}
    <div class="foot">${foot}</div>
    ${watchBtn}
  </div>`;
}
const msg = (el, text) => { el.innerHTML = `<div class="msg">${text}</div>`; };

async function analyzeInto(el, addr, withWatch) {
  el.innerHTML = ""; msg(el, T(lang, "checking"));
  try {
    const a = await analyze(addr);
    if (!a) return msg(el, T(lang, "nodata"));
    if (a.tooFew) return msg(el, T(lang, "toofew"));
    const res = verdict(a);
    const watching = withWatch ? await isWatched(addr) : false;
    el.innerHTML = verdictCard(a, res, addr, { watchBtn: withWatch, watching });
    if (withWatch) {
      const b = $("wtoggle");
      b && (b.onclick = async () => {
        if (await isWatched(addr)) { await delWatch(addr); b.textContent = T(lang, "watch_btn"); }
        else { await addWatch(addr, res.v); b.textContent = T(lang, "unwatch_btn"); }
      });
    }
  } catch (e) { msg(el, T(lang, "err")); }
}

// ---------- CHECK ----------
async function runCheck() {
  const addr = ($("addr").value.match(ADDR_RE) || [""])[0];
  if (!addr) return msg($("out"), T(lang, "bad"));
  $("go").disabled = true; await analyzeInto($("out"), addr, true); $("go").disabled = false;
}

// ---------- COMPARE ----------
async function runCompare() {
  const a = ($("cmpA").value.match(ADDR_RE) || [""])[0];
  const b = ($("cmpB").value.match(ADDR_RE) || [""])[0];
  if (!a || !b) return msg($("cmpOut"), T(lang, "bad"));
  $("cmpGo").disabled = true; $("cmpOut").innerHTML = ""; msg($("cmpOut"), T(lang, "checking"));
  try {
    const out = [];
    for (const addr of [a, b]) {
      const an = await analyze(addr);
      if (!an || an.tooFew) { out.push(`<div class="msg"><code>${addr.slice(0,8)}…</code> — ${T(lang,"nodata")}</div>`); continue; }
      out.push(verdictCard(an, verdict(an), addr));
    }
    $("cmpOut").innerHTML = out.join("");
  } catch (e) { msg($("cmpOut"), T(lang, "err")); }
  $("cmpGo").disabled = false;
}

// ---------- POSITIONS ----------
async function runPositions() {
  const addr = ($("posAddr").value.match(ADDR_RE) || [""])[0];
  if (!addr) return msg($("posOut"), T(lang, "bad"));
  $("posGo").disabled = true; msg($("posOut"), T(lang, "checking"));
  try {
    const ps = await positions(addr);
    if (!ps.length) { msg($("posOut"), T(lang, "pos_none")); }
    else {
      $("posOut").innerHTML = `<div class="sec">${T(lang,"pos_title")}</div>` + ps.map((p) =>
        `<div class="trow"><span>${p.side==="LONG"?"🟢":"🔴"} <b>${p.coin}</b> ${p.lev}x</span>
         <span class="${p.upnl<0?'neg':'pos'}">$${p.value.toLocaleString("en-US",{maximumFractionDigits:0})} · ${money(p.upnl)}</span></div>`).join("");
    }
  } catch (e) { msg($("posOut"), T(lang, "err")); }
  $("posGo").disabled = false;
}

// ---------- WATCHLIST ----------
async function renderWatch() {
  $("watchHint").textContent = T(lang, "watch_hint");
  const w = await getWatch();
  const addrs = Object.keys(w);
  if (!addrs.length) return msg($("watchOut"), T(lang, "watch_empty"));
  $("watchOut").innerHTML = addrs.map((addr) => {
    const v = w[addr]; const icon = v === "COPYABLE" ? "✅" : v === "RISKY" ? "⚠️" : v === "DO NOT COPY" ? "🚫" : "•";
    return `<div class="wl"><span>${icon} <code>${addr.slice(0,8)}…${addr.slice(-4)}</code></span>
      <span class="rm" data-addr="${addr}">✕</span></div>`;
  }).join("");
  $("watchOut").querySelectorAll(".rm").forEach((el) =>
    el.onclick = async () => { await delWatch(el.dataset.addr); renderWatch(); });
}

// ---------- TOP ----------
async function runTop() {
  $("topGo").disabled = true; msg($("topOut"), T(lang, "top_scanning", { i: 0, n: 30 }));
  try {
    const rows = await scanTop(30, (i, n) => msg($("topOut"), T(lang, "top_scanning", { i, n })));
    if (!rows.length) return msg($("topOut"), T(lang, "top_none"));
    $("topOut").innerHTML = rows.slice(0, 12).map((r, i) =>
      `<div class="trow"><span>${r.v==="COPYABLE"?"✅":"⚠️"} <code>${r.addr.slice(0,8)}…</code></span>
       <span class="pos">${money(r.copier)}</span></div>`).join("");
  } catch (e) { msg($("topOut"), T(lang, "err")); }
  $("topGo").disabled = false;
}

// ---------- tabs + lang ----------
function showView(name) {
  ["check","compare","positions","watch","top"].forEach((v) => { $("view-"+v).hidden = v !== name; });
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.dataset.view === name));
  if (name === "watch") renderWatch();
}
function applyLang() {
  $("tag").textContent = T(lang, "tagline");
  $("addr").placeholder = $("posAddr").placeholder = T(lang, "placeholder");
  $("cmpA").placeholder = T(lang, "a_label"); $("cmpB").placeholder = T(lang, "b_label");
  $("go").textContent = $("posGo").textContent = T(lang, "check");
  $("cmpGo").textContent = T(lang, "compare_btn");
  $("topGo").textContent = T(lang, "top_scan");
  $("shareLink").textContent = T(lang, "share");
  $("shareLink").href = "https://t.me/share/url?" + new URLSearchParams({ url: "https://t.me/vett_hl_bot", text: T(lang, "share_text") });
  document.querySelector('[data-view="check"]').textContent = T(lang, "tab_check");
  document.querySelector('[data-view="compare"]').textContent = T(lang, "tab_compare");
  document.querySelector('[data-view="positions"]').textContent = T(lang, "tab_positions");
  document.querySelector('[data-view="watch"]').textContent = T(lang, "tab_watch");
  document.querySelector('[data-view="top"]').textContent = T(lang, "tab_top");
}
function buildLang() {
  const sel = $("lang");
  for (const c of ["en","es","zh","pt"]) {
    const o = document.createElement("option"); o.value = c; o.textContent = c.toUpperCase();
    if (c === lang) o.selected = true; sel.appendChild(o);
  }
  sel.onchange = () => { lang = sel.value; localStorage.setItem("vett_lang", lang); applyLang(); };
}

// wire up — wrapped so any failure SHOWS in the popup instead of a blank UI
function init() {
  document.querySelectorAll(".tab").forEach((t) => t.onclick = () => showView(t.dataset.view));
  $("go").onclick = runCheck;
  $("addr").addEventListener("keydown", (e) => { if (e.key === "Enter") runCheck(); });
  $("cmpGo").onclick = runCompare;
  $("posGo").onclick = runPositions;
  $("posAddr").addEventListener("keydown", (e) => { if (e.key === "Enter") runPositions(); });
  $("topGo").onclick = runTop;
  buildLang(); applyLang(); showView("check");
  if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const m = ((tabs[0] && tabs[0].url) || "").match(ADDR_RE);
      if (m) { $("addr").value = m[0]; runCheck(); }
    });
  }
}
try {
  init();
} catch (e) {
  // surface the real error right in the popup so it's never a silent blank
  const o = document.getElementById("out") || document.body;
  if (o) o.innerHTML = '<div style="color:#ff5a52;font:12px monospace;padding:10px;white-space:pre-wrap">'
    + "Vett init error:\n" + (e && e.stack ? e.stack : String(e)) + "</div>";
  console.error("Vett init error:", e);
}
