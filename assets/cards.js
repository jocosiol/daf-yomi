/* Flashcards for the daf's key terms.

   Reads window.CARDS_BY_LANG, {lang: [{t: term, m: meaning}]}, built from the
   very same markdown table the Learn view renders — the deck cannot disagree
   with the sheet, because the glossary is written once.

   The deck is shuffled per run, and each card is rated once you have seen its
   back: knew it, or review later. What you flag comes round again as a second,
   shorter pass, so a run ends when the terms are actually known rather than
   when the cards run out.

   Switching language restarts the deck — a half-finished pass cannot survive
   being translated mid-card. */
(function () {
  var BY_LANG = window.CARDS_BY_LANG || {};
  var deck = document.getElementById("deckCard");
  if (!deck) return;

  var STR = {
    en: { card: "Card", flip: "Show meaning →", prev: "← Back",
          again: "↻ Review later", knew: "✓ Knew it", knewN: "known",
          pass: "Review pass", done: "Deck complete", of: "of",
          reviewN: "Review the {n} you flagged →", restart: "↻ Start over",
          m100: "Every term, first time. The daf's vocabulary is yours.",
          m80: "Nearly all of them cold — the rest is one more pass.",
          m0: "Now flip through the ones you flagged; that is where the daf is.",
          // a clean sweep on a review round is not a clean sweep on the deck
          mAgain: "The ones you flagged, cleared. Those are the ones that count." },
    es: { card: "Tarjeta", flip: "Ver significado →", prev: "← Atrás",
          again: "↻ Repasar luego", knew: "✓ Lo sabía", knewN: "sabidas",
          pass: "Ronda de repaso", done: "Mazo completo", of: "de",
          reviewN: "Repasar las {n} que marcaste →", restart: "↻ Empezar de nuevo",
          m100: "Todos los términos, a la primera. El vocabulario del daf es tuyo.",
          m80: "Casi todos de memoria — el resto es una ronda más.",
          m0: "Ahora repasa las que marcaste; ahí está el daf.",
          mAgain: "Las que marcaste, resueltas. Esas son las que cuentan." }
  };

  function lang() {
    var l = window.dafLang ? window.dafLang() : "en";
    return STR[l] && BY_LANG[l] ? l : "en";
  }

  var L = lang(), T = STR[L], ALL = BY_LANG[L] || [];
  var queue = [], pos = 0, flipped = false, knew = 0, flagged = [], pass = 1;

  function shuffled(a) {
    var out = a.slice();
    for (var j = out.length - 1; j > 0; j--) {
      var k = Math.floor(Math.random() * (j + 1));
      var t = out[j]; out[j] = out[k]; out[k] = t;
    }
    return out;
  }

  function start(cards, n) {
    queue = shuffled(cards);
    pos = 0; flipped = false; knew = 0; flagged = []; pass = n;
    render();
  }

  function render() {
    if (pos >= queue.length) return endScreen();
    var c = queue[pos];
    var pct = Math.round(pos / queue.length * 100);
    var tally = pass > 1
      ? '<span class="pill">' + T.pass + "</span>"
      : "<span>" + T.knewN + ' <span class="pill">' + knew + "</span></span>";

    deck.innerHTML =
      '<div class="dbar">' +
        '<span class="dnum">' + T.card + " " + (pos + 1) + " / " + queue.length + "</span>" +
        tally +
      "</div>" +
      '<div class="prog"><i style="width:' + pct + '%"></i></div>' +
      // Both faces are always in the DOM — backface-visibility hides the far
      // one from the eye but not from a screen reader, so aria-hidden does.
      '<button class="flashcard' + (flipped ? " flipped" : "") + '" id="flip" type="button" ' +
              'aria-pressed="' + flipped + '">' +
        '<span class="inner">' +
          // Each face centres its content with flex, which makes every child a
          // flex item — so a meaning containing markup ("the <em>gid</em> is…")
          // must be wrapped, or it lays out as three columns side by side.
          '<span class="face front" aria-hidden="' + flipped + '">' +
            '<span class="term">' + c.t + "</span></span>" +
          '<span class="face back" aria-hidden="' + !flipped + '">' +
            '<span class="meaning">' + c.m + "</span></span>" +
        "</span>" +
      "</button>" +
      '<div class="nav">' +
        '<button class="btn ghost" id="prev" type="button"' + (pos ? "" : " disabled") + ">" +
          T.prev + "</button>" +
        (flipped
          ? '<span class="rate">' +
              '<button class="btn ghost" id="again" type="button">' + T.again + "</button>" +
              '<button class="btn" id="knew" type="button">' + T.knew + "</button></span>"
          : '<button class="btn" id="show" type="button">' + T.flip + "</button>") +
      "</div>";

    on("flip", flip);
    on("show", flip);
    on("prev", back);
    on("again", function () { rate(false); });
    on("knew", function () { rate(true); });
  }

  function on(id, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  }

  function flip() {
    if (flipped) return;
    flipped = true;
    var el = document.getElementById("flip");
    el.classList.add("flipped");
    el.setAttribute("aria-pressed", "true");
    el.querySelector(".front").setAttribute("aria-hidden", "true");
    el.querySelector(".back").setAttribute("aria-hidden", "false");
    // the buttons change with the side showing, so redraw the row beneath
    var nav = deck.querySelector(".nav");
    nav.innerHTML =
      '<button class="btn ghost" id="prev" type="button"' + (pos ? "" : " disabled") + ">" +
        T.prev + "</button>" +
      '<span class="rate">' +
        '<button class="btn ghost" id="again" type="button">' + T.again + "</button>" +
        '<button class="btn" id="knew" type="button">' + T.knew + "</button></span>";
    on("prev", back);
    on("again", function () { rate(false); });
    on("knew", function () { rate(true); });
    document.getElementById("knew").focus();
  }

  function rate(ok) {
    if (!flipped) return;
    if (ok) knew++; else flagged.push(queue[pos]);
    pos++; flipped = false;
    render();
  }

  /* Going back un-rates the card you are returning to: it is about to be
     answered again, and counting it twice would put knew above the deck size. */
  function back() {
    if (!pos) return;
    pos--; flipped = false;
    var c = queue[pos];
    var i = flagged.indexOf(c);
    if (i >= 0) flagged.splice(i, 1); else if (knew) knew--;
    render();
  }

  function endScreen() {
    var total = queue.length;
    var pct = total ? Math.round(knew / total * 100) : 0;
    var emoji = "📚", msg = T.m0;
    if (pct === 100) { emoji = "🏆"; msg = pass > 1 ? T.mAgain : T.m100; }
    else if (pct >= 80) { emoji = "🌟"; msg = T.m80; }

    deck.innerHTML = '<div class="end"><div class="big">' + emoji + "</div>" +
      '<div class="score">' + knew + " / " + total + " &nbsp;·&nbsp; " + T.knewN + "</div>" +
      '<div class="msg">' + msg + "</div>" +
      (flagged.length
        ? '<button class="btn" id="redo" type="button">' +
            T.reviewN.replace("{n}", flagged.length) + "</button> "
        : "") +
      '<button class="btn ghost" id="restart" type="button">' + T.restart + "</button></div>";

    var again = flagged.slice();
    on("redo", function () { start(again, pass + 1); });
    on("restart", function () { start(ALL, 1); });
  }

  document.addEventListener("daflang", function () {
    L = lang(); T = STR[L]; ALL = BY_LANG[L] || [];
    if (ALL.length) start(ALL, 1);
  });

  document.addEventListener("dafview", function (e) {
    if (e.detail.view === "cards" && ALL.length && !deck.innerHTML.trim()) start(ALL, 1);
  });

  document.addEventListener("keydown", function (e) {
    var v = document.getElementById("cards");
    if (!v || !v.classList.contains("active")) return;
    if (e.key === " " || e.key === "Enter") {
      // a focused button activates itself on these; don't also act on them here
      if (e.target && e.target.closest && e.target.closest("button")) return;
      e.preventDefault();                       // space would scroll the page
      if (flipped) rate(true); else flip();
    } else if (e.key === "ArrowRight") {
      if (flipped) rate(true); else flip();
    } else if (e.key === "ArrowLeft") {
      back();
    } else if (e.key === "1") {
      rate(false);
    } else if (e.key === "2") {
      rate(true);
    }
  });

  if (ALL.length) start(ALL, 1);
})();
