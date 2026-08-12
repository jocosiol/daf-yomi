# build/

Turns `content/` into the published site.

```bash
python3 build/build.py         # validate, then rebuild everything
python3 build/validate.py content   # just the checks
```

No arguments: the sunset pin and site URL live in `content/site.json`, so they cannot be
forgotten on the command line.

## Layout

| | |
|---|---|
| `sheet.py` | parses a sheet: YAML front matter, prose, and the quiz's `yaml` block |
| `validate.py` | the format contract, as checks. Exits nonzero; the build refuses to write |
| `i18n.py` | every string the build itself renders, plus per-language date formatting |
| `daftext.py` | caches the daf itself into `content/daf/`: Sefaria's text, and the printed page's URL. Not run by the build |
| `dafpdf.py` | where the printed page lives: tractate name -> shas.org's, and does it answer |
| `build.py` | renders the pages, the archive, the manifest and `assets/` |
| `templates/` | Jinja: `base.html`, `daf.html`, `archive.html` |
| `static/` | `daf.css`, `lang.js`, `tabs.js`, `cards.js`, `quiz.js`, `daf.js`, `speak.js`, `zman.js`, the `icon-*.png` set and `manifest.webmanifest` — copied to `assets/` with a content hash |
| `icons.py` | draws the home-screen icons into `static/`. Run by hand after a design change, not by the build |
| `check_browser.js` | drives the built site in headless Chrome (needs `puppeteer-core`) |
| `migrate_legacy.py` | one-off, already run; its inputs no longer exist. Deletable |

## How a daf is put together

`content/Chullin_98.md` is the source of record and carries the facts. A translation —
`content/Chullin_98.es.md` — carries only what is language-specific and **inherits**
`tractate`, `page`, `daf_he` and `study_date`. Validation rejects a translation that
restates them, so the two files cannot disagree about which day it is. Display dates are
formatted per language from the one ISO value.

Both languages are baked into a single page as `data-lang` blocks and switched by CSS on
the root `<html lang>`, which `lang.js` sets in `<head>` before the first paint. A daf with
no translation emits its English body **once**, marked `data-lang="en es"`, with a short
note above it.

Adding a language is a key in `i18n.LANGS` / `i18n.UI`, a `STR` entry in `quiz.js`,
`cards.js` and `zman.js`, and `<Tractate>_<page>.<lang>.md` sheets. Nothing hardcodes `es`.

## The four views

`tabs.js` switches between them and announces the one it opened as a `dafview` event; each
panel wakes itself up on that. **Learn** is the rendered sheet. **Chazara Quiz** is the
`yaml` block under `## Chazara`. **Flashcards** is the `| Term | Meaning |` table under
`## Key concepts`, read out of the same markdown the Learn view renders — the deck cannot
drift from the sheet, because the glossary is written once. A daf with fewer than
`build.MIN_CARDS` terms gets no deck and no tab. **The Daf** is the daf itself — the
printed page, or the text laid out as tzurat hadaf; below.

## The Daf

The other three views are things we wrote *about* the daf. This one is the daf, in two
readings of it, switched by a pair of chips at the top of the tab.

**Printed page** — the default — is the Vilna daf itself, one PDF per amud, served by
[shas.org](https://www.shas.org/daf-pdf/api/api-documentation.html). It is the whole page:
Gemara, Rashi, Tosafot, Mesoras HaShas, Ein Mishpat, Rabbeinu Gershom, the lot. It is
embedded in an iframe and the browser's own PDF viewer draws it. Not a scan, despite
appearances — the PDFs are typeset, with no images and 47 embedded font subsets, which
matters below.

Under each page are its **passages, line by line**: one row per Sefaria segment in printed
order, the Hebrew clamped to a single line, tapping one to open its English. That is there
because the obvious thing — tap a line *on the page* — cannot be built. Two independent
reasons: a cross-origin iframe hands us no events at all, and even rendering the PDF
ourselves with pdf.js would not help, because only 8 of those 47 font subsets carry a
`ToUnicode` map and of the 184 codepoints they map, 14 are Hebrew — the rest are legacy
Latin-1 slots (`È`, `Ó`, `˙`). The text is not machine-readable as Hebrew, so there is no
telling which words a click landed on; the best available would be to cluster the columns,
find the central block, and guess a segment from the click's height. A strip keyed to the
segment is exact, costs no dependency, and keeps the browser's own viewer with its zoom and
print. The Hebrew is written once, in the row's head, and unwraps when opened rather than
being repeated.

**Text** is the same daf rebuilt from Sefaria as tzurat hadaf — Gemara down the middle,
Rashi on the inner margin, Tosafot on the outer one. Which side is inner depends on the
leaf, and the two amudim swap accordingly: amud alef is a recto, so its spine is on the
left and Rashi sits left of the text; amud bet is its verso and mirrors it. This is the one
that has the translation, that a phone can render, and that a reader can search.

The two are independent, and the build offers only what each daf actually has: the last daf
of a tractate has no amud bet of either, and Shekalim, Kinnim and Middot are printed dapim
that Sefaria has no Bavli text for at all — a page, and no text.

```bash
python3 build/daftext.py Chullin 108   # one daf into content/daf/Chullin_108.json
python3 build/daftext.py --all         # whatever content/ is missing
python3 build/dafpdf.py --all          # check the tractate-name table against shas.org
```

**The build never fetches.** It runs on a laptop that is often only briefly awake, and
eight URLs per daf would turn a flaky connection into a broken site; a page printed in
Vilna in 1886 is also not going to change. So `daftext.py` caches it once under
`content/daf/` — the text, and the page's URL after checking that it answers 200 — and the
build reads what is there. A daf with nothing cached simply has no Daf tab, and the build
says which ones those are and how to fix it. **Run it after writing a sheet and before
building** — it is a step in `DAILY_PROMPT.md` for that reason.

`dafpdf.py` is only the naming and the check. shas.org wants Ashkenazi spellings, which no
rule derives from Sefaria's: Ketubot is `kesubos`, Bava Batra is `bava-basra`, Keritot is
`kereisos`. So it is a table of forty, and `--all` asks the API for the first daf of every
one of them — run it when a tractate is about to turn over, or after editing the table.
Its `exists()` reads only 400 and 404 as "no page"; anything else raises, because the first
version's blanket `except HTTPError: return False` turned a 406 the server was sending to
*every* request into "no printed page exists anywhere in Shas", reported as forty ordinary
absences. A feature that switches itself off has to be loud about it.

The text cache costs about 45 KB per daf, roughly doubling a built page (~65 KB → ~120 KB,
or ~34 KB over the wire once gzipped) and pays for the text mode and the line-by-line strip
both; the pages themselves cost nothing in the repo, since only their URL is stored. The
strip does emit the same Hebrew and English a second time — the two layouts have no DOM in
common — which is another 29 KB of markup, or ~5 KB gzipped. Shuffling nodes between the
modes to avoid that would be a lot of fragile JavaScript for 5 KB. Segments are positional: Sefaria numbers Rashi and Tosafot to the Gemara
segment they comment on, so a row of the layout is one passage with its own commentary. A
commentary with more segments than the Gemara has its tail folded into the last row rather
than dropped.

`daf.js` mostly just reveals what the build already wrote — the mode, the chips that show
and hide Rashi, Tosafot and the translation (every choice remembered site-wide), and the
folding of the margins into collapsible blocks once the columns have stacked on a narrow
screen. Nothing is hidden by the markup itself, so the folding is an addition rather than a
prerequisite. The columns are a right-to-left flex row rather than a grid, so hiding one
hands its width to the others by itself.

The one thing it actually *does* is set the pages' `src`, on the first open of the tab and
never on a page load. Two PDFs of ~140 KB each on every page view, from someone else's
server, for a tab most readers of a given page never open, would be rude as well as slow.
The full-size link in each caption works either way, and is the answer on a phone, where a
whole daf at 390 px is legible to nobody.

Two things the tab has to say for itself. The AI-provenance notices are true of every other
tab and false of this one, so both the top notice and the footer give way to a source notice
when it opens. And each mode carries its own credit: the pages are shas.org's, while the
Gemara and its translation are the William Davidson Talmud, **CC BY-NC 4.0** — that credit
is a licence condition, not a courtesy. Rashi and Tosafot are the Vilna edition, public
domain.

## Read aloud

`speak.js` puts a 🔊 button in every heading of the Learn sheet and reads the section under
it — heading first, then each paragraph, quote, list item and table row until the next
heading of the same or higher level, highlighting whichever one is being said. It uses the
browser's own speech synthesis, so nothing is generated at build time.

The voice is **chosen, not accepted**. Taking the browser's default — or the first voice
matching the language — gets you read Gemara by a joke: macOS lists Albert, Zarvox and Bad
News among its English voices, and offers "Eddy" for Spanish long before Mónica. `speak.js`
scores the list instead (known-good names first, a bonus for an `(Enhanced)` or `(Premium)`
build the reader has installed, a penalty for the novelties) and only scores, never filters,
so even a list of nothing but novelties yields a voice rather than silence. On this Mac that
lands on Samantha, Mónica and Carmit; install a premium voice in **System Settings →
Accessibility → Spoken Content** and the page picks it up on its own.

A Hebrew quotation is spoken by a Hebrew voice, and **skipped** where the browser has none
rather than handed to a voice that would spell it out — every quotation in these sheets is
followed by its translation. The voice follows the language of the *body*, which the build
stamps on each sheet as `data-speak-lang`: an untranslated daf reads in English even for a
reader whose chrome is Spanish.

### Why it stops sounding like a robot

Mostly by **not chopping the text up**. Every utterance boundary is a pause *and* a reset of
the voice's intonation to neutral, so a paragraph split into three stops sounding like
someone reading a paragraph. The first version capped utterances at 220 characters and spent
66 of them on a single section; a paragraph is now said in one breath. Only a voice that
synthesises over the network is chunked short, because that is the one that gets cut off
after a few seconds.

The rest is repairing what the page does for the eye and the ear cannot use:

- A **run of nothing but punctuation is dropped**, and that merges what it separated.
  `אֵין “בְּשֵׁלָה” אֶלָּא שְׁלֵימָה` arrived as five runs — the curly quotes are page
  language sitting inside a Hebrew phrase — and was read as five utterances, two of them a
  quotation mark spoken on its own. It is one phrase and is now said as one.
- An **em dash is silent** in most voices, so `beitzat efroach — an egg with a chick in it`
  arrived as one breathless phrase. It becomes a comma, which is the pause the sentence has
  on the page. `108a–108b` is a range, so it becomes `108a to 108b`, and `R' Yochanan` is a
  name, so it becomes `Rabbi Yochanan`.
- The **newline markdown leaves inside a table cell** was being read as a stumble:
  `What both agree . Where they split`. Space before punctuation is closed up.

What none of this can fix is the voice itself. macOS ships Samantha and a pile of novelties;
the free **(Enhanced)** and **(Premium)** voices are a different era of synthesis, and
`speak.js` already prefers one the moment it exists — **System Settings → Accessibility →
Spoken Content → System Voice → Manage Voices**. Genuinely natural speech means neural TTS,
which means pre-generating audio at build time: a paid API per character, and ~10–25 MB per
daf per language, which a git-backed Pages site cannot carry for long.

## Why the sheets look like this

The previous build scraped its metadata out of prose — a bold `Study date: Thu, 6 August
2026` line, and a quiz whose answer key sat in a separate section matched to questions by
number. That is why the daily prompt spent most of its length policing format, and why a
typo could silently drop a daf out of the homepage routing rather than fail loudly.

Now the facts are declared, the quiz's `correct` sits next to its options, and
`validate.py` fails the build instead of publishing something broken.

## Dependencies

`markdown`, `jinja2`, `pyyaml` (`pip3 install --user markdown jinja2 pyyaml`).
`run_daily.sh` preflights all three.

## Not yet under the pipeline

`Chullin_97.html` predates `content/` and has no markdown source. It is listed in
`content/legacy.json`, which keeps it in the archive and the routing while leaving the
built page alone. Regenerate it from Sefaria into `content/Chullin_97.md` and delete the
entry to bring it in.
