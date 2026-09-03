// Vett content script — flags Hyperliquid wallet addresses on the page with a
// verdict badge. Click a badge → inline card. All analysis runs in the
// background worker (analyzer.js); this file only touches the DOM.
(() => {
  const ADDR_RE = /0x[0-9a-fA-F]{40}/;
  const seen = new WeakSet();

  const css = `
  .vett-badge{display:inline-flex;align-items:center;gap:3px;margin-left:6px;padding:1px 6px;
    border-radius:6px;font:600 11px -apple-system,Segoe UI,Roboto,sans-serif;cursor:pointer;
    background:#12161c;color:#33e1b0;border:1px solid #1e252e;vertical-align:middle;user-select:none}
  .vett-badge:hover{border-color:#33e1b0}
  .vett-card{position:fixed;z-index:2147483647;width:260px;background:#0a0c10;color:#e6edf3;
    border:1px solid #1e252e;border-radius:10px;padding:12px;
    font:12px -apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.6)}
  .vett-card .vh{font-weight:800;font-size:15px;margin-bottom:6px}
  .vett-card .r{display:flex;justify-content:space-between;padding:2px 0}
  .vett-card .k{color:#8b98a5}
  .vett-COPYABLE{color:#40d678}.vett-RISKY{color:#f5c542}.vett-DONOT{color:#ff5a52}
  .vett-pos{color:#40d678}.vett-neg{color:#ff5a52}
  .vett-card .fl{color:#f5c542;font-size:11px;padding:1px 0}
  .vett-card .cl{position:absolute;top:6px;right:9px;color:#8b98a5;cursor:pointer}`;
  const style = document.createElement("style");
  style.textContent = css;
  document.documentElement.appendChild(style);

  const money = (x) =>
    (x < 0 ? "-" : "+") + "$" + Math.abs(x).toLocaleString("en-US", { maximumFractionDigits: 0 });

  let card = null;
  function closeCard() { if (card) { card.remove(); card = null; } }
  document.addEventListener("click", (e) => {
    if (card && !card.contains(e.target) && !e.target.classList.contains("vett-badge")) closeCard();
  });

  function showCard(badge, addr) {
    closeCard();
    const rect = badge.getBoundingClientRect();
    card = document.createElement("div");
    card.className = "vett-card";
    card.style.left = Math.min(rect.left, window.innerWidth - 275) + "px";
    card.style.top = Math.min(rect.bottom + 6, window.innerHeight - 200) + "px";
    card.innerHTML = `<span class="cl">✕</span><div class="k">Vett · analyzing…</div>`;
    document.body.appendChild(card);
    card.querySelector(".cl").onclick = closeCard;
    chrome.runtime.sendMessage({ type: "analyze", addr }, (resp) => {
      if (!card) return;
      if (!resp || resp.error) { card.innerHTML = `<span class="cl">✕</span><div class="k">Couldn't reach Hyperliquid.</div>`; card.querySelector(".cl").onclick = closeCard; return; }
      if (!resp.res) { card.innerHTML = `<span class="cl">✕</span><div class="k">${resp.tooFew ? "Too few closed trades to judge." : "No history for this wallet."}</div>`; card.querySelector(".cl").onclick = closeCard; return; }
      const a = resp.a, v = resp.res.v, cls = v === "DO NOT COPY" ? "DONOT" : v;
      const icon = v === "COPYABLE" ? "✅" : v === "RISKY" ? "⚠️" : "🚫";
      const flags = resp.res.flags.slice(0, 2).map((f) => `<div class="fl">• ${f.split(":")[0]}</div>`).join("");
      card.innerHTML = `<span class="cl">✕</span>
        <div class="vh vett-${cls}">${icon} ${v}</div>
        <div class="r"><span class="k">Advertised</span><span class="${a.raw_pnl<0?'vett-neg':'vett-pos'}">${money(a.raw_pnl)}</span></div>
        <div class="r"><span class="k">Copier would've made</span><span class="${a.copier_pnl<0?'vett-neg':'vett-pos'}">${money(a.copier_pnl)}</span></div>
        <div class="r"><span class="k">Win rate · maker</span><span>${a.win_rate.toFixed(0)}% · ${a.maker_pct.toFixed(0)}%</span></div>
        ${flags}`;
      card.querySelector(".cl").onclick = closeCard;
    });
  }

  function makeBadge(addr) {
    const b = document.createElement("span");
    b.className = "vett-badge";
    b.textContent = "🔍 Vett";
    b.title = "Check this wallet with Vett";
    b.onclick = (e) => { e.stopPropagation(); showCard(b, addr); };
    return b;
  }

  // Walk text nodes, attach a badge after any element containing an address.
  function scan(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    const hits = [];
    let n;
    while ((n = walker.nextNode())) {
      const m = n.nodeValue && n.nodeValue.match(ADDR_RE);
      if (m && n.parentElement && !seen.has(n.parentElement)) hits.push([n.parentElement, m[0]]);
    }
    for (const [el, addr] of hits) {
      seen.add(el);
      if (el.querySelector && el.querySelector(".vett-badge")) continue;
      el.appendChild(makeBadge(addr));
    }
  }

  let pending = false;
  function schedule() {
    if (pending) return;
    pending = true;
    setTimeout(() => { pending = false; try { scan(document.body); } catch (e) {} }, 600);
  }
  new MutationObserver(schedule).observe(document.documentElement, { childList: true, subtree: true });
  schedule();
})();
