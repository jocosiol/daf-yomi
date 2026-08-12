/* Chazara quiz. Reads window.QUIZ_BY_LANG,
   {readerLang: {lang, qs: [{n, q, opts, correct, why}]}}, where `correct` is an
   index into `opts` and `lang` is the language the questions are written in —
   which is not always the key they are filed under.

   Options are shuffled per run, so a second pass through the same daf is a
   real second pass — the old build always rendered a,b,c,d in source order,
   which meant you could remember the position instead of the answer.

   Switching language restarts the quiz: a half-finished run can't survive
   being translated mid-question. */
(function () {
  var BY_LANG = window.QUIZ_BY_LANG || {};
  var LETTERS = ["A", "B", "C", "D"];
  var card = document.getElementById("quizCard");
  if (!card) return;

  var STR = {
    en: { q: "Question", score: "Score", streak: "streak", toGo: "to go",
          next: "Next →", results: "See results →", ok: "✓ Correct.",
          noPre: "✗ Not quite — the answer is ", again: "↻ Play again",
          look: "Worth another look", yours: "Your answer:", right: "Correct:",
          best: "best streak",
          m100: "Perfect score! You own this daf.",
          m80: "Excellent — nearly airtight.",
          m60: "Solid. A quick re-read of the tricky ones and you're set.",
          m0: "Good start — a review round will lock it in." },
    es: { q: "Pregunta", score: "Puntos", streak: "seguidas", toGo: "por responder",
          next: "Siguiente →", results: "Ver resultados →", ok: "✓ Correcto.",
          noPre: "✗ Casi — la respuesta es ", again: "↻ Jugar de nuevo",
          look: "Vale la pena repasar", yours: "Tu respuesta:", right: "Correcta:",
          best: "mejor racha",
          m100: "¡Puntuación perfecta! Dominas este daf.",
          m80: "Excelente — casi impecable.",
          m60: "Bien. Una relectura rápida de las difíciles y ya lo tienes.",
          m0: "Buen comienzo — una ronda de repaso lo afianzará." },
    // Hebrew reads the other way, so the arrows do too: "next" points left.
    he: { q: "שאלה", score: "ניקוד", streak: "ברצף", toGo: "נותרו",
          next: "הבא ←", results: "לתוצאות ←", ok: "✓ נכון.",
          noPre: "✗ כמעט — התשובה היא ", again: "↻ לשחק שוב",
          look: "כדאי לחזור על אלה", yours: "התשובה שלכם:", right: "הנכונה:",
          best: "הרצף הארוך ביותר",
          m100: "ניקוד מושלם! הדף הזה שלכם.",
          m80: "מצוין — כמעט ללא רבב.",
          m60: "יפה. קריאה חוזרת של הקשות ואתם שם.",
          m0: "התחלה טובה — סיבוב חזרה יקבע את זה." }
  };

  /* The quiz the reader asked for, or the one that stands in for it.

     A daf with no Hebrew sheet has no Hebrew quiz either, and what is filed
     under "he" is the English one. It is then shown as the English quiz —
     chrome and all, the way the Learn tab stands in a whole English sheet with
     a note above it. Translating only the buttons would put Hebrew labels and
     their right-to-left arrows around left-to-right questions. */
  function pick() {
    var want = window.dafLang ? window.dafLang() : "en";
    var p = BY_LANG[want];
    if (!p || !p.qs || !p.qs.length) p = BY_LANG.en;
    return p && p.qs && STR[p.lang] ? p : { lang: "en", qs: (p && p.qs) || [] };
  }

  var P = pick(), L = P.lang, T = STR[L], QUIZ = P.qs;

  /* Which way the card reads follows the questions in it, not the page around
     it: an English quiz inside a Hebrew page stays left to right. */
  function markDir() {
    card.lang = L;
    card.dir = window.dafIsRtl && window.dafIsRtl(L) ? "rtl" : "ltr";
  }
  markDir();

  var idx = 0, score = 0, streak = 0, best = 0, answered = false;
  var results = [], view = [];

  function shuffle(n) {
    var a = [];
    for (var i = 0; i < n; i++) a.push(i);
    for (var j = a.length - 1; j > 0; j--) {
      var k = Math.floor(Math.random() * (j + 1));
      var t = a[j]; a[j] = a[k]; a[k] = t;
    }
    return a;
  }

  function renderQuestion() {
    answered = false;
    var q = QUIZ[idx];
    view = shuffle(q.opts.length);
    var pct = Math.round(idx / QUIZ.length * 100);
    var opts = view.map(function (src, pos) {
      return '<button class="opt" type="button" data-pos="' + pos + '">' +
             '<span class="key" aria-hidden="true">' + LETTERS[pos] + "</span>" +
             '<span class="txt">' + q.opts[src] + "</span></button>";
    }).join("");

    card.innerHTML =
      '<div class="qbar">' +
        '<span class="qnum">' + T.q + " " + (idx + 1) + " / " + QUIZ.length + "</span>" +
        "<span>" + T.score + ' <span class="pill">' + score + "</span> " +
        (streak > 1 ? '<span class="streak">🔥 ' + streak + " " + T.streak + "</span>" : "") +
      "</span></div>" +
      '<div class="prog"><i style="width:' + pct + '%"></i></div>' +
      '<div class="qtext">' + q.q + "</div>" +
      '<div class="opts">' + opts + "</div>" +
      '<div class="why" id="why" role="status" aria-live="polite"></div>' +
      '<div class="nav"><span style="color:var(--faint);font-size:.85rem">' +
        (QUIZ.length - idx - 1) + " " + T.toGo + "</span>" +
      '<button class="btn" id="next" type="button" disabled>' + T.next + "</button></div>";

    card.querySelectorAll(".opt").forEach(function (b) {
      b.addEventListener("click", function () { choose(+b.dataset.pos); });
    });
    document.getElementById("next").addEventListener("click", next);
  }

  function choose(pos) {
    if (answered) return;
    answered = true;
    var q = QUIZ[idx];
    var correctPos = view.indexOf(q.correct);
    var right = pos === correctPos;

    if (right) { score++; streak++; best = Math.max(best, streak); } else { streak = 0; }
    results.push({
      n: q.n, q: q.q, why: q.why, right: right,
      chosen: q.opts[view[pos]], chosenKey: LETTERS[pos],
      correct: q.opts[q.correct], correctKey: LETTERS[correctPos]
    });

    card.querySelectorAll(".opt").forEach(function (b) {
      var p = +b.dataset.pos;
      b.classList.add("locked");
      b.disabled = true;
      if (p === correctPos) b.classList.add("correct");
      else if (p === pos) b.classList.add("wrong");
      else b.classList.add("dim");
    });

    var why = document.getElementById("why");
    why.innerHTML = "<b>" + (right ? T.ok : T.noPre + LETTERS[correctPos] + ".") +
                    "</b> " + q.why;
    why.classList.add("show");

    var nb = document.getElementById("next");
    nb.disabled = false;
    nb.textContent = idx === QUIZ.length - 1 ? T.results : T.next;
    nb.focus();
    card.querySelector(".qbar .pill").textContent = score;
  }

  function next() {
    if (!answered) return;
    if (idx < QUIZ.length - 1) {
      idx++;
      renderQuestion();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      endScreen();
    }
  }

  function endScreen() {
    var pct = Math.round(score / QUIZ.length * 100);
    var emoji = "📘", msg = T.m0;
    if (pct === 100) { emoji = "🏆"; msg = T.m100; }
    else if (pct >= 80) { emoji = "🌟"; msg = T.m80; }
    else if (pct >= 60) { emoji = "👍"; msg = T.m60; }

    var wrong = results.filter(function (r) { return !r.right; });
    var review = "";
    if (wrong.length) {
      review = '<div class="review"><h3>' + T.look + "</h3>" +
        wrong.map(function (r) {
          return '<div class="r"><div class="rq">' + r.n + ". " + r.q + "</div>" +
            '<div class="ra no">' + T.yours + " " + r.chosenKey + ") " + r.chosen + "</div>" +
            '<div class="ra ok">' + T.right + " " + r.correctKey + ") " + r.correct + "</div>" +
            '<div class="ra" style="color:var(--ink-soft);margin-top:4px">' + r.why + "</div></div>";
        }).join("") + "</div>";
    }

    card.innerHTML = '<div class="end"><div class="big">' + emoji + "</div>" +
      '<div class="score">' + score + " / " + QUIZ.length + " &nbsp;·&nbsp; " + pct + "%</div>" +
      '<div class="msg">' + msg +
        (best > 1 ? " &nbsp;·&nbsp; " + T.best + " 🔥 " + best : "") + "</div>" +
      '<button class="btn" id="again" type="button">' + T.again + "</button></div>" + review;
    document.getElementById("again").addEventListener("click", restart);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function restart() {
    idx = 0; score = 0; streak = 0; best = 0; results = [];
    renderQuestion();
  }

  document.addEventListener("daflang", function () {
    P = pick(); L = P.lang; T = STR[L]; QUIZ = P.qs;
    markDir();
    if (QUIZ.length) restart();
  });

  /* tabs.js owns the switching; this only has to notice the quiz being opened
     for the first time, in case it was never rendered. */
  document.addEventListener("dafview", function (e) {
    if (e.detail.view === "quiz" && QUIZ.length && !card.innerHTML.trim()) renderQuestion();
  });

  document.addEventListener("keydown", function (e) {
    var q = document.getElementById("quiz");
    if (!q || !q.classList.contains("active")) return;
    if (["1", "2", "3", "4"].indexOf(e.key) !== -1) {
      var b = card.querySelector('.opt[data-pos="' + (+e.key - 1) + '"]');
      if (b) b.click();
    } else if (e.key === "Enter") {
      var n = document.getElementById("next");
      if (n && !n.disabled) n.click();
    }
  });

  if (QUIZ.length) renderQuestion();
})();
