"""Generates the DB Playground app icon (AppIcon.icns) from scratch with
Pillow -- no external SVG rasterizer needed, so this runs anywhere Python
does.

The design deliberately reuses the frontend's own brand mark instead of
inventing a new one: a lime rounded square (--lime, --ink from
frontend/src/styles.css) with lucide's "Database" glyph, stroke-drawn to
match how lucide-react actually renders it in the sidebar
(frontend/src/components/Sidebar.tsx's .brand-mark), just scaled up to fill
an app icon canvas instead of a 36px sidebar badge.

Usage: python3 scripts/generate_app_icon.py
Output: desktop/DBPlaygroundApp/AppIcon.icns
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ICONSET_DIR = ROOT / "build" / "AppIcon.iconset"
ICNS_OUT = ROOT / "desktop" / "DBPlaygroundApp" / "AppIcon.icns"

# frontend/src/styles.css :root -- --lime and --ink
LIME = (201, 243, 106, 255)
INK = (32, 35, 31, 255)

SUPERSAMPLE = 2048
# The 10 filenames iconutil's .iconset format actually recognizes: each base
# size plus its @2x (Retina) variant.
ICON_BASE_SIZES = [16, 32, 128, 256, 512]


def _rounded_square(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = round(size * 0.09)
    radius = round((size - 2 * pad) * 0.225)
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=LIME)
    return img


def _draw_database_glyph(img: Image.Image, size: int) -> None:
    """Reproduces lucide's "database" icon path (viewBox 0 0 24 24):
    <ellipse cx="12" cy="5" rx="9" ry="3"/>
    <path d="M3 5V19A9 3 0 0 0 21 19V5"/>
    <path d="M3 12A9 3 0 0 0 21 12"/>
    i.e. a top cap ellipse, two straight side walls, and two bottom-facing
    half-ellipse arcs (the base and the middle "shelf" seam) -- stroke-only,
    round caps/joins, matching lucide-react's default rendering.
    """
    draw = ImageDraw.Draw(img)
    scale = (size * 0.56) / 24
    stroke = max(2, round(2 * scale))

    def pt(vx: float, vy: float) -> tuple[float, float]:
        return (size / 2 + (vx - 12) * scale, size / 2 + (vy - 12) * scale)

    rx, ry = 9 * scale, 3 * scale
    x_left, x_right = pt(3, 0)[0], pt(21, 0)[0]
    y_top, y_mid, y_bottom = pt(0, 5)[1], pt(0, 12)[1], pt(0, 19)[1]
    cx = size / 2

    def bbox(cy: float) -> list[float]:
        return [cx - rx, cy - ry, cx + rx, cy + ry]

    # Top cap: full ellipse outline.
    draw.ellipse(bbox(y_top), outline=INK, width=stroke)
    # Side walls.
    draw.line([(x_left, y_top), (x_left, y_bottom)], fill=INK, width=stroke)
    draw.line([(x_right, y_top), (x_right, y_bottom)], fill=INK, width=stroke)
    # Base and middle-seam arcs (front-facing bottom half only).
    draw.arc(bbox(y_bottom), start=0, end=180, fill=INK, width=stroke)
    draw.arc(bbox(y_mid), start=0, end=180, fill=INK, width=stroke)

    # Round caps/joins at every stroke endpoint, matching lucide's
    # strokeLinecap="round" strokeLinejoin="round".
    cap_r = stroke / 2
    for jx, jy in [
        (x_left, y_top),
        (x_right, y_top),
        (x_left, y_bottom),
        (x_right, y_bottom),
        (x_left, y_mid),
        (x_right, y_mid),
    ]:
        draw.ellipse([jx - cap_r, jy - cap_r, jx + cap_r, jy + cap_r], fill=INK)


def make_master() -> Image.Image:
    img = _rounded_square(SUPERSAMPLE)
    _draw_database_glyph(img, SUPERSAMPLE)
    return img


def main() -> None:
    if shutil.which("iconutil") is None:
        raise SystemExit("iconutil not found -- this script requires macOS.")

    master = make_master()

    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)

    for size in ICON_BASE_SIZES:
        master.resize((size, size), Image.LANCZOS).save(ICONSET_DIR / f"icon_{size}x{size}.png")
        master.resize((size * 2, size * 2), Image.LANCZOS).save(
            ICONSET_DIR / f"icon_{size}x{size}@2x.png"
        )

    ICNS_OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_OUT)], check=True
    )
    shutil.rmtree(ICONSET_DIR.parent)
    print(f"Wrote {ICNS_OUT}")


if __name__ == "__main__":
    main()
