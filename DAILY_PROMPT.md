# Daf Yomi build — keep the site a week ahead, unattended

You are running non-interactively in the repo `/Users/moshecosio/daf-yomi`
(a clone of `jocosiol/daf-yomi`, published at https://jocosiol.github.io/daf-yomi/).

**You are not building "today's daf" — you are topping up a buffer.** The published site
rolls over at sunset on its own, from a manifest baked into every page, so it does not need
a build every day; it needs a few days in hand. Publishing is not what can fail — CI rebuilds
and deploys on every push. The writing is: this machine is a laptop that is often switched
off, and the buffer is what keeps a missed run from leaving a day with no daf.

Work through steps 0–6 in order, then stop. Do not ask questions — make reasonable
decisions and proceed. Do not skip the Sefaria fetch: accuracy comes from the real text,
never from memory. Every daf ships in **three languages**: English in
`content/<Tractate>_<page>.md`, Spanish in `content/<Tractate>_<page>.es.md` and Hebrew in
`content/<Tractate>_<page>.he.md`. Do not skip the translations.

**You do not have to police the file format.** `build/validate.py` checks it and the build
refuses to write anything if it fails, naming the file and the problem. Write the sheet,
run the build, fix whatever it reports.

---

## Step 0 — Sync

```bash
cd /Users/moshecosio/daf-yomi
git pull --rebase origin main
```

## Step 1 — What needs writing?

```bash
python3 build/buffer.py
```

It prints the whole window and then the work, oldest first and already capped at what one
run should attempt:

```
5 item(s) to write; this run should do at most 3, oldest first:
  2026-08-08  es   (Chullin_100 has no es sheet)
  2026-08-09  he   (Chullin_101 has no he sheet)
  2026-08-10  en   (no sheet)
  … 2 more, left for the next run
```

`en` means the daf itself does not exist yet — write all three sheets for it. `es` or `he`
means the English sheet is already there and only that translation is missing.

**Work oldest first and do not exceed the cap.** The nearest dates matter most, and the job
runs again every two hours, so anything you leave is picked up shortly. If it says the
buffer is full, skip straight to step 5.

For each date you are going to write, ask Sefaria which daf falls on it:

```bash
curl -s "https://www.sefaria.org/api/calendars?timezone=Asia/Jerusalem&year=2026&month=8&day=10"
```

Read the `calendar_items` entry whose `title.en` is exactly `"Daf Yomi"` and take its
`displayValue.en` — e.g. `"Chullin 102"`. That gives `<Tractate>` and `<page>`.

**The `timezone=Asia/Jerusalem` parameter is required** — without it Sefaria answers in its
own default timezone and you will get the wrong daf. Always pass `year`/`month`/`day` too;
never assume the next date is simply the next page, because tractates end.

The date you asked for is the sheet's `study_date`, verbatim. Nothing else about dates
matters — the build formats the display forms, in each language, from that one ISO value.

## Step 2 — Fetch the real text, both amudim, English and Hebrew

Do this for **each** daf you are writing.

```bash
curl -s "https://www.sefaria.org/api/texts/<Tractate>.<page>a"
curl -s "https://www.sefaria.org/api/texts/<Tractate>.<page>b"
```

Each response has parallel arrays: `he` (Hebrew/Aramaic) and `text` (William Davidson
English). Strip HTML tags and read **every** segment of both amudim before writing. Base
every claim, name, and quotation on what is actually there.

`python3 build/daftext.py <Tractate> <page>` fetches the same text into
`content/daf/<Tractate>_<page>.json` — both amudim, tags already stripped, and Rashi and
Tosafot alongside each segment. Step 5 needs that file anyway, so writing from it saves a
fetch and puts Rashi in front of you while you write.

Also glance at the following day's first amud for the one-line `tomorrow` preview. Get that
day's reference from the calendars API with its own date rather than assuming `page + 1` —
tractates end, and the buffer means you are often writing several days out.

## Step 3 — Write `content/<Tractate>_<page>.md`

Warm, clear, and specific, for a reader who has some Gemara background — not a beginner,
not a scholar. Match the tone of the previous sheets in `content/`.

Each daf is written for its own study date, not for today. A sheet dated four days out is
written exactly as if it were the daily sheet for that day — nothing in it should refer to
"today" in the sense of the day you are running.

### Front matter — the facts, declared once

```yaml
---
tractate: Chullin
page: 102
daf_he: חולין קב
chapter:
  n: 7
  name: Gid HaNasheh
  gloss: the sciatic nerve
study_date: 2026-08-10
summary: One sentence for link previews and search — what this daf is about.
tomorrow:
  date: 2026-08-11
  ref: Chullin 103
  teaser: …
---
```

`study_date` is ISO only. The build renders `Mon, 10 August 2026` and
`lun, 10 de agosto de 2026` from it, so there is no date sentence to get wrong.
Sefaria's `heRef` gives the Hebrew numeral: `חולין ק״ב א` → `daf_he: חולין קב`.

**The chapter comes from the tractate's structure, not from the page number, and Sefaria's
text API does not tell you.** In Chullin, ch. 7 *Gid HaNasheh* runs 89b–103b and ch. 8
*Kol HaBasar* begins at 103b. Check where the daf you are writing actually falls; the
example above is chapter 7 because 102 is inside that range, not because 102 implies it.

A daf can straddle the boundary — 103 has the end of ch. 7 on 103a and the start of ch. 8
on 103b. Put the chapter the daf *opens* in the front matter, and say in the prose where
the new chapter begins.

### Then the prose, as `## ` sections in this order

**The order is not presentation — the build cuts the sheet into tabs at these headings.**
The page reads as three moments, in this order:

| Tab | What is in it |
|---|---|
| 📖 **Introduction** | (a) the big picture, (b) the terms — with the flashcard deck under them — and (c) who's who |
| 📜 **The Daf** | the Vilna page and its text. Not written by you; the build fetches it |
| 🎯 **Chazara** | (d) the walkthrough, (e) the grid, (f) the line to carry — then the test |

The cut is the `## Walking through the sugya` heading: everything above it is the
Introduction, and that heading and everything after it is Chazara. So a section in the
wrong place opens in the wrong tab. Write the seven sections in the order below and the
three tabs fall out on their own — there is nothing else to do to build them.

**(a) `## The big picture (read this first)`** — what today's page is really about, and why
it matters. A blockquote for the central idea works well.

**(b) `## Key concepts & terms`** — a markdown table, `| Term | Meaning |`, with the
Hebrew/Aramaic term, its transliteration, and what it means on this daf.

It sits in the Introduction because it is the vocabulary the daf is about to use: read the
terms first and the argument is followable. Write it *after* the walkthrough even so — you
only know which words carry the daf once you have laid the argument out — then put it here.

This table is also the daf's **flashcard deck**: the build turns each row into a card, term
on the front and meaning on the back, and drops the deck into the page directly beneath the
table. So write each side to stand on its own — a meaning that only makes sense while
looking at the row above it makes a poor card. The translation must have the same terms in
the same order; `validate.py` rejects a glossary that has gained or lost a row.

**(c) `## Who's who in today's daf`** — for **every** sage named, a one-line ID: era
(**Tanna** / **Babylonian Amora** / **Eretz-Yisrael Amora**), approximate generation, where
they lived, and a teacher or famous disputant. Group by era if the list is long.
- Title tells: **Rav** = Babylonian Amora; **Rabbi** = Tanna or Eretz-Yisrael Amora;
  **Rebbi** alone = R' Yehuda HaNasi.
- Flag look-alikes explicitly: Rabbah (רבה) vs Rava (רבא); Mar bar Rav Ashi vs Rav Acha bar
  Rav Ashi; Rabbi Chiyya vs Rabbi Chiyya bar Abba; Rav Asi vs Rav Ashi.
- **If you are unsure about a minor figure, say so plainly.** Never invent a biography.

**(d) `## Walking through the sugya, step by step`** — the argument in order, with `### `
subheadings per amud (`### 102a — …`). Bold the moves (**The objection.**, **The answer.**)
so it can be skimmed. Quote key Aramaic inline with its translation.

**(e) `## The distinctions, side by side`** — one markdown table that collapses the daf's
central distinction into a grid you can take in at a glance.

This is **not** the terms table. That one is a glossary: term → meaning, one row per word.
This one is a **matrix**: one row per *case* the daf distinguishes, one column per *question*
the daf asks of every case, and the same question asked of every row. Chullin 105 is the
model — the prose spends three paragraphs on the three waters, and the whole thing is a grid:

| Waters | Grade | Poured into | Temperature |
|---|---|---|---|
| **First** (before bread) | Mitzva | Vessel **or** the ground | Hot or cold |
| **Middle** (between dishes) | Optional — but obligatory before cheese | — | — |
| **Last** (before *bircat hamazon*) | Obligation (*chova*) | Vessel only | Cold only |

Rules that keep it useful:

- **Say nothing the walkthrough did not already establish.** The grid compresses the
  analysis; it never adds a claim, and every cell should be traceable to a line above it.
- **2–4 columns, 2–6 rows.** Cells are a phrase, not a sentence — if a cell needs a full
  sentence, that belongs in the prose.
- **A dash is a legitimate cell.** "The Gemara does not say" is information; inventing a
  value to fill the square is not.
- **Pick the axis the daf actually argues about.** Usually one of: two schools across a set
  of cases (Beit Shammai / Beit Hillel), one case graded on several tests, a sequence of
  attempted readings and why each failed, or a permitted/forbidden split.
- **If the daf genuinely has no clean matrix** — a pure narrative or aggadic stretch — use
  the section for an ordered table of the sugya's moves instead
  (`| Move | The claim | How it ends |`), and keep it short. Do not force a grid.

**(f) `## One line to carry with you`** — one memorable takeaway, as a blockquote.

**(g) `## Chazara — test yourself`** — **the last section**, and the reason to write it last:
the questions should come out of the analysis you have just written.

Not prose — a `yaml` block. The correct answer sits next to its options, so there is no
separate answer key to keep in step:

````markdown
## Chazara — test yourself

```yaml
- q: The question text, ending in a question mark?
  opts:
    - First option.
    - Second option.
    - Third option.
    - Fourth option.
  correct: b
  why: One line on why that answer is right.
```
````

8–10 questions. Exactly four options each, in the order a/b/c/d.

**Write the three wrong options as carefully as the right one.** The instinct is to state
the correct answer precisely and dismiss the others in a few words — and that quietly ruins
the quiz, because the longest option is then always the answer. Across the first eight
sheets that was true 96% of the time, so a reader who never opened the daf could score 96%
by picking the longest one. Page shuffling does not help: it randomises position, not
length.

So: keep all four options within roughly the same length, and make each wrong one a
position someone could actually hold — a view the Gemara raises and rejects, the other
side of the dispute, the right idea attached to the wrong sage. A distractor that is
obviously filler is a question not worth asking.

Vary which letter is correct, too. Separate major prose sections with `---`.

## Step 4 — Write `content/<Tractate>_<page>.es.md` (the Spanish sheet)

A full Spanish translation — same content, same structure, same depth. Not a summary.
Readers pick a language from the 🌐 menu and the choice is remembered site-wide, so the
two sheets must stay in step.

### Front matter — only what differs

```yaml
---
lang: es
title: Daf Yomi — Julín 102 (חולין קב)
chapter:
  name: Guid HaNashé
  gloss: el nervio ciático
summary: Una frase para las vistas previas y la búsqueda.
tomorrow:
  ref: Julín 103
  teaser: …
---
```

`tractate`, `page`, `daf_he`, `study_date` and `chapter.n` are **inherited from the English
sheet — do not restate them.** Validation rejects the file if you do. This is deliberate:
the translation cannot disagree with the English about which day it is.

### What changes, and what does not

- **Keep every Hebrew/Aramaic quotation exactly as it is.** Only the surrounding explanation
  is translated. Transliterations in the terms table get Spanish spelling
  (*mejidush lo gamrinan*, *guzmá*, *jatzí shiur*) — `ch`→`j`, `tz` stays, accents added.
- **The quiz must be the same quiz.** Question 1 in Spanish is question 1 in English, the
  options stay in the same order, and `correct` is the same letter. Validation compares them
  and fails on a mismatch.
- **The side-by-side grid must be the same grid** — same columns in the same order, same rows
  in the same order, only the words translated. Do not add a row the English sheet does not
  have, or merge two of them. Validation compares the shape and fails on a mismatch.
- Names use Spanish-Hebrew convention: Abaie, Rabá, Rava, Iehudá, Iojanán, Iehoshúa, Jiiá,
  Janiná, Itzjak, Erretz Israel, cohén, Guemará, baraita, mishná, halajá, trumá, suguiá,
  jazará.
  The tractate name in `title` is transliterated (`Julín`), but **file names never change** —
  they stay `content/Chullin_<page>.es.md`.
- Register: the warm, direct "tú" voice of the English sheet. Not academic Spanish.

### Spanish headings

| English | Spanish |
|---|---|
| The big picture (read this first) | El panorama general (leer esto primero) |
| Key concepts & terms | Conceptos y términos clave |
| Who's who in today's daf | Quién es quién en el daf de hoy |
| Walking through the sugya, step by step | Recorriendo la suguiá, paso a paso |
| The distinctions, side by side | Las distinciones, lado a lado |
| One line to carry with you | Una línea para llevarte |
| Chazara — test yourself | Jazará — ponte a prueba |

Use `content/Chullin_98.es.md` and `content/Chullin_99.es.md` as the reference for tone and
terminology.

## Step 4b — Write `content/<Tractate>_<page>.he.md` (the Hebrew sheet)

A full Hebrew sheet — same content, same structure, same depth. Everything said about the
Spanish sheet above applies here too: the quiz is the same quiz in the same order with the
same `correct` letter, the side-by-side grid keeps its shape, and the glossary keeps its
row count. Validation compares all three and fails on a mismatch.

### Front matter — only what differs

```yaml
---
lang: he
title: דף יומי — חולין קד
chapter:
  name: כל הבשר
  gloss: כל בשר — דיני בשר בחלב
summary: משפט אחד לתצוגה המקדימה ולחיפוש.
tomorrow:
  ref: חולין קה
  teaser: …
---
```

`tractate`, `page`, `daf_he`, `study_date` and `chapter.n` are **inherited — do not restate
them.** The Hebrew `title` carries no bracketed reference: the Hebrew daf reference the
other two languages put in brackets *is* the title here. The archive link text is whatever
follows the em dash, so `דף יומי — חולין קד` gives `חולין קד`. File names never change —
the file is `content/Chullin_<page>.he.md`.

### What changes, and what does not

- **This is a Hebrew sheet, not a transliterated one.** Drop the parenthetical
  transliterations the English glossary carries — *(gezeirah ligzeirah)* beside
  **גְּזֵירָה לִגְזֵירָה** says nothing to a reader of Hebrew. The term alone is the term.
- **Keep the pointed quotations exactly as they are.** They are already Hebrew; only the
  surrounding explanation is written afresh.
- Register: the plain, direct second-person-plural of an Israeli daf-yomi explainer —
  *קראו*, *בחנו את עצמכם*. Not academic, and not rabbinic-formal.
- Arrows in prose point the other way. In an RTL line "back" is → and "next" is ←; the
  build's own strings already do this, and a sheet that writes one should match.
- Write the Gemara's own idiom in its own words. Where the English says "a decree to guard
  a decree", the Hebrew simply says **גזירה לגזירה** — do not translate the translation.

### Hebrew headings

| English | Hebrew |
|---|---|
| The big picture (read this first) | התמונה הגדולה (לקרוא קודם) |
| Key concepts & terms | מושגים ומונחים מרכזיים |
| Who's who in today's daf | מי ומי בדף של היום |
| Walking through the sugya, step by step | עוברים על הסוגיה, צעד אחר צעד |
| The distinctions, side by side | ההבחנות, זו מול זו |
| One line to carry with you | שורה אחת לקחת אתכם |
| Chazara — test yourself | חזרה — בחנו את עצמכם |

Use `content/Chullin_104.he.md` as the reference for tone and terminology.

## Step 5 — Build

First cache the daf itself, which the Daf tab shows two ways — the printed page from
shas.org, and the Gemara with Rashi and Tosafot from Sefaria:

```bash
python3 build/daftext.py --all
```

It fetches only what `content/daf/` is missing, so it is a no-op once today's daf is in and
costs nothing on a run that wrote nothing. The build never fetches anything itself; a daf
with nothing cached is published without its Daf tab, and the build names it.

If it reports no printed page for a daf, or you have just moved to a new tractate, check
the name table:

```bash
python3 build/dafpdf.py Chullin 108    # this daf
python3 build/dafpdf.py --all         # all forty tractates, first daf of each
```

shas.org spells tractates the Ashkenazi way — Ketubot is `kesubos` — so a new tractate needs
an entry in `SLUG` in `build/dafpdf.py`. All forty are already there; this is the check that
proves it, not a step to run every day.

```bash
python3 build/build.py
```

That is the whole build. No arguments: the sunset pin and the site URL live in
`content/site.json`, so they cannot be forgotten on the command line.

It validates first and **writes nothing if validation fails** — it prints the file and the
problem. Fix the sheet and run it again. Warnings are advisory; errors are not.

You are running this as a **check, not as the publishing step.** It writes `site/`, which is
git-ignored and never committed; GitHub Actions rebuilds the same tree from your pushed
sources and deploys that. So run it to prove the sheets you just wrote actually build — but
do not go looking for output to add to the commit, and never commit `site/`.

Expect output like:

```
Built 5 daf (6 translated, 5 with the daf text) + 1 legacy = 6 routed
languages: en, es, he
index.html seeded with Chullin_102 (2026-08-10)
rollover: sunset, location pinned to 31.7683,35.2137
```

Then confirm the buffer actually moved:

```bash
python3 build/buffer.py
```

Three things to know:

- **Most sheets are dated ahead of today.** That is the design, not a mistake: the homepage
  rolls over at sunset on its own. Never delete a future daf's sheet.
- The buffer does not have to be full when you finish. If it still reports items, you hit
  the per-run cap and the next run continues. It should be *shorter* than when you started.
- A `warn` about a missing `es` or `he` sheet is only a reminder for a future daf, but it
  means you skipped step 4 or 4b if it names one you just wrote.

Optional, if a browser is available and you changed anything under `build/`:

```bash
python3 -m http.server 8891 --directory site & sleep 1
node build/check_browser.js       # needs puppeteer-core; skip if not installed
kill %1
```

## Step 6 — Publish

Publishing is a push and nothing else. `.github/workflows/deploy.yml` rebuilds the site from
the sources you are about to push and deploys it to Pages; the build you just ran locally is
not what gets served.

```bash
git add -A
git commit -m "<Tractate> <page> — <ISO date>"
git push origin main
```

`git add -A` is safe: `site/` is git-ignored, so the commit is markdown and cached daf text.
**If `git status` is showing you built HTML, stop** — something wrote to the repo root, which
nothing should any more.

One commit for the run is fine when you wrote several dapim; name the range in the subject,
e.g. `Chullin 102-104 — 2026-08-10..12`. Commit even if you only got part way through the
list: a partial top-up is worth publishing, and the next run continues from there.

Then confirm it went live. Actions has to build before Pages serves anything, so allow ~2
minutes rather than the 30–90s a branch deploy took:

```bash
sleep 120
curl -s "https://jocosiol.github.io/daf-yomi/?cb=$$" | grep -o '<title>[^<]*</title>'
gh run list --workflow deploy.yml --limit 1   # if gh is available
```

It should name today's daf. A stale title with a green workflow run usually means Pages is
still set to "Deploy from a branch" instead of "GitHub Actions" — say so in the report rather
than trying to fix it. If the push failed on a non-fast-forward, `git pull --rebase origin
main` and push again.

Finish with a two-line report: what you wrote and what the buffer is now, and whether the
live site confirmed today's daf.
