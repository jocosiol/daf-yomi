#!/usr/bin/env python3
"""The printed daf — where to find the scan of it.

shas.org publishes the Vilna Shas a page at a time, one PDF per amud, and
documents the endpoint for embedding:

    https://www.shas.org/daf-pdf/api/?masechta=chullin&daf=108&amud=a
    https://www.shas.org/daf-pdf/api/api-documentation.html

This module is only the naming and the check. It resolves a tractate as our
sheets spell it — Sefaria's spelling, because that is what the sheets carry —
to the Ashkenazi slug the API wants, which is not a transformation any rule
gets right: Ketubot is `kesubos`, Bava Batra is `bava-basra`, Keritot is
`kereisos`. So it is a table, and the table is checked rather than trusted:

  python3 build/dafpdf.py Chullin 108   # resolve one daf and see if it is there
  python3 build/dafpdf.py --all         # every tractate in the table, daf 2

`--all` is the check to run when a tractate is about to turn over, or after
this file is edited: it asks the API for the first daf of all forty and reports
any that do not answer, which is the only way a typo in the table shows up
before a reader meets it.

Nothing here runs at build time. `daftext.py` calls it while caching a daf and
records the URL it verified, so the built page carries a link that was known
good — and a daf whose scan is missing simply has no scan to show.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request

API = "https://www.shas.org/daf-pdf/api/"
DOCS = "https://www.shas.org/daf-pdf/api/api-documentation.html"
TIMEOUT = 20
# shas.org answers 406 to urllib's default "Python-urllib/3.9". Say who we are
# instead of pretending to be a browser — it is their bandwidth.
UA = {"User-Agent": "daf-yomi build (+https://jocosiol.github.io/daf-yomi)"}

# Sefaria's spelling -> the API's. Every one of the forty the API lists is here;
# Shekalim, Kinnim and Middot have no Bavli text on Sefaria but do have a
# printed daf, which is exactly the case the scan covers and the text cannot.
SLUG = {
    "Berakhot": "berachos",
    "Shabbat": "shabbos",
    "Eruvin": "eruvin",
    "Pesachim": "pesachim",
    "Shekalim": "shekalim",
    "Yoma": "yoma",
    "Sukkah": "sukkah",
    "Beitzah": "beitzah",
    "Rosh Hashanah": "rosh-hashanah",
    "Taanit": "taanis",
    "Megillah": "megillah",
    "Moed Katan": "moed-katan",
    "Chagigah": "chagigah",
    "Yevamot": "yevamos",
    "Ketubot": "kesubos",
    "Nedarim": "nedarim",
    "Nazir": "nazir",
    "Sotah": "sotah",
    "Gittin": "gittin",
    "Kiddushin": "kiddushin",
    "Bava Kamma": "bava-kamma",
    "Bava Metzia": "bava-metzia",
    "Bava Batra": "bava-basra",
    "Sanhedrin": "sanhedrin",
    "Makkot": "makkos",
    "Shevuot": "shevuos",
    "Avodah Zarah": "avodah-zarah",
    "Horayot": "horayos",
    "Zevachim": "zevachim",
    "Menachot": "menachos",
    "Chullin": "chullin",
    "Bekhorot": "bechoros",
    "Arakhin": "arachin",
    "Temurah": "temurah",
    "Keritot": "kereisos",
    "Meilah": "meilah",
    "Kinnim": "kinim",
    "Tamid": "tamid",
    "Middot": "middos",
    "Niddah": "niddah",
}

# "Bava_Metzia", "bava metzia" and "Bava Metzia" are the same tractate; the
# calendars API also hands back Shekalim as "Jerusalem Talmud Shekalim".
_NORM = {re.sub(r"[^a-z]", "", k.lower()): v for k, v in SLUG.items()}
_PREFIX = re.compile(r"^(jerusalem\s*talmud|talmud|masechta|tractate)\s+", re.I)


def slug(tractate):
    """The API's name for a tractate, or None if we do not have one."""
    name = _PREFIX.sub("", str(tractate or "").strip())
    return _NORM.get(re.sub(r"[^a-z]", "", name.lower()))


def url(tractate, page, amud):
    """The PDF of one amud, or None if the tractate is not in the table."""
    s = slug(tractate)
    if not s:
        return None
    return f"{API}?masechta={s}&daf={page}&amud={amud}"


def exists(pdf_url):
    """Is there actually a page there?

    Only the two answers that mean "no page" are read as no: 400 for an amud
    that does not exist — the last daf of a tractate has no bet — and 404 for a
    name it does not know. Anything else is raised.

    That distinction is the whole point of this function. Written as a blanket
    `except HTTPError: return False`, the first version turned a 406 the server
    was sending to every single request into "no scan exists for any daf in
    Shas" — a systemic failure quietly reported as forty ordinary absences. A
    feature that switches itself off must be loud about it.
    """
    req = urllib.request.Request(pdf_url, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            return False
        raise RuntimeError(
            f"shas.org answered {e.code} for {pdf_url} — that is not 'no such "
            f"page', so the scan is being treated as unknown rather than "
            f"missing. Check {DOCS}") from e


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tractate", nargs="?")
    ap.add_argument("page", nargs="?", type=int)
    ap.add_argument("--all", action="store_true",
                    help="check every tractate in the table against the API")
    args = ap.parse_args()

    if args.all:
        bad = []
        for name in SLUG:
            u = url(name, 2, "a")
            ok = exists(u)
            print(f"  {'ok  ' if ok else 'MISS'}  {name:16s} {slug(name)}")
            if not ok:
                bad.append(name)
        print(f"\n{len(SLUG) - len(bad)}/{len(SLUG)} resolve. See {DOCS}")
        sys.exit(f"{', '.join(bad)} did not answer — fix SLUG" if bad else 0)

    if not (args.tractate and args.page):
        ap.error("give a tractate and page, or --all")

    if not slug(args.tractate):
        sys.exit(f"No slug for {args.tractate!r} — add it to SLUG in this file. "
                 f"The API lists its names at {DOCS}")
    for amud in ("a", "b"):
        u = url(args.tractate, args.page, amud)
        print(f"  {'ok  ' if exists(u) else 'MISS'}  {u}")
    meta = url(args.tractate, args.page, "a") + "&format=json"
    try:
        with urllib.request.urlopen(urllib.request.Request(meta, headers=UA),
                                    timeout=TIMEOUT) as r:
            print(json.dumps(json.load(r), ensure_ascii=False))
    except urllib.error.HTTPError as e:
        # The error body says what is wrong — "Masechta Chullin ends at daf
        # 142a" — which is more use than the status code on its own.
        print(f"  {e.code}  {e.read().decode('utf-8', 'replace')[:300]}")


if __name__ == "__main__":
    main()
