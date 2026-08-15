#!/usr/bin/env python3
"""Extract the boss icons from the user's second contact sheet.

The second sheet is far easier than the first: the art already sits on transparency, with no captions
to mask and no soft-edged panel background, so the cells can be found from the alpha channel alone
and the background needs no flood fill at all.

Still a high-resolution render of pixel art, so the job is the same in principle: find the block size,
then sample one pixel per block. Resizing would destroy it.
"""
import struct
import subprocess
import sys
import zlib
from pathlib import Path

SRC = Path("/home/red/uploads/2026-08-15_01-32-19-b826.png")
OUT = Path(__file__).resolve().parents[2] / "src/icons/upload/native2"
COLUMNS = ["dragon", "elder", "warden", "wither"]
ROWS = 5


def load_rgba(path):
    """RGBA rows via ImageMagick, so we never hand-roll a PNG decoder for arbitrary encodings."""
    dims = subprocess.run(["identify", "-format", "%w %h", str(path)],
                          capture_output=True, text=True, check=True).stdout.split()
    width, height = int(dims[0]), int(dims[1])
    raw = subprocess.run(["convert", str(path), "-depth", "8", "rgba:-"],
                         capture_output=True, check=True).stdout
    return width, height, raw


def bands(mask, length, other):
    """Runs of rows (or columns) containing any opaque pixel."""
    hits = [any(mask(i, j) for j in range(other)) for i in range(length)]
    out, start = [], None
    for i, on in enumerate(hits):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, length - 1))
    return out


# Anti-aliased block edges break shortest-run detection (it returns 2). The sheet is the same render
# scale as the first one, whose grid was measured at 6 by three independent methods, and 6 is the only
# value that reproduces the earlier extraction's icon sizes. Pinned, with the size check below as the
# guard: a wrong block size shows up immediately as icons that are not ~25-40px wide.
BLOCK = 6


def block_size(alpha, x0, x1, y0, y1):
    """Shortest run of identical alpha along a scanline is the block size."""
    best = None
    for y in range(y0, y1 + 1):
        run, prev = 1, alpha(x0, y)
        for x in range(x0 + 1, x1 + 1):
            cur = alpha(x, y)
            if cur == prev:
                run += 1
            else:
                if run > 1:
                    best = run if best is None else min(best, run)
                run, prev = 1, cur
    return best or 1


def write_png(path, width, height, pixels):
    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + bytes(pixels[y]) for y in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main():
    width, height, raw = load_rgba(SRC)

    def px(x, y):
        o = (y * width + x) * 4
        return raw[o:o + 4]

    def opaque(x, y):
        return raw[(y * width + x) * 4 + 3] > 16

    row_bands = bands(lambda y, x: opaque(x, y), height, width)
    if len(row_bands) != ROWS:
        raise SystemExit(f"expected {ROWS} rows, found {len(row_bands)}: {row_bands}")

    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for r, (y0, y1) in enumerate(row_bands, start=1):
        cols = bands(lambda x, y: opaque(x, y) and y0 <= y <= y1, width, height)
        cols = [c for c in cols if c[1] - c[0] > 20]
        if len(cols) != len(COLUMNS):
            raise SystemExit(f"row {r}: expected {len(COLUMNS)} columns, found {len(cols)}: {cols}")

        for (x0, x1), name in zip(cols, COLUMNS):
            b = BLOCK
            nw = (x1 - x0 + 1 + b // 2) // b
            nh = (y1 - y0 + 1 + b // 2) // b
            rows = []
            for ny in range(nh):
                line = bytearray()
                for nx in range(nw):
                    sx = min(x0 + nx * b + b // 2, x1)
                    sy = min(y0 + ny * b + b // 2, y1)
                    line += px(sx, sy)
                rows.append(line)
            out = OUT / f"v{r}_{name}.png"
            write_png(out, nw, nh, rows)
            made.append((out.name, b, nw, nh))

    bad = [(n, w, h) for n, _, w, h in made if not (20 <= w <= 50 and 14 <= h <= 40)]
    if bad:
        raise SystemExit(f"block size looks wrong, icons out of range: {bad}")
    for name, b, nw, nh in made:
        print(f"{name:18} block={b:2}  native={nw}x{nh}")
    print(f"\n{len(made)} icons -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
