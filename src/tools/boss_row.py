#!/usr/bin/env python3
"""Build the four boss glyphs from sheet 3's last row, as a single 1x4 row.

These icons ship their own stone slot, so nothing here adds a frame - doing so would put a frame
inside a frame. They are also rendered art rather than pixel art on an integer grid, so they are
reduced with an area average (Box), which is the right filter for a large downscale; point sampling
would drop most of the shading and alias the stone edges.

Authored at 2x the on-screen size and halved by the font's height field, so the renderer does the
final downscale.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/icons/upload/native3"
HUD = ROOT / "pack/assets/hcpack/textures/hud"
ROW = 3

# 4 icons across a 115px budget: 4 * (DISPLAY + 1) must stay under it, so 27 gives 112 with the
# slots touching. The PNG is twice that; the font halves it.
DISPLAY = 27
CANVAS = DISPLAY * 2

BOSSES = ["dragon", "elder", "warden", "wither"]


def run(*args):
    subprocess.run([str(a) for a in args], check=True, capture_output=True)


def build(boss, state, dest):
    src = SRC / f"r{ROW}_{boss}.png"
    if not src.exists():
        raise SystemExit(f"missing {src} - run sheet3_extract.py first")
    args = [src, "-filter", "Box", "-resize", f"{CANVAS}x{CANVAS}"]
    if state == "grey":
        # Desaturate, then compress into a dark band. A plain multiply would crush this art - the
        # dragon and wither are already near-black - and lose the shapes entirely.
        args += ["-colorspace", "Gray", "-colorspace", "sRGB",
                 "-channel", "RGB", "+level", "10%,45%", "+channel"]
    args += ["-background", "none", "-gravity", "center", "-extent", f"{CANVAS}x{CANVAS}", dest]
    run("convert", *args)


def main():
    HUD.mkdir(parents=True, exist_ok=True)
    for boss in BOSSES:
        build(boss, "colour", HUD / f"{boss}.png")
        build(boss, "grey", HUD / f"{boss}_grey.png")

    for boss in BOSSES:
        for suffix in ("", "_grey"):
            f = HUD / f"{boss}{suffix}.png"
            size = subprocess.run(["identify", "-format", "%wx%h", str(f)],
                                  capture_output=True, text=True, check=True).stdout
            if size != f"{CANVAS}x{CANVAS}":
                raise SystemExit(f"{f.name} is {size}, expected {CANVAS}x{CANVAS}")

    row = 4 * (DISPLAY + 1)
    print(f"8 glyphs at {CANVAS}x{CANVAS}, displayed at {DISPLAY} via the font height")
    print(f"row of 4: advance {DISPLAY + 1} each, {row}px total - budget is 115")


if __name__ == "__main__":
    sys.exit(main())
