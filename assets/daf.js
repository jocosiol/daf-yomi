/* The Daf tab — which reading of the page is showing, and how it folds.

   Almost everything here is presentation of markup the build already wrote: the
   daf, its Rashi and its Tosafot are all in the HTML whether or not this file
   loads, so nothing is hidden by the markup itself.

   Three jobs:

   1. The mode. The scan of the printed page, or the text laid out in columns.
      Both are in the page; a class on #daf decides which one is on screen.

   2. The chips. Rashi, Tosafot and the English translation each toggle a class
      too, and every choice is remembered site-wide — someone who reads without
      Tosafot wants that tomorrow too.

   3. Folding. Below the breakpoint the three text columns have stacked, and a
      daf of Gemara followed by every word of both commentaries is a very long
      scroll. There the commentary blocks collapse behind their heading. The
      passages under the printed page fold the same way, at every width, each
      opening onto its English. Both are shut here rather than in the markup, so
      the page never ships content the reader cannot get at.

   The one thing it does rather than merely reveal is load the scans: two PDFs of
   ~140 KB each, from someone else's server, so their `src` is set the first time
   this tab is opened and never on a page load. */
(function () {
  var root = document.getElementById("daf");
  if (!root) return;

  var KEY = "dafView";      // {mode:"scan"|"text", rashi, tosafot, en}
  var NARROW = window.matchMedia("(max-width: 860px)");
  var chips = [].slice.call(root.querySelectorAll(".chip[data-daf]"));
  var modes = [].slice.call(root.querySelectorAll(".chip[data-mode]"));

  /* ---- what is shown ---------------------------------------------------- */
  /* The build decided which modes this daf has and marked one of them on the
     section; a remembered preference for a mode the daf does not have — a
     Shekalim daf has no text — is ignored rather than obeyed into a blank tab. */
  var state = { mode: root.classList.contains("mode-scan") ? "scan" : "text",
                rashi: true, tosafot: true, en: false };
  var offered = modes.map(function (m) { return m.dataset.mode; });
  try {
    var stored = JSON.parse(localStorage.getItem(KEY) || "{}");
    Object.keys(state).forEach(function (k) {
      if (typeof stored[k] === typeof state[k]) state[k] = stored[k];
    });
    if (offered.indexOf(state.mode) < 0) state.mode = offered[0] || state.mode;
  } catch (e) {}

  function paint() {
    root.classList.toggle("mode-scan", state.mode === "scan");
    root.classList.toggle("mode-text", state.mode !== "scan");
    root.classList.toggle("hide-rashi", !state.rashi);
    root.classList.toggle("hide-tosafot", !state.tosafot);
    root.classList.toggle("show-en", state.en);
    chips.forEach(function (c) {
      var on = !!state[c.dataset.daf];
      c.classList.toggle("on", on);
      c.setAttribute("aria-pressed", on ? "true" : "false");
    });
    modes.forEach(function (m) {
      var on = m.dataset.mode === state.mode;
      m.classList.toggle("on", on);
      m.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (state.mode === "scan") loadScans();
  }

  function remember() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
  }

  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      state[c.dataset.daf] = !state[c.dataset.daf];
      paint();
      remember();
    });
  });

  modes.forEach(function (m) {
    m.addEventListener("click", function () {
      state.mode = m.dataset.mode;
      paint();
      remember();
    });
  });

  /* ---- the scans -------------------------------------------------------- */
  /* Not on page load, and not while the tab is shut: a reader who never opens
     this tab should never cost shas.org a request. */
  function loadScans() {
    if (!root.classList.contains("active")) return;
    root.querySelectorAll("iframe[data-src]").forEach(function (f) {
      f.src = f.dataset.src;
      f.removeAttribute("data-src");
    });
  }

  paint();

  /* ---- folding on a narrow screen -------------------------------------- */
  var heads = [].slice.call(root.querySelectorAll(".col-head"));

  function fold(on) {
    heads.forEach(function (h) {
      /* Only ever fold a block the reader has not opened by hand: widening the
         window and narrowing it again should not shut what they just opened. */
      if (on && !h.dataset.touched) setOpen(h, false);
      if (!on) setOpen(h, true);
    });
  }

  function setOpen(head, open) {
    head.parentNode.classList.toggle("collapsed", !open);
    head.setAttribute("aria-expanded", open ? "true" : "false");
  }

  heads.forEach(function (h) {
    h.addEventListener("click", function () {
      h.dataset.touched = "1";
      setOpen(h, h.parentNode.classList.contains("collapsed"));
    });
  });

  /* ---- line by line, under the printed page ----------------------------- */
  /* The page itself cannot answer a tap: it is a cross-origin PDF drawn by the
     browser's viewer, and its fonts carry no usable Unicode map, so there is no
     telling which words a click landed on. So the passages sit underneath it and
     each opens onto its English. Shut here rather than in the markup, for the
     same reason as the margins: the page never ships text it cannot reveal. */
  root.querySelectorAll(".daf-lines .line-head").forEach(function (h) {
    if (h.tagName !== "BUTTON") return;         // nothing to open: no translation
    setOpen(h, false);
    h.addEventListener("click", function () {
      setOpen(h, h.parentNode.classList.contains("collapsed"));
    });
  });

  fold(NARROW.matches);
  /* addListener: Safari only grew addEventListener on MediaQueryList in 14. */
  if (NARROW.addEventListener) {
    NARROW.addEventListener("change", function (e) { fold(e.matches); });
  } else if (NARROW.addListener) {
    NARROW.addListener(function (e) { fold(e.matches); });
  }

  /* ---- the notice above the tabs --------------------------------------- */
  /* The AI-provenance line is true of every other tab and false of this one,
     so the pair swaps over on the body class rather than being repeated in
     each view. tabs.js announces the switch. */
  document.addEventListener("dafview", function (e) {
    document.body.classList.toggle("view-daf", e.detail.view === "daf");
    if (e.detail.view === "daf" && state.mode === "scan") loadScans();
  });
})();
