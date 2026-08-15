#!/usr/bin/env python3
"""Force every HUD glyph to the same advance.

Minecraft measures a bitmap glyph's advance from its non-transparent content, not from the canvas,
so a helmet whose art starts at x=3 advances 14 while a boss head spanning the full canvas advances
17. GlyphHud composes with one constant (17) and backs up by -17 to slide a durability bar under an
icon, which lands 3px left under a helmet and 1px left under a chestplate.

Stamping an alpha=1 pixel into the top-left and top-right corners makes every glyph span x0..x15, so
they all advance 17 and the composition arithmetic is simply true. Alpha 1 is invisible in game but
counts as content for the width scan.
"""
import struct
import sys
import zlib
from pathlib import Path

HUD = Path(__file__).resolve().parents[2] / "pack/assets/hcpack/textures/hud"


def read_png(path):
    data = path.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    if data[25] != 6:
        raise SystemExit(f"{path.name}: expected RGBA (colour type 6), got {data[25]}")
    idat = b""
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        if data[offset + 4:offset + 8] == b"IDAT":
            idat += data[offset + 8:offset + 8 + length]
        offset += 12 + length
    raw = zlib.decompress(idat)

    stride = width * 4
    rows, prev, pos = [], bytearray(stride), 0
    for _ in range(height):
        filt = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if filt == 1:
                line[x] = (line[x] + a) & 255
            elif filt == 2:
                line[x] = (line[x] + b) & 255
            elif filt == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pred) & 255
        rows.append(line)
        prev = line
    return width, height, rows


def write_png(path, width, height, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def pad(path):
    width, height, rows = read_png(path)
    changed = False
    for x in (0, width - 1):
        alpha = x * 4 + 3
        if rows[0][alpha] == 0:
            rows[0][alpha] = 1
            changed = True
    if changed:
        write_png(path, width, height, rows)
    return changed


def content_span(path):
    width, _, rows = read_png(path)
    lo, hi = width, -1
    for row in rows:
        for x in range(width):
            if row[x * 4 + 3]:
                lo, hi = min(lo, x), max(hi, x)
    return lo, hi


def main():
    files = sorted(HUD.glob("*.png"))
    if not files:
        raise SystemExit(f"no glyphs under {HUD}")
    padded = sum(pad(f) for f in files)

    spans = {content_span(f) for f in files}
    if spans != {(0, 15)}:
        raise SystemExit(f"glyphs still disagree on advance: {sorted(spans)}")
    print(f"padded {padded}/{len(files)} glyphs; all span x0..x15, advance 17")


if __name__ == "__main__":
    sys.exit(main())
