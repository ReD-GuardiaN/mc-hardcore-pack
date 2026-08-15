#!/usr/bin/env python3
"""Set 2: the four bosses drawn from scratch at 32x32, vanilla item conventions.

Art is authored as flat shapes only. The conventions that make a sprite look
like Minecraft are applied by code so they stay consistent across all four:

  - a dark outline dilated around the silhouette
  - a light source fixed to the top-left: pixels on a top/left edge take the
    light tone, pixels on a bottom/right edge take the shadow tone
  - a checkerboard dither ring between each tone and the base, so nothing is a
    large flat fill
  - limited, desaturated, slightly warm palettes - no saturated primaries

Shapes are authored as a 16-wide left half and mirrored, which keeps them
symmetric for free. The shading runs after mirroring, so the light source
stays top-left instead of being mirrored with the shape.

  python3 src/tools/boss_art.py        # writes 32x32 PNGs + silhouettes
"""

import os
import struct
import zlib

SIZE = 32
HALF = SIZE // 2

# 'b' shades with the light source. Anything else is a fixed feature colour
# (eyes, glow, teeth) and is left alone - vanilla does the same with emissive
# bits like a blaze rod's core or a spider's eyes.
SHADED = "b"


def mirror(rows):
    out = [r + r[::-1] for r in rows]
    for i, r in enumerate(out):
        assert len(r) == SIZE, "row %d is %d wide" % (i, len(r))
    assert len(out) == SIZE, "art is %d rows" % len(out)
    return out


WITHER = mirror([
    "................",
    "................",
    ".........bbbbbbb",
    "........bbbbbbbb",
    ".......bbbbbbbbb",
    "......bbbbbbbbbb",
    "......bbbbbbbbbb",
    ".....bbbbbbbbbbb",
    ".....bbbbbbbbbbb",
    ".....bbbbbbbbbbb",
    ".....bbeeeeebbbb",
    ".....bbeeeeebbbb",
    ".....bbeeeeebbbb",
    ".....bbeeeeebbbb",
    ".....bbbbbbbbbbb",
    ".....bbbbbbbbbbb",
    "......bbbbbbbbnn",
    "......bbbbbbbbnn",
    "......bbbbbbbbbb",
    ".......bbbbbbbbb",
    ".......bbbbbbbbb",
    "........bbbbbbbb",
    "........bbbbbbbb",
    "........bb.bb.bb",
    "........bb.bb.bb",
    "........bbbbbbbb",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
])

DRAGON = mirror([
    "................",
    "................",
    "...bb...........",
    "...bb...........",
    "....bb..........",
    "....bbb.........",
    ".....bbb........",
    ".....bbbbb......",
    "......bbbbbbb...",
    "......bbbbbbbbbb",
    ".....bbbbbbbbbbb",
    ".....bbbbbbbbbbb",
    "....bbbbbbbbbbbb",
    "....bbeeeebbbbbb",
    "....bbeeeebbbbbb",
    "....bbeeeebbbbbb",
    "....bbbbbbbbbbbb",
    ".....bbbbbbbbbbb",
    "......bbbbbbbbbb",
    ".......bbbbbbbbb",
    "........bbbbbbbb",
    "........bbbbbbbb",
    ".........bbbbbbb",
    ".........bwbwbbb",
    ".........bbbbbbb",
    "..........bbbbbb",
    "..........bbbbbb",
    "................",
    "................",
    "................",
    "................",
    "................",
])

WARDEN = mirror([
    "................",
    "................",
    "................",
    "........bbbbbbbb",
    ".......bbbbbbbbb",
    "......bbbbbbbbbb",
    "......bbbbbbbbbb",
    "......bbggbbbbbb",
    "......bbggbbbbbb",
    "......bbbbbbbbbb",
    ".......bbbbbbbbb",
    "........bbbbbbbb",
    "......bbbbbbbbbb",
    "....bbbbbbbbbbbb",
    "..bbbbbbbbbbbbbb",
    "..bbbbbbbbbbbbbb",
    "..bbbbbbbbgggggg",
    "..bbbbbbbggggggg",
    "..bbbbbbbggggggg",
    "..bbbbbbbbgggggg",
    "..bbbbbbbbbbbbbb",
    "..bbbbbbbbbbbbbb",
    "...bbbbbbbbbbbbb",
    "...bbb....bbbbbb",
    "...bbb....bbbbbb",
    "...bbb....bbbbbb",
    "...bbb....bbbbbb",
    "................",
    "................",
    "................",
    "................",
    "................",
])

ELDER = mirror([
    "................",
    "................",
    "................",
    "..b...bbbbbbbbbb",
    "...b.bbbbbbbbbbb",
    "....bbbbbbbbbbbb",
    "...bbbbbbbbbbbbb",
    "..bbbbbbbbbbbbbb",
    "..bbbbbbbbbbbbbb",
    "..bbbbbwwwwwwwww",
    "..bbbbwwwwwwwwww",
    "..bbbwwwwwwwwwww",
    "..bbbwwwwwwwwppp",
    "..bbbwwwwwwwwppp",
    "..bbbwwwwwwwwppp",
    "..bbbwwwwwwwwppp",
    "..bbbwwwwwwwwwww",
    "..bbbbwwwwwwwwww",
    "..bbbbbwwwwwwwww",
    "..bbbbbbbbbbbbbb",
    "..bbbbbbbbbbbbbb",
    "...bbbbbbbbbbbbb",
    "....bbbbbbbbbbbb",
    "...b.bbbbbbbbbbb",
    "..b...bbbbbbbbbb",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
])

# base / light / shadow / outline, plus fixed feature colours. Everything is
# pulled off the pure hue: no channel is at 00 or FF except the outlines.
ART = {
    "wither": (WITHER, {
        "b": ("#4a4a45", "#63635c", "#333330", "#1c1c1a"),
        "e": "#d9752a",   # ember eyes, burnt orange rather than pure orange
        "n": "#2b2b28",
    }),
    "dragon": (DRAGON, {
        "b": ("#2e2333", "#453a4d", "#1c1421", "#100b14"),
        "e": "#c060e0",
        "w": "#c9c2b4",   # warm off-white teeth, not #FFFFFF
    }),
    "warden": (WARDEN, {
        "b": ("#1e4245", "#2c5a5c", "#12292c", "#0a1517"),
        "g": "#4fc7be",
    }),
    "elder": (ELDER, {
        "b": ("#9aa08c", "#b4b9a5", "#767b6b", "#3f4239"),
        "w": "#d8d5c4",
        "p": "#46506b",
    }),
}


def png_bytes(px, w=SIZE, h=SIZE):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(px[y * w + x])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def hexc(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


CLEAR = (0, 0, 0, 0)


def render(name, silhouette=False):
    rows, pal = ART[name]
    solid = {(x, y) for y in range(SIZE) for x in range(SIZE) if rows[y][x] != "."}

    if silhouette:
        px = [CLEAR] * (SIZE * SIZE)
        for x, y in solid:
            px[y * SIZE + x] = (0, 0, 0, 255)
        return px

    base, light, shadow, outline = pal[SHADED]
    px = [CLEAR] * (SIZE * SIZE)

    # Outline first, dilated one pixel outward from the whole silhouette.
    for x, y in solid:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) not in solid:
                px[ny * SIZE + nx] = hexc(outline)

    def out(x, y):
        return (x, y) not in solid

    # Light source top-left: a pixel on a top or left edge catches the light,
    # one on a bottom or right edge falls into shadow.
    edge_l = {(x, y) for x, y in solid
              if rows[y][x] == SHADED and (out(x - 1, y) or out(x, y - 1))}
    edge_s = {(x, y) for x, y in solid
              if rows[y][x] == SHADED and (x, y) not in edge_l
              and (out(x + 1, y) or out(x, y + 1))}

    for y in range(SIZE):
        for x in range(SIZE):
            ch = rows[y][x]
            if ch == ".":
                continue
            if ch != SHADED:
                px[y * SIZE + x] = hexc(pal[ch])
                continue
            if (x, y) in edge_l:
                c = light
            elif (x, y) in edge_s:
                c = shadow
            else:
                # Dither ring: every other pixel next to a shaded edge takes
                # that edge's tone, so the transition is never a hard band.
                near_l = any((x + dx, y + dy) in edge_l
                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                near_s = any((x + dx, y + dy) in edge_s
                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if near_l and (x + y) % 2 == 0:
                    c = light
                elif near_s and (x + y) % 2 == 1:
                    c = shadow
                else:
                    c = base
            px[y * SIZE + x] = hexc(c)
    return px


def write_all(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for name in ART:
        for sil in (False, True):
            p = os.path.join(out_dir, "%s%s.png" % (name, "_silhouette" if sil else ""))
            with open(p, "wb") as fh:
                fh.write(png_bytes(render(name, sil)))
            paths[(name, sil)] = p
    return paths


def _selfcheck():
    for name in ART:
        px = render(name)
        assert len(px) == SIZE * SIZE
        opaque = [p for p in px if p[3]]
        assert len(opaque) > 200, "%s is nearly empty" % name
        assert len({p[:3] for p in opaque}) >= 4, "%s has no shading" % name
        for r, g, b, _a in opaque:
            assert not (r == g == b == 255), "%s uses pure white" % name
    print("boss_art selfcheck ok:", ", ".join(sorted(ART)))


if __name__ == "__main__":
    _selfcheck()
    d = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "src", "icons", "drawn")
    write_all(d)
    print("wrote", d)
