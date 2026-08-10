/* The Daf tab — what is shown of the page, and how it folds on a phone.

   Everything here is presentation of markup the build already wrote: the daf,
   its Rashi and its Tosafot are in the HTML whether or not this file loads. So
   with no JavaScript you get the whole page, unfolded — never a blank tab.

   Two jobs:

   1. The chips. Rashi, Tosafot and the English translation each toggle a class
      on the #daf section, and the choice is remembered site-wide — someone who
      reads without Tosafot wants that tomorrow too.

   2. Folding. Below the breakpoint the three columns have stacked, and a daf
      of Gemara followed by every word of both commentaries is a very long
      scroll. There the commentary blocks collapse behind their heading. That is
      done here rather than in the markup so that the no-JS page stays whole. */
(function () {
  var root = document.getElementById("daf");
  if (!root) return;

  var KEY = "dafView";                 // {rashi:bool, tosafot:bool, en:bool}
  var NARROW = window.matchMedia("(max-width: 860px)");
  var chips = [].slice.call(root.querySelectorAll(".chip[data-daf]"));

  /* ---- what is shown ---------------------------------------------------- */
  var state = { rashi: true, tosafot: true, en: false };
  try {
    var stored = JSON.parse(localStorage.getItem(KEY) || "{}");
    Object.keys(state).forEach(function (k) {
      if (typeof stored[k] === "boolean") state[k] = stored[k];
    });
  } catch (e) {}

  function paint() {
    root.classList.toggle("hide-rashi", !state.rashi);
    root.classList.toggle("hide-tosafot", !state.tosafot);
    root.classList.toggle("show-en", state.en);
    chips.forEach(function (c) {
      var on = !!state[c.dataset.daf];
      c.classList.toggle("on", on);
      c.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      var k = c.dataset.daf;
      state[k] = !state[k];
      paint();
      try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    });
  });
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
  });
})();
