#!/usr/bin/env python3
"""Convert the Daf Yomi markdown study sheet to a nicely styled, Hebrew-aware PDF."""
import sys, re, markdown
from playwright.sync_api import sync_playwright

src = sys.argv[1]
out = sys.argv[2]

with open(src, encoding="utf-8") as f:
    md_text = f.read()

html_body = markdown.markdown(
    md_text,
    extensions=["tables", "sane_lists", "smarty"],
)

# Tag Hebrew-containing runs so the browser applies RTL bidi cleanly.
# (Chromium already does Unicode bidi; explicit dir=auto keeps punctuation tidy.)

CSS = """
@page { size: A4; margin: 18mm 16mm 16mm 16mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: "FreeSerif", "Liberation Serif", "DejaVu Serif", serif;
  font-size: 11.5pt; line-height: 1.5; color: #24201b;
  max-width: 720px; margin: 0 auto;
}
:lang(he), [dir="rtl"] { font-family: "FreeSerif", "DejaVu Sans", serif; }
h1 {
  font-family: "FreeSans", "Liberation Sans", sans-serif;
  font-size: 20pt; color: #6b3f1d; margin: 0 0 2pt;
  border-bottom: 3px solid #c9a86a; padding-bottom: 6pt;
}
h2 {
  font-family: "FreeSans", "Liberation Sans", sans-serif;
  font-size: 14.5pt; color: #7a4a22; margin: 20pt 0 6pt;
  border-bottom: 1px solid #e2d3b3; padding-bottom: 3pt;
}
h3 {
  font-family: "FreeSans", "Liberation Sans", sans-serif;
  font-size: 12pt; color: #8a5a2b; margin: 14pt 0 4pt;
}
p { margin: 6pt 0; }
strong { color: #5a3a17; }
em { color: #6b5033; }
blockquote {
  margin: 10pt 0; padding: 8pt 14pt; background: #faf5ea;
  border-left: 4px solid #c9a86a; border-radius: 3px; font-style: italic;
}
ul { margin: 6pt 0; padding-left: 20pt; }
li { margin: 3pt 0; }
table {
  border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 10.5pt;
}
th, td { border: 1px solid #ddcba0; padding: 5pt 8pt; text-align: left; vertical-align: top; }
th { background: #f0e4c8; color: #5a3a17; }
tr:nth-child(even) td { background: #fbf7ee; }
hr { border: none; border-top: 1px solid #e2d3b3; margin: 16pt 0; }
h2, h3 { break-after: avoid; }
table, blockquote, li { break-inside: avoid; }
"""

full_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body>{html_body}</body></html>"""

import os, tempfile, pathlib
tmp_html = os.path.join(tempfile.gettempdir(), "_sheet.html")
with open(tmp_html, "w", encoding="utf-8") as f:
    f.write(full_html)

import glob
chrome_candidates = sorted(glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome"))
chrome_path = chrome_candidates[0] if chrome_candidates else None

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome_path)
    page = browser.new_page()
    page.goto(pathlib.Path(tmp_html).as_uri())
    page.pdf(path=out, format="A4", print_background=True,
             margin={"top": "18mm", "bottom": "16mm", "left": "16mm", "right": "16mm"})
    browser.close()

print("PDF written:", out)
