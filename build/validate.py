#!/usr/bin/env python3
"""Check every study sheet against the format contract. Exit 1 on any error.

This is the gate the daily build runs before it commits. It replaces the old
arrangement, where the format was described in prose in DAILY_PROMPT.md and
verified by eye — so a malformed date line, an answer key pointing at a missing
option, or a translation whose answers disagreed with the English would all
publish silently.

Usage:
  python3 build/validate.py [content_dir]     # default: content/
"""
import datetime
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n                        # noqa: E402
import sheet as sheet_mod          # noqa: E402

REQUIRED_SECTIONS = {
    "en": ["The big picture", "Walking through the sugya", "Key concepts",
           "Who's who", "One line to carry with you"],
    "es": ["panorama general", "paso a paso", "Conceptos", "Quién es quién", "Una línea"],
}
QUIZ_MIN, QUIZ_MAX = 8, 10
LETTERS = "abcd"


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    @property
    def ok(self):
        return not self.errors


def name(s):
    return os.path.basename(s.path)


def check_base_meta(s, rep):
    where = name(s)

    if not s.meta.get("tractate"):
        rep.error(where, "front matter is missing 'tractate'")
    if not isinstance(s.meta.get("page"), int):
        rep.error(where, f"front matter 'page' must be a whole number, got {s.meta.get('page')!r}")

    # the filename is part of the URL, so it must agree with the metadata
    stem = os.path.splitext(os.path.basename(s.path))[0]
    if s.tractate and isinstance(s.page, int) and stem != s.slug:
        rep.error(where, f"filename should be {s.slug}.md to match tractate/page")

    if s.meta.get("study_date") is None:
        rep.error(where, "front matter is missing 'study_date'")
    elif s.study_date is None:
        rep.error(where, f"'study_date' must be ISO yyyy-mm-dd, got {s.meta['study_date']!r}")

    ch = s.meta.get("chapter") or {}
    if not ch:
        rep.warn(where, "no 'chapter' block — the subtitle will only show the date")
    else:
        if ch.get("n") is None:
            rep.error(where, "'chapter' is missing 'n'")
        if not ch.get("name"):
            rep.error(where, "'chapter' is missing 'name'")

    if not s.daf_he:
        rep.warn(where, "no 'daf_he' — the title will have no Hebrew page numeral")
    elif not re.search(r"[\u0590-\u05FF]", s.daf_he):
        rep.error(where, f"'daf_he' has no Hebrew characters: {s.daf_he!r}")

    t = s.meta.get("tomorrow")
    if t and sheet_mod.as_date(t.get("date")) is None:
        rep.error(where, f"'tomorrow.date' must be ISO yyyy-mm-dd, got {t.get('date')!r}")


def check_translation_meta(tr, rep):
    where = name(tr)

    if tr.lang not in i18n.LANGS:
        rep.error(where, f"lang '{tr.lang}' is not in i18n.LANGS ({', '.join(i18n.LANGS)})")
    if not tr.meta.get("lang"):
        rep.error(where, f"front matter is missing 'lang: {sheet_mod.split_stem(tr.path)[1]}'")

    # The whole point of inheritance: a translation cannot state a fact the
    # base already states, so the two can never disagree about the date.
    for key in sheet_mod.INHERITED:
        if key in tr.meta:
            rep.error(where, f"'{key}' is inherited from {name(tr.base)} — remove it")

    if not tr.meta.get("title"):
        rep.warn(where, "no 'title' — the page will show the English one")
    ch = tr.meta.get("chapter") or {}
    if "n" in ch:
        rep.error(where, "'chapter.n' is inherited from the base sheet — remove it")
    if not ch.get("name"):
        rep.warn(where, "'chapter.name' is untranslated")
    if not tr.meta.get("summary"):
        rep.warn(where, "no 'summary' — link previews in this language fall back to English")


def check_common_meta(s, rep):
    where = name(s)
    if not s.summary:
        rep.warn(where, "no 'summary' — link previews and search will have no description")
    elif len(s.summary) > 200:
        rep.warn(where, f"'summary' is {len(s.summary)} chars; under 160 previews best")


def check_body(s, rep):
    where = name(s)
    headings = [h.strip() for h in re.findall(r"^##\s+(.*)$", s.body_md, re.M)]
    for want in REQUIRED_SECTIONS.get(s.lang, REQUIRED_SECTIONS[i18n.DEFAULT]):
        if not any(want.lower() in h.lower() for h in headings):
            rep.error(where, f"missing section: ## …{want}…")
    if len(s.body_md) < 1500:
        rep.warn(where, f"body is only {len(s.body_md)} chars — is it complete?")


def check_quiz(s, rep):
    where = name(s)
    q = s.quiz

    if not q:
        rep.error(where, "no quiz questions found in the Chazara yaml block")
        return
    if not QUIZ_MIN <= len(q) <= QUIZ_MAX:
        rep.error(where, f"{len(q)} quiz questions; want {QUIZ_MIN}–{QUIZ_MAX}")

    seen = []
    for i, item in enumerate(q, 1):
        at = f"{where} q{i}"
        if not isinstance(item, dict):
            rep.error(at, f"must be a mapping with q/opts/correct/why, got {type(item).__name__}")
            continue

        text = str(item.get("q", "") or "").strip()
        if not text:
            rep.error(at, "empty 'q'")
        elif not text.endswith(("?", "؟")):
            rep.warn(at, "question does not end in a question mark")

        opts = item.get("opts")
        if not isinstance(opts, list):
            rep.error(at, "'opts' must be a list of four strings")
            continue
        if len(opts) != 4:
            rep.error(at, f"{len(opts)} options; want exactly 4")
        if any(not str(o).strip() for o in opts):
            rep.error(at, "one of the options is empty")
        if len({str(o).strip().lower() for o in opts}) != len(opts):
            rep.error(at, "two options are identical")

        correct = str(item.get("correct", "") or "").strip().lower()
        if correct not in LETTERS:
            rep.error(at, f"'correct' must be one of a/b/c/d, got {item.get('correct')!r}")
        elif LETTERS.index(correct) >= len(opts):
            rep.error(at, f"'correct: {correct}' but there are only {len(opts)} options")
        else:
            seen.append(correct)

        if not str(item.get("why", "") or "").strip():
            rep.error(at, "'why' is empty — every answer needs its one-line reason")

    # a quiz where every answer is (b) is a quiz you can pass without reading
    if len(seen) >= QUIZ_MIN and len(set(seen)) < 3:
        rep.warn(where, f"answers only use {sorted(set(seen))} — vary the correct letter")


def check_quiz_parity(base, tr, rep):
    """A translated quiz must be the same quiz, question for question."""
    where = name(tr)
    if len(tr.quiz) != len(base.quiz):
        rep.error(where, f"{len(tr.quiz)} questions but {name(base)} has {len(base.quiz)}")
        return
    for i, (b, t) in enumerate(zip(base.quiz, tr.quiz), 1):
        if not isinstance(b, dict) or not isinstance(t, dict):
            continue
        bc = str(b.get("correct", "")).strip().lower()
        tc = str(t.get("correct", "")).strip().lower()
        if bc != tc:
            rep.error(f"{where} q{i}",
                      f"correct answer is '{tc}' but '{bc}' in {name(base)} — "
                      "options must stay in the same order across languages")


def check_collection(sheets, rep):
    by_date, by_ref = {}, {}
    for s in sheets:
        if s.iso:
            by_date.setdefault(s.iso, []).append(name(s))
        if s.tractate and s.page is not None:
            by_ref.setdefault((s.tractate, s.page), []).append(name(s))

    for iso, names in sorted(by_date.items()):
        if len(names) > 1:
            rep.error("collection", f"two sheets share study_date {iso}: {', '.join(names)}")
    for ref, names in sorted(by_ref.items(), key=lambda kv: str(kv[0])):
        if len(names) > 1:
            rep.error("collection", f"duplicate daf {ref[0]} {ref[1]}: {', '.join(names)}")

    # a gap means the homepage will sit on a stale daf for a day
    dated = sorted([s for s in sheets if s.study_date], key=lambda s: s.study_date)
    for prev, nxt in zip(dated, dated[1:]):
        gap = (nxt.study_date - prev.study_date).days - 1
        if gap > 0:
            rep.warn("collection", f"{gap} day gap between {prev.slug} ({prev.iso}) "
                                   f"and {nxt.slug} ({nxt.iso})")

    # translation coverage, so a missing sheet is visible rather than silent
    today = datetime.date.today()
    for lang in i18n.LANGS:
        if lang == i18n.DEFAULT:
            continue
        missing = [s.slug for s in sheets
                   if lang not in s.translations and s.study_date and s.study_date >= today]
        if missing:
            rep.warn("collection",
                     f"no '{lang}' sheet for {', '.join(missing)} "
                     f"— those pages fall back to {i18n.DEFAULT}")


def validate(content_dir):
    rep = Report()
    paths = sorted(glob.glob(os.path.join(content_dir, "*.md")))
    if not paths:
        rep.error(content_dir, "no sheets found")
        return rep, []

    bases = []
    for path in paths:
        if sheet_mod.split_stem(path)[1]:      # a translation; checked with its base
            continue
        try:
            s = sheet_mod.load(path)
        except sheet_mod.SheetError as e:
            rep.error(os.path.basename(path), str(e))
            continue
        bases.append(s)

    # a translation whose base is missing would otherwise never be looked at
    known = {os.path.splitext(b.path)[0] for b in bases}
    for path in paths:
        stem, lang = sheet_mod.split_stem(path)
        if lang and os.path.join(content_dir, stem) not in known:
            rep.error(os.path.basename(path),
                      f"no base sheet {stem}.md for this '{lang}' translation")

    for s in bases:
        check_base_meta(s, rep)
        check_common_meta(s, rep)
        check_body(s, rep)
        check_quiz(s, rep)
        for tr in s.translations.values():
            check_translation_meta(tr, rep)
            check_common_meta(tr, rep)
            check_body(tr, rep)
            check_quiz(tr, rep)
            check_quiz_parity(s, tr, rep)

    check_collection(bases, rep)
    return rep, bases


def main():
    content = sys.argv[1] if len(sys.argv) > 1 else "content"
    rep, sheets = validate(content)

    for w in rep.warnings:
        print(f"  warn   {w}")
    for e in rep.errors:
        print(f"  ERROR  {e}")

    today = datetime.date.today().isoformat()
    ahead = sum(1 for s in sheets if s.iso and s.iso > today)
    tr = sum(len(s.translations) for s in sheets)
    print(f"{len(sheets)} daf + {tr} translation(s) checked · "
          f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s) · "
          f"{ahead} built ahead of today")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
