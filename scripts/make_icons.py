"""Generate Mostkultura logo and app icons from one canonical mark geometry.

The PNG icons use a full-bleed coral background because iOS and maskable web app
icons apply their own corner treatment. Run: .venv/bin/python scripts/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parents[1] / "mostek_kultura" / "static"
CORAL = "#E45E3D"
CORAL_RGB = (228, 94, 61)
WHITE = (255, 255, 255)

# These commands are the source of truth for the standalone logo, favicon and PNGs.
BRIDGE_COMMANDS = [
    ("M", 18, 96), ("V", 65), ("C", 18, 45, 29, 33, 46, 33),
    ("C", 54, 33, 60, 36, 64, 41), ("C", 69, 36, 75, 33, 83, 33),
    ("C", 101, 33, 112, 45, 112, 65), ("V", 96), ("H", 94), ("V", 65),
    ("C", 94, 56, 90, 51, 83, 51), ("C", 76, 51, 73, 56, 73, 65),
    ("V", 96), ("H", 55), ("V", 65), ("C", 55, 56, 51, 51, 46, 51),
    ("C", 39, 51, 36, 56, 36, 65), ("V", 96), ("Z",),
]
SPARKLE_COMMANDS = [
    ("M", 102, 5), ("C", 104, 13, 106, 15, 114, 17),
    ("C", 106, 19, 104, 21, 102, 29), ("C", 100, 21, 98, 19, 90, 17),
    ("C", 98, 15, 100, 13, 102, 5), ("Z",),
]


def _path_string(commands: list[tuple]) -> str:
    return "".join(op + " ".join(str(value) for value in values) for op, *values in commands)


def logo_svg(fill: str = CORAL) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 112">
<g fill="{fill}">
<path d="{_path_string(BRIDGE_COMMANDS)}"/>
<path d="{_path_string(SPARKLE_COMMANDS)}"/>
</g>
</svg>
'''


def favicon_svg() -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="112" fill="{CORAL}"/>
<g transform="translate(64 80) scale(3)" fill="#fff">
<path d="{_path_string(BRIDGE_COMMANDS)}"/>
<path d="{_path_string(SPARKLE_COMMANDS)}"/>
</g>
</svg>
'''


def _cubic(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float], steps: int = 16):
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        yield (
            u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
        )


def _path_points(commands: list[tuple]) -> list[tuple[float, float]]:
    """Sample the small M/V/H/C/Z path subset used by the canonical mark."""
    points: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    start = current
    for command in commands:
        op, values = command[0], command[1:]
        if op == "M":
            current = (float(values[0]), float(values[1]))
            start = current
            points.append(current)
        elif op == "V":
            current = (current[0], float(values[0]))
            points.append(current)
        elif op == "H":
            current = (float(values[0]), current[1])
            points.append(current)
        elif op == "C":
            p1, p2, p3 = (tuple(map(float, values[i : i + 2])) for i in (0, 2, 4))
            points.extend(_cubic(current, p1, p2, p3))
            current = p3
        elif op == "Z":
            points.append(start)
            current = start
        else:  # pragma: no cover - paths above are deliberately fixed
            raise ValueError(f"Unsupported path command: {op}")
    return points


def _scaled(points: list[tuple[float, float]], scale: float, tx: float = 0, ty: float = 0):
    return [(x * scale + tx, y * scale + ty) for x, y in points]


def draw_icon(size: int) -> Image.Image:
    # Render at 4x then downsample for smooth curves and small 180px output.
    supersample = 4
    canvas = size * supersample
    img = Image.new("RGB", (canvas, canvas), CORAL_RGB)
    draw = ImageDraw.Draw(img)
    mark_scale = 3 * supersample * size / 512
    tx = 64 * supersample * size / 512
    ty = 80 * supersample * size / 512
    draw.polygon(_scaled(_path_points(BRIDGE_COMMANDS), mark_scale, tx, ty), fill=WHITE)
    draw.polygon(_scaled(_path_points(SPARKLE_COMMANDS), mark_scale, tx, ty), fill=WHITE)
    return img.resize((size, size), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    STATIC.mkdir(parents=True, exist_ok=True)
    (STATIC / "logo.svg").write_text(logo_svg(), encoding="utf-8")
    (STATIC / "logo-monochrome.svg").write_text(logo_svg("currentColor"), encoding="utf-8")
    (STATIC / "icon.svg").write_text(favicon_svg(), encoding="utf-8")
    print("wrote logo.svg, logo-monochrome.svg, icon.svg")
    for size, name in ((180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        draw_icon(size).save(STATIC / name, optimize=True)
        print("wrote", name)
