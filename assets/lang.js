/* Language preference, shared site-wide.

   One localStorage key ("dafLang") for the whole site, so choosing Spanish on
   a daf leaves the archive in Spanish too. `?lang=es` in the URL overrides the
   stored choice and becomes it, which makes a Spanish link shareable.

   Which version of a multilingual page is visible is decided purely by the
   root <html lang> attribute, set here synchronously — this script must load in
   <head>, not deferred, so no version ever flashes.

   `dir` goes on the same element and from the same choice: Hebrew is right to
   left, so the whole page turns round with it. Blocks that are not in the
   reader's language carry their own lang/dir from the build — an untranslated
   daf shows its English sheet to a Hebrew reader, and that block stays LTR.

   Everything the build renders is marked up in every language at once
   (<span data-lang="en">…</span><span data-lang="es">…</span>) and switched by
   CSS. Only content JavaScript writes — the quiz, the archive badge — has to
   listen for the "daflang" event and re-render. */
(function () {
  var KEY = "dafLang";
  var cfg = {};
  var el = document.getElementById("daf-config");
  if (el) { try { cfg = JSON.parse(el.textContent) || {}; } catch (e) {} }

  var SUP = cfg.langs && cfg.langs.length ? cfg.langs : ["en"];
  var RTL = cfg.rtl || [];
  var cur = SUP[0];

  function apply() {
    document.documentElement.lang = cur;
    document.documentElement.dir = RTL.indexOf(cur) >= 0 ? "rtl" : "ltr";
  }

  try {
    var stored = localStorage.getItem(KEY);
    if (SUP.indexOf(stored) >= 0) cur = stored;
  } catch (e) {}

  var q = (location.search.match(/[?&]lang=([A-Za-z-]+)/) || [])[1];
  if (q) {
    q = q.toLowerCase().slice(0, 2);
    if (SUP.indexOf(q) >= 0) {
      cur = q;
      try { localStorage.setItem(KEY, cur); } catch (e) {}
    }
  }

  apply();                                      // before first paint

  window.dafLang = function () { return cur; };
  window.dafIsRtl = function (l) { return RTL.indexOf(l || cur) >= 0; };

  window.dafSetLang = function (l) {
    if (SUP.indexOf(l) < 0 || l === cur) return;
    cur = l;
    try { localStorage.setItem(KEY, cur); } catch (e) {}
    apply();
    document.dispatchEvent(new CustomEvent("daflang", { detail: { lang: cur } }));
  };

  function wire() {
    var b = document.getElementById("lang-btn");
    if (!b) return;
    b.addEventListener("click", function () {
      window.dafSetLang(SUP[(SUP.indexOf(cur) + 1) % SUP.length]);
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
