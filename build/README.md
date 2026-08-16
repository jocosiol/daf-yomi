# build/

Turns `content/` into the published site.

```bash
python3 build/build.py              # validate, then rebuild into site/
python3 build/validate.py content   # just the checks
python3 -m http.server -d site 8891 # look at it
```

No arguments: the sunset pin and site URL live in `content/site.json`, so they cannot be
forgotten on the command line.

## Publishing

**The built site is not in this repo.** `build.py` writes `site/`, which is git-ignored, and
[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) rebuilds it from source on
every push to `main` and publishes it as a Pages artifact. Git holds `content/`, `build/` and
nothing that a build can regenerate.

It used to hold the output, flat at the root, and that does not scale. A page is 150–230 KB;
`index.html` is a *full copy* of the current daf and is rewritten every build; and one
template edit rewrites every page at once — commit `255eb12` touched fourteen pages to
reorder the tabs, and at three hundred dapim the same edit is sixty megabytes in a single
commit. A Shas cycle is 2,711 dapim. Building in CI keeps the history proportional to what is
actually written by hand, and takes the laptop off the critical path: a push is now the whole
publishing act.

Two consequences worth knowing:

- **Pages must be set to deploy from Actions** — Settings → Pages → Source → *GitHub Actions*.
  Left on "Deploy from a branch" the workflow still runs green while serving the old committed
  tree, which is the failure mode to watch for on the first deploy.
- **A daily `schedule:` rebuild exists**, and it is only about `index.html`'s seed — the daf
  that the raw HTML names before any JavaScript runs. The sunset rollover is still done in the
  browser from the baked manifest and needs no build.

Local builds write to the same `site/`, which is not cleaned between runs; a page whose sheet
you deleted lingers there and the build says so. CI always starts from an empty checkout.

## Layout

| | |
|---|---|
| `sheet.py` | parses a sheet: YAML front matter, prose, and the quiz's `yaml` block |
| `validate.py` | the format contract, as checks. Exits nonzero; the build refuses to write |
| `i18n.py` | every string the build itself renders, plus per-language date formatting |
| `daftext.py` | caches the daf itself into `content/daf/`: Sefaria's text, and the printed page's URL. Not run by the build |
| `dafpdf.py` | where the printed page lives: tractate name -> shas.org's, and does it answer |
| `build.py` | renders the pages, the archive, the manifest and `assets/` into `site/` |
| `templates/` | Jinja: `base.html`, `daf.html`, `archive.html` |
| `static/` | `daf.css`, `lang.js`, `tabs.js`, `cards.js`, `quiz.js`, `daf.js`, `speak.js`, `zman.js`, the `icon-*.png` set and `manifest.webmanifest` — the source of the chrome, copied to `site/assets/` with a content hash. Edit these, never the copies |
| `icons.py` | draws the home-screen icons into `static/`. Run by hand after a design change, not by the build |
| `check_browser.js` | drives the built site in headless Chrome (needs `puppeteer-core`) |
| `migrate_legacy.py` | one-off, already run; its inputs no longer exist. Deletable |

## How a daf is put together

`content/Chullin_98.md` is the source of record and carries the facts. A translation —
`content/Chullin_98.es.md` — carries only what is language-specific and **inherits**
`tractate`, `page`, `daf_he` and `study_date`. Validation rejects a translation that
restates them, so the two files cannot disagree about which day it is. Display dates are
formatted per language from the one ISO value.

Every language is baked into a single page as `data-lang` blocks and switched by CSS on
the root `<html lang>`, which `lang.js` sets in `<head>` before the first paint. A daf with
no Hebrew sheet emits its English body **once**, marked `data-lang="en he"`, with a short
note above it.

The site is English, Spanish and Hebrew, and the 🌐 button opens a menu of all of them —
it names the language on screen and ticks it in the list, rather than stepping to the next
one, which with three languages would hide the third behind a guess. Each item is written
in its own language, since that is the one its reader can read. Adding another is a key in
`i18n.LANGS` / `i18n.UI` / `i18n.NAME` /
`i18n.VIEW_IN`, a `STR` entry in `quiz.js`, `cards.js`, `zman.js` and `speak.js`, a section
list in `validate.REQUIRED_SECTIONS`, one `html[lang="xx"] [data-lang~="xx"]` line in
`daf.css`, and `<Tractate>_<page>.<lang>.md` sheets. Nothing hardcodes `es` or `he`.

### Right to left

`i18n.RTL` names the languages written the other way; `lang.js` puts `dir` on `<html>`
beside `lang`, so the whole page turns with the switch. The stylesheet uses logical
properties (`padding-inline-start`, `border-inline-start`, `text-align:start`) rather than
physical ones, so one rule serves both directions.

Direction follows the *text*, not the reader. A block carries its own `lang`/`dir` from the
build, so a Hebrew reader on an untranslated daf gets an English sheet that still reads
left to right inside a right-to-left page — and `quiz.js` and `cards.js` do the same, each
standing in the whole English quiz or deck rather than framing English questions in Hebrew
chrome. `hebrew_spans` leaves an RTL sheet alone for the same reason: it is already marked
`he`/`rtl`, and marking every run inside it again would cut each one off from the
punctuation between them.

## The three views

The tabs are the order the daf is meant to be learnt in — meet it, read it, review it — not
a menu of features:

| Tab | What is in it |
|---|---|
| 📖 **Introduction** | the big picture, the glossary, the deck built from it, and who's who |
| 📜 **The Daf** | the daf itself: the printed page, or the text as tzurat hadaf; below |
| 🎯 **Chazara** | the walkthrough, the grid, the line to carry — and then the test |

`tabs.js` switches between them and announces the one it opened as a `dafview` event; each
panel wakes itself up on that.

The two prose tabs are one sheet, cut in two. `build.split_body` cuts it at the
`## Walking through the sugya` heading — named per language in `validate.WALK_SECTION` — and
again at Who's who, so the deck can be dropped between the glossary and the sages. The
sheet decides where the cut falls by where it puts its sections; nothing in the build knows
which section is which beyond those headings.

The deck and the test are inside those panels rather than tabs of their own, because neither
is a thing you go to: the cards are the glossary you have just read, and the test is what
you do at the end of the review. **Flashcards** is the `| Term | Meaning |` table under
`## Key concepts`, read out of the same markdown the Introduction renders — the deck cannot
drift from the sheet, because the glossary is written once. A daf with fewer than
`build.MIN_CARDS` terms gets no deck at all. The test is the `yaml` block under
`## Chazara`, which `sheet.split_quiz` lifts out of the body.

## The Daf

The other two views are things we wrote *about* the daf. This one is the daf, in two
readings of it, switched by a pair of chips at the top of the tab.

**Printed page** — the default — is the Vilna daf itself, one PDF per amud, served by
[shas.org](https://www.shas.org/daf-pdf/api/api-documentation.html). It is the whole page:
Gemara, Rashi, Tosafot, Mesoras HaShas, Ein Mishpat, Rabbeinu Gershom, the lot. It is
embedded in an iframe and the browser's own PDF viewer draws it. Not a scan, despite
appearances — the PDFs are typeset, with no images and 47 embedded font subsets, which
matters below.

Under each page are its **passages, line by line**: one row per Sefaria segment in printed
order, the Hebrew clamped to a single line, tapping one to open its English (in the English
view — below). That is there
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

### The translation is English, and only English

Both readings carry Sefaria's translation, and there is only the one — Steinsaltz in
English. To a reader who asked for Spanish or Hebrew that is not a translation of anything
they asked for, it is a third language in the middle of the daf, so **outside the English
view it is not shown at all**: not the column in the text mode, not the line each passage
opens onto under the printed page, and not the chip that would ask for it. The Hebrew and
Aramaic of the daf, its Rashi and its Tosafot are of course untouched — they are the daf.

Three consequences, and each is handled where it belongs:

- `daf.css` hides the translation and the chip on `html:not([lang="en"])`, so the rule holds
  whether or not `daf.js` ran. This is the one place in the stylesheet that names the
  language the translation is in; adding a fourth site language needs nothing here.
- `daf.js` does what a stylesheet cannot. A remembered "show English" is not honoured; the
  bar goes if hiding the chip leaves it with nothing but its label (a daf with no margins);
  and the passages under the printed page stop folding — they fold in order to open onto
  their English, and clamped to one line with nothing to open they would hide the daf behind
  a control that reveals nothing. It reads which language the translation is in off the
  markup (`lang` on `.g-en` / `.line-body`) rather than repeating it, and redoes all of this
  on `daflang`, since the language can change without leaving the tab.
- `i18n.py` drops the promise from the copy in those languages: the Spanish and Hebrew
  `daf_intro_scan` and `daf_lines` say what the strip under the page *is* — the text of the
  daf, passage by passage — instead of offering an English the reader will not be shown.

The Davidson credit stays in every language regardless: the Hebrew text of the Gemara comes
from the same **CC BY-NC 4.0** edition as the translation, and that credit is a licence
condition, not a courtesy.

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

`speak.js` puts a 🔊 button in every heading of the written sheet — both prose tabs — and
reads the section under
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

## Feedback

Under the footer notice on every daf, and at the foot of the archive, is a
**Found a mistake? Tell me** link. The notice says the sheet can be wrong; this
is the reply to it, which is why it sits directly beneath.

It is a `mailto:` and nothing else — the site is static files on Pages, so a form
would mean a third-party endpoint, an account and a cross-origin POST from a page
that currently makes none. The address is `feedback_email` in `content/site.json`;
`null` removes the link everywhere, and the build says which of the two it did
rather than leaving an absent link to look like an absent feature. An address
without an `@` fails the build instead of publishing a link that goes nowhere.

The mail arrives prefilled. `feedback_queries` bakes one per language, the same
way every other translated string on the page is baked. Only the prompt is in the
reader's language; the subject and the trailer that names the page are English
whatever the page is, because they are read by whoever opens the inbox — and a
subject that changed with the sender's language could not be filtered on. The
trailer's URL is the daf's own permalink even when the reader was on the homepage,
which is a different daf tomorrow, and carries `?lang=` so opening it lands on the
sheet they were actually reading.

    ✉️ Found a mistake? Tell me
    →  To:      dafyomi@example.com
       Subject: Daf Yomi feedback — Chullin 111
       Body:    What is wrong, or what is missing? …

                — Chullin 111 (en)
                https://jocosiol.github.io/daf-yomi/Chullin_111.html?lang=en

### The address is not in the page

An address published in the markup of every page is an address that gets
harvested, so the HTML carries the prefilled mail with nobody to send it to: the
link has no `href`, only its subject and body in `data-q`. The address is in the
config block as hex, XOR'd with a key written in front of it (`hide_email`), and
`feedback.js` joins the two on load.

Obfuscation, not secrecy — `feedback.js` is served to everyone, so anything that
executes it can read the address back, and it has to be able to: the mail client
is the thing that opens it. What it stops is the crawler that regexes HTML for
`something@something`, which is what actually collects addresses at this scale.
Withholding it until someone writes needs a server to write *to* — a form
endpoint holding the address on its side, which is a third party, an account and
a cross-origin POST. Still use an alias you can retire.

The key is fixed rather than per-build, because this repo is the web server: a
random key would rewrite the address in every page in git every morning and show
up as 2,700 changed files.

The block is hidden in the markup and revealed by the script, rather than shown
and then repaired. With JavaScript off the link would have nowhere to go, and an
invitation that does nothing when tapped is worse than none. It is the one part
of the sheet that needs JS, which is the price of keeping the address out.

What the link does **not** carry is which tab was open — the prompt asks for the
section instead.

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

`content/legacy/Chullin_97.html` predates `content/` and has no markdown source — it is the
one piece of HTML in this repo that is a *source*, since nothing can regenerate it. It is
listed in `content/legacy.json`, which keeps it in the archive and the routing, and the build
copies it to the published root beside the pages it renders. A listed file that is missing
fails the build rather than publishing an archive that links to a 404. Regenerate it from
Sefaria into `content/Chullin_97.md`, delete the HTML and drop the entry to bring it in.
