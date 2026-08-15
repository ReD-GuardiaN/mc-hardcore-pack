#!/usr/bin/env python3
"""Generate 16x16 boss checklist icons (locked/unlocked, plain + framed).

No Pillow on this host, so PNGs are written by hand (zlib + struct).
Art is authored at final size: a 14x14 pixel map that sits inside a 1px frame.

    python3 src/tools/boss_icons.py            # writes PNGs + preview/icons.html
"""

import base64
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICON_DIR = os.path.join(ROOT, "src", "icons", "boss")
PREVIEW = os.path.join(ROOT, "preview", "icons.html")

SIZE = 16
ART = 14  # 16 minus the 1px frame on each side


# --------------------------------------------------------------------------
# PNG writing
# --------------------------------------------------------------------------

def png_bytes(pixels, w=SIZE, h=SIZE):
    """pixels: flat list of (r,g,b,a) tuples, row-major."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        for x in range(w):
            raw.extend(pixels[y * w + x])

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def hexc(s, a=255):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), a)


CLEAR = (0, 0, 0, 0)


# --------------------------------------------------------------------------
# Art maps. '.' = transparent, any other char indexes the icon's palette.
# --------------------------------------------------------------------------

A_DRAGON = ([
    "..............",
    "..d........d..",
    "..dd......dd..",
    "...ddd..ddd...",
    "..dddddddddd..",
    ".dddddddddddd.",
    ".dmmddddddmmd.",
    ".dddddddddddd.",
    "..dddddddddd..",
    "...dddddddd...",
    "....dwwwwd....",
    "....dddddd....",
    ".....dwwd.....",
    "..............",
], {"d": "2b2036", "m": "cf5cff", "w": "ded4e6"})

A_WITHER = ([
    "..............",
    "....bbbbbb....",
    "...bbbbbbbb...",
    "..bbbbbbbbbb..",
    "..bhhbbbbhhb..",
    "..beebbbbeeb..",
    "..beebbbbeeb..",
    "..bbbbbbbbbb..",
    "..bbbbhhbbbb..",
    "...bbbbbbbb...",
    "....bbbbbb....",
    "....b.bb.b....",
    "..............",
    "..............",
], {"b": "3b3b3b", "h": "5e5e5e", "e": "ff6a1c"})

A_WARDEN = ([
    "..............",
    "....tttttt....",
    "...tttttttt...",
    "...tttttttt...",
    "....tttttt....",
    "..tttttttttt..",
    ".tttttttttttt.",
    ".ttttCCCCtttt.",
    ".tttCCCCCCttt.",
    ".ttttCCCCtttt.",
    ".tttttttttttt.",
    "..tt......tt..",
    "..tt......tt..",
    "..............",
], {"t": "14424a", "C": "2ff0d8"})

A_ELDER = ([
    "..............",
    ".s..........s.",
    ".sggggggggggs.",
    "..gggggggggg..",
    ".gggeeeeeeggg.",
    ".ggeeeeeeeegg.",
    ".ggeeeppeeegg.",
    ".ggeeeppeeegg.",
    ".ggeeeeeeeegg.",
    ".gggeeeeeeggg.",
    "..gggggggggg..",
    ".sggggggggggs.",
    ".s..........s.",
    "..............",
], {"g": "8a9c8e", "s": "5d6b60", "e": "ece6d4", "p": "e2551f"})

B_DRAGON = ([
    "..............",
    "......rr......",
    ".....rkkr.....",
    "....rkhkkr....",
    "...rkkkkkkr...",
    "...rkkpkkkr...",
    "..rkkkkkkkkr..",
    "..rkkkkkpkkr..",
    "..rkkpkkkkkr..",
    "..rkkkkkkkkr..",
    "...rkkkkkkr...",
    "....rrrrrr....",
    "..............",
    "..............",
], {"k": "17121f", "h": "3d3350", "p": "b64bff", "r": "7b2fc4"})

B_WITHER = ([
    "..............",
    "......ww......",
    "......ww......",
    "..w...ww...w..",
    "...w..ww..w...",
    "....wwwwww....",
    ".wwwwwyywwwww.",
    ".wwwwwyywwwww.",
    "....wwwwww....",
    "...w..ww..w...",
    "..w...ww...w..",
    "......ww......",
    "......ww......",
    "..............",
], {"w": "e8ecf2", "y": "fff6b0"})

B_WARDEN = ([
    "..............",
    "....tttttt....",
    "..tttttttttt..",
    ".tttCCCCCCttt.",
    ".ttCCttttCCtt.",
    "tttCttttttCttt",
    "ttCCttCCttCCtt",
    "ttCCttCCttCCtt",
    "tttCttttttCttt",
    ".ttCCttttCCtt.",
    ".tttCCCCCCttt.",
    "..tttttttttt..",
    "....tttttt....",
    "..............",
], {"t": "0f3239", "C": "2ff0d8"})

B_ELDER = ([
    "..............",
    "..yyyyyyyyyy..",
    ".yyyyyyyyyyyy.",
    ".yyooyyyyooyy.",
    ".yyooyyyyooyy.",
    ".yyyyyoyyyyyy.",
    ".yyyyyoyyyyyy.",
    ".yooyyyyyyooy.",
    ".yooyyyyyyooy.",
    ".yyyyyyyyyyyy.",
    ".yyyoyyyoyyyy.",
    "..yyyyyyyyyy..",
    "..............",
    "..............",
], {"y": "d6c531", "o": "6f6415"})

DIRECTIONS = [
    {
        "id": "a",
        "name": "Direction A - creature silhouettes",
        "blurb": "Each boss drawn as its own head/body shape. Reads as \"who\", "
                 "at the cost of more shape complexity.",
        "icons": [
            ("dragon", "Ender Dragon", "head profile, snout + jaw", A_DRAGON),
            ("wither", "Wither", "wither skull, glowing eyes", A_WITHER),
            ("warden", "Warden", "torso + glowing chest sensor", A_WARDEN),
            ("elder", "Elder Guardian", "spiked body + big eye", A_ELDER),
        ],
    },
    {
        "id": "b",
        "name": "Direction B - emblems",
        "blurb": "One bold object per boss (its drop or signature block) instead "
                 "of the mob. Chunkier, more contrast, less \"mob portrait\".",
        "icons": [
            ("dragon", "Ender Dragon", "dragon egg", B_DRAGON),
            ("wither", "Wither", "nether star", B_WITHER),
            ("warden", "Warden", "sculk shrieker ring", B_WARDEN),
            ("elder", "Elder Guardian", "wet sponge", B_ELDER),
        ],
    },
]


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render_art(art):
    """14x14 art map -> flat pixel list, art centred in a 16x16 transparent canvas."""
    rows, pal = art
    assert len(rows) == ART, "art must be %d rows, got %d" % (ART, len(rows))
    px = [CLEAR] * (SIZE * SIZE)
    for y, row in enumerate(rows):
        assert len(row) == ART, "row %d is %d wide, want %d" % (y, len(row), ART)
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            px[(y + 1) * SIZE + (x + 1)] = hexc(pal[ch])
    return px


def lock(px):
    """Desaturate AND darken - locked must read as off, not just dim."""
    out = []
    for r, g, b, a in px:
        if a == 0:
            out.append(CLEAR)
            continue
        l = 0.299 * r + 0.587 * g + 0.114 * b
        out.append((
            int(l * 0.34 + 10),
            int(l * 0.36 + 12),
            int(l * 0.42 + 18),
            a,
        ))
    return out


FRAMES = {
    "unlocked": {"edge": "5cff6a", "corner": "b6ffbc", "fill": "0e2a12", "fill_a": 210},
    "locked": {"edge": "474d55", "corner": "5b636d", "fill": "0c0e13", "fill_a": 210},
}


def frame(px, state):
    f = FRAMES[state]
    edge, corner = hexc(f["edge"]), hexc(f["corner"])
    fill = hexc(f["fill"], f["fill_a"])
    out = list(px)
    for y in range(SIZE):
        for x in range(SIZE):
            i = y * SIZE + x
            on_edge = x in (0, SIZE - 1) or y in (0, SIZE - 1)
            if on_edge:
                is_corner = x in (0, SIZE - 1) and y in (0, SIZE - 1)
                out[i] = corner if is_corner else edge
            elif out[i][3] == 0:
                out[i] = fill
    return out


def main():
    os.makedirs(ICON_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    data = {}  # (dir_id, slug, state, framed) -> data uri

    for d in DIRECTIONS:
        out_dir = os.path.join(ICON_DIR, d["id"])
        os.makedirs(out_dir, exist_ok=True)
        for slug, _label, _desc, art in d["icons"]:
            base = render_art(art)
            for state, px in (("unlocked", base), ("locked", lock(base))):
                for framed in (False, True):
                    img = frame(px, state) if framed else px
                    blob = png_bytes(img)
                    name = "%s_%s%s.png" % (slug, state, "_framed" if framed else "")
                    with open(os.path.join(out_dir, name), "wb") as fh:
                        fh.write(blob)
                    data[(d["id"], slug, state, framed)] = (
                        "data:image/png;base64," + base64.b64encode(blob).decode()
                    )

    with open(PREVIEW, "w") as fh:
        fh.write(build_html(data))
    print("wrote %d PNGs to %s" % (len(data), ICON_DIR))
    print("wrote %s" % PREVIEW)


# --------------------------------------------------------------------------
# Preview page (fragment: no doctype/html/head/body - it gets wrapped)
# --------------------------------------------------------------------------

CSS = """
:root {
  --bg: #f4f5f7;
  --panel: #ffffff;
  --border: #d7dae0;
  --text: #16181d;
  --muted: #5c6370;
  --scene-a: #1b2430;
  --scene-b: #0d1219;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1116;
    --panel: #171a21;
    --border: #2a2f39;
    --text: #e6e8ec;
    --muted: #98a0ad;
    --scene-a: #1b2430;
    --scene-b: #0d1219;
  }
}
:root[data-theme="dark"] {
  --bg: #0f1116;
  --panel: #171a21;
  --border: #2a2f39;
  --text: #e6e8ec;
  --muted: #98a0ad;
  --scene-a: #1b2430;
  --scene-b: #0d1219;
}
body {
  margin: 0;
  padding: 24px 16px 64px;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  overflow-x: hidden;
}
.wrap { max-width: 1000px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 32px 0 2px; }
h3 { font-size: 14px; margin: 20px 0 8px; color: var(--muted); font-weight: 600;
     text-transform: uppercase; letter-spacing: .04em; }
p.blurb { color: var(--muted); margin: 4px 0 12px; }
img { image-rendering: pixelated; image-rendering: crisp-edges; display: block; }
.scroller { overflow-x: auto; max-width: 100%; padding-bottom: 6px; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px 12px;
}
.card .name { font-weight: 600; font-size: 14px; }
.card .desc { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
.states { display: flex; gap: 14px; flex-wrap: wrap; }
.state { flex: 1 1 auto; }
.state .tag { font-size: 11px; color: var(--muted); margin-bottom: 4px; }
.pair { display: flex; align-items: flex-end; gap: 10px; }
.pair .cell { text-align: center; }
.pair .cell span { display: block; font-size: 10px; color: var(--muted); margin-top: 4px; }
.zoom8 { width: 128px; height: 128px; }
.zoom4 { width: 64px; height: 64px; }
.actual { width: 16px; height: 16px; }
.scene {
  border-radius: 8px;
  border: 1px solid var(--border);
  padding: 22px 18px;
  background:
    repeating-linear-gradient(90deg, rgba(255,255,255,.025) 0 2px, transparent 2px 6px),
    linear-gradient(160deg, var(--scene-a), var(--scene-b) 70%);
}
.hotbar {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: rgba(0,0,0,.35);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 3px;
}
.scene .caption { color: #9aa3b0; font-size: 12px; margin: 0 0 10px; }
.scene + .scene { margin-top: 12px; }
"""


def cell(uri, cls, label):
    return ('<div class="cell"><img class="%s" src="%s" alt=""><span>%s</span></div>'
            % (cls, uri, label))


def build_html(data):
    o = []
    o.append("<title>Boss icon directions - 16x16</title>")
    o.append("<style>%s</style>" % CSS)
    o.append('<div class="wrap">')
    o.append("<h1>Boss checklist icons</h1>")
    o.append('<p class="blurb">Every icon is authored at 16x16 and drawn 1:1 in game. '
             "Judge the actual-size column - the zoom is only for reading the pixels. "
             'Reply like &ldquo;direction B, but the warden from A&rdquo;.</p>')

    for d in DIRECTIONS:
        o.append("<h2>%s</h2>" % d["name"])
        o.append('<p class="blurb">%s</p>' % d["blurb"])

        for framed, title in ((True, "Framed slot (what ships)"), (False, "Icon only (no frame)")):
            o.append("<h3>%s</h3>" % title)
            o.append('<div class="grid">')
            for slug, label, desc, _art in d["icons"]:
                o.append('<div class="card">')
                o.append('<div class="name">%s</div>' % label)
                o.append('<div class="desc">%s</div>' % desc)
                o.append('<div class="states">')
                for state in ("unlocked", "locked"):
                    uri = data[(d["id"], slug, state, framed)]
                    o.append('<div class="state"><div class="tag">%s</div><div class="pair">'
                             % state)
                    o.append(cell(uri, "zoom4", "16px&times;4"))
                    o.append(cell(uri, "actual", "actual"))
                    o.append("</div></div>")
                o.append("</div></div>")
            o.append("</div>")

        o.append("<h3>Zoomed 8x - unlocked</h3>")
        o.append('<div class="scroller"><div class="pair">')
        for slug, label, _desc, _art in d["icons"]:
            o.append(cell(data[(d["id"], slug, "unlocked", True)], "zoom8", label))
        o.append("</div></div>")

        o.append("<h3>In context - actual size, dark scene</h3>")
        rows = [
            ("All locked - fresh world",
             [(s, "locked") for s, _l, _d, _a in d["icons"]]),
            ("Mixed - dragon and wither down",
             [("dragon", "unlocked"), ("wither", "unlocked"),
              ("warden", "locked"), ("elder", "locked")]),
            ("All unlocked - run complete",
             [(s, "unlocked") for s, _l, _d, _a in d["icons"]]),
        ]
        for caption, combo in rows:
            o.append('<div class="scene"><p class="caption">%s</p><div class="hotbar">'
                     % caption)
            for slug, state in combo:
                o.append('<img class="actual" src="%s" alt="">'
                         % data[(d["id"], slug, state, True)])
            o.append("</div></div>")

    o.append("</div>")
    return "\n".join(o)


if __name__ == "__main__":
    main()
