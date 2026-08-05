"""Every translatable string the build itself emits, in one place.

Runtime strings — the quiz chrome, the archive badge, the sunset line — live
in the JS that writes them (static/quiz.js, static/zman.js, static/lang.js).
This module covers only what Python renders into the HTML.

Adding a language is: a key here, plus `<Tractate>_<page>.<lang>.md` sheets.
Nothing in the build hardcodes "es".
"""

DEFAULT = "en"
LANGS = ["en", "es"]

# 0 = Monday, matching date.weekday()
DAYS = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
}
MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
}
DATE_FMT = {
    "en": "{dow}, {d} {month} {y}",
    "es": "{dow}, {d} de {month} de {y}",
}

UI = {
    "en": {
        "learn": "Learn",
        "quiz": "Chazara Quiz",
        "tip": "Tip: press keys 1–4 to answer, Enter for next.",
        "tomorrow": "Tomorrow",
        "archive_title": "Daf Yomi — Archive",
        "archive_lede": "Every daily study sheet · newest first",
        "archive_desc": "Every Daf Yomi study sheet, newest first.",
        "back": "← Back to today's daf",
        "nav_today": "📖 Today",
        "nav_archive": "🗂 Archive",
        # shown when a daf has no sheet in the reader's language
        "untranslated": "",
    },
    "es": {
        "learn": "Aprender",
        "quiz": "Repaso (Chazará)",
        "tip": "Consejo: pulsa las teclas 1–4 para responder y Enter para continuar.",
        "tomorrow": "Mañana",
        "archive_title": "Daf Yomi — Archivo",
        "archive_lede": "Todas las hojas de estudio diarias · las más recientes primero",
        "archive_desc": "Todas las hojas de estudio de Daf Yomi, las más recientes primero.",
        "back": "← Volver al daf de hoy",
        "nav_today": "📖 Hoy",
        "nav_archive": "🗂 Archivo",
        "untranslated": "Esta hoja todavía no está traducida al español; abajo está la versión en inglés.",
    },
}


def t(lang, key):
    return UI.get(lang, UI[DEFAULT]).get(key, UI[DEFAULT].get(key, ""))


def fmt_date(d, lang=DEFAULT):
    """date -> 'Thu, 6 August 2026' / 'jue, 6 de agosto de 2026'.

    Done here rather than with strftime, which would depend on whichever
    locales happen to be installed on the machine running the 6am build.
    """
    if not d:
        return ""
    lang = lang if lang in DAYS else DEFAULT
    return DATE_FMT[lang].format(
        dow=DAYS[lang][d.weekday()],
        d=d.day,
        month=MONTHS[lang][d.month - 1],
        y=d.year,
    )
