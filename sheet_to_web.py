#!/usr/bin/env python3
"""Turn a Daf Yomi markdown study sheet into a self-contained interactive HTML page:
a nicely styled "Learn" view plus a "Quiz" game built from the Chazara section.

Usage: python3 sheet_to_web.py <sheet>.md <out>.html [<sheet-es>.md]

If a Spanish companion sheet exists it is baked into the same page, and a language
toggle (added by build_site.py, in the top-right nav) switches title, subtitle,
study sheet, quiz and all chrome between English and Spanish. The preference lives
in localStorage under "dafLang", so it follows the reader across the whole site.

The Spanish sheet is looked up automatically as <sheet>.es.md unless given
explicitly as a third argument. Without one the page still carries the toggle;
Spanish then shows the English sheet under a short note.
"""
import sys, os, re, json, html, markdown

if len(sys.argv) < 3:
    sys.exit(__doc__)
src, out = sys.argv[1], sys.argv[2]

# ---- Spanish companion: explicit 3rd arg, else <sheet>.es.md next to the English one ----
if len(sys.argv) >= 4:
    src_es = sys.argv[3]
else:
    guess = re.sub(r"\.md$", ".es.md", src)
    src_es = guess if guess != src and os.path.exists(guess) else None
if src_es and not os.path.exists(src_es):
    sys.exit(f"Spanish sheet not found: {src_es}")


# ---- inline markdown -> minimal HTML (for question/option/why text) ----
def inline(t):
    t = html.escape(t.strip())
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


# A section is "the quiz" / "the answer key" in either language. The English sheets
# head both with "Chazara"; the Spanish ones with "Chazará" (accented or not).
QUIZ_H = re.compile(r"^chazar[aá]", re.I)
KEY_H = re.compile(r"answer key|respuestas|clave", re.I)
SUB_H = re.compile(r"^\*\*(Chapter|Cap[íi]tulo)")


def parse_sheet(raw):
    """One markdown sheet -> {title, subtitle, learn (HTML), quiz (list)}."""
    lines = raw.split("\n")

    # ---- title + subtitle ----
    title = "Daf Yomi"
    subtitle = ""
    for ln in lines:
        if ln.startswith("# "):
            title = ln[2:].strip()
            break
    for ln in lines:
        s = ln.strip()
        if SUB_H.match(s) or "Study date" in s or "Fecha de estudio" in s:
            subtitle = re.sub(r"\*\*", "", s)
            subtitle = re.sub(r"\*(.+?)\*", r"<em>\1</em>", subtitle)
            break

    # ---- split into H2 sections ----
    # intro = text before first "## "; then a list of (h2_title, body_md)
    first = raw.find("\n## ")
    intro_md = raw[:first] if first != -1 else raw
    rest = raw[first:] if first != -1 else ""
    chunks = re.split(r"\n## ", rest)
    sections = []
    for c in chunks:
        if not c.strip():
            continue
        nl = c.find("\n")
        h = c[:nl].strip() if nl != -1 else c.strip()
        body = c[nl + 1:] if nl != -1 else ""
        sections.append((h, body))

    # strip the leading H1/subtitle out of intro for the Learn body (shown in header instead)
    intro_body = re.sub(r"^#\s.*$", "", intro_md, flags=re.M)
    intro_body = re.sub(r"^\*\*(Chapter|Cap[íi]tulo).*$", "", intro_body, flags=re.M)
    intro_body = intro_body.replace("---", "").strip()

    # ---- assemble Learn markdown (everything except the two Chazara sections) ----
    learn_parts = []
    if intro_body:
        learn_parts.append(intro_body)
    quiz_qsection = quiz_asection = ""
    for h, body in sections:
        if QUIZ_H.match(h.strip()):
            if KEY_H.search(h):
                quiz_asection = body
            else:
                quiz_qsection = body
            continue
        learn_parts.append("## " + h + "\n" + body)
    learn_md = "\n\n".join(learn_parts)
    learn_html = markdown.markdown(learn_md, extensions=["tables", "sane_lists", "smarty"])

    # ---- parse quiz questions ----
    questions = {}
    order = []
    cur = None
    for ln in quiz_qsection.split("\n"):
        mq = re.match(r"\s*\*\*(\d+)\.\s*(.*?)\*\*\s*$", ln)
        mo = re.match(r"\s*-\s*\(([a-d])\)\s*(.*)$", ln)
        if mq:
            cur = mq.group(1)
            questions[cur] = {"n": int(cur), "q": inline(mq.group(2)), "opts": {},
                              "correct": None, "why": ""}
            order.append(cur)
        elif mo and cur:
            questions[cur]["opts"][mo.group(1)] = inline(mo.group(2))

    # ---- parse answer key ----
    for ln in quiz_asection.split("\n"):
        ma = re.match(r"\s*(\d+)\.\s*\*\*\(([a-d])\)\*\*\s*(?:—|-|–)?\s*(.*)$", ln)
        if ma and ma.group(1) in questions:
            questions[ma.group(1)]["correct"] = ma.group(2)
            questions[ma.group(1)]["why"] = inline(ma.group(3))

    quiz = [questions[n] for n in order
            if questions[n]["opts"] and questions[n]["correct"]]
    return {"title": title, "subtitle": subtitle, "learn": learn_html, "quiz": quiz}


en = parse_sheet(open(src, encoding="utf-8").read())
es = parse_sheet(open(src_es, encoding="utf-8").read()) if src_es else None

NO_ES_NOTE = ('<div class="sheet nolang" data-lang="es">Esta hoja todavía no está '
              'disponible en español; abajo aparece la versión en inglés. '
              '<em>This sheet is not yet available in Spanish; the English version '
              'follows below.</em></div>')

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --paper:#fbf7ee; --ink:#2c261d; --accent:#8a5a2b; --accent2:#6b3f1d;
    --gold:#c9a86a; --gold-soft:#ead9b3; --panel:#fffdf8; --line:#e2d3b3;
    --good:#3f8f5b; --good-bg:#e7f4ec; --bad:#c0453b; --bad-bg:#fbe9e7;
    --shadow:0 6px 24px rgba(80,55,20,.10);
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  body{
    background:linear-gradient(180deg,#f4ecd8 0%,#fbf7ee 220px) fixed;
    color:var(--ink); font-family:"Iowan Old Style","Palatino Linotype",Georgia,"Times New Roman",serif;
    line-height:1.6; -webkit-font-smoothing:antialiased;
  }
  :lang(he),.he{font-family:"Frank Ruhl Libre","Times New Roman",Georgia,serif;}
  .wrap{max-width:820px;margin:0 auto;padding:0 18px 80px}
  header.top{
    text-align:center;padding:34px 18px 22px;margin-bottom:8px;
  }
  header.top h1{
    font-size:2.05rem;line-height:1.2;margin:0 0 6px;color:var(--accent2);
    letter-spacing:.2px;
  }
  header.top .sub{color:#7a6a4d;font-size:1rem;font-style:italic}
  .tabs{
    display:flex;gap:8px;justify-content:center;position:sticky;top:0;z-index:20;
    padding:12px 0;background:linear-gradient(180deg,var(--paper) 70%,rgba(251,247,238,0));
    margin-bottom:10px;
  }
  .tab{
    border:1px solid var(--gold);background:var(--panel);color:var(--accent2);
    padding:9px 22px;border-radius:999px;cursor:pointer;font-size:1rem;font-weight:600;
    box-shadow:var(--shadow);transition:.18s;font-family:inherit;
  }
  .tab:hover{transform:translateY(-1px)}
  .tab.active{background:var(--accent2);color:#fff;border-color:var(--accent2)}
  .view{display:none;animation:fade .35s ease}
  .view.active{display:block}
  @keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

  /* ---- Learn view ---- */
  .sheet{background:var(--panel);border:1px solid var(--line);border-radius:16px;
    padding:26px 30px;box-shadow:var(--shadow)}
  .sheet h2{font-size:1.4rem;color:var(--accent2);border-bottom:2px solid var(--gold-soft);
    padding-bottom:6px;margin:26px 0 10px}
  .sheet h2:first-child{margin-top:0}
  .sheet h3{font-size:1.12rem;color:var(--accent);margin:18px 0 6px}
  .sheet blockquote{margin:14px 0;padding:12px 18px;background:#faf3e3;
    border-left:4px solid var(--gold);border-radius:6px;font-style:italic}
  .sheet table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.95rem}
  .sheet th,.sheet td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
  .sheet th{background:var(--gold-soft);color:var(--accent2)}
  .sheet tr:nth-child(even) td{background:#fbf7ee}
  .sheet code{background:#f0e6ce;padding:1px 5px;border-radius:4px;font-size:.9em}
  .sheet hr{border:none;border-top:1px solid var(--line);margin:22px 0}
  .sheet ul{padding-left:22px}
  .sheet li{margin:5px 0}
  .sheet strong{color:var(--accent2)}
  .sheet.nolang{margin-bottom:14px;font-size:.92rem;color:#7a6a4d;padding:14px 18px}

  /* ---- Quiz view ---- */
  .quiz{background:var(--panel);border:1px solid var(--line);border-radius:16px;
    padding:26px 28px;box-shadow:var(--shadow)}
  .qbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:6px;
    font-size:.92rem;color:#7a6a4d}
  .prog{height:9px;background:var(--gold-soft);border-radius:999px;overflow:hidden;margin:8px 0 22px}
  .prog>i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--gold),var(--accent));
    border-radius:999px;transition:width .4s ease}
  .qnum{font-size:.85rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700}
  .qtext{font-size:1.28rem;line-height:1.45;margin:8px 0 20px;color:var(--ink)}
  .opts{display:flex;flex-direction:column;gap:12px}
  .opt{display:flex;align-items:flex-start;gap:12px;text-align:left;width:100%;
    border:1.5px solid var(--line);background:#fffdf8;border-radius:12px;padding:14px 16px;
    cursor:pointer;font-size:1.05rem;font-family:inherit;color:var(--ink);transition:.15s}
  .opt:hover:not(.locked){border-color:var(--accent);transform:translateY(-1px);
    box-shadow:0 3px 12px rgba(120,80,30,.10)}
  .opt .key{flex:0 0 28px;height:28px;border-radius:50%;background:var(--gold-soft);
    color:var(--accent2);font-weight:700;display:flex;align-items:center;justify-content:center;
    font-size:.95rem}
  .opt.correct{border-color:var(--good);background:var(--good-bg)}
  .opt.correct .key{background:var(--good);color:#fff}
  .opt.wrong{border-color:var(--bad);background:var(--bad-bg)}
  .opt.wrong .key{background:var(--bad);color:#fff}
  .opt.locked{cursor:default}
  .opt.dim{opacity:.55}
  .why{margin-top:18px;padding:14px 16px;border-radius:12px;background:#f6efe0;
    border-left:4px solid var(--gold);font-size:1rem;display:none;animation:fade .3s}
  .why.show{display:block}
  .why b{color:var(--accent2)}
  .nav{display:flex;justify-content:space-between;align-items:center;margin-top:22px;gap:12px}
  .btn{border:none;border-radius:999px;padding:12px 26px;font-size:1.02rem;font-weight:700;
    cursor:pointer;font-family:inherit;background:var(--accent2);color:#fff;box-shadow:var(--shadow);
    transition:.16s}
  .btn:hover{transform:translateY(-1px);filter:brightness(1.06)}
  .btn.ghost{background:var(--panel);color:var(--accent2);border:1px solid var(--gold)}
  .btn:disabled{opacity:.4;cursor:default;transform:none}
  .pill{background:var(--gold-soft);color:var(--accent2);border-radius:999px;padding:4px 12px;font-weight:700}
  .streak{color:var(--accent)}
  /* end screen */
  .end{text-align:center;padding:14px 6px}
  .end .big{font-size:3.4rem;margin:6px 0}
  .end .score{font-size:1.6rem;color:var(--accent2);font-weight:700;margin:4px 0}
  .end .msg{font-size:1.1rem;color:#6a5a3d;margin:8px 0 20px}
  .review{text-align:left;margin-top:20px}
  .review .r{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0;background:#fffdf8}
  .review .r .rq{font-weight:700;color:var(--ink);margin-bottom:6px}
  .review .r .ra{font-size:.96rem;margin:2px 0}
  .review .ok{color:var(--good)} .review .no{color:var(--bad)}
  .hint{color:#9a8a6d;font-size:.82rem;text-align:center;margin-top:14px}
  @media(max-width:520px){.sheet,.quiz{padding:20px 16px}.qtext{font-size:1.14rem}header.top h1{font-size:1.6rem}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>__H1__</h1>
    <div class="sub">__SUB__</div>
  </header>

  <div class="tabs">
    <button class="tab active" data-v="learn">📖 <span data-lang="en">Learn</span><span data-lang="es">Aprender</span></button>
    <button class="tab" data-v="quiz">🎯 <span data-lang="en">Chazara Quiz</span><span data-lang="es">Repaso (Chazará)</span></button>
  </div>

  <section class="view active" id="learn">
__LEARN__
  </section>

  <section class="view" id="quiz">
    <div class="quiz" id="quizCard"></div>
    <div class="hint">
      <span data-lang="en">Tip: press keys 1–4 to answer, Enter for next.</span>
      <span data-lang="es">Consejo: pulsa las teclas 1–4 para responder y Enter para continuar.</span>
    </div>
  </section>
</div>

<script>
const QUIZ_BY_LANG = __QUIZJSON__;
const TITLE_BY_LANG = __TITLEJSON__;
const STR = {
  en:{q:"Question", score:"Score", streak:"streak", toGo:"to go", next:"Next →",
      results:"See results →", ok:"✓ Correct.", noPre:"✗ Not quite — the answer is ",
      again:"↻ Play again", look:"Worth another look", yours:"Your answer:", right:"Correct:",
      best:"best streak",
      m100:"Perfect score! You own this daf.", m80:"Excellent — nearly airtight.",
      m60:"Solid. A quick re-read of the tricky ones and you're set.",
      m0:"Good start — a review round will lock it in."},
  es:{q:"Pregunta", score:"Puntos", streak:"seguidas", toGo:"por responder",
      next:"Siguiente →", results:"Ver resultados →", ok:"✓ Correcto.",
      noPre:"✗ Casi — la respuesta es ", again:"↻ Jugar de nuevo",
      look:"Vale la pena repasar", yours:"Tu respuesta:", right:"Correcta:",
      best:"mejor racha",
      m100:"¡Puntuación perfecta! Dominas este daf.", m80:"Excelente — casi impecable.",
      m60:"Bien. Una relectura rápida de las difíciles y ya lo tienes.",
      m0:"Buen comienzo — una ronda de repaso lo afianzará."}
};
// build_site.py injects the toggle and window.dafLang(); standalone, fall back to English.
let L = window.dafLang ? window.dafLang() : "en";
if(!STR[L]) L = "en";
let QUIZ = QUIZ_BY_LANG[L] || QUIZ_BY_LANG.en;
let T = STR[L];

const KEYS = ["a","b","c","d"];
let idx=0, score=0, streak=0, best=0, answered=false, results=[];

const card = document.getElementById("quizCard");

function renderQuestion(){
  answered=false;
  const q = QUIZ[idx];
  const pct = Math.round((idx)/QUIZ.length*100);
  let opts = Object.keys(q.opts).sort().map(k=>`
    <button class="opt" data-k="${k}">
      <span class="key">${k.toUpperCase()}</span>
      <span class="txt">${q.opts[k]}</span>
    </button>`).join("");
  card.innerHTML = `
    <div class="qbar">
      <span class="qnum">${T.q} ${idx+1} / ${QUIZ.length}</span>
      <span>${T.score} <span class="pill">${score}</span> ${streak>1?`<span class="streak">🔥 ${streak} ${T.streak}</span>`:""}</span>
    </div>
    <div class="prog"><i style="width:${pct}%"></i></div>
    <div class="qtext">${q.q}</div>
    <div class="opts">${opts}</div>
    <div class="why" id="why"></div>
    <div class="nav">
      <span style="color:#9a8a6d;font-size:.85rem">${QUIZ.length-idx-1} ${T.toGo}</span>
      <button class="btn" id="next" disabled>${idx===QUIZ.length-1?T.results:T.next}</button>
    </div>`;
  card.querySelectorAll(".opt").forEach(b=>b.addEventListener("click",()=>choose(b.dataset.k)));
  document.getElementById("next").addEventListener("click",next);
}

function choose(k){
  if(answered) return;
  answered=true;
  const q=QUIZ[idx];
  const correct=q.correct;
  const chosenRight = k===correct;
  if(chosenRight){score++;streak++;best=Math.max(best,streak);} else {streak=0;}
  results.push({n:q.n,q:q.q,chosen:k,correct:correct,opts:q.opts,why:q.why,right:chosenRight});
  card.querySelectorAll(".opt").forEach(b=>{
    b.classList.add("locked");
    const bk=b.dataset.k;
    if(bk===correct) b.classList.add("correct");
    else if(bk===k) b.classList.add("wrong");
    else b.classList.add("dim");
  });
  const why=document.getElementById("why");
  why.innerHTML = `<b>${chosenRight?T.ok:T.noPre+correct.toUpperCase()+"."}</b> ${q.why}`;
  why.classList.add("show");
  const nb=document.getElementById("next");
  nb.disabled=false; nb.focus();
  nb.textContent = idx===QUIZ.length-1 ? T.results : T.next;
  // update live score display
  card.querySelector(".qbar .pill").textContent=score;
}

function next(){
  if(!answered) return;
  if(idx<QUIZ.length-1){idx++;renderQuestion();window.scrollTo({top:0,behavior:"smooth"});}
  else endScreen();
}

function endScreen(){
  const pct=Math.round(score/QUIZ.length*100);
  let emoji="📘",msg=T.m0;
  if(pct===100){emoji="🏆";msg=T.m100;}
  else if(pct>=80){emoji="🌟";msg=T.m80;}
  else if(pct>=60){emoji="👍";msg=T.m60;}
  const reviewWrong = results.filter(r=>!r.right);
  let reviewHtml="";
  if(reviewWrong.length){
    reviewHtml = `<div class="review"><h3 style="color:var(--accent2)">${T.look}</h3>` +
      reviewWrong.map(r=>`<div class="r">
        <div class="rq">${r.n}. ${r.q}</div>
        <div class="ra no">${T.yours} ${r.chosen.toUpperCase()}) ${r.opts[r.chosen]}</div>
        <div class="ra ok">${T.right} ${r.correct.toUpperCase()}) ${r.opts[r.correct]}</div>
        <div class="ra" style="color:#6a5a3d;margin-top:4px">${r.why}</div>
      </div>`).join("") + `</div>`;
  }
  card.innerHTML = `<div class="end">
      <div class="big">${emoji}</div>
      <div class="score">${score} / ${QUIZ.length} &nbsp;·&nbsp; ${pct}%</div>
      <div class="msg">${msg}${best>1?` &nbsp;·&nbsp; ${T.best} 🔥 ${best}`:""}</div>
      <button class="btn" id="again">${T.again}</button>
    </div>${reviewHtml}`;
  document.getElementById("again").addEventListener("click",restart);
  window.scrollTo({top:0,behavior:"smooth"});
}

function restart(){idx=0;score=0;streak=0;best=0;results=[];renderQuestion();}

// Language switch: the quiz can't carry answers across a translation, so start it over.
document.addEventListener("daflang",e=>{
  const l = STR[e.detail.lang] ? e.detail.lang : "en";
  if(l===L) return;
  L=l; T=STR[L]; QUIZ = QUIZ_BY_LANG[L] || QUIZ_BY_LANG.en;
  if(TITLE_BY_LANG[L]) document.title = TITLE_BY_LANG[L];
  restart();
});
if(TITLE_BY_LANG[L]) document.title = TITLE_BY_LANG[L];

// tab switching
document.querySelectorAll(".tab").forEach(t=>t.addEventListener("click",()=>{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
  document.querySelectorAll(".view").forEach(x=>x.classList.remove("active"));
  t.classList.add("active");
  document.getElementById(t.dataset.v).classList.add("active");
  if(t.dataset.v==="quiz" && !card.innerHTML.trim()) renderQuestion();
}));

// keyboard
document.addEventListener("keydown",e=>{
  if(!document.getElementById("quiz").classList.contains("active")) return;
  if(["1","2","3","4"].includes(e.key)){const k=KEYS[+e.key-1];const b=card.querySelector(`.opt[data-k="${k}"]`);if(b)b.click();}
  else if(e.key==="Enter"){const n=document.getElementById("next");if(n&&!n.disabled)n.click();}
});

renderQuestion();
</script>
</body>
</html>"""


def span(txt, langs):
    return f'<span data-lang="{langs}">{txt}</span>'


if es:
    h1 = span(html.escape(en["title"]), "en") + span(html.escape(es["title"]), "es")
    sub = span(en["subtitle"], "en") + span(es["subtitle"], "es")
    learn = ('    <div class="sheet" data-lang="en">' + en["learn"] + "</div>\n"
             '    <div class="sheet" data-lang="es">' + es["learn"] + "</div>")
    quiz_json = {"en": en["quiz"], "es": es["quiz"]}
    titles = {"en": en["title"], "es": es["title"]}
else:
    # No Spanish sheet: the English body serves both languages (data-lang="en es"),
    # so nothing is duplicated — Spanish just gets a note above it.
    h1 = span(html.escape(en["title"]), "en es")
    sub = span(en["subtitle"], "en es")
    learn = ("    " + NO_ES_NOTE + "\n"
             '    <div class="sheet" data-lang="en es">' + en["learn"] + "</div>")
    quiz_json = {"en": en["quiz"], "es": en["quiz"]}
    titles = {"en": en["title"], "es": en["title"]}

out_html = (TEMPLATE
            .replace("__TITLE__", html.escape(en["title"]))
            .replace("__H1__", h1)
            .replace("__SUB__", sub)
            .replace("__LEARN__", learn)
            .replace("__QUIZJSON__", json.dumps(quiz_json, ensure_ascii=False))
            .replace("__TITLEJSON__", json.dumps(titles, ensure_ascii=False)))

open(out, "w", encoding="utf-8").write(out_html)
n_en, n_es = len(en["quiz"]), len(es["quiz"]) if es else 0
extra = f", {n_es} Spanish (from {os.path.basename(src_es)})" if es else ", no Spanish sheet"
print(f"Wrote {out}  ({n_en} quiz questions{extra})")
