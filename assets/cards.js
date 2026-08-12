/* Flashcards for the daf's key terms.

   Reads window.CARDS_BY_LANG, {readerLang: {lang, cards: [{t: term, m: meaning}]}},
   built from the very same markdown table the Learn view renders — the deck
   cannot disagree with the sheet, because the glossary is written once. `lang`
   is the language the cards are written in, which is not always the key they
   are filed under.

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
          mAgain: "Las que marcaste, resueltas. Esas son las que cuentan." },
    // Hebrew reads the other way, so the arrows do too: forward points left.
    he: { card: "כרטיס", flip: "להצגת המשמעות ←", prev: "→ הקודם",
          again: "↻ לחזור על זה", knew: "✓ ידעתי", knewN: "ידועים",
          pass: "סיבוב חזרה", done: "סיימתם את החפיסה", of: "מתוך",
          reviewN: "לחזור על {n} שסימנתם ←", restart: "↻ להתחיל מחדש",
          m100: "כל המונחים, בפעם הראשונה. אוצר המילים של הדף שלכם.",
          m80: "כמעט כולם בעל פה — השאר זה סיבוב אחד נוסף.",
          m0: "עכשיו עברו על אלה שסימנתם; שם נמצא הדף.",
          mAgain: "אלה שסימנתם — סגרתם. אלה שקובעים." }
  };

  /* The deck the reader asked for, or the one that stands in for it.

     A daf with no Hebrew sheet has no Hebrew glossary either, and what is filed
     under "he" is the English deck. It is then shown as the English deck —
     chrome and all, the way the Learn tab stands in a whole English sheet with
     a note above it. Translating only the buttons would put Hebrew labels and
     their right-to-left arrows around left-to-right terms. */
  function pick() {
    var want = window.dafLang ? window.dafLang() : "en";
    var p = BY_LANG[want];
    if (!p || !p.cards || !p.cards.length) p = BY_LANG.en;
    return p && p.cards && STR[p.lang] ? p : { lang: "en", cards: (p && p.cards) || [] };
  }

  var P = pick(), L = P.lang, T = STR[L], ALL = P.cards;

  /* Which way the card reads follows the terms on it, not the page around it:
     an English deck inside a Hebrew page stays left to right. */
  function rtl() { return !!(window.dafIsRtl && window.dafIsRtl(L)); }
  function markDir() {
    deck.lang = L;
    deck.dir = rtl() ? "rtl" : "ltr";
  }
  markDir();
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
      '<div class="nav"></div>';

    on("flip", turn);
    renderNav();
  }

  function on(id, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  }

  /* Only the row under the card, because turning the card must not rebuild the
     card — a fresh element has no previous state to transition from, and the
     flip would jump instead of turning. */
  function renderNav() {
    deck.querySelector(".nav").innerHTML =
      '<button class="btn ghost" id="prev" type="button"' + (pos ? "" : " disabled") + ">" +
        T.prev + "</button>" +
      (flipped
        ? '<span class="rate">' +
            '<button class="btn ghost" id="again" type="button">' + T.again + "</button>" +
            '<button class="btn" id="knew" type="button">' + T.knew + "</button></span>"
        : '<button class="btn" id="show" type="button">' + T.flip + "</button>");
    on("prev", back);
    on("show", turn);
    on("again", function () { rate(false); });
    on("knew", function () { rate(true); });
  }

  /* Turns the card either way: a flashcard you can only turn once is a card
     you cannot check yourself against a second time. */
  function turn() {
    flipped = !flipped;
    var el = document.getElementById("flip");
    el.classList.toggle("flipped", flipped);
    el.setAttribute("aria-pressed", String(flipped));
    el.querySelector(".front").setAttribute("aria-hidden", String(flipped));
    el.querySelector(".back").setAttribute("aria-hidden", String(!flipped));
    renderNav();
    // the rating is the next thing wanted, so put the keyboard on it
    if (flipped) document.getElementById("knew").focus();
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
    P = pick(); L = P.lang; T = STR[L]; ALL = P.cards;
    markDir();
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
      turn();                                   // as the hint says: it flips
    } else if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      // The arrows follow the text, not the keyboard: forward is left in
      // Hebrew, so pressing ← there does what → does in English.
      if (e.key === (rtl() ? "ArrowLeft" : "ArrowRight")) {
        // keep going: show the meaning, or take the card as known and move on
        if (flipped) rate(true); else turn();
      } else {
        back();
      }
    } else if (e.key === "1") {
      rate(false);
    } else if (e.key === "2") {
      rate(true);
    }
  });

  if (ALL.length) start(ALL, 1);
})();
