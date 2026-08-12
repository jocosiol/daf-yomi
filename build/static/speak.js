/* Read a section aloud.

   Every heading in the Learn sheet gets a 🔊 button that speaks the section
   under it: the heading, then each paragraph, quote, list item and table row
   until the next heading of the same or higher level. It runs on the browser's
   own speech synthesis, so there is no audio to generate at build time and
   nothing extra to download — 2,700 dapim stay 2,700 files of text.

   Three things the naive version gets wrong:

   * Hebrew. The quotations are marked lang="he", and an English voice handed
     Hebrew glyphs either says nothing or spells the letters out. Each run of
     text is spoken by a voice for its own language, and a Hebrew run is
     skipped entirely when the browser has no Hebrew voice — every quotation in
     these sheets is followed by its translation, so nothing is lost.
   * Which language the sheet is in. Not necessarily the language of the page
     chrome: an untranslated daf shows its English body to a Spanish reader.
     The build stamps the body's own language on the sheet as data-speak-lang.
   * Length. A single long utterance gets truncated (Chrome cuts remote voices
     off after a few seconds), so text is broken at sentence ends. That also
     gives the highlight something to follow. */
(function () {
  var synth = window.speechSynthesis;
  if (!synth || typeof window.SpeechSynthesisUtterance !== "function") return;

  var STR = {
    en: { play: "Read this section aloud", stop: "Stop reading" },
    es: { play: "Leer esta sección en voz alta", stop: "Detener la lectura" },
    he: { play: "להקריא את החלק הזה", stop: "להפסיק את ההקראה" }
  };
  /* The button is chrome, not content, so it follows the reader's UI language
     — which is the root lang, not the sheet's. */
  function t(key) {
    var l = (document.documentElement.lang || "en").slice(0, 2);
    return (STR[l] || STR.en)[key];
  }

  var TAG = { en: "en-US", es: "es-ES", he: "he-IL" };
  /* An utterance boundary is not free: the voice stops, pauses, and starts the
     next one with its intonation reset to neutral. Cut a paragraph into three
     and it stops sounding like someone reading a paragraph. So a paragraph is
     said in one breath — no paragraph in these sheets comes near this ceiling,
     which is here only to bound a freak table row. A voice that synthesises
     over the network is the exception: it gets cut off after a few seconds, so
     for those the text is broken at sentence ends and choppy beats silence. */
  var MAX_LOCAL = 1000;
  var MAX_NET = 220;
  /* Read through these to their parts, so the highlight lands on the sentence
     being said rather than on a whole table. A blockquote is a wrapper too:
     its paragraphs read as paragraphs. */
  var WRAP = /^(?:DIV|BLOCKQUOTE|UL|OL|TABLE|THEAD|TBODY|TFOOT|SECTION)$/;
  var MUTE = /^(?:HR|BUTTON|SCRIPT|STYLE|IMG|BR)$/;
  // A letter or a digit — Latin, accented Latin, or Hebrew. Anything without
  // one of these is punctuation, and a voice saying punctuation is noise.
  var SPEAKABLE = /[0-9A-Za-zÀ-ɏ֐-׿יִ-ﭏ]/;

  // ---- voices ----------------------------------------------------------
  // getVoices() is empty until the list arrives, so it is re-read rather than
  // captured, and the Hebrew question is asked at play time, not at load.
  var voices = [], picked = {};
  function loadVoices() { voices = synth.getVoices() || []; picked = {}; }
  loadVoices();
  if (synth.addEventListener) synth.addEventListener("voiceschanged", loadVoices);

  /* Which voice reads the daf.
     Taking the browser's "default", or the first voice that matches the
     language, is how you end up being read Gemara by a joke: macOS lists
     Albert, Zarvox and Bad News among its English voices, and offers "Eddy"
     for Spanish long before Mónica. So the voices are scored — and only
     scored, never filtered, so even a list of nothing but novelties still
     yields a voice rather than silence. */
  var GOOD = {
    en: ["ava", "allison", "samantha", "susan", "nicky", "tom", "alex", "serena",
         "daniel", "google us english", "google uk english", "aria", "jenny", "zira"],
    es: ["mónica", "monica", "paulina", "angélica", "angelica", "marisol",
         "jorge", "juan", "google español", "sabina", "helena"],
    he: ["carmit", "google עברית", "asaf"]
  };
  // The same voice in the higher-quality build, where the reader has installed
  // one — macOS calls it "Samantha (Enhanced)".
  var FINE = /\b(premium|enhanced|natural|neural)\b/i;
  // Fine for "Bad News". Not for a page of Gemara.
  var SILLY = new RegExp("^(albert|bad news|bahh|bells|boing|bubbles|cellos|" +
    "deranged|eddy|flo|fred|good news|grandma|grandpa|hysterical|jester|junior|" +
    "kathy|organ|pipe organ|princess|ralph|reed|rocko|sandy|shelley|superstar|" +
    "trinoids|whisper|wobble|zarvox)\\b", "i");

  function score(v, lang) {
    var name = (v.name || "").toLowerCase(), s = 0;
    var good = GOOD[lang] || [];
    for (var i = 0; i < good.length; i++) {
      if (name.indexOf(good[i]) >= 0) { s += 100 - i; break; }   // earlier is better
    }
    if (FINE.test(name)) s += 40;
    if (SILLY.test(name)) s -= 60;
    if (v["default"]) s += 5;          // a tie-break, not a decision
    return s;
  }

  function voiceFor(lang) {
    if (!voices.length) loadVoices();
    if (lang in picked) return picked[lang];
    var best = null, top = 0;
    for (var i = 0; i < voices.length; i++) {
      var v = voices[i], vl = (v.lang || "").toLowerCase().replace(/_/g, "-");
      if (vl !== lang && vl.indexOf(lang + "-") !== 0) continue;
      var s = score(v, lang);
      if (!best || s > top) { best = v; top = s; }   // ties go to the earlier one
    }
    // Not cached until there is a list to have chosen from, or the first
    // utterance would pin its answer from before the voices arrived.
    if (voices.length) picked[lang] = best;
    return best;
  }

  // ---- what to say -----------------------------------------------------
  function sheetLang(el) {
    var s = el.closest ? el.closest(".sheet") : null;
    var l = (s && s.getAttribute("data-speak-lang")) ||
            document.documentElement.lang || "en";
    return l.slice(0, 2).toLowerCase();
  }

  /* The blocks of one section, in reading order. */
  function blocks(head) {
    var level = +head.tagName.slice(1);
    var out = [head];
    for (var el = head.nextElementSibling; el; el = el.nextElementSibling) {
      var m = /^H([1-6])$/.exec(el.tagName);
      if (m && +m[1] <= level) break;  // the next section starts here
      collect(el, out);
    }
    return out;
  }

  function collect(el, out) {
    if (MUTE.test(el.tagName)) return;
    if (!WRAP.test(el.tagName)) { out.push(el); return; }
    for (var k = el.firstElementChild; k; k = k.nextElementSibling) collect(k, out);
  }

  /* One block as runs of text, each tagged with the language it is written in.
     Walked by hand rather than taken from textContent, because the lang="he"
     spans have to be found and the 🔊 button itself left out. */
  function runs(el) {
    var out = [];
    walk(el, sheetLang(el), out);

    /* Drop the runs with nothing to say and merge what that leaves adjacent.
       אֵין “בְּשֵׁלָה” אֶלָּא שְׁלֵימָה arrives as five runs, because the two
       curly quotes are page language sitting inside a Hebrew phrase — and it
       was being read as five utterances, two of them a quotation mark spoken
       on its own. It is one Hebrew phrase, and now it is said as one.
       (A punctuation-only run can only ever appear between two languages:
       same-language neighbours were already joined on the way in.) */
    var keep = [];
    out.forEach(function (r) {
      if (!SPEAKABLE.test(r.text)) return;
      var last = keep[keep.length - 1];
      if (last && last.lang === r.lang) last.text += " " + r.text;
      else keep.push({ lang: r.lang, text: r.text });
    });

    return keep.map(function (r) {
      return { lang: r.lang, text: say(r.text) };
    }).filter(function (r) { return SPEAKABLE.test(r.text); });
  }

  /* Small repairs for the ear, not for the eye.

     An em dash is silent in most voices, so "beitzat efroach — an egg with a
     chick in it" arrives as one breathless phrase; a comma gives it the pause
     the sentence has on the page. A run that *begins* with a dash is the tail
     of a sentence whose middle was a Hebrew quotation, and needs no comma at
     all — the gap between two utterances is already the pause. "108a–108b" is
     a range and should be said as one, and "R' Yochanan" is a name, not a
     letter. Punctuation left stranded at either end by a quotation that moved
     into its own utterance goes too — a sentence beginning ”, is a robot. */
  function say(text) {
    return text
      .replace(/\s+/g, " ")
      .replace(/(\d[ab]?)\s*[–—]\s*(?=\d)/g, "$1 to ")
      .replace(/\s*[—–]\s*/g, ", ")
      .replace(/\bR['’]\s*(?=[A-Z])/g, "Rabbi ")
      // "What both agree . Where they split" — the gap is the newline the
      // markdown put inside the table cell, and a voice reads it as a stumble.
      .replace(/\s+([.,;:!?…])/g, "$1")
      .replace(/,\s*([,.;:])/g, "$1")
      .replace(/^[\s—–\-,.;:"'“”‘’]+/, "")
      .replace(/[\s,;:"'“”‘’]+$/, "")
      .trim();
  }

  function push(out, lang, text) {
    var last = out[out.length - 1];
    if (last && last.lang === lang) last.text += text;
    else out.push({ lang: lang, text: text });
  }

  function walk(node, lang, out) {
    for (var n = node.firstChild; n; n = n.nextSibling) {
      if (n.nodeType === 3) { push(out, lang, n.nodeValue); continue; }
      if (n.nodeType !== 1) continue;
      if (MUTE.test(n.tagName) || n.classList.contains("speak")) continue;
      // A row read straight through would run "kachal the udder" together.
      if ((n.tagName === "TD" || n.tagName === "TH") && n.previousElementSibling) {
        push(out, lang, ". ");
      }
      var l = n.getAttribute("lang");
      walk(n, l ? l.slice(0, 2).toLowerCase() : lang, out);
    }
  }

  /* Whole, if the voice can take it. Otherwise at sentence ends, and only
     inside an overlong sentence at commas — a pause where the prose has none
     is worse than a long utterance. */
  function pieces(text, voice) {
    var max = voice && voice.localService ? MAX_LOCAL : MAX_NET;
    if (text.length <= max) return [text];
    return split(text, /[^.!?…]+[.!?…]*\s*/g, max).reduce(function (acc, s) {
      return acc.concat(s.length > max * 2 ? split(s, /[^,;:]+[,;:]*\s*/g, max) : [s]);
    }, []);
  }

  function split(text, re, max) {
    var parts = text.match(re) || [text], out = [], buf = "";
    for (var i = 0; i < parts.length; i++) {
      if (buf && (buf + parts[i]).length > max) { out.push(buf.trim()); buf = ""; }
      buf += parts[i];
    }
    if (buf.trim()) out.push(buf.trim());
    return out;
  }

  // ---- playback --------------------------------------------------------
  var cur = null;                      // {btn, queue, i, mark}

  /* 🔊 to start, matching the emoji the tabs and the nav are labelled with —
     but a plain ■ to stop, because ⏹ is an emoji: it would keep its own colour
     on the filled pill instead of taking the button's. */
  function label(btn, on) {
    btn.textContent = on ? "■" : "🔊";
    btn.title = t(on ? "stop" : "play");
    btn.setAttribute("aria-label", btn.title);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  }

  function stop() {
    if (!cur) return;
    var c = cur;
    cur = null;                        // cleared first: the onend it fires must
    label(c.btn, false);               // not advance the queue we are dropping
    c.btn.classList.remove("on");
    if (c.mark) c.mark.classList.remove("speaking");
    synth.cancel();
  }

  function start(btn, head) {
    var wasPlaying = !!cur;
    stop();

    var queue = [];
    blocks(head).forEach(function (el) {
      runs(el).forEach(function (r) {
        var voice = voiceFor(r.lang);
        if (r.lang === "he" && !voice) return;
        pieces(r.text, voice).forEach(function (text) {
          queue.push({ el: el, text: text, lang: r.lang });
        });
      });
    });
    if (!queue.length) return;

    cur = { btn: btn, queue: queue, i: 0, mark: null };
    btn.classList.add("on");
    label(btn, true);
    // Chrome swallows a speak() issued in the same tick as a cancel(); on a
    // first press there is nothing to cancel, and speaking straight out of the
    // click is what iOS requires.
    if (wasPlaying) setTimeout(next, 80); else next();
  }

  function next() {
    var c = cur;
    if (!c) return;
    if (c.i >= c.queue.length) { stop(); return; }

    var item = c.queue[c.i++];
    var u = new window.SpeechSynthesisUtterance(item.text);
    var v = voiceFor(item.lang);
    if (v) u.voice = v;
    u.lang = (v && v.lang) || TAG[item.lang] || item.lang;
    u.rate = 0.95;                     // a hair under speed: this is a shiur
    u.onstart = function () { if (cur === c) mark(c, item.el); };
    // 'error' is also how a cancel arrives, hence the identity check on both
    u.onend = function () { if (cur === c) next(); };
    u.onerror = function () { if (cur === c) next(); };
    synth.speak(u);
  }

  function mark(c, el) {
    if (c.mark === el) return;
    if (c.mark) c.mark.classList.remove("speaking");
    c.mark = el;
    el.classList.add("speaking");
  }

  // ---- the buttons -----------------------------------------------------
  // Both language halves of the sheet are in the DOM at once, so this hangs a
  // button on the hidden one too; only the visible one can be pressed.
  document.querySelectorAll(".sheet h2, .sheet h3").forEach(function (head) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "speak";
    label(btn, false);
    btn.addEventListener("click", function () {
      if (cur && cur.btn === btn) stop(); else start(btn, head);
    });
    head.appendChild(btn);
  });

  document.addEventListener("daflang", function () {
    stop();                            // the body under the voice just changed
    document.querySelectorAll(".speak").forEach(function (b) { label(b, false); });
  });
  document.addEventListener("dafview", function () { stop(); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") stop();
  });
  // Speech outlives the page it started on: a back-navigation would otherwise
  // leave a voice reading a daf that is no longer on screen.
  window.addEventListener("pagehide", function () { stop(); });
})();
