#!/usr/bin/env python3
"""Assemble the Daf Yomi GitHub Pages site — FLAT layout (no subfolders),
so it uploads cleanly via GitHub's web uploader.

Usage:
  python3 build_site.py <site_dir> <new_daf_html> <Tractate> <page>   # add/refresh a daf
  python3 build_site.py <site_dir>                                    # rebuild from what's there

- <Tractate>_<page>.html = archived copy of each daf (root level)
- index.html            = today's daf + a router that self-corrects by date
- archive.html          = list of all dapim, newest first

index.html is seeded with whichever daf matches today's date, and carries an
inline manifest of every daf's study date. On load it re-checks the date and
redirects to the right daf, so the homepage rolls over on its own — build
several dapim ahead, push once, and it stays correct.

Study dates are read out of each sheet's "Study date: ..." line, so the
calendar is never reimplemented here.
"""
import sys, os, re, glob, json, datetime

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
site = args[0]
src = tractate = page = None
if len(args) >= 4:
    src, tractate, page = args[1], args[2], args[3]
elif len(args) != 1:
    sys.exit("usage: build_site.py <site_dir> [<new_daf_html> <Tractate> <page>]")
os.makedirs(site, exist_ok=True)

NAV_CSS = """
<style id="site-nav-css">
#site-nav{position:fixed;top:12px;right:14px;z-index:50;display:flex;gap:8px}
#site-nav a{font-family:Georgia,serif;font-size:.85rem;text-decoration:none;
  background:#fffdf8;color:#6b3f1d;border:1px solid #c9a86a;border-radius:999px;
  padding:6px 14px;box-shadow:0 3px 12px rgba(80,55,20,.12)}
#site-nav a:hover{background:#6b3f1d;color:#fff}
@media print{#site-nav{display:none}}
</style>
"""

# Router runs in <head>, before the body paints, so a stale daf never flashes.
ROUTER_JS = """
<script id="daf-router">
(function(){
  var SELF = __SELF__, DAPIM = __MANIFEST__;   // DAPIM sorted ascending by .d (ISO date)
  if(!DAPIM.length) return;
  var n = new Date(), p = function(x){return String(x).padStart(2,"0")};
  var today = n.getFullYear()+"-"+p(n.getMonth()+1)+"-"+p(n.getDate());
  var target = null;
  for(var i=0;i<DAPIM.length;i++){ if(DAPIM[i].d <= today) target = DAPIM[i]; }
  if(!target) target = DAPIM[0];               // nothing published yet: show the earliest
  if(target.f !== SELF) location.replace(target.f + location.hash);
})();
</script>
"""

def with_nav(html, is_index):
    nav = '<div id="site-nav">'
    if not is_index:
        nav += '<a href="index.html">📖 Today</a>'
    nav += '<a href="archive.html">🗂 Archive</a></div>'
    if "site-nav-css" not in html:
        html = html.replace("</head>", NAV_CSS + "</head>", 1)
    # \s* so re-running is a no-op instead of accumulating a blank line each build
    html = re.sub(r'<div id="site-nav">.*?</div>\s*', "", html, flags=re.S)
    html = re.sub(r'\s*<script id="daf-router">.*?</script>\s*', "", html, flags=re.S)
    return html.replace("<body>", "<body>\n" + nav + "\n", 1)

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june",
     "july", "august", "september", "october", "november", "december"])}

def iso_date(text):
    """'Wed, 6 August 2026' / 'Aug 6, 2026' -> '2026-08-06' (None if unparseable)."""
    if not text:
        return None
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text) \
        or re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", text)
    if not m:
        return None
    a, b, year = m.groups()
    day, mon = (a, b) if a.isdigit() else (b, a)
    for name, num in MONTHS.items():
        if name.startswith(mon.lower()[:3]):
            return f"{int(year):04d}-{num:02d}-{int(day):02d}"
    return None

# ---- archived copy of the incoming daf (written first so it lands in the manifest) ----
if src:
    raw = open(src, encoding="utf-8").read()
    open(os.path.join(site, f"{tractate}_{page}.html"), "w", encoding="utf-8").write(
        with_nav(raw, False))

# ---- scan every daf at root, refresh its nav, collect study dates ----
items = []
for f in sorted(glob.glob(os.path.join(site, "*.html"))):
    base = os.path.basename(f)
    if base in ("index.html", "archive.html"):
        continue
    txt = open(f, encoding="utf-8").read()
    fixed = with_nav(txt, False)
    if fixed != txt:
        open(f, "w", encoding="utf-8").write(fixed)
    md = re.search(r"Study date:\s*([^<·]+)", txt)
    when = md.group(1).strip() if md else ""
    items.append({
        "file": base,
        "label": base.replace("_", " ").replace(".html", ""),
        "when": when,
        "iso": iso_date(when),
    })

if not items:
    sys.exit(f"No daf pages found in {site} — pass a daf to add one.")

dated = sorted([i for i in items if i["iso"]], key=lambda i: i["iso"])
undated = [i for i in items if not i["iso"]]
for i in undated:
    print(f"  ! no study date parsed in {i['file']} — archive only, not routed")

manifest = [{"f": i["file"], "d": i["iso"]} for i in dated]

# ---- index.html = the daf that is current *today*, plus the router ----
today = datetime.date.today().isoformat()
seed = next((i for i in reversed(dated) if i["iso"] <= today), None) \
    or (dated[0] if dated else items[0])
seed_html = open(os.path.join(site, seed["file"]), encoding="utf-8").read()
router = (ROUTER_JS
          .replace("__SELF__", json.dumps(seed["file"]))
          .replace("__MANIFEST__", json.dumps(manifest, separators=(",", ":"))))
index_html = with_nav(seed_html, True).replace("</head>", router + "</head>", 1)
open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(index_html)

# ---- archive.html, newest first, with a client-side "Today" badge ----
def sort_key(i):
    n = re.search(r"(\d+)", i["label"])
    return (i["iso"] or "", int(n.group(1)) if n else 0)

rows = "\n".join(
    f' <li data-date="{i["iso"] or ""}"><a href="{i["file"]}">{i["label"]}</a>'
    f'{(" &middot; <span>" + i["when"] + "</span>") if i["when"] else ""}</li>'
    for i in sorted(items, key=sort_key, reverse=True)
)

archive_html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daf Yomi — Archive</title>
<style>
 body{{background:linear-gradient(180deg,#f4ecd8,#fbf7ee 260px) fixed;color:#2c261d;
   font-family:Georgia,serif;max-width:640px;margin:0 auto;padding:40px 22px 80px;line-height:1.6}}
 h1{{color:#6b3f1d;text-align:center;font-size:1.9rem;margin-bottom:4px}}
 .sub{{text-align:center;color:#7a6a4d;font-style:italic;margin-bottom:28px}}
 ul{{list-style:none;padding:0}}
 li{{background:#fffdf8;border:1px solid #e2d3b3;border-radius:12px;margin:10px 0;padding:14px 18px;
   box-shadow:0 4px 16px rgba(80,55,20,.08)}}
 li a{{color:#8a5a2b;text-decoration:none;font-weight:700;font-size:1.1rem}}
 li a:hover{{text-decoration:underline}} li span{{color:#9a8a6d;font-size:.9rem}}
 li.today{{border-color:#c9a86a;box-shadow:0 4px 18px rgba(140,100,40,.18)}}
 li.today .badge{{background:#6b3f1d;color:#fff;border-radius:999px;padding:2px 10px;
   font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;margin-left:8px}}
 li.future{{opacity:.6}}
 .home{{display:block;text-align:center;margin-top:26px}} .home a{{color:#6b3f1d}}
</style></head>
<body>
 <h1>Daf Yomi — Archive</h1>
 <div class="sub">Every daily study sheet · newest first</div>
 <ul id="list">
{rows}
 </ul>
 <div class="home"><a href="index.html">← Back to today's daf</a></div>
<script>
(function(){{
  var n = new Date(), p = function(x){{return String(x).padStart(2,"0")}};
  var today = n.getFullYear()+"-"+p(n.getMonth()+1)+"-"+p(n.getDate());
  var li = [].slice.call(document.querySelectorAll("#list li[data-date]"));
  var cur = null;
  li.forEach(function(el){{
    var d = el.dataset.date;
    if(!d) return;
    if(d > today) el.classList.add("future");
    else if(!cur || d > cur.dataset.date) cur = el;
  }});
  if(cur){{
    cur.classList.add("today");
    var b = document.createElement("span");
    b.className = "badge";
    b.textContent = cur.dataset.date === today ? "Today" : "Most recent";
    cur.appendChild(b);
  }}
}})();
</script>
</body></html>"""
open(os.path.join(site, "archive.html"), "w", encoding="utf-8").write(archive_html)
open(os.path.join(site, ".nojekyll"), "w").write("")

print(f"Built FLAT site in {site}: {len(items)} daf pages, {len(manifest)} routed")
print(f"index.html seeded with {seed['label']} ({seed['iso']}), self-corrects by date")
if dated:
    print(f"schedule: {dated[0]['iso']} … {dated[-1]['iso']}")
