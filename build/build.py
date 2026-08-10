#!/usr/bin/env python3
"""Build the Daf Yomi site from content/.

  python3 build/build.py                    # validate, then rebuild everything
  python3 build/build.py --out /tmp/preview # build somewhere else to compare
  python3 build/build.py --no-validate      # skip the gate (local fiddling only)

Settings live in content/site.json, not in flags, so the sunset pin can no
longer be forgotten on the command line and silently change behaviour.

Output (flat at the repo root, so existing URLs keep working):
  Chullin_98.html    one page per daf, every language baked in — content only;
                     the chrome is in assets/
  index.html         the daf current at build time, plus a router that
                     self-corrects by date and rolls over at sunset
  archive.html       every daf, newest first
  dapim.json         the manifest, for anything else that wants it
  assets/            daf.css, lang.js, quiz.js, zman.js — served once and
                     cached across days instead of inlined into every page
"""
import argparse
import datetime
import filecmp
import glob
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import sys

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i18n                        # noqa: E402
import sheet as sheet_mod          # noqa: E402
import validate as validate_mod    # noqa: E402

REPO = os.path.dirname(HERE)
LETTERS = "abcd"
# Below this a deck is not worth a tab of its own; the table in Learn says it
# just as well. validate.py already warns under TERMS_MIN_ROWS.
MIN_CARDS = 3

# Hebrew, Aramaic and the Hebrew presentation forms, plus the punctuation that
# lives inside a quoted phrase (geresh, gershayim, maqaf, sof pasuq).
# Escapes, not literals: writing the presentation-forms endpoint as a literal
# glyph risks pasting a decomposed sequence, which silently turns this into a
# range spanning most of the BMP.
HEB_CHAR = "\u0590-\u05FF\uFB1D-\uFB4F"
HEB_RUN = re.compile(r"[{c}]+(?:[\s־׀׃׳״.,;:!?'\"()\[\]–—-]*[{c}]+)*".format(c=HEB_CHAR))
TAG = re.compile(r"(<[^>]+>)")
TABLE = re.compile(r"(<table\b.*?</table>)", re.S)

# The label the toggle shows is the language it switches TO.
SWITCH = {"en": {"label": "Español", "title": "Ver en español"},
          "es": {"label": "English", "title": "View in English"}}


def hebrew_spans(fragment):
    """Wrap runs of Hebrew in <span lang="he" dir="rtl">.

    The stylesheet has always had a :lang(he) rule, but nothing ever emitted
    the attribute — so Hebrew rendered in the Latin serif, and a quoted phrase
    followed by a comma could reorder on screen. Applied only to text between
    tags, never inside markup.
    """
    out = []
    for part in TAG.split(fragment):
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(HEB_RUN.sub(
                lambda m: f'<span lang="he" dir="rtl">{m.group(0)}</span>', part))
    return "".join(out)


def inline_md(text):
    """The small subset of markdown that appears inside quiz strings."""
    t = html_mod.escape(str(text).strip())
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return hebrew_spans(t)


def render_body(md_text):
    body = markdown.markdown(md_text, extensions=["tables", "sane_lists", "smarty"])
    body = hebrew_spans(body)
    # wide term tables must scroll inside themselves, not push the page sideways
    return TABLE.sub(r'<div class="table-scroll">\1</div>', body)


def quiz_payload(s):
    """A sheet's quiz in the shape quiz.js wants: `correct` is an index."""
    out = []
    for i, q in enumerate(s.quiz, 1):
        letter = str(q.get("correct", "")).strip().lower()
        out.append({
            "n": i,
            "q": inline_md(q.get("q", "")),
            "opts": [inline_md(o) for o in q.get("opts", [])],
            "correct": LETTERS.index(letter) if letter in LETTERS else 0,
            "why": inline_md(q.get("why", "")),
        })
    return out


def cards_payload(s):
    """The Key concepts table as a flashcard deck: [{"t": term, "m": meaning}].

    Read out of the same markdown table the Learn view renders, so the deck can
    never drift from the sheet — there is one glossary, written once.
    """
    rows = validate_mod.terms_table(s) or []
    return [{"t": inline_md(r[0]), "m": inline_md(" — ".join(c for c in r[1:] if c))}
            for r in rows if len(r) >= 2 and r[0].strip() and r[1].strip()]


def with_deck_cta(body_md, lang):
    """Splice a 'study these as flashcards' button under the glossary table.

    The deck has a tab like Learn and Quiz do, but the moment you actually want
    it is while reading the terms — so the button sits there too, and switches
    to the tab. Inserted as markdown (python-markdown passes a block of raw HTML
    through) rather than patched into the rendered fragment, which would mean
    parsing our own output back.
    """
    needle = validate_mod.TERMS_SECTION.get(lang, validate_mod.TERMS_SECTION[i18n.DEFAULT])
    span = validate_mod.section_span(body_md, needle)
    if not span:
        return body_md
    start, end = span
    seg = body_md[start:end]
    # above the horizontal rule that closes the section, not below it
    rule = re.search(r"(?:\s*^---\s*$\s*)+\Z", seg, re.M)
    at = start + (rule.start() if rule else len(seg.rstrip()))
    label = html_mod.escape(i18n.t(lang, "cards_cta"))
    return (f'{body_md[:at]}\n\n<p class="deck-cta">'
            f'<button class="btn ghost" type="button" data-open="cards">🃏 {label}</button>'
            f'</p>\n\n{body_md[at:]}')


def script_json(obj):
    """JSON for embedding in a <script> block.

    Escaping the slash in "</" means a string containing "</script>" cannot end
    the element early. \\u003c is still a valid JSON escape, so JSON.parse reads
    it back unchanged.
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def load_settings(content_dir):
    settings = {"site_url": "", "pin": None, "offset": 0}
    path = os.path.join(content_dir, "site.json")
    if os.path.exists(path):
        settings.update(json.load(open(path, encoding="utf-8")))
    return settings


def load_legacy(content_dir):
    """Pages that predate content/ and have no markdown source.

    They are already-built HTML sitting at the root; listing them here keeps
    them in the archive and the routing without the build having to glob
    *.html and guess.
    """
    path = os.path.join(content_dir, "legacy.json")
    if not os.path.exists(path):
        return []
    out = []
    for e in json.load(open(path, encoding="utf-8")):
        d = sheet_mod.as_date(e.get("study_date"))
        label = e.get("label") or os.path.splitext(e["file"])[0].replace("_", " ")
        out.append({
            "file": e["file"],
            "iso": d.isoformat() if d else "",
            "label": {l: (e.get("labels") or {}).get(l, label) for l in i18n.LANGS},
            "display": {l: i18n.fmt_date(d, l) for l in i18n.LANGS},
        })
    return out


def build_assets(out_dir):
    """Copy assets and return a name -> cache-busted URL map."""
    src = os.path.join(HERE, "static")
    dst = os.path.join(out_dir, "assets")
    os.makedirs(dst, exist_ok=True)
    urls = {}
    for name in sorted(os.listdir(src)):
        if name.startswith("."):
            continue
        data = open(os.path.join(src, name), "rb").read()
        shutil.copyfile(os.path.join(src, name), os.path.join(dst, name))
        urls[name] = f"assets/{name}?v={hashlib.sha256(data).hexdigest()[:8]}"
    return urls


def language_groups(s, has_cards=False):
    """Collapse languages onto the sheet each one actually renders.

    A daf with a Spanish translation yields two groups; one without yields a
    single group marked data-lang="en es", so an untranslated daf carries its
    English body once rather than twice.
    """
    order, by_variant = [], {}
    for lang in i18n.LANGS:
        v = s.variant(lang)
        if id(v) not in by_variant:
            by_variant[id(v)] = {"sheet": v, "langs": []}
            order.append(id(v))
        by_variant[id(v)]["langs"].append(lang)

    groups = []
    for key in order:
        g = by_variant[key]
        v = g["sheet"]
        body_md = with_deck_cta(v.body_md, v.lang) if has_cards else v.body_md
        groups.append({
            "langs": " ".join(g["langs"]),
            "lang": v.lang,
            "title_html": hebrew_spans(html_mod.escape(v.title)),
            "subtitle": hebrew_spans(v.subtitle),
            "learn_html": render_body(body_md),
            "tomorrow": v.tomorrow,
        })
    return groups


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=os.path.join(REPO, "content"))
    ap.add_argument("--out", default=REPO)
    ap.add_argument("--at", metavar="LAT,LON", help="override the sunset pin from site.json")
    ap.add_argument("--offset", type=int, help="override minutes after sunset")
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args()

    content, out_dir = args.content, args.out

    # ---- gate ----
    if not args.no_validate:
        rep, _ = validate_mod.validate(content)
        for w in rep.warnings:
            print(f"  warn   {w}")
        for e in rep.errors:
            print(f"  ERROR  {e}")
        if not rep.ok:
            sys.exit(f"\n{len(rep.errors)} error(s) — nothing was written.")

    settings = load_settings(content)
    if args.at:
        m = re.match(r"^\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*$", args.at)
        if not m:
            sys.exit("--at wants LAT,LON  e.g. --at 31.7683,35.2137")
        settings["pin"] = {"lat": float(m.group(1)), "lon": float(m.group(2))}
    if args.offset is not None:
        settings["offset"] = args.offset

    sheets = sheet_mod.load_all(content)
    if not sheets:
        sys.exit(f"No sheets found in {content}")

    os.makedirs(out_dir, exist_ok=True)
    asset_urls = build_assets(out_dir)
    env = Environment(
        loader=FileSystemLoader(os.path.join(HERE, "templates")),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True, lstrip_blocks=True,
    )
    env.globals["asset"] = lambda name: asset_urls.get(name, f"assets/{name}")

    # ---- manifest: the sources decide what exists, not a glob of the output ----
    entries = [{
        "file": s.out_name,
        "iso": s.iso or "",
        "label": {l: s.variant(l).label for l in i18n.LANGS},
        "display": {l: i18n.fmt_date(s.study_date, l) for l in i18n.LANGS},
    } for s in sheets] + load_legacy(content)
    entries.sort(key=lambda e: (e["iso"], e["label"][i18n.DEFAULT]))
    dapim = [{"f": e["file"], "d": e["iso"]} for e in entries if e["iso"]]

    def config(self_file=None, with_manifest=False):
        """Only index and archive need the manifest; a daf page needs the
        language list and nothing more."""
        cfg = {"langs": i18n.LANGS}
        if with_manifest:
            cfg.update(pin=settings["pin"], offset=settings["offset"], dapim=dapim)
        if self_file:
            cfg["self"] = self_file
        return script_json(cfg)

    common = {
        "langs": i18n.LANGS,
        "default_lang": i18n.DEFAULT,
        "ui": i18n.UI,
        "switch": SWITCH,
        "site_url": settings["site_url"],
    }
    daf_tpl = env.get_template("daf.html")

    def render_daf(s, is_index):
        quiz_by_lang = {l: quiz_payload(s.variant(l)) for l in i18n.LANGS}
        # A language with too thin a glossary is left out entirely rather than
        # given an empty deck, so cards.js falls back to English for it — the
        # same way an untranslated body does.
        cards_by_lang = {l: c for l, c in
                         ((l, cards_payload(s.variant(l))) for l in i18n.LANGS)
                         if len(c) >= MIN_CARDS}
        has_cards = bool(cards_by_lang)
        return daf_tpl.render(
            groups=language_groups(s, has_cards),
            untranslated=[l for l in i18n.LANGS if l != s.lang and l not in s.translations],
            page_title=s.title,
            description=s.summary,
            canonical="" if is_index else s.out_name,
            has_quiz=bool(s.quiz),
            quiz_json=script_json(quiz_by_lang),
            has_cards=has_cards,
            cards_json=script_json(cards_by_lang),
            is_index=is_index,
            is_archive=False,
            needs_zman=is_index,
            config_json=config(s.out_name if is_index else None, with_manifest=is_index),
            **common,
        )

    for s in sheets:
        with open(os.path.join(out_dir, s.out_name), "w", encoding="utf-8") as f:
            f.write(render_daf(s, is_index=False))

    # ---- index.html: whichever daf is current at build time ----
    today = datetime.date.today().isoformat()
    seed = next((s for s in reversed(sheets) if s.iso and s.iso <= today), sheets[0])
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_daf(seed, is_index=True))

    # ---- archive.html ----
    with open(os.path.join(out_dir, "archive.html"), "w", encoding="utf-8") as f:
        f.write(env.get_template("archive.html").render(
            entries=list(reversed(entries)),
            page_title=i18n.t(i18n.DEFAULT, "archive_title"),
            description=i18n.t(i18n.DEFAULT, "archive_desc"),
            canonical="archive.html",
            is_index=False, is_archive=True, needs_zman=True,
            config_json=config(with_manifest=True),
            **common,
        ))

    with open(os.path.join(out_dir, "dapim.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()

    # ---- stale output: report, never delete (a future daf must survive) ----
    expected = {e["file"] for e in entries} | {"index.html", "archive.html"}
    for p in sorted(glob.glob(os.path.join(out_dir, "*.html"))):
        base = os.path.basename(p)
        if base not in expected:
            print(f"  warn   {base} is at the root but has no source in content/ "
                  f"— delete it, or list it in content/legacy.json")

    # ---- a preview build leaves the published tree behind ----
    # Easy to edit static/, build only to --out to look at it, and commit: the
    # source moves, the served assets do not, and the site quietly runs the old
    # code. Say so, and name what is actually stale.
    # A brand-new asset has no published copy at all — that is the most stale a
    # file can be, so say so rather than dying in filecmp.
    def stale_asset(name):
        published = os.path.join(REPO, "assets", name)
        return (not os.path.exists(published) or
                not filecmp.cmp(os.path.join(HERE, "static", name), published, shallow=False))

    if os.path.abspath(out_dir) != os.path.abspath(REPO):
        stale = [n for n in sorted(asset_urls) if stale_asset(n)]
        print(f"\nPreview build — {out_dir}. The published tree at {REPO} was not touched.")
        if stale:
            print(f"  warn   {', '.join(stale)} differ(s) from assets/ there "
                  f"— rerun without --out before committing")

    where = (f"pinned to {settings['pin']['lat']},{settings['pin']['lon']}"
             if settings["pin"] else "per-visitor (browser timezone)")
    off = f" + {settings['offset']} min" if settings["offset"] else ""
    n_tr = sum(len(s.translations) for s in sheets)
    print(f"Built {len(sheets)} daf ({n_tr} translated) "
          f"+ {len(entries) - len(sheets)} legacy = {len(dapim)} routed")
    print(f"languages: {', '.join(i18n.LANGS)}")
    print(f"index.html seeded with {seed.slug} ({seed.iso})")
    print(f"rollover: sunset{off}, location {where}")
    if dapim:
        print(f"schedule: {dapim[0]['d']} … {dapim[-1]['d']}")


if __name__ == "__main__":
    main()
