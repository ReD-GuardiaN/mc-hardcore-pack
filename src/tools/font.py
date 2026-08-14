#!/usr/bin/env python3
"""Generates pack/assets/hcpack/font/hud.json."""
import json
import pathlib

# The two tuning knobs. Raising ASCENT moves the glyph up. ASCENT <= HEIGHT.
HEIGHT = 16
ASCENT = 12

ICONS = [
    ("dragon_grey", 0xE000), ("dragon", 0xE001),
    ("wither_grey", 0xE002), ("wither", 0xE003),
    ("warden_grey", 0xE004), ("warden", 0xE005),
    ("elder_grey",  0xE006), ("elder",  0xE007),
]
WIDTHS = [1, 2, 3, 4, 8, 16, 32, 64]

advances = {}
for i, w in enumerate(WIDTHS):
    advances[chr(0xE100 + i)] = -w
    advances[chr(0xE110 + i)] = w

providers = [{"type": "space", "advances": advances}]
providers += [
    {"type": "bitmap", "file": f"hcpack:hud/{name}.png",
     "height": HEIGHT, "ascent": ASCENT, "chars": [chr(cp)]}
    for name, cp in ICONS
]

out = pathlib.Path(__file__).parents[2] / "pack/assets/hcpack/font/hud.json"
out.write_text(json.dumps({"providers": providers}, indent=2, ensure_ascii=True) + "\n")
print(f"{out}: height={HEIGHT} ascent={ASCENT}")
