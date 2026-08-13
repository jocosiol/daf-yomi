/* The "found a mistake?" link, finished in the browser.

   The page ships the mail without its address: each link carries only the
   prefilled subject and body in data-q, and the address sits in the config
   block as hex XOR'd with a key written in front of it (build.py's hide_email).
   That is obfuscation, not secrecy — this file is served to everyone, and
   anything that runs it can read the address back. It defeats the crawler that
   reads HTML and regexes it for something@something, which is what harvests an
   address published on 2,700 pages.

   So the link is hidden in the markup and revealed here, rather than shown and
   then repaired: with JavaScript off it would be a link with nowhere to go, and
   an invitation that does nothing when tapped is worse than no invitation. */
(function () {
  var links = document.querySelectorAll(".feedback a[data-q]");
  if (!links.length) return;

  var cfg = {};
  var el = document.getElementById("daf-config");
  if (el) { try { cfg = JSON.parse(el.textContent) || {}; } catch (e) {} }

  var hex = cfg.mail || "";
  // The key is the first byte; the address is the rest.
  if (hex.length < 4 || hex.length % 2) return;
  var key = parseInt(hex.substr(0, 2), 16), addr = "";
  for (var i = 2; i < hex.length; i += 2) {
    addr += String.fromCharCode(parseInt(hex.substr(i, 2), 16) ^ key);
  }
  if (addr.indexOf("@") < 0) return;

  for (var n = 0; n < links.length; n++) {
    links[n].href = "mailto:" + addr + "?" + links[n].getAttribute("data-q");
  }
  var block = links[0].closest(".feedback");
  if (block) block.hidden = false;
})();
