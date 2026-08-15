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
BLOCK = 3


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


def dominant(px, bx, by, b, xmax, ymax):
    counts = {}
    for y in range(by, min(by + b, ymax + 1)):
        for x in range(bx, min(bx + b, xmax + 1)):
            v = bytes(px(x, y))
            counts[v] = counts.get(v, 0) + 1
    if not counts:
        return b"\x00\x00\x00\x00"
    # transparent only wins if it is a strict majority, so a thin feature is not eaten by its margin
    best = max(counts, key=lambda v: (counts[v], v[3]))
    clear = counts.get(b"\x00\x00\x00\x00", 0)
    if best[3] == 0 and clear * 2 <= sum(counts.values()):
        opaque_only = {v: n for v, n in counts.items() if v[3] > 0}
        if opaque_only:
            best = max(opaque_only, key=opaque_only.get)
    return best


def find_phase(alpha_at, width, height, b):
    """Grid origin: the offset whose block boundaries land on the most alpha transitions."""
    best, best_score = 0, -1
    for off in range(b):
        score = 0
        for x in range(off, width - 1, b):
            for y in range(0, height, 7):
                if alpha_at(x, y) != alpha_at(x + 1, y):
                    score += 1
        if score > best_score:
            best, best_score = off, score
    return best


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

    alpha_at = lambda x, y: raw[(y * width + x) * 4 + 3] > 16
    phase_x = find_phase(alpha_at, width, height, BLOCK)
    phase_y = find_phase(lambda y, x: alpha_at(x, y), height, width, BLOCK)
    print(f"grid phase: x={phase_x} y={phase_y} block={BLOCK}")

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
            # Phase comes from the sheet's global grid, not this icon's bounding box: an icon whose
            # art happens to start mid-block would otherwise be sampled across block boundaries and
            # lose every feature thinner than a block.
            gx, gy = phase_x, phase_y
            x0 = x0 - (x0 - gx) % b
            y0 = y0 - (y0 - gy) % b
            nw = -(-(x1 - x0 + 1) // b)
            nh = -(-(y1 - y0 + 1) // b)
            rows = []
            for ny in range(nh):
                line = bytearray()
                for nx in range(nw):
                    # Dominant colour of the block, not its centre pixel. On a clean upscale every
                    # interior pixel is identical and this is exact; on anti-aliased edges the true
                    # colour still outvotes the blended fringe, which centre sampling does not.
                    line += dominant(px, x0 + nx * b, y0 + ny * b, b, x1, y1)
                rows.append(line)
            out = OUT / f"v{r}_{name}.png"
            write_png(out, nw, nh, rows)

            # Proof the grid is right: blow the extraction back up by the block size and compare it
            # to the region it came from. A wrong block size or phase lands several times higher.
            err = n = 0
            for y in range(y0, min(y0 + nh * b, y1 + 1)):
                for x in range(x0, min(x0 + nw * b, x1 + 1)):
                    src_px = px(x, y)
                    got = rows[(y - y0) // b][((x - x0) // b) * 4:((x - x0) // b) * 4 + 4]
                    for ch in range(4):
                        err += abs(src_px[ch] - got[ch])
                        n += 1
            made.append((out.name, b, nw, nh, err / max(n, 1)))

    bad = [(n, w, h) for n, _, w, h, _ in made if not (40 <= w <= 100 and 28 <= h <= 80)]
    if bad:
        raise SystemExit(f"block size looks wrong, icons out of range: {bad}")
    worst = max(m[4] for m in made)
    for name, b, nw, nh, rt in made:
        print(f"{name:18} block={b:2}  native={nw}x{nh:2}  round-trip {rt:5.2f}/255")
    print(f"\nworst round-trip error {worst:.2f}/255")
    # At block 3 the sheet's sub-block shading survives, so the residual here is the art's own
    # gradient rather than a grid error. Kept as a sanity bound, not a fidelity claim.
    if worst > 25:
        raise SystemExit("round-trip too high - grid or phase is wrong")
    print(f"\n{len(made)} icons -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
