#!/usr/bin/env python3
"""What still needs writing to keep the site a week ahead.

The site rolls over at sunset from a manifest baked into every page, so it does
not need a build every day — it needs a buffer. What can run dry is the writing,
not the publishing: CI rebuilds and deploys on every push, but the sheets come
from a laptop that is often switched off. Keeping several days in hand turns a
missed run into a non-event instead of a homepage with no daf for today.

  python3 build/buffer.py            # report; exit 0 if full, 1 if short
  python3 build/buffer.py --missing  # one "YYYY-MM-DD lang" pair per line

Depth and per-run cap come from content/site.json:
  buffer_days       how many days ahead to keep, counting today (default 7)
  max_per_run       most dapim to write in one run (default 3), so a single
                    run stays bounded and the next trigger continues
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n                # noqa: E402
import sheet as sheet_mod  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULTS = {"buffer_days": 7, "max_per_run": 3}


def settings(content_dir):
    s = dict(DEFAULTS)
    path = os.path.join(content_dir, "site.json")
    if os.path.exists(path):
        loaded = json.load(open(path, encoding="utf-8"))
        for k in DEFAULTS:
            if isinstance(loaded.get(k), int):
                s[k] = loaded[k]
    return s


def survey(content_dir, today=None):
    """(settings, [(date, lang, why)]) — everything missing inside the window.

    lang is the sheet that needs writing: the default language means the daf
    itself does not exist yet; another means only its translation is missing.
    """
    cfg = settings(content_dir)
    today = today or datetime.date.today()
    have = {s.study_date: s for s in sheet_mod.load_all(content_dir) if s.study_date}

    gaps = []
    for i in range(cfg["buffer_days"]):
        d = today + datetime.timedelta(days=i)
        s = have.get(d)
        if s is None:
            gaps.append((d, i18n.DEFAULT, "no sheet"))
            continue
        for lang in i18n.LANGS:
            if lang != i18n.DEFAULT and lang not in s.translations:
                gaps.append((d, lang, f"{s.slug} has no {lang} sheet"))
    return cfg, gaps, have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", default=os.path.join(REPO, "content"))
    ap.add_argument("--missing", action="store_true",
                    help="machine-readable: 'YYYY-MM-DD lang' per line, oldest first, capped")
    args = ap.parse_args()

    cfg, gaps, have = survey(args.content)
    capped = gaps[:cfg["max_per_run"]]

    if args.missing:
        for d, lang, _ in capped:
            print(f"{d.isoformat()} {lang}")
        return 0 if not gaps else 1

    today = datetime.date.today()
    print(f"buffer target: {cfg['buffer_days']} days "
          f"({today} … {today + datetime.timedelta(days=cfg['buffer_days'] - 1)})")
    for i in range(cfg["buffer_days"]):
        d = today + datetime.timedelta(days=i)
        s = have.get(d)
        when = "today" if i == 0 else f"+{i}d"
        if s is None:
            print(f"  {d}  {when:5}  — MISSING")
        else:
            langs = "+".join([s.lang] + sorted(s.translations))
            short = "" if len(s.translations) + 1 == len(i18n.LANGS) else "   <- needs translation"
            print(f"  {d}  {when:5}  {s.slug} ({langs}){short}")

    if not gaps:
        print(f"\nbuffer is full — {cfg['buffer_days']} days in hand, nothing to write")
        return 0

    print(f"\n{len(gaps)} item(s) to write; this run should do at most "
          f"{cfg['max_per_run']}, oldest first:")
    for d, lang, why in capped:
        print(f"  {d}  {lang:3}  ({why})")
    if len(gaps) > len(capped):
        print(f"  … {len(gaps) - len(capped)} more, left for the next run")
    return 1


if __name__ == "__main__":
    sys.exit(main())
