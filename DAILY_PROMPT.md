# Daily Daf Yomi build — run this whole pipeline, unattended

You are running non-interactively in the repo `/Users/moshecosio/daf-yomi`
(a clone of `jocosiol/daf-yomi`, published at https://jocosiol.github.io/daf-yomi/).

Work through steps 1–5 in order, then stop. Do not ask questions — make reasonable
decisions and proceed. Do not skip the Sefaria fetch: accuracy comes from the real text,
never from memory.

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
`displayValue.en` — e.g. `"Chullin 98"`. That gives `<Tractate>` and `<page>`.

**The `timezone=Asia/Jerusalem` parameter is required** — without it Sefaria answers in its
own default timezone and you will get yesterday's daf.

Confirm the local date with `date` and note it in two forms:
- ISO, for your own use: `2026-08-06`
- Display, for the sheet: `Thu, 6 August 2026`  (`date "+%a, %-d %B %Y"`)

If `<Tractate>_<page>.md` already exists and its study date line already matches today,
you may reuse it — skip to step 4 rather than rewriting it.

## Step 2 — Fetch the real text, both amudim, English and Hebrew

```bash
curl -s "https://www.sefaria.org/api/texts/<Tractate>.<page>a"
curl -s "https://www.sefaria.org/api/texts/<Tractate>.<page>b"
```

Each response has parallel arrays: `he` (Hebrew/Aramaic) and `text` (William Davidson
English). Strip HTML tags and read **every** segment of both amudim before writing. Base
every claim, name, and quotation on what is actually there.

Also glance at `<Tractate>.<page+1>a` for the one-line preview of tomorrow's daf. If the
page is the last in the tractate, the calendar's next entry starts a new tractate — check
tomorrow's date via the calendars API instead of guessing.

## Step 3 — Write `<Tractate>_<page>.md`

Warm, clear, and specific, for a reader who has some Gemara background — not a beginner,
not a scholar. The tone to match is the previous days' sheets in this folder.

### The format is a contract with the build scripts. Follow it exactly.

```markdown
# Daf Yomi — <Tractate> <page> (<Hebrew tractate name> <Hebrew page numeral>)

**Chapter <n>: *<Chapter Name>* (<short gloss>) · Study date: <Display Date>**
```

- The `# ` line becomes the page title. The `**Chapter …**` line becomes the subtitle —
  it **must** start with `**Chapter` and **must** contain the literal text
  `Study date: <Display Date>`. `build_site.py` parses that date to decide which daf is
  "today", so a malformed date line silently drops the daf out of the homepage routing.
- Get the chapter number and name from the tractate's structure (Chullin ch. 7 is
  *Gid HaNasheh*, 89b–103b; ch. 8 *Kol HaBasar* begins 103b). Sefaria's `heRef` field
  gives you the Hebrew page numeral, e.g. `חולין צ״ח א` → use `חולין צח`.

Then these sections, as `## ` headings, in this order:

**(a) `## The big picture (read this first)`** — what today's page is really about, and
why it matters. A blockquote for the central idea works well.

**(b) `## Walking through the sugya, step by step`** — the argument in order, using `### `
subheadings per amud (e.g. `### 98a — …`, `### 98b — …`). Bold the moves
(**The objection.**, **The answer.**) so it can be skimmed. Quote the key Aramaic phrases
inline with their translation.

**(c) `## Key concepts & terms`** — a markdown table, `| Term | Meaning |`, with the
Hebrew/Aramaic term, its transliteration, and what it means on this daf.

**(d) `## Who's who in today's daf`** — for **every** sage named on the daf, a bulleted
one-line ID: era (**Tanna** / **Babylonian Amora** / **Eretz-Yisrael Amora**), approximate
generation, where they lived, and a teacher or famous disputant. Group by era if the list
is long.
- Use the title tells: **Rav** = Babylonian Amora; **Rabbi** = Tanna or Eretz-Yisrael
  Amora; **Rebbi** standing alone = R' Yehuda HaNasi.
- Flag look-alike names explicitly, e.g. Rabbah (רבה) vs Rava (רבא); Mar bar Rav Ashi vs
  Rav Acha bar Rav Ashi; Rabbi Chiyya vs Rabbi Chiyya bar Abba; Rav Asi vs Rav Ashi.
- **If you are unsure about a minor figure, say so plainly** ("a genuinely obscure figure;
  I would not want to guess at his generation"). Never invent a biography.

**(e) `## Chazara — test yourself`** — 8–10 multiple-choice questions, no answers shown.
The exact shape, including the blank line between question and options:

```markdown
**1. The question text, ending in a question mark?**

- (a) First option.
- (b) Second option.
- (c) Third option.
- (d) Fourth option.
```

Always four options `(a)`–`(d)`, always numbered `**1.` … `**10.`, always a blank line
after the bold question. Vary which letter is correct across the set. Don't use `**bold**`
inside a question line — it breaks the parser.

**(f) `## One line to carry with you`** — one memorable takeaway, as a blockquote.

**(g)** Immediately after it, a one-line italic preview of tomorrow:
`*Tomorrow (<D Mon YYYY>): <Tractate> <page+1> — …*`

**(h) `## Chazara — answer key`** — **the very last section on the page.** One line per
question, in this exact shape:

```markdown
1. **(b)** — one-line reason the answer is right.
```

The letter must be inside the parentheses inside the bold: `**(b)**`. Every question in
(e) needs a matching line here, or it is dropped from the quiz.

Separate major sections with `---`.

## Step 4 — Build

```bash
python3 sheet_to_web.py <Tractate>_<page>.md <Tractate>_<page>.html
python3 build_site.py . <Tractate>_<page>.html <Tractate> <page> --at 31.7683,35.2137
```

**The `--at 31.7683,35.2137` is required.** `index.html` rolls over to the next daf at *sunset*,
not midnight, and that flag pins sunset to Jerusalem so the homepage always agrees with the
`timezone=Asia/Jerusalem` calendar you read in step 1. Omit it and the page falls back to guessing
each visitor's location from their browser timezone — a silent behaviour change. To roll over at
nightfall instead, add `--offset 40` (minutes after sunset).

Because rollover is automatic, **dapim may already be built ahead** of today. That is fine: this
build re-seeds `index.html` from whichever daf is current and leaves the future ones in place.
Never delete a future daf's `.md` or `.html`.

Write the HTML to **exactly** `<Tractate>_<page>.html` — never a temporary name in this
folder, because `build_site.py` globs every `*.html` at the root and a stray file becomes a
bogus archive entry.

`sheet_to_web.py` prints the question count. **Verify it says 8–10.** If it says fewer than
you wrote, a question or an answer-key line didn't match the format above — fix the
markdown and rebuild. Then sanity-check:

```bash
python3 - <<'PY'
import re, json
h = open('index.html', encoding='utf-8').read()
q = json.loads(re.search(r'const QUIZ = (\[.*?\]);\n', h, re.S).group(1))
print(len(q), "questions;",
      sum(1 for x in q if len(x['opts']) == 4 and x['correct'] in x['opts'] and x['why']),
      "fully formed")
print(re.search(r'<div class="sub">(.*?)</div>', h).group(1))
PY
```

## Step 5 — Publish

```bash
git add -A
git commit -m "<Tractate> <page> — <Display Date>"
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
