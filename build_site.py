#!/usr/bin/env python3
"""Assemble the Daf Yomi GitHub Pages site — FLAT layout (no subfolders),
so it uploads cleanly via GitHub's web uploader.

Usage:
  python3 build_site.py <site_dir> <new_daf_html> <Tractate> <page>   # add/refresh a daf
  python3 build_site.py <site_dir>                                    # rebuild from what's there

Options:
  --at LAT,LON    pin the sunset location for every visitor (default: per-visitor,
                  guessed from the browser timezone). e.g. --at 31.7683,35.2137
  --offset MIN    minutes after sunset to roll over (default 0 = shkia).
                  Use e.g. --offset 40 for an approximate tzeis hakochavim.

- <Tractate>_<page>.html = archived copy of each daf (root level)
- index.html            = today's daf + a router that self-corrects by date
- archive.html          = list of all dapim, newest first

index.html carries an inline manifest of every daf's study date and rolls over at
SUNSET, not midnight — the halachic day begins in the evening, so the daf whose
study date is Friday goes live at sunset on Thursday. Build dapim ahead, push
once, and the homepage tracks the calendar on its own.

Study dates are read out of each sheet's "Study date: ..." line, so the Daf Yomi
cycle is never reimplemented here.
"""
import sys, os, re, glob, json, datetime

# ---- args ----
argv = sys.argv[1:]
pin = None
offset = 0
rest = []
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--at" and i + 1 < len(argv):
        m = re.match(r"^\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*$", argv[i + 1])
        if not m:
            sys.exit("--at wants LAT,LON  e.g. --at 31.7683,35.2137")
        pin = {"lat": float(m.group(1)), "lon": float(m.group(2))}
        i += 2
    elif a == "--offset" and i + 1 < len(argv):
        offset = int(argv[i + 1]); i += 2
    else:
        rest.append(a); i += 1

if not rest:
    sys.exit(__doc__)
site = rest[0]
src = tractate = page = None
if len(rest) >= 4:
    src, tractate, page = rest[1], rest[2], rest[3]
elif len(rest) != 1:
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

# Sunset + "which halachic day is it" helper, shared by index and archive.
# Sunset is the NOAA/standard sunrise equation; validated against known times for
# Jerusalem, New York, London, Los Angeles and Melbourne (all within ~5 minutes).
# Longitude is EAST-positive.
ZMAN_JS = r"""
<script id="daf-zman">
(function(){
  var TZ = {
    "Asia/Jerusalem":[31.78,35.21],"Asia/Tel_Aviv":[32.08,34.78],
    "America/New_York":[40.71,-74.01],"America/Detroit":[42.33,-83.05],
    "America/Chicago":[41.88,-87.63],"America/Denver":[39.74,-104.99],
    "America/Phoenix":[33.45,-112.07],"America/Los_Angeles":[34.05,-118.24],
    "America/Toronto":[43.65,-79.38],"America/Montreal":[45.50,-73.57],
    "America/Vancouver":[49.28,-123.12],"America/Mexico_City":[19.43,-99.13],
    "America/Sao_Paulo":[-23.55,-46.63],"America/Argentina/Buenos_Aires":[-34.60,-58.38],
    "America/Panama":[8.98,-79.52],"America/Bogota":[4.71,-74.07],
    "Europe/London":[51.51,-0.13],"Europe/Dublin":[53.35,-6.26],
    "Europe/Paris":[48.86,2.35],"Europe/Brussels":[50.85,4.35],
    "Europe/Amsterdam":[52.37,4.90],"Europe/Berlin":[52.52,13.40],
    "Europe/Zurich":[47.38,8.54],"Europe/Vienna":[48.21,16.37],
    "Europe/Rome":[41.90,12.50],"Europe/Madrid":[40.42,-3.70],
    "Europe/Prague":[50.08,14.44],"Europe/Budapest":[47.50,19.04],
    "Europe/Warsaw":[52.23,21.01],"Europe/Kiev":[50.45,30.52],
    "Europe/Moscow":[55.76,37.62],"Europe/Istanbul":[41.01,28.98],
    "Australia/Sydney":[-33.87,151.21],"Australia/Melbourne":[-37.81,144.96],
    "Australia/Perth":[-31.95,115.86],"Pacific/Auckland":[-36.85,174.76],
    "Africa/Johannesburg":[-26.20,28.05],"Asia/Hong_Kong":[22.32,114.17],
    "Asia/Tokyo":[35.68,139.69],"Asia/Shanghai":[31.23,121.47],
    "Asia/Singapore":[1.35,103.82],"Asia/Kolkata":[19.08,72.88]
  };
  function guess(){
    var tz=""; try{ tz=Intl.DateTimeFormat().resolvedOptions().timeZone||"" }catch(e){}
    if(TZ[tz]) return {lat:TZ[tz][0], lon:TZ[tz][1], src:tz};
    // Unknown zone: longitude from the UTC offset is good; latitude is a temperate guess.
    return {lat:32, lon:-new Date().getTimezoneOffset()/4, src:"utc-offset"};
  }
  // Sunset as a UTC instant for the given local calendar date, or null at the poles.
  function sunset(Y,M,D,lat,lon){
    var rad=Math.PI/180;
    var a=Math.floor((14-M)/12), y=Y+4800-a, m=M+12*a-3;
    var JDN=D+Math.floor((153*m+2)/5)+365*y+Math.floor(y/4)-Math.floor(y/100)
            +Math.floor(y/400)-32045;
    var n=JDN-2451545.0+0.0008, Js=n-lon/360;
    var Ma=(357.5291+0.98560028*Js)%360;
    var C=1.9148*Math.sin(Ma*rad)+0.0200*Math.sin(2*Ma*rad)+0.0003*Math.sin(3*Ma*rad);
    var L=(Ma+C+180+102.9372)%360;
    var Jtr=2451545.0+Js+0.0053*Math.sin(Ma*rad)-0.0069*Math.sin(2*L*rad);
    var dec=Math.asin(Math.sin(L*rad)*Math.sin(23.4397*rad))/rad;
    var co=(Math.sin(-0.833*rad)-Math.sin(lat*rad)*Math.sin(dec*rad))
           /(Math.cos(lat*rad)*Math.cos(dec*rad));
    if(co>1||co<-1) return null;                       // polar night / midnight sun
    return new Date(((Jtr+(Math.acos(co)/rad)/360)-2440587.5)*86400000);
  }
  // The halachic date as an ISO string: today's civil date, +1 once the sun has set.
  window.dafToday = function(pin, offsetMin){
    var loc = pin || guess(), now = new Date();
    var ss = sunset(now.getFullYear(), now.getMonth()+1, now.getDate(), loc.lat, loc.lon);
    var eff = new Date(now.getTime());
    if(ss && now.getTime() >= ss.getTime() + (offsetMin||0)*60000) eff.setDate(eff.getDate()+1);
    var p=function(x){return String(x).padStart(2,"0")};
    return {date: eff.getFullYear()+"-"+p(eff.getMonth()+1)+"-"+p(eff.getDate()),
            sunset: ss, loc: loc};
  };
})();
</script>
"""

# Router runs in <head>, before the body paints, so a stale daf never flashes.
ROUTER_JS = """
<script id="daf-router">
(function(){
  var SELF = __SELF__, DAPIM = __MANIFEST__;   // DAPIM sorted ascending by .d (ISO date)
  if(!DAPIM.length || !window.dafToday) return;
  var today = window.dafToday(__PIN__, __OFFSET__).date;
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
    html = re.sub(r'\s*<script id="daf-zman">.*?</script>\s*', "", html, flags=re.S)
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
for i in [i for i in items if not i["iso"]]:
    print(f"  ! no study date parsed in {i['file']} — archive only, not routed")

manifest = [{"f": i["file"], "d": i["iso"]} for i in dated]
PIN_JS = json.dumps(pin) if pin else "null"

# ---- index.html = the daf current at build time, plus the router ----
today = datetime.date.today().isoformat()
seed = next((i for i in reversed(dated) if i["iso"] <= today), None) \
    or (dated[0] if dated else items[0])
seed_html = open(os.path.join(site, seed["file"]), encoding="utf-8").read()
router = (ROUTER_JS
          .replace("__SELF__", json.dumps(seed["file"]))
          .replace("__MANIFEST__", json.dumps(manifest, separators=(",", ":")))
          .replace("__PIN__", PIN_JS)
          .replace("__OFFSET__", str(offset)))
index_html = with_nav(seed_html, True).replace("</head>", ZMAN_JS + router + "</head>", 1)
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
{ZMAN_JS}<style>
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
 .zman{{text-align:center;color:#9a8a6d;font-size:.8rem;margin-top:18px}}
</style></head>
<body>
 <h1>Daf Yomi — Archive</h1>
 <div class="sub">Every daily study sheet · newest first</div>
 <ul id="list">
{rows}
 </ul>
 <div class="zman" id="zman"></div>
 <div class="home"><a href="index.html">← Back to today's daf</a></div>
<script>
(function(){{
  var z = window.dafToday({PIN_JS}, {offset}), today = z.date, cur = null;
  [].slice.call(document.querySelectorAll("#list li[data-date]")).forEach(function(el){{
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
  if(z.sunset){{
    var t = z.sunset.toLocaleTimeString([], {{hour:"numeric", minute:"2-digit"}});
    document.getElementById("zman").textContent =
      "The daf turns over at sunset — today's sunset is " + t + " local time.";
  }}
}})();
</script>
</body></html>"""
open(os.path.join(site, "archive.html"), "w", encoding="utf-8").write(archive_html)
open(os.path.join(site, ".nojekyll"), "w").write("")

where = f"pinned to {pin['lat']},{pin['lon']}" if pin else "per-visitor (browser timezone)"
print(f"Built FLAT site in {site}: {len(items)} daf pages, {len(manifest)} routed")
print(f"index.html seeded with {seed['label']} ({seed['iso']})")
print(f"rollover: sunset{f' + {offset} min' if offset else ''}, location {where}")
if dated:
    print(f"schedule: {dated[0]['iso']} … {dated[-1]['iso']}")
