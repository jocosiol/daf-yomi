#!/usr/bin/env python3
"""Draw the home-screen icons into static/.

The icons are committed, not built on every run: they change about never, and
build.py has no image dependency. Re-run this by hand after editing the design:

    python3 build/icons.py

The mark is the site's own palette — parchment field, gold frame, דף in ink —
so the tile on a phone home screen reads like the top of a sheet.
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")

PARCHMENT = "#f4ecd8"
INK = "#2c261d"
GOLD = "#c9a86a"

# Times has a Hebrew face on macOS, and its דף is a book letterform rather than
# a UI one — the same register as the sheet's serif body text.
FONT = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"

# Pillow here is built without Raqm, so it lays glyphs out left to right and
# never applies the bidi algorithm. The word is דף; drawing it in visual order
# means handing it over reversed.
WORD = "דף"[::-1]

# Drawn large and downsampled: the frame's corners and the ף descender stay
# clean at 60px, which is all an iPhone ever shows of this.
MASTER = 1024


def fit(text, box_w, box_h):
    """Largest font size whose text fits inside the box."""
    size = 8
    while True:
        nxt = ImageFont.truetype(FONT, size + 8)
        l, t, r, b = nxt.getbbox(text)
        if r - l > box_w or b - t > box_h:
            return ImageFont.truetype(FONT, size)
        size += 8


def draw(scale=1.0, frame=True):
    """One icon at master size. `scale` shrinks the artwork inside the tile.

    A maskable icon may be cropped to a circle by the launcher, so its artwork
    is drawn small enough to survive that crop; the plain icon fills the tile.
    """
    im = Image.new("RGB", (MASTER, MASTER), PARCHMENT)
    d = ImageDraw.Draw(im)
    s = MASTER * scale
    cx = cy = MASTER / 2

    if frame:
        half = s * 0.40
        d.rounded_rectangle([cx - half, cy - half, cx + half, cy + half],
                            radius=s * 0.10, outline=GOLD, width=int(s * 0.022))

    f = fit(WORD, s * 0.54, s * 0.44)
    l, t, r, b = f.getbbox(WORD)
    d.text((cx - (l + r) / 2, cy - (t + b) / 2), WORD, font=f, fill=INK)
    return im


def save(im, name, size):
    im.resize((size, size), Image.LANCZOS).save(os.path.join(STATIC, name))
    print(f"  {name}  {size}x{size}")


def main():
    plain = draw()
    # iOS rounds the corners of apple-touch-icon itself and ignores alpha.
    save(plain, "icon-180.png", 180)
    save(plain, "icon-192.png", 192)
    save(plain, "icon-512.png", 512)
    save(plain, "icon-32.png", 32)
    # Android may crop to any shape inside the outer 20%; keep the mark clear of it.
    save(draw(scale=0.72), "icon-maskable-512.png", 512)


if __name__ == "__main__":
    main()
