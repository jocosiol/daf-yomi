# daf-yomi

A daily Daf Yomi study sheet, in English, Spanish and Hebrew —
**<https://jocosiol.github.io/daf-yomi/>**

Each daf gets three tabs, in the order it is meant to be learnt: the big picture and the
glossary, then the daf itself (the printed Vilna page from shas.org, or the text rebuilt as
tzurat hadaf from Sefaria), then a walkthrough of the sugya and a test. The homepage rolls
over to the next daf at sunset on its own, in the browser, from a manifest baked into every
page.

## Where the site comes from

**This repo holds sources. The built site is not in it.**

```
content/     the sheets — Chullin_104.md, .es.md, .he.md — and the cached daf text
build/       the build: templates, stylesheet, scripts, and the validator
site/        the built site. git-ignored; produced by the build, published by CI
```

`build/build.py` renders `content/` into `site/`, and
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) does that on every push to
`main` and publishes the result as a GitHub Pages artifact. Committing the output does not
scale — a page is 150–230 KB, and a Shas cycle is 2,711 dapim — so nothing a build can
regenerate is tracked here.

```bash
pip3 install --user markdown jinja2 pyyaml
python3 build/build.py               # validate, then build into site/
python3 -m http.server -d site 8891  # look at it
```

Full detail, and the reasoning behind most of it, is in [`build/README.md`](build/README.md).

## Where the sheets come from

The sheets are written by Claude Code, unattended. `run_daily.sh` runs on a Mac under
launchd, feeds it [`DAILY_PROMPT.md`](DAILY_PROMPT.md), and pushes; the job tops up a buffer
a week deep rather than racing the calendar, because the laptop is often switched off.
Every sheet is built from the real text fetched from Sefaria, never from memory.

They are not reviewed by a person before they go up. Every page says so, and carries a
"found a mistake?" link.

## Credits

The Hebrew text of the Gemara and its English translation are the William Davidson Talmud,
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), via
[Sefaria](https://www.sefaria.org). Rashi and Tosafot are the Vilna edition, public domain.
The printed pages are served by [shas.org](https://www.shas.org).
