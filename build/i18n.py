"""Every translatable string the build itself emits, in one place.

Runtime strings — the quiz chrome, the archive badge, the sunset line — live
in the JS that writes them (static/quiz.js, static/zman.js, static/lang.js).
This module covers only what Python renders into the HTML.

Adding a language is: a key here, plus `<Tractate>_<page>.<lang>.md` sheets.
Nothing in the build hardcodes "es" or "he".
"""

DEFAULT = "en"
LANGS = ["en", "es", "he"]

# Written right to left. The build marks content with it, lang.js puts `dir` on
# <html> for it, and hebrew_spans stops wrapping Hebrew runs inside it — a sheet
# that is Hebrew throughout is not a Latin page with Hebrew quotations in it.
RTL = ["he"]

# What the 🌐 picker lists. The name of each language, written in that language,
# and the tooltip likewise — both are read by someone who wants that language,
# so neither is any use in the one they are currently looking at. The menu is
# therefore the same in every language: one line per language, in that language.
NAME = {"en": "English", "es": "Español", "he": "עברית"}
VIEW_IN = {"en": "View in English", "es": "Ver en español", "he": "לצפייה בעברית"}

# 0 = Monday, matching date.weekday()
DAYS = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
    # The civil week, named the way it is said in Israel: Monday is יום שני.
    "he": ["יום ב׳", "יום ג׳", "יום ד׳", "יום ה׳", "יום ו׳", "שבת", "יום א׳"],
}
MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    # Gregorian, in Hebrew — the study_date is a civil date, and rendering it as
    # a Hebrew-calendar date here would be a different date, not a translation.
    "he": ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
           "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"],
}
DATE_FMT = {
    "en": "{dow}, {d} {month} {y}",
    "es": "{dow}, {d} de {month} de {y}",
    "he": "{dow}, {d} ב{month} {y}",
}

UI = {
    "en": {
        # the word in the subtitle, before the chapter number
        "chapter": "Chapter",
        # The three tabs, which are the three moments of learning a daf: what you
        # want before you open it, the daf itself, and what you do afterwards.
        "intro": "Introduction",
        "chazara": "Chazara",
        "cards": "Flashcards",
        "quiz_head": "Test yourself",
        "cards_intro": "The terms above, one per card. Read the term, recall what it means "
                       "on this daf, then turn the card over and say whether you had it. "
                       "Whatever you flag comes back at the end in a shorter second round.",
        "tip": "Tip: click the card, then keys 1–4 answer and Enter moves on.",
        "cards_tip": "Tip: click the card, then space flips it, ← → move, 1 / 2 rate it.",
        "daf": "The Daf",
        "daf_mode_scan": "Printed page",
        "daf_mode_text": "Text",
        "daf_intro_scan": "The whole Vilna page as it is printed — Gemara in the middle, Rashi "
                          "and Tosafot in the margins, Mesoras HaShas and Ein Mishpat down the "
                          "sides. Open it full size to read it comfortably, and tap any line "
                          "underneath it for the English of that passage.",
        "daf_intro": "The daf laid out as it is printed: the Gemara in the middle, Rashi on "
                     "the inner margin and Tosafot on the outer one. Nothing here was written "
                     "by us.",
        "daf_show": "Show",
        # The chip for Sefaria's translation, which exists only in English and is
        # therefore shown only in the English view — daf.css hides it in the
        # others. The label is still written in every language, since it is the
        # reader's chrome and not the translation, and it is what would be shown
        # if a second translation ever made the chip worth offering to them.
        "daf_en": "English",
        "daf_sefaria": "Open on Sefaria",
        "daf_open_pdf": "Open full size",
        "daf_lines": "Line by line — tap one for its English",
        "daf_note": "This is the daf itself — the Vilna page, not our writing. "
                    "It is not AI-generated.",
        "daf_credit_scan": 'The Vilna page served by <a href="https://www.shas.org" '
                           'target="_blank" rel="noopener">shas.org</a>, one PDF per amud.',
        "daf_credit": 'Text from <a href="https://www.sefaria.org" target="_blank" '
                      'rel="noopener">Sefaria</a>. Gemara and translation from the William '
                      'Davidson Talmud, with commentary by Rabbi Adin Even-Israel Steinsaltz, '
                      '<a href="https://creativecommons.org/licenses/by-nc/4.0/" '
                      'target="_blank" rel="noopener">CC BY-NC 4.0</a>. Rashi and Tosafot are '
                      'the Vilna edition, public domain.',
        "tomorrow": "Tomorrow",
        "archive_title": "Daf Yomi — Archive",
        "archive_lede": "Every daily study sheet · newest first",
        "archive_desc": "Every Daf Yomi study sheet, newest first.",
        "back": "← Back to today's daf",
        "nav_today": "📖 Today",
        "nav_archive": "🗂 Archive",
        # Names the 🌐 picker for a screen reader. Not shown: the button's
        # visible text is the language on screen, which says which one is
        # selected but not what the control is.
        "language": "Language",
        # shown when a daf has no sheet in the reader's language
        "untranslated": "",
        # top of every daf page, and again at the foot
        "disclaimer": "AI-generated study aid, built from the text of the daf. "
                      "It does not replace learning the daf itself.",
        "disclaimer_foot": "This sheet was written by AI from the text of the daf. It can be "
                           "incomplete or mistaken, and it is only a helper for your learning "
                           "— not a substitute for learning the actual daf in the Gemara. "
                           "Check anything you rely on against the source.",
        # The link under the footer, and the one line of the mail it opens that
        # the sender reads. Everything else in that mail is addressed to whoever
        # receives it, so the build writes it in English; see feedback_links.
        "feedback": "Found a mistake? Tell me",
        "feedback_prompt": "What is wrong, or what is missing? Be as precise as you can — "
                           "which section, and what it should say.",
    },
    "es": {
        "chapter": "Capítulo",
        "intro": "Introducción",
        "chazara": "Repaso (Jazará)",
        "cards": "Tarjetas",
        "quiz_head": "Ponte a prueba",
        "cards_intro": "Los términos de arriba, uno por tarjeta. Lee el término, recuerda "
                       "qué significa en este daf, luego gira la tarjeta y di si lo sabías. "
                       "Lo que marques vuelve al final en una segunda ronda, más corta.",
        "tip": "Consejo: pulsa en la tarjeta; luego 1–4 responden y Enter continúa.",
        "cards_tip": "Consejo: pulsa en la tarjeta; la barra espaciadora la gira, ← → navegan, 1 / 2 califican.",
        "daf": "El Daf",
        "daf_mode_scan": "Página impresa",
        "daf_mode_text": "Texto",
        # La única traducción del daf está en inglés, así que no se muestra a
        # quien lee en español: nada aquí la ofrece. Debajo de la página está su
        # texto, pasaje por pasaje, en hebreo y arameo.
        "daf_intro_scan": "La página de Vilna completa, tal como está impresa — la Guemará en "
                          "el centro, Rashi y Tosafot en los márgenes, Masoret HaShas y Ein "
                          "Mishpat a los lados. Ábrela a tamaño completo para leerla con "
                          "comodidad; debajo está su texto, pasaje por pasaje.",
        "daf_intro": "El daf con la disposición de la página impresa: la Guemará en el centro, "
                     "Rashi en el margen interior y Tosafot en el exterior. Nada de esto fue "
                     "escrito por nosotros.",
        "daf_show": "Mostrar",
        "daf_en": "Inglés",
        "daf_sefaria": "Abrir en Sefaria",
        "daf_open_pdf": "Abrir a tamaño completo",
        "daf_lines": "El texto de la página, pasaje por pasaje",
        "daf_note": "Este es el daf mismo — la página de Vilna, no nuestra redacción. "
                    "No está generado por IA.",
        "daf_credit_scan": 'La página de Vilna servida por <a href="https://www.shas.org" '
                           'target="_blank" rel="noopener">shas.org</a>, un PDF por amud.',
        "daf_credit": 'Texto de <a href="https://www.sefaria.org" target="_blank" '
                      'rel="noopener">Sefaria</a>. La Guemará y su traducción provienen del '
                      'Talmud William Davidson, con comentario del rabino Adin Even-Israel '
                      'Steinsaltz (traducción al inglés), '
                      '<a href="https://creativecommons.org/licenses/by-nc/4.0/" '
                      'target="_blank" rel="noopener">CC BY-NC 4.0</a>. Rashi y Tosafot son de '
                      'la edición de Vilna, de dominio público.',
        "tomorrow": "Mañana",
        "archive_title": "Daf Yomi — Archivo",
        "archive_lede": "Todas las hojas de estudio diarias · las más recientes primero",
        "archive_desc": "Todas las hojas de estudio de Daf Yomi, las más recientes primero.",
        "back": "← Volver al daf de hoy",
        "nav_today": "📖 Hoy",
        "nav_archive": "🗂 Archivo",
        "language": "Idioma",
        "untranslated": "Esta hoja todavía no está traducida al español; abajo está la versión en inglés.",
        "disclaimer": "Hoja generada por IA a partir del texto del daf. "
                      "No reemplaza el estudio del daf mismo.",
        "disclaimer_foot": "Esta hoja fue escrita por una inteligencia artificial a partir del "
                           "texto del daf. Puede contener errores u omisiones, y es solo una "
                           "ayuda para tu estudio, no un sustituto de aprender el daf mismo en "
                           "la Guemará. Verifica en la fuente todo aquello en lo que te apoyes.",
        "feedback": "¿Encontraste un error? Avísame",
        "feedback_prompt": "¿Qué está mal, o qué falta? Sé lo más preciso posible: en qué "
                           "sección, y qué debería decir.",
    },
    # Hebrew reads right to left, so an arrow in a label points the other way:
    # "back" is → and "next" is ←. The glyph is not mirrored by the browser —
    # only its position in the line is — so the right one has to be written here.
    "he": {
        "chapter": "פרק",
        "intro": "הקדמה",
        "chazara": "חזרה",
        "cards": "כרטיסיות",
        "quiz_head": "בחנו את עצמכם",
        "cards_intro": "המונחים שלמעלה, אחד לכל כרטיס. קראו את המונח, נסו להיזכר מה משמעותו "
                       "בדף הזה, ואז הפכו את הכרטיס ואמרו אם ידעתם. כל מה שתסמנו יחזור בסוף "
                       "בסיבוב שני, קצר יותר.",
        "tip": "טיפ: הקישו על הכרטיס; אחר כך 1–4 עונים ו-Enter ממשיך.",
        "cards_tip": "טיפ: הקישו על הכרטיס; מקש הרווח הופך אותו, ← → מדפדפים, 1 / 2 מדרגים.",
        "daf": "הדף",
        "daf_mode_scan": "הדף המודפס",
        "daf_mode_text": "טקסט",
        # התרגום היחיד של הדף הוא לאנגלית, ולכן אינו מוצג למי שקורא בעברית —
        # ואין כאן מה שמציע אותו. מתחת לדף מופיע הטקסט שלו, קטע אחר קטע.
        "daf_intro_scan": "דף וילנא כולו כפי שהוא מודפס — הגמרא באמצע, רש״י ותוספות בשוליים, "
                          "מסורת הש״ס ועין משפט בצדדים. פתחו אותו בגודל מלא כדי לקרוא בנוחות; "
                          "מתחתיו מופיע הטקסט שלו, קטע אחר קטע.",
        "daf_intro": "הדף בעימוד שבו הוא מודפס: הגמרא באמצע, רש״י בשוליים הפנימיים ותוספות "
                     "בחיצוניים. שום דבר כאן לא נכתב על ידינו.",
        "daf_show": "הצגה",
        "daf_en": "אנגלית",
        "daf_sefaria": "פתיחה בספריא",
        "daf_open_pdf": "פתיחה בגודל מלא",
        "daf_lines": "טקסט הדף, קטע אחר קטע",
        "daf_note": "זהו הדף עצמו — דף וילנא, ולא כתיבה שלנו. "
                    "הוא אינו מיוצר בבינה מלאכותית.",
        "daf_credit_scan": 'דף וילנא מוגש על ידי <a href="https://www.shas.org" '
                           'target="_blank" rel="noopener">shas.org</a>, קובץ PDF אחד לכל עמוד.',
        "daf_credit": 'הטקסט מתוך <a href="https://www.sefaria.org" target="_blank" '
                      'rel="noopener">ספריא</a>. הגמרא והתרגום מתוך תלמוד ויליאם דוידסון, עם '
                      'פירושו של הרב עדין אבן־ישראל שטיינזלץ (התרגום לאנגלית), '
                      '<a href="https://creativecommons.org/licenses/by-nc/4.0/" '
                      'target="_blank" rel="noopener">CC BY-NC 4.0</a>. רש״י ותוספות הם '
                      'ממהדורת וילנא, נחלת הכלל.',
        "tomorrow": "מחר",
        "archive_title": "דף יומי — ארכיון",
        "archive_lede": "כל דפי הלימוד היומיים · החדשים ביותר תחילה",
        "archive_desc": "כל דפי הלימוד של הדף היומי, החדשים ביותר תחילה.",
        "back": "→ חזרה לדף של היום",
        "nav_today": "📖 היום",
        "nav_archive": "🗂 ארכיון",
        "language": "שפה",
        "untranslated": "הדף הזה עדיין לא תורגם לעברית; למטה מופיעה הגרסה האנגלית.",
        "disclaimer": "דף עזר ללימוד שנוצר בבינה מלאכותית מתוך טקסט הדף. "
                      "אינו מחליף את לימוד הדף עצמו.",
        "disclaimer_foot": "הדף הזה נכתב בידי בינה מלאכותית מתוך טקסט הדף. הוא עלול להיות "
                           "חלקי או שגוי, והוא רק עזר ללימוד — לא תחליף ללימוד הדף עצמו "
                           "בגמרא. בדקו במקור כל דבר שאתם נסמכים עליו.",
        "feedback": "מצאתם טעות? כתבו לי",
        "feedback_prompt": "מה שגוי, או מה חסר? כתבו במדויק כמה שאפשר — באיזה חלק, "
                           "ומה צריך להיות כתוב.",
    },
}


def is_rtl(lang):
    return lang in RTL


def dir_of(lang):
    return "rtl" if is_rtl(lang) else "ltr"


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
