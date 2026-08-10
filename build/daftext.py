#!/usr/bin/env python3
"""The daf itself — fetched from Sefaria once, cached in content/daf/.

The study sheets explain the daf; this is the daf. Gemara, Rashi and Tosafot for
both amudim, laid out in the Daf tab the way the Vilna page lays them out.

  python3 build/daftext.py Chullin 108   # fetch one daf into content/daf/
  python3 build/daftext.py --all         # fetch whatever content/ is missing
  python3 build/daftext.py --all --force # refetch even what is already cached

Why a cache and not a fetch at build time: `build.py` must work with no network
— it runs on a laptop that is often only briefly awake, and a build that reached
for six URLs per daf would turn a flaky connection into a broken site. The text
of a daf printed in Vilna in 1886 is also not going to change, so fetching it
again on every build would buy nothing. A daf with no cached text simply has no
Daf tab, and the build says which ones those are.

Cache shape (content/daf/Chullin_108.json):

    {"tractate": "Chullin", "page": 108,
     "fetched": "2026-08-10",
     "versions": {"he": "William Davidson Edition - Vocalized Aramaic", ...},
     "amudim": [
       {"amud": "a", "ref": "Chullin 108a", "he_ref": "חולין ק״ח.",
        "url": "https://www.sefaria.org/Chullin.108a",
        "segments": [{"he": "…", "en": "…",
                      "rashi": ["…", "…"], "tosafot": ["…"]}]}]}

Segments are positional: Sefaria numbers Rashi and Tosafot to the Gemara
segment they comment on, so `segments[3]` is one passage with its own
commentary. Where a commentary has more segments than the Gemara (it happens),
the surplus is appended to the last one rather than dropped.
"""
import argparse
import datetime
import glob
import html as html_mod
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sheet as sheet_mod    # noqa: E402

API = "https://www.sefaria.org/api/v3/texts/"
SITE = "https://www.sefaria.org/"
CACHE_DIR = "daf"
TIMEOUT = 30

# What Sefaria's Talmud text actually uses: <big> marks the מתני׳ / גמ׳ openers,
# <b> and <i> carry the Steinsaltz reading of the English. Everything else is
# escaped rather than trusted — this text is baked straight into the page.
KEEP_TAGS = ("b", "strong", "i", "em", "big", "small", "sup", "sub")
KEEP_RE = re.compile(r"&lt;(/?)(" + "|".join(KEEP_TAGS) + r")\s*/?&gt;", re.I)
BR_RE = re.compile(r"&lt;br\s*/?&gt;", re.I)
# The lemma a Rashi or Tosafot opens with, printed in bold in the Vilna edition
# and separated from the comment by a hyphen. Bounded, so a hyphen deep inside
# a long comment cannot swallow half of it.
LEMMA_RE = re.compile(r"^([^-]{2,140}?)\s+-\s+")


def sanitize(s):
    """Sefaria's markup, reduced to the handful of tags we render.

    quote=False: this text only ever lands in an element body, never in an
    attribute, and Hebrew is full of geresh — escaping every one of them to
    &#x27; would make the cache unreadable for no gain.
    """
    out = html_mod.escape(str(s or "").strip(), quote=False)
    out = KEEP_RE.sub(r"<\1\2>", out)
    return BR_RE.sub("<br>", out)


def bold_lemma(s):
    """Bold the phrase a commentary quotes before commenting on it."""
    if "<b>" in s or "<strong>" in s:
        return s
    return LEMMA_RE.sub(lambda m: f"<b>{m.group(1)}</b> — ", s, count=1)


def get(ref, version=None):
    """One Sefaria text call -> (segments, version title). ([], "") if absent.

    A missing commentary is normal, not an error: plenty of tractates have no
    Tosafot, and the last daf of a tractate has no amud bet.
    """
    url = API + urllib.parse.quote(ref)
    if version:
        url += "?version=" + urllib.parse.quote(version)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return [], "", ""
        raise
    versions = data.get("versions") or []
    if not versions:
        return [], "", data.get("heRef", "")
    v = versions[0]
    return v.get("text") or [], v.get("versionTitle", ""), data.get("heRef", "")


def as_lines(text):
    """A Sefaria text tree flattened to one string per segment."""
    out = []
    for seg in text or []:
        if isinstance(seg, list):
            out.append(" ".join(str(x) for x in seg if x))
        else:
            out.append(str(seg or ""))
    return out


def as_comments(text):
    """A Sefaria commentary flattened to a list of comments per segment."""
    out = []
    for seg in text or []:
        if isinstance(seg, list):
            out.append([str(x) for x in seg if str(x).strip()])
        else:
            out.append([str(seg)] if str(seg).strip() else [])
    return out


def align(commentary, n):
    """Commentary indexed by Gemara segment, never longer than the Gemara.

    Sefaria numbers a commentary to the segment it comments on, so this is
    usually already true. When it is not, the tail is folded into the last
    segment: better crowded than silently missing.
    """
    rows = [list(c) for c in commentary[:n]]
    rows += [[] for _ in range(n - len(rows))]
    if len(commentary) > n and rows:
        for extra in commentary[n:]:
            rows[-1].extend(extra)
    return rows


def he_label(he_ref, amud):
    """'חולין ק״ח ב' -> 'חולין ק״ח:' — how the daf is actually named.

    Amud alef takes a full stop and amud bet a colon; Sefaria spells the amud
    out as a letter instead, which no one says aloud.
    """
    if not he_ref:
        return ""
    parts = he_ref.split()
    if len(parts) > 1 and parts[-1] in ("א", "ב"):
        parts = parts[:-1]
    return " ".join(parts) + ("." if amud == "a" else ":")


def fetch(tractate, page, today=None):
    """Everything the Daf tab needs for one daf, ready to cache."""
    book = str(tractate).strip().replace(" ", "_")
    versions = {}
    amudim = []

    for amud in ("a", "b"):
        ref = f"{book}.{page}{amud}"
        he, versions["he"], he_ref = get(ref, "hebrew")
        if not he:
            continue                      # a tractate that ends on amud alef
        en, versions["en"], _ = get(ref, "english")
        rashi, versions["rashi"], _ = get(f"Rashi_on_{ref}")
        tosafot, versions["tosafot"], _ = get(f"Tosafot_on_{ref}")

        he, en = as_lines(he), as_lines(en)
        n = len(he)
        en += [""] * (n - len(en))
        rashi = align(as_comments(rashi), n)
        tosafot = align(as_comments(tosafot), n)

        amudim.append({
            "amud": amud,
            "ref": f"{tractate} {page}{amud}",
            "he_ref": he_label(he_ref, amud),
            "url": SITE + f"{book}.{page}{amud}",
            "segments": [{
                "he": sanitize(he[i]),
                "en": sanitize(en[i]),
                "rashi": [bold_lemma(sanitize(c)) for c in rashi[i]],
                "tosafot": [bold_lemma(sanitize(c)) for c in tosafot[i]],
            } for i in range(n)],
        })

    if not amudim:
        raise SystemExit(f"Sefaria has no text for {tractate} {page} — check the tractate name")

    return {
        "tractate": str(tractate).strip(),
        "page": page,
        "fetched": (today or datetime.date.today()).isoformat(),
        "versions": {k: v for k, v in versions.items() if v},
        "amudim": amudim,
    }


# ---- the cache -----------------------------------------------------------
def path(content_dir, slug):
    return os.path.join(content_dir, CACHE_DIR, f"{slug}.json")


def load(content_dir, slug):
    """The cached daf, or None. A daf without one simply has no Daf tab."""
    p = path(content_dir, slug)
    if not os.path.exists(p):
        return None
    try:
        data = json.load(open(p, encoding="utf-8"))
    except (ValueError, OSError) as e:
        print(f"  warn   {os.path.relpath(p, content_dir)} is unreadable ({e}) "
              f"— built without its Daf tab")
        return None
    if not data.get("amudim"):
        return None
    return data


def save(content_dir, slug, data):
    p = path(content_dir, slug)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return p


def counts(data):
    segs = sum(len(a["segments"]) for a in data["amudim"])
    com = sum(len(s[k]) for a in data["amudim"] for s in a["segments"]
              for k in ("rashi", "tosafot"))
    return segs, com


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tractate", nargs="?")
    ap.add_argument("page", nargs="?")
    ap.add_argument("--all", action="store_true",
                    help="every daf in content/ that has no cached text yet")
    ap.add_argument("--force", action="store_true", help="refetch what is cached")
    ap.add_argument("--content", default=os.path.join(REPO, "content"))
    args = ap.parse_args()

    if args.all:
        wanted = [(s.tractate, s.page, s.slug) for s in sheet_mod.load_all(args.content)]
    elif args.tractate and args.page:
        page = int(args.page) if str(args.page).isdigit() else args.page
        wanted = [(args.tractate, page, f"{args.tractate}_{page}")]
    else:
        ap.error("give a tractate and page, or --all")

    todo = [w for w in wanted if args.force or not os.path.exists(path(args.content, w[2]))]
    if not todo:
        print(f"Nothing to fetch — all {len(wanted)} daf already cached in "
              f"{os.path.join(args.content, CACHE_DIR)}")
        return

    for tractate, page, slug in todo:
        data = fetch(tractate, page)
        p = save(args.content, slug, data)
        segs, com = counts(data)
        print(f"{slug}: {len(data['amudim'])} amud, {segs} segments, "
              f"{com} comments -> {os.path.relpath(p, REPO)}")

    left = len(wanted) - len(todo)
    if left:
        print(f"({left} already cached, left alone — use --force to refetch)")


if __name__ == "__main__":
    main()
