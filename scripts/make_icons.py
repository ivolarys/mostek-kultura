"""Generate PNG icons (apple-touch-icon 180, 192, 512) matching static/icon.svg.

iOS ignores SVG icons on the home screen and rounds the corners itself, so the PNGs are
full-bleed squares (no transparent corners). Run: .venv/bin/python scripts/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parents[1] / "mostek_kultura" / "static"
BG = "#C2552B"
FG = "#FFFFFF"


def draw(size: int) -> Image.Image:
    s = size / 512  # SVG viewBox is 512
    scale = 4
    big = size * scale
    img = Image.new("RGB", (big, big), BG)
    d = ImageDraw.Draw(img)
    k = s * scale
    w = int(24 * k)
    d.rounded_rectangle([96 * k, 140 * k, 416 * k, 412 * k], radius=28 * k, outline=FG, width=w)
    d.line([96 * k, 204 * k, 416 * k, 204 * k], fill=FG, width=w)
    for x in (176, 336):
        d.line([x * k, 100 * k, x * k, 164 * k], fill=FG, width=w)
        d.ellipse([x * k - w / 2, 100 * k - w / 2, x * k + w / 2, 100 * k + w / 2], fill=FG)
    d.ellipse([220 * k, 264 * k, 292 * k, 336 * k], fill=FG)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    for size, name in ((180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        draw(size).save(STATIC / name, optimize=True)
        print("wrote", name)
