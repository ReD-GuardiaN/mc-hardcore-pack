#!/usr/bin/env python3
"""Extract the pre-framed boss icons from the user's third contact sheet.

This sheet is different from the previous two: each icon already sits in its own stone slot, so the
pack must NOT add an inventory frame on top. The cells are separated by ragged black/white/red noise
rather than clean transparency, so the grid is found by projecting "is this a frame pixel" - the
stone is a narrow grey band - rather than by alpha alone.

Only the last row ships; the other two are extracted for reference.
"""
import struct
import subprocess
import sys
import zlib
from pathlib import Path

SRC = Path("/home/red/uploads/2026-08-15_02-02-17-dbf6.png")
OUT = Path(__file__).resolve().parents[2] / "src/icons/upload/native3"
COLUMNS = ["dragon", "elder", "warden", "wither"]
ROWS = 3


def load_rgba(path):
    w, h = subprocess.run(["identify", "-format", "%w %h", str(path)],
                          capture_output=True, text=True, check=True).stdout.split()
    raw = subprocess.run(["convert", str(path), "-depth", "8", "rgba:-"],
                         capture_output=True, check=True).stdout
    return int(w), int(h), raw


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


def bands(hits, min_len):
    out, start = [], None
    for i, on in enumerate(hits):
        if on and start is None:
            start = i
        elif not on and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(hits) - start >= min_len:
        out.append((start, len(hits) - 1))
    return out


def main():
    width, height, raw = load_rgba(SRC)

    def at(x, y):
        o = (y * width + x) * 4
        return raw[o], raw[o + 1], raw[o + 2], raw[o + 3]

    def stone(x, y):
        """The slot's stone: opaque, desaturated, mid-to-light. Excludes the noise between cells,
        which is pure black, pure white or saturated red/yellow."""
        r, g, b, a = at(x, y)
        if a < 200:
            return False
        mx, mn = max(r, g, b), min(r, g, b)
        return 70 <= mx <= 230 and mx - mn <= 28

    col_hits = [sum(stone(x, y) for y in range(0, height, 4)) > height // 40 for x in range(width)]
    row_hits = [sum(stone(x, y) for x in range(0, width, 4)) > width // 40 for y in range(height)]

    cols = bands(col_hits, width // 12)
    rows_ = bands(row_hits, height // 9)
    if len(cols) != len(COLUMNS) or len(rows_) != ROWS:
        raise SystemExit(f"grid detect failed: {len(cols)} cols {cols}, {len(rows_)} rows {rows_}")

    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for ri, (y0, y1) in enumerate(rows_, start=1):
        for (x0, x1), name in zip(cols, COLUMNS):
            cw, ch = x1 - x0 + 1, y1 - y0 + 1
            out_rows = []
            for y in range(y0, y1 + 1):
                line = bytearray()
                for x in range(x0, x1 + 1):
                    line += bytes(at(x, y))
                out_rows.append(line)
            dest = OUT / f"r{ri}_{name}.png"
            write_png(dest, cw, ch, out_rows)
            made.append((dest.name, cw, ch))

    for n, w, h in made:
        print(f"{n:16} {w}x{h}")
    print(f"\n{len(made)} cells -> {OUT}   (row {ROWS} is the shipping row)")


if __name__ == "__main__":
    sys.exit(main())
