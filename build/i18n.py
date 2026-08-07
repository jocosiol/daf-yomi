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
        "cards": "Flashcards",
        "cards_cta": "Study these as flashcards",
        "cards_intro": "Today's key terms, one per card — the same glossary as in Learn. "
                       "Read the term, recall what it means on this daf, then turn the card "
                       "over and say whether you had it. Whatever you flag comes back at the "
                       "end in a shorter second round.",
        "tip": "Tip: press keys 1–4 to answer, Enter for next.",
        "cards_tip": "Tip: space flips the card, ← → move, 1 / 2 rate it.",
        "tomorrow": "Tomorrow",
        "archive_title": "Daf Yomi — Archive",
        "archive_lede": "Every daily study sheet · newest first",
        "archive_desc": "Every Daf Yomi study sheet, newest first.",
        "back": "← Back to today's daf",
        "nav_today": "📖 Today",
        "nav_archive": "🗂 Archive",
        # shown when a daf has no sheet in the reader's language
        "untranslated": "",
        # top of every daf page, and again at the foot
        "disclaimer": "AI-generated study aid, built with the Sefaria APIs. "
                      "It does not replace learning the daf itself.",
        "disclaimer_foot": "This sheet was written by AI from texts retrieved through the "
                           "Sefaria APIs. It can be incomplete or mistaken, and it is only a "
                           "helper for your learning — not a substitute for learning the "
                           "actual daf in the Gemara. Check anything you rely on against "
                           "the source.",
    },
    "es": {
        "learn": "Aprender",
        "quiz": "Repaso (Chazará)",
        "cards": "Tarjetas",
        "cards_cta": "Estudiar estos con tarjetas",
        "cards_intro": "Los términos clave de hoy, uno por tarjeta — el mismo glosario que "
                       "en Aprender. Lee el término, recuerda qué significa en este daf, "
                       "luego gira la tarjeta y di si lo sabías. Lo que marques vuelve al "
                       "final en una segunda ronda, más corta.",
        "tip": "Consejo: pulsa las teclas 1–4 para responder y Enter para continuar.",
        "cards_tip": "Consejo: la barra espaciadora gira la tarjeta, ← → navegan, 1 / 2 califican.",
        "tomorrow": "Mañana",
        "archive_title": "Daf Yomi — Archivo",
        "archive_lede": "Todas las hojas de estudio diarias · las más recientes primero",
        "archive_desc": "Todas las hojas de estudio de Daf Yomi, las más recientes primero.",
        "back": "← Volver al daf de hoy",
        "nav_today": "📖 Hoy",
        "nav_archive": "🗂 Archivo",
        "untranslated": "Esta hoja todavía no está traducida al español; abajo está la versión en inglés.",
        "disclaimer": "Hoja generada por IA con las APIs de Sefaria. "
                      "No reemplaza el estudio del daf mismo.",
        "disclaimer_foot": "Esta hoja fue escrita por una inteligencia artificial a partir de "
                           "textos obtenidos mediante las APIs de Sefaria. Puede contener "
                           "errores u omisiones, y es solo una ayuda para tu estudio, no un "
                           "sustituto de aprender el daf mismo en la Guemará. Verifica en la "
                           "fuente todo aquello en lo que te apoyes.",
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
