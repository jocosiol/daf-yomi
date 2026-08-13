/* The Introduction / The Daf / Chazara tabs.

   This used to live at the bottom of quiz.js, which meant tab switching only
   existed on a daf that had a quiz. It is now its own file, and announces the
   view it opened as a "dafview" event so each panel can wake itself up.

   Anything with data-open="<view id>" acts as a link to a tab, for a control
   inside one panel that means to send the reader to another. */
(function () {
  var tabs = [].slice.call(document.querySelectorAll(".tab"));
  if (!tabs.length) return;

  function show(v) {
    if (!document.getElementById(v)) return;
    tabs.forEach(function (t) {
      var on = t.dataset.v === v;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".view").forEach(function (x) {
      x.classList.toggle("active", x.id === v);
    });
    document.dispatchEvent(new CustomEvent("dafview", { detail: { view: v } }));
  }

  window.dafShowView = show;

  tabs.forEach(function (t) {
    t.addEventListener("click", function () { show(t.dataset.v); });
  });

  /* Delegated, because the buttons inside the sheet are rendered by the build
     and re-rendered by nothing — but the language switch does mean two of them
     exist at once, one hidden. */
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-open]");
    if (!b) return;
    show(b.getAttribute("data-open"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();
