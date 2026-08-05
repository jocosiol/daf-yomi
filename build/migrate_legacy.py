#!/usr/bin/env python3
"""One-off: the old root-level sheets -> content/ with front matter.

The old format encoded metadata in prose the build had to parse back out — a
bold "Study date: Thu, 6 August 2026" line, and a quiz whose answer key sat in
a separate section matched to questions by number. This rewrites each sheet so
those facts are declared, and a translation inherits everything the base
already states rather than repeating it.

    python3 build/migrate_legacy.py [repo_dir]

**Already run, and its inputs are gone** — the root sheets were removed in the
same commit that added content/. Kept only so the conversion is auditable
against the sheets as they were one commit earlier. Safe to delete.
"""
import datetime
import glob
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n  # noqa: E402

REPO = (sys.argv[1] if len(sys.argv) > 1
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "content")

MONTH_NUM = {}
for _lang, _names in i18n.MONTHS.items():
    for _n, _month in enumerate(_names, 1):
        MONTH_NUM[_month.lower()[:3]] = _n

SUB_H = re.compile(r"^\*\*(?:Chapter|Cap[íi]tulo)\s+(\d+):\s*(.*?)\*\*\s*$", re.M)
TOMORROW = re.compile(r"^\*(?:Tomorrow|Ma[ñn]ana)\s*\(([^)]*)\):\s*(.*?)\*\s*$", re.M | re.S)
QUIZ_H = re.compile(r"^chazar[aá]", re.I)
KEY_H = re.compile(r"answer key|respuestas|clave", re.I)


def parse_date(text):
    m = (re.search(r"(\d{1,2})\s+(?:de\s+)?([^\W\d_]+)\.?\s+(?:de\s+)?(\d{4})", text or "")
         or re.search(r"([^\W\d_]+)\.?\s+(\d{1,2}),?\s+(\d{4})", text or ""))
    if not m:
        return None
    a, b, year = m.groups()
    day, mon = (a, b) if a.isdigit() else (b, a)
    num = MONTH_NUM.get(mon.lower()[:3])
    return datetime.date(int(year), num, int(day)) if num else None


def strip_md(t):
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*(.+?)\*", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def h2_spans(body):
    """[(heading, start, body_start, end)] for every H2."""
    hits = list(re.finditer(r"^##\s+(.*)$", body, re.M))
    return [(h.group(1).strip(), h.start(), h.end(),
             hits[i + 1].start() if i + 1 < len(hits) else len(body))
            for i, h in enumerate(hits)]


def parse_old(path):
    raw = open(path, encoding="utf-8").read()

    title = re.search(r"^#\s+(.*)$", raw, re.M).group(1).strip()
    t = re.search(r"—\s*(.+?)\s+(\d+)\s*\(([^)]*)\)", title)
    page, daf_he = int(t.group(2)), t.group(3).strip()

    sub = SUB_H.search(raw)
    ch_n, tail = int(sub.group(1)), sub.group(2)
    ch_name = re.search(r"\*(.+?)\*", tail).group(1).strip()
    gloss_m = re.search(r"\*.+?\*\s*\(([^)]*)\)", tail)
    gloss = gloss_m.group(1).strip() if gloss_m else ""
    study = parse_date(re.split(r"Study date:|Fecha de estudio:", tail)[-1])

    body = raw[sub.end():]

    # ---- quiz: questions here, answers 200 lines away, matched by number ----
    questions, key, order, keep = {}, {}, [], []
    for head, start, hend, end in h2_spans(body):
        chunk = body[hend:end]
        if QUIZ_H.match(head):
            if KEY_H.search(head):
                for ln in chunk.split("\n"):
                    a = re.match(r"\s*(\d+)\.\s*\*\*\(([a-d])\)\*\*\s*(?:—|–|-)?\s*(.*)$", ln)
                    if a:
                        key[a.group(1)] = (a.group(2), a.group(3).strip())
            else:
                cur = None
                for ln in chunk.split("\n"):
                    q = re.match(r"\s*\*\*(\d+)\.\s*(.*?)\*\*\s*$", ln)
                    o = re.match(r"\s*-\s*\(([a-d])\)\s*(.*)$", ln)
                    if q:
                        cur = q.group(1)
                        questions[cur] = {"q": q.group(2).strip(), "opts": {}}
                        order.append(cur)
                    elif o and cur:
                        questions[cur]["opts"][o.group(1)] = o.group(2).strip()
        else:
            keep.append((start, end))

    quiz = []
    for n in order:
        correct, why = key.get(n, (None, ""))
        if correct is None:
            print(f"  ! q{n} has no answer key")
        quiz.append({
            "q": questions[n]["q"],
            "opts": [questions[n]["opts"][k] for k in sorted(questions[n]["opts"])],
            "correct": correct,
            "why": why,
        })

    # ---- tomorrow ----
    tom = None
    tm = TOMORROW.search(body)
    if tm:
        rest = re.sub(r"\s+", " ", tm.group(2)).strip()
        rm = re.match(r"(.+?\s+\d+)\s*(?:—|–|-)\s*(.*)$", rest)
        tom = {"date": parse_date(tm.group(1)),
               "ref": (rm.group(1) if rm else rest).strip(),
               "teaser": rm.group(2).strip() if rm else ""}

    # ---- body: drop both quiz sections and the tomorrow line ----
    kept = "\n\n".join(body[s:e].strip() for s, e in keep)
    kept = TOMORROW.sub("", kept)
    kept = re.sub(r"\n{3,}", "\n\n", kept).strip()

    # ---- summary: first real sentence of the opening section ----
    first = body[keep[0][0]:keep[0][1]] if keep else ""
    para = ""
    for blk in re.split(r"\n\s*\n", re.sub(r"^##.*$", "", first, flags=re.M).strip()):
        blk = blk.strip()
        if blk and not blk.startswith((">", "-", "|", "#", "1.")):
            para = blk
            break
    flat = strip_md(para)
    sm = re.match(r"(.+?[.?!])(\s|$)", flat, re.S)
    summary = (sm.group(1) if sm else flat)[:180].strip()

    return {"title": title, "page": page, "daf_he": daf_he,
            "chapter": {"n": ch_n, "name": ch_name, "gloss": gloss},
            "study_date": study, "summary": summary, "tomorrow": tom,
            "body": kept, "quiz": quiz}


def dump(meta, quiz, body, dst):
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False,
                        default_flow_style=False, width=95)
    qy = yaml.safe_dump(quiz, allow_unicode=True, sort_keys=False,
                        default_flow_style=False, width=95)
    heading = ("Chazará — ponte a prueba" if meta.get("lang") == "es"
               else "Chazara — test yourself")
    open(dst, "w", encoding="utf-8").write(
        f"---\n{fm}---\n\n{body}\n\n---\n\n## {heading}\n\n```yaml\n{qy}```\n")
    print(f"  -> content/{os.path.basename(dst)}  ({len(quiz)} questions)")


def main():
    os.makedirs(OUT, exist_ok=True)
    for stale in glob.glob(os.path.join(OUT, "*.md")):
        os.remove(stale)

    for path in sorted(glob.glob(os.path.join(REPO, "*.md"))):
        base = os.path.basename(path)
        if base in ("README.md", "DAILY_PROMPT.md"):
            continue
        stem, lang = os.path.splitext(base)[0], None
        m = re.match(r"^(.+)\.([a-z]{2})$", stem)
        if m and m.group(2) in i18n.LANGS:
            stem, lang = m.group(1), m.group(2)

        print(f"{base}:")
        d = parse_old(path)

        if lang:
            # A translation states only what differs; tractate, page, daf_he and
            # study_date are inherited, so the two files cannot drift apart.
            meta = {"lang": lang, "title": d["title"],
                    "chapter": {"name": d["chapter"]["name"], "gloss": d["chapter"]["gloss"]},
                    "summary": d["summary"]}
            if d["tomorrow"]:
                meta["tomorrow"] = {"ref": d["tomorrow"]["ref"],
                                    "teaser": d["tomorrow"]["teaser"]}
            dump(meta, d["quiz"], d["body"], os.path.join(OUT, f"{stem}.{lang}.md"))
        else:
            meta = {"tractate": stem.rsplit("_", 1)[0], "page": d["page"],
                    "daf_he": d["daf_he"], "chapter": d["chapter"],
                    "study_date": d["study_date"], "summary": d["summary"]}
            if d["tomorrow"]:
                meta["tomorrow"] = d["tomorrow"]
            dump(meta, d["quiz"], d["body"], os.path.join(OUT, f"{stem}.md"))


if __name__ == "__main__":
    main()
