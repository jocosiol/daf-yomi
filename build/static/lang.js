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

  /* The picker: a button that names the language on screen, and a menu of all of
     them. Built as a menu rather than a <select> because the options have to be
     styled like the rest of the nav and each carries its own lang, and rather
     than a cycling button because three languages make "the next one" a guess.

     Keyboard: the button opens on Enter, Space or ↓ (the browser's own click
     handles the first two); inside, ↑ ↓ Home End move, Escape and Tab close.
     Choosing does not reload — dafSetLang switches the page in place — so focus
     goes back to the button, which now reads as the language just chosen. */
  function wire() {
    var btn = document.getElementById("lang-btn");
    var menu = document.getElementById("lang-menu");
    if (!btn || !menu) return;
    var items = [].slice.call(menu.querySelectorAll("[data-set-lang]"));

    function mark() {
      items.forEach(function (it) {
        it.setAttribute("aria-checked",
          it.getAttribute("data-set-lang") === cur ? "true" : "false");
      });
    }

    function isOpen() { return !menu.hidden; }

    function open(focus) {
      menu.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      if (focus) {
        var i = items.map(function (it) { return it.getAttribute("data-set-lang"); }).indexOf(cur);
        (items[i < 0 ? 0 : i] || items[0]).focus();
      }
    }

    function close(refocus) {
      if (!isOpen()) return;
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      if (refocus) btn.focus();
    }

    function move(from, step) {
      var i = items.indexOf(from);
      var n = items.length;
      items[((i < 0 ? 0 : i) + step + n) % n].focus();
    }

    btn.addEventListener("click", function () {
      if (isOpen()) close(false); else open(false);
    });
    btn.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        open(true);
      } else if (e.key === "Escape") {
        close(false);
      }
    });

    items.forEach(function (it) {
      it.addEventListener("click", function () {
        window.dafSetLang(it.getAttribute("data-set-lang"));
        close(true);
      });
    });

    menu.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); move(e.target, 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(e.target, -1); }
      else if (e.key === "Home") { e.preventDefault(); items[0].focus(); }
      else if (e.key === "End") { e.preventDefault(); items[items.length - 1].focus(); }
      else if (e.key === "Escape") { e.preventDefault(); close(true); }
      else if (e.key === "Tab") { close(false); }
    });

    // A tap anywhere else. pointerdown rather than click, so the menu is gone by
    // the time the tap lands on whatever is underneath it.
    document.addEventListener("pointerdown", function (e) {
      if (isOpen() && !menu.contains(e.target) && !btn.contains(e.target)) close(false);
    });

    // Marked here as well as after a choice, because the language may already
    // have come from ?lang= or from localStorage before this ran.
    document.addEventListener("daflang", mark);
    mark();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
