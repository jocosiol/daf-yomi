/* Sunset, and which daf that makes today.

   The halachic day begins in the evening, so the daf whose study date is
   Friday goes live at sunset on Thursday. Every page that needs to know this
   reads the same <script type="application/json" id="daf-config"> block:

     { pin: {lat, lon} | null,   // fixed location, or null to guess per visitor
       offset: 0,                // minutes after sunset (40 ≈ tzeis hakochavim)
       self: "Chullin_98.html",  // present only on index.html, which redirects
       dapim: [{f, d}, …] }      // ascending by ISO study date

   Load this in <head>, not deferred, so the router runs before the body
   paints and a stale daf never flashes. */
(function () {
  var TZ = {
    "Asia/Jerusalem": [31.78, 35.21], "Asia/Tel_Aviv": [32.08, 34.78],
    "America/New_York": [40.71, -74.01], "America/Detroit": [42.33, -83.05],
    "America/Chicago": [41.88, -87.63], "America/Denver": [39.74, -104.99],
    "America/Phoenix": [33.45, -112.07], "America/Los_Angeles": [34.05, -118.24],
    "America/Toronto": [43.65, -79.38], "America/Montreal": [45.50, -73.57],
    "America/Vancouver": [49.28, -123.12], "America/Mexico_City": [19.43, -99.13],
    "America/Sao_Paulo": [-23.55, -46.63], "America/Argentina/Buenos_Aires": [-34.60, -58.38],
    "America/Panama": [8.98, -79.52], "America/Bogota": [4.71, -74.07],
    "Europe/London": [51.51, -0.13], "Europe/Dublin": [53.35, -6.26],
    "Europe/Paris": [48.86, 2.35], "Europe/Brussels": [50.85, 4.35],
    "Europe/Amsterdam": [52.37, 4.90], "Europe/Berlin": [52.52, 13.40],
    "Europe/Zurich": [47.38, 8.54], "Europe/Vienna": [48.21, 16.37],
    "Europe/Rome": [41.90, 12.50], "Europe/Madrid": [40.42, -3.70],
    "Europe/Prague": [50.08, 14.44], "Europe/Budapest": [47.50, 19.04],
    "Europe/Warsaw": [52.23, 21.01], "Europe/Kiev": [50.45, 30.52],
    "Europe/Moscow": [55.76, 37.62], "Europe/Istanbul": [41.01, 28.98],
    "Australia/Sydney": [-33.87, 151.21], "Australia/Melbourne": [-37.81, 144.96],
    "Australia/Perth": [-31.95, 115.86], "Pacific/Auckland": [-36.85, 174.76],
    "Africa/Johannesburg": [-26.20, 28.05], "Asia/Hong_Kong": [22.32, 114.17],
    "Asia/Tokyo": [35.68, 139.69], "Asia/Shanghai": [31.23, 121.47],
    "Asia/Singapore": [1.35, 103.82], "Asia/Kolkata": [19.08, 72.88]
  };

  function guess() {
    var tz = "";
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    if (TZ[tz]) return { lat: TZ[tz][0], lon: TZ[tz][1], src: tz };
    // Unknown zone: longitude from the UTC offset is good; latitude is a temperate guess.
    return { lat: 32, lon: -new Date().getTimezoneOffset() / 4, src: "utc-offset" };
  }

  /* Sunset as a UTC instant for the given local calendar date, or null at the
     poles. NOAA/standard sunrise equation; validated against known times for
     Jerusalem, New York, London, Los Angeles and Melbourne (within ~5 min).
     Longitude is EAST-positive. */
  function sunset(Y, M, D, lat, lon) {
    var rad = Math.PI / 180;
    var a = Math.floor((14 - M) / 12), y = Y + 4800 - a, m = M + 12 * a - 3;
    var JDN = D + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4)
            - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
    var n = JDN - 2451545.0 + 0.0008, Js = n - lon / 360;
    var Ma = (357.5291 + 0.98560028 * Js) % 360;
    var C = 1.9148 * Math.sin(Ma * rad) + 0.0200 * Math.sin(2 * Ma * rad)
          + 0.0003 * Math.sin(3 * Ma * rad);
    var L = (Ma + C + 180 + 102.9372) % 360;
    var Jtr = 2451545.0 + Js + 0.0053 * Math.sin(Ma * rad) - 0.0069 * Math.sin(2 * L * rad);
    var dec = Math.asin(Math.sin(L * rad) * Math.sin(23.4397 * rad)) / rad;
    var co = (Math.sin(-0.833 * rad) - Math.sin(lat * rad) * Math.sin(dec * rad))
           / (Math.cos(lat * rad) * Math.cos(dec * rad));
    if (co > 1 || co < -1) return null;            // polar night / midnight sun
    return new Date(((Jtr + (Math.acos(co) / rad) / 360) - 2440587.5) * 86400000);
  }

  /* The halachic date as an ISO string: today's civil date, +1 once the sun has set. */
  window.dafToday = function (pin, offsetMin) {
    var loc = pin || guess(), now = new Date();
    var ss = sunset(now.getFullYear(), now.getMonth() + 1, now.getDate(), loc.lat, loc.lon);
    var eff = new Date(now.getTime());
    if (ss && now.getTime() >= ss.getTime() + (offsetMin || 0) * 60000) {
      eff.setDate(eff.getDate() + 1);
    }
    var p = function (x) { return String(x).padStart(2, "0"); };
    return {
      date: eff.getFullYear() + "-" + p(eff.getMonth() + 1) + "-" + p(eff.getDate()),
      sunset: ss,
      loc: loc
    };
  };

  var el = document.getElementById("daf-config");
  if (!el) return;
  var cfg;
  try { cfg = JSON.parse(el.textContent); } catch (e) { return; }
  var dapim = cfg.dapim || [];

  window.dafConfig = cfg;
  window.dafCurrent = function () {
    var today = window.dafToday(cfg.pin, cfg.offset).date, target = null;
    for (var i = 0; i < dapim.length; i++) {
      if (dapim[i].d <= today) target = dapim[i];
    }
    return target || dapim[0] || null;   // nothing published yet: show the earliest
  };

  // ---- index.html: self-correct by date, before the body paints ----
  if (cfg.self && dapim.length) {
    var target = window.dafCurrent();
    if (target && target.f !== cfg.self) {
      // keep the query string so ?lang=es survives the hop to the current daf
      location.replace(target.f + location.search + location.hash);
    }
  }

  // ---- archive.html: mark today, dim the future, name the sunset ----
  var STR = {
    en: { today: "Today", recent: "Most recent",
          zman: function (t) {
            return "The daf turns over at sunset — today's sunset is " + t + " local time.";
          } },
    es: { today: "Hoy", recent: "Más reciente",
          zman: function (t) {
            return "El daf cambia al atardecer — hoy el atardecer es a las " + t + ", hora local.";
          } }
  };

  document.addEventListener("DOMContentLoaded", function () {
    var list = document.getElementById("list");
    if (!list) return;
    var z = window.dafToday(cfg.pin, cfg.offset), today = z.date, cur = null;
    Array.prototype.slice.call(list.querySelectorAll("li[data-date]")).forEach(function (li) {
      var d = li.dataset.date;
      if (!d) return;
      if (d > today) li.classList.add("future");
      else if (!cur || d > cur.dataset.date) cur = li;
    });

    var badge = null;
    if (cur) {
      cur.classList.add("today");
      badge = document.createElement("span");
      badge.className = "badge";
      cur.appendChild(badge);
    }

    function paint() {
      var l = window.dafLang ? window.dafLang() : "en";
      var s = STR[l] || STR.en;
      if (badge) badge.textContent = cur.dataset.date === today ? s.today : s.recent;
      var zEl = document.getElementById("zman");
      if (zEl && z.sunset) {
        zEl.textContent = s.zman(
          z.sunset.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }));
      }
    }
    paint();
    document.addEventListener("daflang", paint);
  });
})();
