#!/usr/bin/env python3
"""Build the Daf Yomi site from content/.

  python3 build/build.py                    # validate, then rebuild into site/
  python3 build/build.py --out /tmp/preview # build somewhere else to compare
  python3 build/build.py --no-validate      # skip the gate (local fiddling only)

Settings live in content/site.json, not in flags, so the sunset pin can no
longer be forgotten on the command line and silently change behaviour.

Output — flat inside site/, which is the published root, so existing URLs keep
working. site/ is git-ignored: the site is built and deployed by
.github/workflows/deploy.yml from the sources, never committed. See the
"Publishing" section of build/README.md for why.

  Chullin_98.html    one page per daf, every language baked in — content only;
                     the chrome is in assets/
  index.html         the daf current at build time, plus a router that
                     self-corrects by date and rolls over at sunset
  archive.html       every daf, newest first
  dapim.json         the manifest, for anything else that wants it
  assets/            daf.css, lang.js, quiz.js, zman.js — served once and
                     cached across days instead of inlined into every page
  Chullin_97.html    copied verbatim from content/legacy/ — see load_legacy
"""
import argparse
import datetime
import glob
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import sys
import urllib.parse

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daftext                     # noqa: E402
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
# The section sign Sefaria's English opens a new sugya with (see new_sugya).
SUGYA_RE = re.compile(r"^\s*§\s*")

# The 🌐 picker's menu: every language, each named in itself. Unlike everything
# else the build renders this is not per-display-language — a language's own
# name is the same string whatever the page around it is currently in — so it is
# one list, emitted once, rather than a data-lang block per language.
LANG_MENU = [{"code": l, "name": i18n.NAME[l], "title": i18n.VIEW_IN[l]}
             for l in i18n.LANGS]


def hebrew_spans(fragment, lang=i18n.DEFAULT):
    """Wrap runs of Hebrew in <span lang="he" dir="rtl">.

    The stylesheet has always had a :lang(he) rule, but nothing ever emitted
    the attribute — so Hebrew rendered in the Latin serif, and a quoted phrase
    followed by a comma could reorder on screen. Applied only to text between
    tags, never inside markup.

    A sheet written in Hebrew is skipped entirely: the whole block is already
    marked he/rtl by the template, and marking every run inside it again would
    isolate each one from the punctuation between them — the reverse of what
    this is for.
    """
    if i18n.is_rtl(lang):
        return fragment
    out = []
    for part in TAG.split(fragment):
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(HEB_RUN.sub(
                lambda m: f'<span lang="he" dir="rtl">{m.group(0)}</span>', part))
    return "".join(out)


def inline_md(text, lang=i18n.DEFAULT):
    """The small subset of markdown that appears inside quiz strings."""
    t = html_mod.escape(str(text).strip())
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return hebrew_spans(t, lang)


def render_body(md_text, lang=i18n.DEFAULT):
    body = markdown.markdown(md_text, extensions=["tables", "sane_lists", "smarty"])
    body = hebrew_spans(body, lang)
    # wide term tables must scroll inside themselves, not push the page sideways
    return TABLE.sub(r'<div class="table-scroll">\1</div>', body)


def quiz_payload(s):
    """A sheet's quiz in the shape quiz.js wants: `correct` is an index."""
    out = []
    for i, q in enumerate(s.quiz, 1):
        letter = str(q.get("correct", "")).strip().lower()
        out.append({
            "n": i,
            "q": inline_md(q.get("q", ""), s.lang),
            "opts": [inline_md(o, s.lang) for o in q.get("opts", [])],
            "correct": LETTERS.index(letter) if letter in LETTERS else 0,
            "why": inline_md(q.get("why", ""), s.lang),
        })
    return out


def cards_payload(s):
    """The Key concepts table as a flashcard deck: [{"t": term, "m": meaning}].

    Read out of the same markdown table the Learn view renders, so the deck can
    never drift from the sheet — there is one glossary, written once.
    """
    rows = validate_mod.terms_table(s) or []
    return [{"t": inline_md(r[0], s.lang),
             "m": inline_md(" — ".join(c for c in r[1:] if c), s.lang)}
            for r in rows if len(r) >= 2 and r[0].strip() and r[1].strip()]


def new_sugya(en):
    """Sefaria's § — a passage that opens a new topic — said in words.

    Steinsaltz marks the start of a sugya with a bare section sign, which means
    nothing to a reader who has not learnt to read Sefaria. It carries real
    information (this is where one discussion ends and the next begins), so it
    is kept and labelled rather than dropped. Only ever leading: the marker
    introduces a passage, it never appears inside one.
    """
    return SUGYA_RE.sub('<span class="sugya">new sugya</span>', en or "", count=1)


def daf_payload(data):
    """A cached daf, plus what the Daf tab should actually offer.

    Every control is built from what the daf turned out to have rather than from
    a fixed list: a tractate with no Tosafot must not be given a Tosafot switch,
    there is nothing to translate on a daf Sefaria has not translated, and the
    two modes are independent — Shekalim has a printed page and no Bavli text on
    Sefaria, and the last daf of a tractate has no amud bet of either.
    """
    if not data:
        return None
    # Done here rather than in the cache, so the wording is the build's to change
    # and no daf has to be fetched again to change it.
    data = dict(data, amudim=[
        dict(a, segments=[dict(s, en=new_sugya(s["en"])) for s in a["segments"]])
        for a in data["amudim"]])
    segments = [s for a in data["amudim"] for s in a["segments"]]
    return dict(data,
                has_rashi=any(s["rashi"] for s in segments),
                has_tosafot=any(s["tosafot"] for s in segments),
                has_en=any(s["en"] for s in segments),
                has_text=bool(segments),
                has_scan=any(a.get("pdf") for a in data["amudim"]))


def split_body(body_md, lang):
    """Cut a sheet into the three pieces the two prose tabs are built from.

    The page is read in one order — meet the daf, read the daf, review it — and
    the tabs are that order: **Introduction** is everything above the
    walkthrough (the big picture, the glossary, who's who), the Daf itself sits
    between them, and **Chazara** is the walkthrough and everything after it.
    The cut is the walkthrough heading, so a sheet decides where it falls by
    where it puts its sections; validate.py names the headings that mark it.

    Who's who comes back separately from the rest of the Introduction so the
    deck can be dropped between the two: the terms are read, then turned into
    cards, then the sages. Returned as markdown rather than rendered, so each
    piece is still one parse of a well-formed document.

    A sheet missing either heading degrades instead of failing — whatever is
    not found leaves its piece empty, and the rest keeps its place.
    """
    def cut_at(md, table):
        needle = table.get(lang, table[i18n.DEFAULT])
        return validate_mod.section_start(md, needle)

    # The rule a section ends with divides it from the next one. Where the cut
    # falls there is no next one — the piece ends, and the gap between two cards
    # says it better than a line drawn inside one.
    def trim(md):
        return re.sub(r"(?:\s*^---\s*$)+\s*\Z", "\n", md, flags=re.M)

    at = cut_at(body_md, validate_mod.WALK_SECTION)
    head, chazara = (body_md[:at], body_md[at:]) if at is not None else (body_md, "")
    at = cut_at(head, validate_mod.WHO_SECTION)
    intro, who = (head[:at], head[at:]) if at is not None else (head, "")
    return trim(intro), trim(who), trim(chazara)


def script_json(obj):
    """JSON for embedding in a <script> block.

    Escaping the slash in "</" means a string containing "</script>" cannot end
    the element early. \\u003c is still a valid JSON escape, so JSON.parse reads
    it back unchanged.
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


FEEDBACK_SUBJECT = "Daf Yomi feedback — {what}"
# XOR'd against the address before it is written out, and written in front of it
# so feedback.js reads it back rather than carrying a copy of it. Fixed, not
# random, so that the same sources build the same bytes: a scheduled rebuild
# that changed nothing would otherwise produce a different page every day, and
# "did this change anything?" would stop being answerable with diff.
MAIL_KEY = 0x2f


def hide_email(email):
    """The address as hex, each byte XOR'd with a key stored in front of it.

    Not encryption, and not meant to be: anything that runs the page's
    JavaScript gets the address back, which is the point — the reader's mail
    client has to be able to open it. What it defeats is the thing that actually
    harvests addresses, a crawler that reads the HTML and regexes it for
    something@something. That address would otherwise sit in the markup of every
    page on the site, in triplicate.

    Truly withholding it until someone writes needs a server to write *to* — a
    form endpoint that holds the address on its side. That is a third party, an
    account and a cross-origin POST; this is the static-site answer.
    """
    return "%02x" % MAIL_KEY + "".join(
        "%02x" % (b ^ MAIL_KEY) for b in email.encode("utf-8"))


def feedback_queries(email, what, url):
    """{lang: mailto query} for the "found a mistake?" link, or None if unset.

    The query only — subject and body, no address. feedback.js joins the two on
    load, so the HTML carries a prefilled mail with nobody to send it to.

    Baked one per language, like every other translated string on the page: the
    CSS has already picked the reader's language by the time they see the link,
    so nothing here has to be assembled per reader.

    The mail is addressed to one inbox, so the subject and the trailer that says
    which page it came from are English whatever the page is — the recipient does
    not read three languages, and a subject that changes with the sender's
    language cannot be filtered on. Only the prompt is translated, because it is
    the one line the *sender* reads.

    `what` names the page for both, and stays English for the same reason: it is
    the tractate and page as the repo spells them, not the reader's label. The
    URL is the daf's own permalink even on the homepage, which is a different
    daf tomorrow.
    """
    if not email:
        return None
    out = {}
    for lang in i18n.LANGS:
        # ?lang= so opening the link lands on the sheet the sender was reading,
        # whatever the recipient's own saved language is.
        where = f"{url}?lang={lang}" if url else ""
        body = (f"{i18n.t(lang, 'feedback_prompt')}\n\n\n"
                f"— {what} ({lang})\n{where}\n")
        out[lang] = urllib.parse.urlencode(
            {"subject": FEEDBACK_SUBJECT.format(what=what), "body": body},
            # quote, not quote_plus: a "+" in a mailto body is read literally by
            # some clients and as a space by others, so encode spaces as %20 and
            # leave no plus signs to be guessed at.
            quote_via=urllib.parse.quote, safe="/:")
    return out


def load_settings(content_dir):
    settings = {"site_url": "", "pin": None, "offset": 0, "feedback_email": None}
    path = os.path.join(content_dir, "site.json")
    if os.path.exists(path):
        settings.update(json.load(open(path, encoding="utf-8")))
    return settings


def load_legacy(content_dir):
    """Pages that predate content/ and have no markdown source.

    They are already-built HTML, kept in content/legacy/ because they are the
    only HTML in this repo that is a *source*: nothing can regenerate them.
    Listing them here keeps them in the archive and the routing without the
    build having to glob *.html and guess, and copy_legacy puts them back at
    the published root beside the pages that do get built.
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


def copy_legacy(content_dir, out_dir, entries):
    """Put the source-less pages at the published root, verbatim.

    Fatal if one is missing: it is listed in the archive and routed to by every
    page's manifest, so a build that quietly omitted it would publish a link to
    a 404 on the whole site rather than on one page.
    """
    for e in entries:
        src = os.path.join(content_dir, "legacy", e["file"])
        if not os.path.exists(src):
            sys.exit(f"content/legacy.json lists {e['file']}, but {src} does not "
                     f"exist — restore it, or drop the entry.")
        shutil.copyfile(src, os.path.join(out_dir, e["file"]))


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


def language_groups(s):
    """Collapse languages onto the sheet each one actually renders.

    A daf with a Spanish translation yields two groups; one without yields a
    single group marked data-lang="en es", so an untranslated daf carries its
    English body once rather than twice.

    Each group carries its sheet already cut into the pieces the tabs place
    (see split_body), because the cut is per language: the heading that marks
    it is written in the language of the sheet.
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
        intro_md, who_md, chazara_md = split_body(v.body_md, v.lang)
        groups.append({
            "langs": " ".join(g["langs"]),
            "lang": v.lang,
            # The direction of the sheet, which is not always the reader's: a
            # Hebrew reader on an untranslated daf gets the English sheet, and
            # that block has to stay left-to-right inside an RTL page.
            "dir": i18n.dir_of(v.lang),
            "title_html": hebrew_spans(html_mod.escape(v.title), v.lang),
            "subtitle": hebrew_spans(v.subtitle, v.lang),
            "intro_html": render_body(intro_md, v.lang),
            "who_html": render_body(who_md, v.lang) if who_md.strip() else "",
            "chazara_html": render_body(chazara_md, v.lang) if chazara_md.strip() else "",
            "tomorrow": v.tomorrow,
        })
    return groups


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=os.path.join(REPO, "content"))
    ap.add_argument("--out", default=os.path.join(REPO, "site"))
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

    # A typo here would publish a "tell me" link that silently goes nowhere on
    # every page, which is worse than having no link at all.
    email = str(settings.get("feedback_email") or "").strip()
    if email and ("@" not in email or " " in email):
        sys.exit(f"feedback_email in content/site.json is not an address: {email!r}")

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
    legacy = load_legacy(content)
    copy_legacy(content, out_dir, legacy)
    entries = [{
        "file": s.out_name,
        "iso": s.iso or "",
        "label": {l: s.variant(l).label for l in i18n.LANGS},
        "display": {l: i18n.fmt_date(s.study_date, l) for l in i18n.LANGS},
    } for s in sheets] + legacy
    entries.sort(key=lambda e: (e["iso"], e["label"][i18n.DEFAULT]))
    dapim = [{"f": e["file"], "d": e["iso"]} for e in entries if e["iso"]]

    def config(self_file=None, with_manifest=False):
        """Only index and archive need the manifest; a daf page needs the
        language list and nothing more."""
        cfg = {"langs": i18n.LANGS, "rtl": i18n.RTL}
        # The feedback address, obscured — once per page, since the three links
        # share it. See hide_email.
        if email:
            cfg["mail"] = hide_email(email)
        if with_manifest:
            cfg.update(pin=settings["pin"], offset=settings["offset"], dapim=dapim)
        if self_file:
            cfg["self"] = self_file
        return script_json(cfg)

    common = {
        "langs": i18n.LANGS,
        "default_lang": i18n.DEFAULT,
        "default_dir": i18n.dir_of(i18n.DEFAULT),
        "ui": i18n.UI,
        "lang_menu": LANG_MENU,
        "site_url": settings["site_url"],
    }

    def page_url(name):
        """A page's absolute URL, or its filename when site_url is unset — a
        local build still produces a mailto that says which page it came from."""
        base = settings["site_url"].rstrip("/")
        return f"{base}/{name}" if base else name
    # The text of the daf, cached by build/daftext.py. Loaded once per daf
    # rather than per rendered page, so the index does not read it twice and a
    # broken cache is reported once.
    daf_by_slug = {s.slug: daf_payload(daftext.load(content, s.slug)) for s in sheets}

    daf_tpl = env.get_template("daf.html")

    def render_daf(s, is_index):
        # Keyed by the reader's language, but each entry also names the language
        # its content is actually written in — on an untranslated daf that is
        # the English quiz sitting under the Hebrew key, and quiz.js has to know
        # so it can show it as the English quiz rather than frame it in Hebrew
        # and turn it right to left.
        quiz_by_lang = {l: {"lang": s.variant(l).lang, "qs": quiz_payload(s.variant(l))}
                        for l in i18n.LANGS}
        # A language with too thin a glossary is left out entirely rather than
        # given an empty deck, so cards.js falls back to English for it — the
        # same way an untranslated body does.
        cards_by_lang = {}
        for l in i18n.LANGS:
            v = s.variant(l)
            deck = cards_payload(v)
            if len(deck) >= MIN_CARDS:
                cards_by_lang[l] = {"lang": v.lang, "cards": deck}
        has_cards = bool(cards_by_lang)
        return daf_tpl.render(
            groups=language_groups(s),
            untranslated=[l for l in i18n.LANGS if l != s.lang and l not in s.translations],
            page_title=s.title,
            description=s.summary,
            canonical="" if is_index else s.out_name,
            has_quiz=bool(s.quiz),
            quiz_json=script_json(quiz_by_lang),
            has_cards=has_cards,
            cards_json=script_json(cards_by_lang),
            daf=daf_by_slug.get(s.slug),
            is_index=is_index,
            is_archive=False,
            needs_zman=is_index,
            config_json=config(s.out_name if is_index else None, with_manifest=is_index),
            feedback=feedback_queries(email, f"{s.tractate} {s.page}", page_url(s.out_name)),
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
            feedback=feedback_queries(email, "archive", page_url("archive.html")),
            **common,
        ))

    with open(os.path.join(out_dir, "dapim.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()

    # ---- the daf itself: without cached text a page simply has no Daf tab ----
    # Said out loud, because a missing tab is easy not to notice and the fix is
    # one command. Never fatal: the sheets are the site, the daf is an addition.
    no_text = [s.slug for s in sheets if not daf_by_slug.get(s.slug)]
    if no_text:
        print(f"  warn   no daf text for {', '.join(no_text)} — built without the "
              f"Daf tab; fetch it with: python3 build/daftext.py --all")

    # ---- stale output: report, never delete (a future daf must survive) ----
    expected = {e["file"] for e in entries} | {"index.html", "archive.html"}
    for p in sorted(glob.glob(os.path.join(out_dir, "*.html"))):
        base = os.path.basename(p)
        if base not in expected:
            print(f"  warn   {base} is left over in {out_dir} from an earlier build "
                  f"— it has no source in content/. Delete it, or list it in "
                  f"content/legacy.json. (A clean CI build never sees this.)")

    # The whole tree is rebuilt from source on every run and published from the
    # artifact, so there is no longer a "published copy" for a preview build to
    # drift from — the check that used to compare build/static against a
    # committed assets/ went with the committed output.

    where = (f"pinned to {settings['pin']['lat']},{settings['pin']['lon']}"
             if settings["pin"] else "per-visitor (browser timezone)")
    off = f" + {settings['offset']} min" if settings["offset"] else ""
    n_tr = sum(len(s.translations) for s in sheets)
    n_text = sum(1 for v in daf_by_slug.values() if v)
    print(f"Built {len(sheets)} daf ({n_tr} translated, {n_text} with the daf text) "
          f"+ {len(entries) - len(sheets)} legacy = {len(dapim)} routed")
    print(f"languages: {', '.join(i18n.LANGS)}")
    print(f"index.html seeded with {seed.slug} ({seed.iso})")
    print(f"rollover: sunset{off}, location {where}")
    # Said every build rather than warned about once: a link that is quietly
    # absent from every page looks exactly like a site nobody has feedback for.
    print(f"feedback: {email or 'off — set feedback_email in content/site.json'}")
    if dapim:
        print(f"schedule: {dapim[0]['d']} … {dapim[-1]['d']}")


if __name__ == "__main__":
    main()
