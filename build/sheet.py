"""Parse a Daf Yomi study sheet into structured data.

A daf is one base sheet in content/, plus one optional file per translation:

    content/Chullin_98.md      the English sheet, and the source of record
    content/Chullin_98.es.md   the Spanish translation

The base carries the facts:

    ---
    tractate: Chullin
    page: 98
    daf_he: חולין צח
    chapter: {n: 7, name: Gid HaNasheh, gloss: the sciatic nerve}
    study_date: 2026-08-06
    summary: One sentence for search results and link previews.
    tomorrow: {date: 2026-08-07, ref: Chullin 99, teaser: …}
    ---

    ## The big picture …

A translation carries only what is language-specific — title, chapter name,
summary, teaser — and inherits the rest:

    ---
    lang: es
    title: Daf Yomi — Julín 98 (חולין צח)
    chapter: {name: Guid HaNashé, gloss: el nervio ciático}
    summary: …
    tomorrow: {ref: Julín 99, teaser: …}
    ---

That inheritance is the point: a translation cannot disagree with the English
about which day it is, because it never states the date. Display dates are
formatted per language from the one ISO value (see i18n.fmt_date).

The quiz lives in a fenced ```yaml block under the `## Chazara` heading, so it
can be written last — after the analysis it draws on — while the metadata above
is known up front. Nothing the build needs is scraped out of prose.
"""
import datetime
import glob
import os
import re

import yaml

import i18n

FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
CHAZARA_H2 = re.compile(r"^##\s+(?:Chazar[aá]|חזרה)\b.*$", re.M | re.I)
YAML_FENCE = re.compile(r"```ya?ml\r?\n(.*?)```", re.S)
# Chullin_98.es.md -> ("Chullin_98", "es");  Chullin_98.md -> ("Chullin_98", None)
STEM = re.compile(r"^(?P<base>.+?)(?:\.(?P<lang>[a-z]{2}(?:-[a-z]{2})?))?$", re.I)

# Fields a translation must not restate; they are inherited from the base so
# the two files cannot drift apart.
INHERITED = ("tractate", "page", "daf_he", "study_date")


class SheetError(Exception):
    """Raised when a sheet cannot be parsed at all. Softer problems are
    reported by validate.py so one bad sheet lists every issue at once."""


class Sheet:
    def __init__(self, path, meta, body_md, quiz, lang=i18n.DEFAULT, base=None):
        self.path = path
        self.meta = meta
        self.body_md = body_md
        self.quiz = quiz
        self.lang = lang
        self.base = base                 # None on a base sheet
        self.translations = {}           # lang -> Sheet, on a base sheet only

    # ---- inheritance ----------------------------------------------------
    def _get(self, key, default=None):
        """This sheet's value, falling back to the base sheet's."""
        if key in self.meta and self.meta[key] is not None:
            return self.meta[key]
        if self.base is not None:
            return self.base._get(key, default)
        return default

    @property
    def is_translation(self):
        return self.base is not None

    def langs(self):
        return [self.lang] + sorted(self.translations)

    def variant(self, lang):
        """The sheet to show in `lang` — the translation, or self as fallback."""
        return self.translations.get(lang, self)

    # ---- identity -------------------------------------------------------
    @property
    def tractate(self):
        return str(self._get("tractate", "")).strip()

    @property
    def page(self):
        return self._get("page")

    @property
    def slug(self):
        return f"{self.tractate}_{self.page}"

    @property
    def out_name(self):
        return f"{self.slug}.html"

    # ---- display --------------------------------------------------------
    @property
    def daf_he(self):
        return str(self._get("daf_he", "")).strip()

    @property
    def title(self):
        if self.meta.get("title"):
            return str(self.meta["title"])
        if self.is_translation:
            return self.base.title
        he = f" ({self.daf_he})" if self.daf_he else ""
        return f"Daf Yomi — {self.tractate} {self.page}{he}"

    @property
    def chapter(self):
        """Merged: the translation supplies name/gloss, the base supplies n."""
        merged = dict((self.base.chapter if self.is_translation else {}) or {})
        merged.update(self.meta.get("chapter") or {})
        return merged

    @property
    def label(self):
        """'Chullin 98' / 'Julín 98' / 'חולין קד' — the archive's link text.

        The Hebrew title carries no parenthetical, because the Hebrew reference
        the other languages put in brackets is the title itself — so the
        bracket is optional and the reference simply runs to the end.
        """
        m = re.search(r"—\s*(.+?)(?:\s*\(|$)", self.title)
        return m.group(1).strip() if m else f"{self.tractate} {self.page}"

    @property
    def subtitle(self):
        """'Chapter 7: Gid HaNasheh (the sciatic nerve) · Thu, 6 August 2026'.

        Assembled from fields, not parsed back out of a sentence — which is
        what used to let a typo silently drop a daf out of the routing.
        """
        ch = self.chapter
        bits = []
        if ch.get("n") is not None:
            word = i18n.t(self.lang, "chapter")
            name = f"<em>{ch['name']}</em>" if ch.get("name") else ""
            gloss = f" ({ch['gloss']})" if ch.get("gloss") else ""
            bits.append(f"{word} {ch['n']}: {name}{gloss}".strip())
        if self.display_date:
            bits.append(self.display_date)
        return " · ".join(bits)

    @property
    def summary(self):
        return str(self._get("summary", "") or "").strip()

    # ---- dates ----------------------------------------------------------
    @property
    def study_date(self):
        """datetime.date, or None if absent/unparseable."""
        return as_date(self._get("study_date"))

    @property
    def iso(self):
        d = self.study_date
        return d.isoformat() if d else None

    @property
    def display_date(self):
        return i18n.fmt_date(self.study_date, self.lang)

    @property
    def tomorrow(self):
        base_t = dict((self.base.meta.get("tomorrow") if self.is_translation else {}) or {})
        base_t.update(self.meta.get("tomorrow") or {})
        d = as_date(base_t.get("date"))
        if d:
            base_t["display"] = i18n.fmt_date(d, self.lang)
        return base_t


def as_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    if isinstance(v, str):
        try:
            return datetime.date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def split_front_matter(text):
    m = FRONT_MATTER.match(text)
    if not m:
        raise SheetError("no YAML front matter — the file must start with a '---' line")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise SheetError(f"front matter is not valid YAML: {e}")
    if not isinstance(meta, dict):
        raise SheetError("front matter must be a mapping of key: value")
    return meta, text[m.end():]


def split_quiz(body_md):
    """Pull the Chazara section out of the body and parse its yaml fence.

    Returns (body_without_chazara, quiz_list). A missing section yields an
    empty quiz; validate.py decides whether that is acceptable.
    """
    m = CHAZARA_H2.search(body_md)
    if not m:
        return body_md, []
    nxt = re.search(r"^##\s+", body_md[m.end():], re.M)      # runs to the next H2, or EOF
    end = m.end() + nxt.start() if nxt else len(body_md)
    section, rest = body_md[m.end():end], body_md[:m.start()] + body_md[end:]

    fence = YAML_FENCE.search(section)
    if not fence:
        raise SheetError(
            "the Chazara section has no ```yaml block — the quiz must be declared as data"
        )
    try:
        quiz = yaml.safe_load(fence.group(1))
    except yaml.YAMLError as e:
        raise SheetError(f"the Chazara yaml block is not valid YAML: {e}")
    if quiz is None:
        quiz = []
    if not isinstance(quiz, list):
        raise SheetError("the Chazara yaml block must be a list of questions")
    return rest, quiz


def parse(path, base=None):
    meta, body = split_front_matter(open(path, encoding="utf-8").read())
    body, quiz = split_quiz(body)
    body = re.sub(r"(?:\s*^---\s*$)+\Z", "", body.rstrip(), flags=re.M)   # trailing rules
    lang = str(meta.get("lang") or i18n.DEFAULT).strip().lower()
    return Sheet(path, meta, body.strip(), quiz, lang=lang, base=base)


def split_stem(path):
    m = STEM.match(os.path.splitext(os.path.basename(path))[0])
    lang = (m.group("lang") or "").lower()
    if lang in i18n.LANGS and lang != i18n.DEFAULT:
        return m.group("base"), lang
    return os.path.splitext(os.path.basename(path))[0], None


def load(path):
    """One base sheet plus any translations sitting beside it."""
    base = parse(path)
    stem = os.path.splitext(path)[0]
    for lang in i18n.LANGS:
        if lang == i18n.DEFAULT:
            continue
        companion = f"{stem}.{lang}.md"
        if os.path.exists(companion):
            base.translations[lang] = parse(companion, base=base)
    return base


def load_all(content_dir):
    """Every daf in content/, sorted by study date then page.

    The manifest comes from here — from the sources — rather than from globbing
    *.html at the site root, so a stray file in the output directory can no
    longer become a bogus archive entry.
    """
    sheets = []
    for p in sorted(glob.glob(os.path.join(content_dir, "*.md"))):
        if split_stem(p)[1]:            # a translation; loaded with its base
            continue
        sheets.append(load(p))
    return sorted(sheets, key=lambda s: (s.iso or "9999-99-99", s.page or 0))
