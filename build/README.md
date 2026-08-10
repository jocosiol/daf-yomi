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

A Hebrew quotation is spoken by a Hebrew voice, and **skipped** where the browser has none
rather than handed to a voice that would spell it out — every quotation in these sheets is
followed by its translation. The voice follows the language of the *body*, which the build
stamps on each sheet as `data-speak-lang`: an untranslated daf reads in English even for a
reader whose chrome is Spanish. Text is broken at sentence ends because a long utterance
gets cut off mid-word.

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
