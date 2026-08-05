# Daily Daf Yomi build — run this whole pipeline, unattended

You are running non-interactively in the repo `/Users/moshecosio/daf-yomi`
(a clone of `jocosiol/daf-yomi`, published at https://jocosiol.github.io/daf-yomi/).

Work through steps 0–6 in order, then stop. Do not ask questions — make reasonable
decisions and proceed. Do not skip the Sefaria fetch: accuracy comes from the real text,
never from memory. Every daf ships in **two languages**: English in
`content/<Tractate>_<page>.md` and Spanish in `content/<Tractate>_<page>.es.md`.
Do not skip the Spanish sheet.

**You do not have to police the file format.** `build/validate.py` checks it and the build
refuses to write anything if it fails, naming the file and the problem. Write the sheet,
run the build, fix whatever it reports.

---

## Step 0 — Sync

```bash
cd /Users/moshecosio/daf-yomi
git pull --rebase origin main
```

## Step 1 — Which daf is today?

```bash
curl -s "https://www.sefaria.org/api/calendars?timezone=Asia/Jerusalem"
```

Read the `calendar_items` entry whose `title.en` is exactly `"Daf Yomi"` and take its
`displayValue.en` — e.g. `"Chullin 102"`. That gives `<Tractate>` and `<page>`.

**The `timezone=Asia/Jerusalem` parameter is required** — without it Sefaria answers in its
own default timezone and you will get yesterday's daf.

Confirm today's date with `date +%F`. You need it as ISO (`2026-08-10`) and nothing else —
display dates are now formatted by the build, in each language, from that one value.

If `content/<Tractate>_<page>.md` already exists with today's `study_date`, skip to step 5
rather than rewriting it.

## Step 2 — Fetch the real text, both amudim, English and Hebrew

```bash
curl -s "https://www.sefaria.org/api/texts/<Tractate>.<page>a"
curl -s "https://www.sefaria.org/api/texts/<Tractate>.<page>b"
```

Each response has parallel arrays: `he` (Hebrew/Aramaic) and `text` (William Davidson
English). Strip HTML tags and read **every** segment of both amudim before writing. Base
every claim, name, and quotation on what is actually there.

Also glance at `<Tractate>.<page+1>a` for the one-line preview of tomorrow. If the page is
the last in the tractate, check tomorrow's entry via the calendars API rather than guessing.

## Step 3 — Write `content/<Tractate>_<page>.md`

Warm, clear, and specific, for a reader who has some Gemara background — not a beginner,
not a scholar. Match the tone of the previous sheets in `content/`.

### Front matter — the facts, declared once

```yaml
---
tractate: Chullin
page: 102
daf_he: חולין קב
chapter:
  n: 8
  name: Kol HaBasar
  gloss: all flesh
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

### Then the prose, as `## ` sections in this order

**(a) `## The big picture (read this first)`** — what today's page is really about, and why
it matters. A blockquote for the central idea works well.

**(b) `## Walking through the sugya, step by step`** — the argument in order, with `### `
subheadings per amud (`### 102a — …`). Bold the moves (**The objection.**, **The answer.**)
so it can be skimmed. Quote key Aramaic inline with its translation.

**(c) `## Key concepts & terms`** — a markdown table, `| Term | Meaning |`, with the
Hebrew/Aramaic term, its transliteration, and what it means on this daf.

**(d) `## Who's who in today's daf`** — for **every** sage named, a one-line ID: era
(**Tanna** / **Babylonian Amora** / **Eretz-Yisrael Amora**), approximate generation, where
they lived, and a teacher or famous disputant. Group by era if the list is long.
- Title tells: **Rav** = Babylonian Amora; **Rabbi** = Tanna or Eretz-Yisrael Amora;
  **Rebbi** alone = R' Yehuda HaNasi.
- Flag look-alikes explicitly: Rabbah (רבה) vs Rava (רבא); Mar bar Rav Ashi vs Rav Acha bar
  Rav Ashi; Rabbi Chiyya vs Rabbi Chiyya bar Abba; Rav Asi vs Rav Ashi.
- **If you are unsure about a minor figure, say so plainly.** Never invent a biography.

**(e) `## One line to carry with you`** — one memorable takeaway, as a blockquote.

**(f) `## Chazara — test yourself`** — **the last section**, and the reason to write it last:
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

8–10 questions. Exactly four options each, in the order a/b/c/d. Vary which letter is
correct. Separate major prose sections with `---`.

## Step 4 — Write `content/<Tractate>_<page>.es.md` (the Spanish sheet)

A full Spanish translation — same content, same structure, same depth. Not a summary.
Readers pick a language with the 🌐 toggle and the choice is remembered site-wide, so the
two sheets must stay in step.

### Front matter — only what differs

```yaml
---
lang: es
title: Daf Yomi — Julín 102 (חולין קב)
chapter:
  name: Kol HaBasar
  gloss: toda la carne
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
- Names use Spanish-Hebrew convention: Abaie, Rabá, Rava, Iehudá, Iojanán, Iehoshúa, Jiiá,
  Janiná, Itzjak, Erretz Israel, cohén, Guemará, baraita, mishná, halajá, trumá, suguiá.
  The tractate name in `title` is transliterated (`Julín`), but **file names never change** —
  they stay `content/Chullin_<page>.es.md`.
- Register: the warm, direct "tú" voice of the English sheet. Not academic Spanish.

### Spanish headings

| English | Spanish |
|---|---|
| The big picture (read this first) | El panorama general (leer esto primero) |
| Walking through the sugya, step by step | Recorriendo la suguiá, paso a paso |
| Key concepts & terms | Conceptos y términos clave |
| Who's who in today's daf | Quién es quién en el daf de hoy |
| One line to carry with you | Una línea para llevarte |
| Chazara — test yourself | Chazará — ponte a prueba |

Use `content/Chullin_98.es.md` and `content/Chullin_99.es.md` as the reference for tone and
terminology.

## Step 5 — Build

```bash
python3 build/build.py
```

That is the whole build. No arguments: the sunset pin and the site URL live in
`content/site.json`, so they cannot be forgotten on the command line.

It validates first and **writes nothing if validation fails** — it prints the file and the
problem. Fix the sheet and run it again. Warnings are advisory; errors are not.

Expect output like:

```
Built 5 daf (3 translated) + 1 legacy = 6 routed
languages: en, es
index.html seeded with Chullin_102 (2026-08-10)
rollover: sunset, location pinned to 31.7683,35.2137
```

Two things to know:

- **Dapim may already be built ahead of today.** That is fine and expected: the homepage
  rolls over at sunset on its own. Never delete a future daf's sheet.
- A `warn` about a missing `es` sheet for a future daf is only a reminder. A `warn` about
  *today's* daf missing Spanish means you skipped step 4 — go back and do it.

Optional, if a browser is available and you changed anything under `build/`:

```bash
python3 -m http.server 8891 --directory . & sleep 1
node build/check_browser.js       # needs puppeteer-core; skip if not installed
kill %1
```

## Step 6 — Publish

```bash
git add -A
git commit -m "<Tractate> <page> — <ISO date>"
git push origin main
```

Then confirm it went live (Pages takes 30–90s):

```bash
sleep 60
curl -s https://jocosiol.github.io/daf-yomi/ | grep -o '<title>[^<]*</title>'
```

It should name today's daf. If the push failed on a non-fast-forward, `git pull --rebase
origin main` and push again.

Finish with a two-line report: which daf was built, and whether the live site confirmed it.
