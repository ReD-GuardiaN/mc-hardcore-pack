#!/usr/bin/env python3
"""Centre every HUD glyph's art in its canvas so composition needs no offset.

The durability bar is drawn under an armor icon by backing the pen up one full glyph and drawing at
the same coordinate. That is only correct if both glyphs carry their art at the same place in the
canvas, which they did not: armor art sits at x1..14 or x3..12 (centre 7.5) while the bar sat at
x2..14 (centre 8.0), and 13 is an odd width that cannot centre in 16 at all.

This widens each bar by one column - duplicating its leftmost column, which is a flat run of the bar
colour - so it becomes 14 wide at x1..14, centre 7.5, exactly matching the armor icons. Composition
then aligns with a zero offset and there is no sign convention left to get backwards.
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
        raise SystemExit(f"{path.name}: expected RGBA, got colour type {data[25]}")
    idat, offset = b"", 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        if data[offset + 4:offset + 8] == b"IDAT":
            idat += data[offset + 8:offset + 8 + length]
        offset += 12 + length
    raw = zlib.decompress(idat)

    stride, rows, prev, pos = width * 4, [], bytearray(width * 4), 0
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
                line[x] = (line[x] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 255
        rows.append(line)
        prev = line
    return width, height, rows


def write_png(path, width, height, rows):
    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def px(row, x):
    return row[x * 4:x * 4 + 4]


def opaque_span(rows, width, floor=8):
    """Columns holding real art, ignoring the alpha=1 advance padding."""
    lo, hi = width, -1
    for row in rows:
        for x in range(width):
            if row[x * 4 + 3] >= floor:
                lo, hi = min(lo, x), max(hi, x)
    return lo, hi


def widen_bar(path):
    """Duplicate the bar's leftmost column so it spans x1..14 instead of x2..14."""
    width, height, rows = read_png(path)
    lo, hi = opaque_span(rows, width)
    if (lo, hi) == (1, 14):
        return False
    if (lo, hi) != (2, 14):
        raise SystemExit(f"{path.name}: expected bar art at x2..14, found x{lo}..{hi}")
    for row in rows:
        if row[lo * 4 + 3] >= 8:
            row[(lo - 1) * 4:(lo - 1) * 4 + 4] = px(row, lo)
    write_png(path, width, height, rows)
    return True


def main():
    bars = sorted(HUD.glob("bar_*.png"))
    if not bars:
        raise SystemExit(f"no bar glyphs under {HUD}")
    widened = sum(widen_bar(b) for b in bars)

    spans = set()
    for b in bars:
        width, _, rows = read_png(b)
        spans.add(opaque_span(rows, width))
    if spans != {(1, 14)}:
        raise SystemExit(f"bars still disagree: {sorted(spans)}")

    print(f"widened {widened}/{len(bars)} bars to x1..14, centre 7.5 - matches the armor icons")


if __name__ == "__main__":
    sys.exit(main())
