// Loaded FIRST — a catch-all that paints any script error/load-failure into the
// popup, so the UI can never fail silently (blank).
(function () {
  function show(msg) {
    var d = document.getElementById("out") || document.body;
    if (d) d.innerHTML =
      '<div style="color:#ff5a52;font:11px monospace;padding:12px;white-space:pre-wrap;line-height:1.5">'
      + "Vett error:\n" + msg + "</div>";
  }
  window.addEventListener("error", function (e) {
    if (e && e.target && (e.target.src || e.target.href)) {
      show("A file failed to load:\n" + (e.target.src || e.target.href)
        + "\n\n(the extension folder is likely missing this file — re-download & reload)");
    } else {
      show((e.message || String(e)) + "\n  at " + (e.filename || "") + ":" + (e.lineno || "") + ":" + (e.colno || ""));
    }
  }, true);
  window.addEventListener("unhandledrejection", function (e) {
    show("Unhandled promise rejection:\n" + (e.reason && e.reason.message || e.reason));
  });
})();
