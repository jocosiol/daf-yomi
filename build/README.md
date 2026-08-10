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
| `build.py` | renders the pages, the archive, the manifest and `assets/` |
| `templates/` | Jinja: `base.html`, `daf.html`, `archive.html` |
| `static/` | `daf.css`, `lang.js`, `tabs.js`, `cards.js`, `quiz.js`, `speak.js`, `zman.js` — copied to `assets/` with a content hash |
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

## The three views

`tabs.js` switches between them and announces the one it opened as a `dafview` event; each
panel wakes itself up on that. **Learn** is the rendered sheet. **Chazara Quiz** is the
`yaml` block under `## Chazara`. **Flashcards** is the `| Term | Meaning |` table under
`## Key concepts`, read out of the same markdown the Learn view renders — the deck cannot
drift from the sheet, because the glossary is written once. A daf with fewer than
`build.MIN_CARDS` terms gets no deck and no tab.

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
