#!/usr/bin/env python3
"""Extracts the user's 5-variant boss art off the supplied contact sheet and
builds the preview page.

The sheet is pixel art rendered large: one authored pixel covers a 6x6 block of
image pixels, on a grid whose origin is (1,2). So this is a sampling job, not a
resize - averaging across cell boundaries is what turns pixel art to mush.
Downsampling takes each cell's dominant colour, and round_trip() checks the
result by scaling it back up and comparing against the source.

  python3 src/tools/boss_upload.py
"""

import collections
import os
import subprocess
import sys

import boss_art
import boss_slots as bs

SRC = "/home/red/uploads/2026-08-15_00-58-01-341b.png"
SHEET_W, SHEET_H = 1536, 1024
BLOCK = 6
PHASE = (1, 2)

ROOT = bs.ROOT
OUT = os.path.join(ROOT, "src", "icons", "upload")
# The second contact sheet supersedes the first: it ships the art on transparency with no captions,
# and sheet2_extract.py reads it on a block-3 grid, which halves the round-trip error against the
# block-6 read of sheet one. extract_all() below still parses the OLD sheet, so it must not be
# allowed to write here or it silently replaces the good art with the low-detail version.
NATIVE = os.path.join(OUT, "native2")
PREVIEW = bs.PREVIEW

BG = (23, 25, 28)
INK = 40

# Icon rows and the column window each boss sits in, in native pixels. The
# dragon window starts at 24 because the "VARIANTA n" label ends at x=22.
BANDS = [(2, 29), (40, 65), (76, 100), (110, 133), (143, 163)]
WINDOWS = [(24, 70), (70, 128), (128, 180), (180, 250)]
LABEL_X, LABEL_H = 26, 3   # the caption block to mask out of each band
BOSSES = ["dragon", "elder", "warden", "wither"]
LABEL = {"dragon": "Ender Dragon", "elder": "Elder Guardian",
         "warden": "Warden", "wither": "Wither"}
VARIANTS = [1, 2, 3, 4, 5]

# Art sizes. 40x40 holds every icon with its sparkles intact, so 48 clips
# nothing; 32 is the smaller option and crops the widest art.
SIZES = {
    32: {"scale": 2, "note": "crops the outermost sparkles, and the wither "
                             "only fits as a single skull"},
    48: {"scale": 3, "note": "nothing is clipped - every icon's native art "
                             "is at most 40x40"},
    # Authored at double the on-screen size. The source sheet is not a clean integer upscale - it
    # carries shading finer than its own block grid - so decimating it to 48 before shipping threw
    # detail away. Shipping 96 and letting the font's height field halve it keeps that detail and
    # moves the downscale into the renderer, which is where it belongs.
    96: {"scale": 6, "note": "2x supersampled, displayed at 48 via the font height"},
}
FRAMES = {
    "inventory": {"tile": "slot", "src_size": 18, "bevel": 1},
    "hotbar": {"tile": "hotbar_slot", "src_size": 20, "bevel": 2},
}

# --- the final pick: one line per boss ---
PICK = {"dragon": 1, "elder": 5, "warden": 4, "wither": 3}
PICK_SIZE = 48
PICK_FRAME = "inventory"
# Three skulls are 40 native px wide, so at 32px art the outer two get sliced.
# Below SHIP_SIZE 48 the wither ships as its centre skull only.
WITHER_CENTRE_W = 15
SHIP_SIZE = 96
SHIP_FRAME = "inventory"
HUD = os.path.join(ROOT, "pack", "assets", "hcpack", "textures", "hud")

MIXED_STATES = ["unlocked", "unlocked", "locked", "locked"]


def load_sheet():
    raw = subprocess.run(["convert", SRC, "-depth", "8", "rgba:-"],
                         capture_output=True, check=True).stdout
    assert len(raw) == SHEET_W * SHEET_H * 4, "unexpected sheet size"
    return raw


def downsample(raw):
    """One sample per grid cell: the cell's dominant colour, median as fallback."""
    px, py = PHASE
    nw, nh = (SHEET_W - px) // BLOCK, (SHEET_H - py) // BLOCK

    def at(x, y):
        i = (y * SHEET_W + x) * 4
        return (raw[i], raw[i + 1], raw[i + 2])

    grid = []
    for cy in range(nh):
        row = []
        for cx in range(nw):
            x0, y0 = px + cx * BLOCK, py + cy * BLOCK
            vals = [at(x0 + i, y0 + j) for j in range(BLOCK) for i in range(BLOCK)]
            c, n = collections.Counter(vals).most_common(1)[0]
            if n < 3:
                c = tuple(sorted(v[k] for v in vals)[len(vals) // 2]
                          for k in range(3))
            row.append(c)
        grid.append(row)
    return grid


def round_trip(raw, grid):
    """Scale the downsample back up and see how close it lands to the source.

    The sheet is a soft-edged render rather than a clean integer upscale, so
    this will not be exact; it is here to catch a wrong block size or phase,
    which shows up as a hugely worse number.
    """
    px, py = PHASE

    def at(x, y):
        i = (y * SHEET_W + x) * 4
        return (raw[i], raw[i + 1], raw[i + 2])

    err = n = 0
    for cy in range(0, len(grid), 3):
        for cx in range(0, len(grid[0]), 3):
            c = grid[cy][cx]
            x0, y0 = px + cx * BLOCK, py + cy * BLOCK
            for j in range(BLOCK):
                for i in range(BLOCK):
                    s = at(x0 + i, y0 + j)
                    err += sum(abs(a - b) for a, b in zip(s, c))
                    n += 3
    return err / n


def carve(grid, y0, y1, xa, xb):
    """The icon's pixels: everything the background flood-fill cannot reach."""
    xb = min(xb, len(grid[0]))

    def isbg(x, y):
        # The "VARIANTA n" caption sits in the top-left of every band and its
        # last glyph reaches x=24, inside the dragon's window. Mask it off.
        if x < LABEL_X and y <= y0 + LABEL_H:
            return True
        return sum(abs(a - b) for a, b in zip(grid[y][x], BG)) <= INK

    outside = set()
    stack = [(x, y) for x in range(xa, xb) for y in (y0, y1) if isbg(x, y)]
    stack += [(x, y) for y in range(y0, y1 + 1) for x in (xa, xb - 1) if isbg(x, y)]
    outside.update(stack)
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if (xa <= q[0] < xb and y0 <= q[1] <= y1 and q not in outside
                    and isbg(*q)):
                outside.add(q)
                stack.append(q)
    return {(x, y) for x in range(xa, xb) for y in range(y0, y1 + 1)
            if (x, y) not in outside}


def write_icon(grid, pts, dest, crop=None):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if crop == "centre":
        cx = (x0 + x1) // 2
        x0, x1 = cx - WITHER_CENTRE_W // 2, cx + WITHER_CENTRE_W // 2
    w, h = x1 - x0 + 1, y1 - y0 + 1
    px = [(0, 0, 0, 0)] * (w * h)
    for x, y in pts:
        if x0 <= x <= x1:
            px[(y - y0) * w + (x - x0)] = grid[y][x] + (255,)
    with open(dest, "wb") as fh:
        fh.write(boss_art.png_bytes(px, w, h))
    return w, h


def extract_all(grid):
    # Superseded by sheet2_extract.py - kept for the preview's variant grid, but it writes to the old
    # directory so it cannot clobber the shipping art.
    legacy = os.path.join(OUT, "native")
    os.makedirs(legacy, exist_ok=True)
    dims = {}
    for vi, (y0, y1) in enumerate(BANDS):
        for boss, (xa, xb) in zip(BOSSES, WINDOWS):
            pts = carve(grid, y0, y1, xa, xb)
            crops = [None, "centre"] if boss == "wither" else [None]
            for crop in crops:
                key = (VARIANTS[vi], boss if crop is None else "wither_centre")
                d = os.path.join(legacy, "v%d_%s.png" % key)
                dims[key] = write_icon(grid, pts, d, crop)
    return dims


# The boss art is almost entirely dark - a black dragon, a charcoal wither, a deep-teal warden - and
# vanilla's slot interior is light grey, which is the worst possible ground for it: the silhouettes
# stop reading. Darkening only the interior keeps the vanilla bevel (so it still looks like a real
# slot) while giving the art something to separate from.
SLOT_INTERIOR = "#2b2b2b"


def frame_tile(frame, scale, dest):
    f = FRAMES[frame]
    if frame == "inventory":
        bs.run(bs.r("slot"), "-filter", "point",
               "-resize", "%d%%" % (scale * 100),
               # flood the interior from the centre, leaving the bevel untouched
               "-fill", SLOT_INTERIOR, "-draw",
               "color %d,%d floodfill" % (scale * 9, scale * 9),
               dest)
    else:
        bs.run(bs.r("hotbar"), "-crop", "20x20+1+1", "+repage",
               "-filter", "point", "-resize", "%d%%" % (scale * 100), dest)


def art(variant, boss, size, state, tmp):
    src = os.path.join(NATIVE, "v%d_%s.png" % (variant, boss))
    args = [src]
    if state == "locked":
        # Desaturate, then compress the range into a dark band. A plain
        # multiply drives this art - which is already very dark - to near
        # black, losing the internal detail that makes it readable; +level
        # keeps the detail while staying clearly darker than the light slot.
        args += ["-colorspace", "Gray", "-colorspace", "sRGB",
                 "-channel", "RGB", "+level", "12%,50%", "+channel"]
    args += ["-background", "none", "-gravity", "center",
             "-extent", "%dx%d" % (size, size)]
    bs.run(*args, tmp)
    return tmp


def make_icon(dest, variant, boss, size, frame, state):
    scale = SIZES[size]["scale"]
    f = FRAMES[frame]
    outer = f["src_size"] * scale
    inset = f["bevel"] * scale
    tile = bs.r("_ft_%s_%d" % (frame, scale))
    frame_tile(frame, scale, tile)
    a = art(variant, boss, size, state, bs.r("_a"))
    bs.run(tile, "(", a, ")", "-geometry", "+%d+%d" % (inset, inset),
           "-composite", dest)
    return outer


def make_cluster(dest, picks, size, frame, states):
    """2x2 only - four across does not fit the budget at any of these sizes."""
    scale = SIZES[size]["scale"]
    f = FRAMES[frame]
    outer, inset = f["src_size"] * scale, f["bevel"] * scale
    tile = bs.r("_ft_%s_%d" % (frame, scale))
    frame_tile(frame, scale, tile)
    args = ["-size", "%dx%d" % (outer * 2, outer * 2), "xc:none"]
    for i in range(4):
        args += ["(", tile, ")", "-geometry",
                 "+%d+%d" % ((i % 2) * outer, (i // 2) * outer), "-composite"]
    for i, boss in enumerate(BOSSES):
        src = wither_art(size) if boss == "wither" else boss
        a = art(picks[boss], src, size, states[i], bs.r("_a%d" % i))
        args += ["(", a, ")", "-geometry",
                 "+%d+%d" % ((i % 2) * outer + inset, (i // 2) * outer + inset),
                 "-composite"]
    bs.run(*args, dest)
    return outer * 2, outer * 2


def make_mock(dest, picks, size, frame, scene):
    cluster = bs.r("_cl")
    cw, ch = make_cluster(cluster, picks, size, frame, MIXED_STATES)
    w = bs.PAD + bs.ROW_DX + max(cw, bs.BUDGET) + bs.PAD
    h = max(bs.MOCK_H, ch + 40)
    hy = h - 32
    bg = bs.r("_bg")
    bs.make_bg(bg, scene, w, h)
    bs.run(bg,
           "(", bs.r("hotbar"), ")", "-geometry", "+%d+%d" % (bs.PAD, hy),
           "-composite",
           "(", bs.r("hotbar_offhand_right"), ")",
           "-geometry", "+%d+%d" % (bs.PAD + 182, hy - 1), "-composite",
           "(", cluster, ")",
           "-geometry", "+%d+%d" % (bs.PAD + bs.ROW_DX, hy + 22 - ch), "-composite",
           "-depth", "8", "-strip", dest)
    return w, h, cw, ch


def wither_art(size):
    """Which wither extraction fits: all three skulls need 40px of art."""
    return "wither" if size >= 40 else "wither_centre"


def ship():
    """Write the eight pack glyphs at the existing codepoint names."""
    os.makedirs(HUD, exist_ok=True)
    for boss in BOSSES:
        src = wither_art(SHIP_SIZE) if boss == "wither" else boss
        for state, suffix in (("unlocked", ""), ("locked", "_grey")):
            dest = os.path.join(HUD, boss + suffix + ".png")
            outer = make_icon(dest, PICK[boss], src, SHIP_SIZE, SHIP_FRAME, state)
            # The framed slot is fully opaque, so ImageMagick drops the alpha
            # channel; pad_advance.py needs RGBA to stamp its corner pixels.
            bs.run(dest, "-alpha", "set", "-strip", "PNG32:" + dest)
    return outer


def main():
    bs.ensure_jar()
    bs.extract()
    os.makedirs(OUT, exist_ok=True)

    raw = load_sheet()
    grid = downsample(raw)
    rt = round_trip(raw, grid)
    print("block %d, phase %s, native sheet %dx%d"
          % (BLOCK, PHASE, len(grid[0]), len(grid)))
    print("round-trip mean channel error: %.1f / 255" % rt)
    assert rt < 20, "round trip is way off - block size or phase is wrong"

    dims = extract_all(grid)
    print("native icon sizes:")
    for v in VARIANTS:
        print("  v%d  " % v + "  ".join(
            "%s %dx%d" % (b, *dims[(v, b)])
            for b in BOSSES + ["wither_centre"]))

    icons, clusters, mocks = {}, {}, {}
    for size in SIZES:
        for frame in FRAMES:
            for v in VARIANTS:
                for boss in BOSSES + ["wither_centre"]:
                    for state in ("unlocked", "locked"):
                        d = os.path.join(OUT, "%d_%s_v%d_%s_%s.png"
                                         % (size, frame, v, boss, state))
                        outer = make_icon(d, v, boss, size, frame, state)
                        icons[(size, frame, v, boss, state)] = (bs.uri(d), outer)

    for size in SIZES:
        for frame in FRAMES:
            key = (size, frame)
            c = os.path.join(OUT, "cluster_%d_%s.png" % key)
            cw, ch = make_cluster(c, PICK, size, frame, MIXED_STATES)
            clusters[key] = (bs.uri(c), cw, ch, cw <= bs.BUDGET)
            for scene in ("dark", "grass"):
                m = os.path.join(OUT, "mock_%d_%s_%s.png" % (size, frame, scene))
                mw, mh, _, _ = make_mock(m, PICK, size, frame, scene)
                mocks[(size, frame, scene)] = (bs.uri(m), mw, mh)
            print("2x2  %2dpx art  %-9s  %3dx%-3d  %s"
                  % (size, frame, cw, ch, "fits" if cw <= bs.BUDGET else "OVER"))

    outer = ship()
    print("shipped 8 glyphs to %s at %dx%d (art %dpx + %dpx bevel)"
          % (HUD, outer, outer, SHIP_SIZE, (outer - SHIP_SIZE) // 2))

    with open(PREVIEW, "w") as fh:
        fh.write(build_html(icons, clusters, mocks, dims, rt))
    print("wrote %s" % PREVIEW)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(icons, clusters, mocks, dims, rt):
    o = ["<title>Boss icons - your art, 5 variants</title>",
         "<style>%s</style>" % bs.CSS, '<div class="wrap">']
    o.append("<h1>Your art, extracted</h1>")
    o.append('<p class="muted">Pulled off the contact sheet at its native '
             "resolution: the art is drawn on a <b>%d&times;%d pixel grid</b> with "
             "its origin at (%d,%d), so each authored pixel was sampled once "
             "rather than averaged. Native icons come out at most 40&times;40. "
             "Our own two sets are dropped.</p>"
             % (BLOCK, BLOCK, PHASE[0], PHASE[1]))
    o.append('<p class="muted">Round-trip check: scaling the extraction back up '
             "by %d and comparing against the source gives a mean channel error "
             "of <b>%.1f/255</b>. Not zero, because the sheet is a soft-edged "
             "render rather than a clean integer upscale - but low enough that "
             "the grid is right. A wrong block size lands several times higher."
             % (BLOCK, rt))

    o.append("<h2>Pick per boss</h2>")
    o.append('<p class="muted">Grouped by boss so the five variants can be '
             "compared directly. Framed in the inventory slot at 48px art, "
             "unlocked then locked, actual size next to 3x.</p>")

    size, frame = PICK_SIZE, PICK_FRAME
    for boss in BOSSES + ["wither_centre"]:
        name = LABEL.get(boss, "Wither - centre skull only")
        o.append("<h3>%s</h3>" % esc(name))
        for state in ("unlocked", "locked"):
            o.append('<div class="panel"><div class="head">'
                     '<span class="title">%s</span></div><div class="row">' % state)
            for v in VARIANTS:
                u, outer = icons[(size, frame, v, boss, state)]
                o.append(bs.img(u, outer * 3, outer * 3, "variant %d" % v, "3x"))
                o.append(bs.img(u, outer, outer, "&nbsp;", "actual"))
            o.append("</div></div>")

    o.append("<h2>The wither is wider than it is tall</h2>")
    o.append('<div class="warn">Its three skulls are 39-40 native pixels across '
             "but only 20-24 tall, so it never fits a square slot the way the "
             "others do. Two ways out, both above: <b>full</b> keeps all three "
             "skulls and letterboxes them with transparent padding top and bottom "
             "- which needs the 48px art size, since at 32px the outer skulls get "
             "cut. <b>Centre skull</b> crops to the middle head and fits any size, "
             "at the cost of the wither's most recognisable feature. At 32px "
             "art the full version is unusable - the outer skulls get sliced - "
             "so 32px ships the centre skull and 48px ships all three.</div>")

    o.append("<h2>Size and frame</h2>")
    o.append('<table><tr><th>Art</th><th>Frame</th><th>Per icon</th>'
             "<th>2x2 cluster</th><th>Fits %dpx</th><th>Note</th></tr>" % bs.BUDGET)
    for size in SIZES:
        for frame in FRAMES:
            _u, cw, ch, fits = clusters[(size, frame)]
            o.append("<tr><td>%dpx</td><td>%s</td><td>%d&times;%d</td>"
                     "<td>%d&times;%d</td><td>%s</td><td>%s</td></tr>"
                     % (size, frame, cw // 2, ch // 2, cw, ch,
                        "yes" if fits else "no", esc(SIZES[size]["note"])))
    o.append("</table>")
    o.append('<p class="muted">Four across is not offered: it does not fit at '
             "32px in any framing, which was settled earlier.</p>")

    o.append("<h2>In game, at actual size</h2>")
    o.append('<p class="muted">Current pick: %s. Hotbar adjacent at true scale, '
             "dragon and wither unlocked, warden and elder locked.</p>"
             % esc(", ".join("%s v%d" % (LABEL[b], PICK[b]) for b in BOSSES)))
    for size in SIZES:
        for frame in FRAMES:
            _u, cw, ch, fits = clusters[(size, frame)]
            o.append('<div class="panel"><div class="head">'
                     '<span class="title">%dpx art, %s frame</span>'
                     '<span class="tag">%d&times;%d</span>'
                     '<span class="tag %s">%s</span></div>'
                     % (size, frame, cw, ch, "ok" if fits else "no",
                        "fits" if fits else "over budget"))
            for scene, cap in (("dark", "Dark scene"),
                               ("grass", "Daylight on grass")):
                u, mw, mh = mocks[(size, frame, scene)]
                o.append('<div class="mock"><div class="cap">%s</div>'
                         '<div class="scroller">'
                         '<img style="width:%dpx;height:%dpx" src="%s" alt="">'
                         "</div></div>" % (cap, mw, mh, u))
            o.append("</div>")

    o.append('<p class="muted" style="margin-top:32px">Reply with a variant '
             "number per boss, plus full or centre for the wither.</p>")
    o.append("</div>")
    return "\n".join(o)


if __name__ == "__main__":
    sys.exit(main())
