#!/usr/bin/env python3
"""Builds the boss checklist preview: two 32x32 art sets, three framings,
two layouts, two scenes.

  set "faces"  the bosses' real faces, cropped out of Mojang's entity
               textures and scaled up nearest-neighbour to 32x32
  set "drawn"  custom art, drawn from scratch at 32x32 - see boss_art.py

  unlocked     full colour
  locked       flat silhouette, in a tone picked per frame: dark on the light
               inventory slot, light on the dark hotbar slot

MIX lets a single boss be taken from the other set without touching the rest.

  python3 src/tools/boss_slots.py     # writes src/icons/slots/* + preview/icons.html
"""

import base64
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

import boss_art

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.expanduser("~/.cache/mc-jars")
JAR = os.path.join(CACHE, "client-26.1.2.jar")
JAR_URL = ("https://piston-data.mojang.com/v1/objects/"
           "4e618f09a0c649dde3fdf829df443ce0b8831e65/client.jar")
JAR_SHA1 = "4e618f09a0c649dde3fdf829df443ce0b8831e65"

RAW = os.path.join(CACHE, "raw")
OUT = os.path.join(ROOT, "src", "icons", "slots")
DRAWN = os.path.join(ROOT, "src", "icons", "drawn")
PREVIEW = os.path.join(ROOT, "preview", "icons.html")

ART = 32                # every icon in both sets is 32x32
BUDGET = 115            # usable width per side, +125 to +240

ORDER = ["dragon", "wither", "warden", "elder"]
LABEL = {"dragon": "Ender Dragon", "wither": "Wither",
         "warden": "Warden", "elder": "Elder Guardian"}

TEX = {
    "dragon_src": "assets/minecraft/textures/entity/enderdragon/dragon.png",
    "wither_src": "assets/minecraft/textures/entity/wither/wither.png",
    "warden_src": "assets/minecraft/textures/entity/warden/warden.png",
    "warden_glow": "assets/minecraft/textures/entity/warden/"
                   "warden_bioluminescent_layer.png",
    "elder_src": "assets/minecraft/textures/entity/guardian/guardian_elder.png",
    "hotbar": "assets/minecraft/textures/gui/sprites/hud/hotbar.png",
    "hotbar_offhand_right": "assets/minecraft/textures/gui/sprites/hud/"
                            "hotbar_offhand_right.png",
    "slot": "assets/minecraft/textures/gui/sprites/container/slot.png",
    "grass_block_top": "assets/minecraft/textures/block/grass_block_top.png",
}

# Where each boss's face lives in its entity texture, and what it takes to make
# it read at 32px. Verified by cropping and looking at the pixels, not assumed.
FACE_CROPS = {
    "dragon": "dragon.png (128,46) 16x16, scaled 2x - the head front face, "
              "black with magenta eyes and mouth. The cleanest of the four.",
    "wither": "wither.png (8,8) 8x8, scaled 4x - the skull front face. Only 8x8 "
              "exists, so its pixels end up twice the size of the others'.",
    "warden": "warden.png (10,44) 16x16 with the bioluminescent layer "
              "composited on and brightened 1.9x, scaled 2x. The raw face is "
              "nearly black and unreadable without the glow layer.",
    "elder": "guardian_elder.png (16,16) 12x12 padded to 16x16, with the eye "
             "from (0,0) 8x8 composited into the centre, scaled 2x. The eye is "
             "a separate texture region because it moves on the live mob.",
}

# outer size, art inset, locked silhouette tone. The tone flips with the frame:
# dark art vanishes on the dark hotbar slot, light art vanishes on the light
# inventory slot.
FRAMES = {
    "none": {"outer": ART, "inset": 0, "locked": "#555555",
             "name": "No frame", "note": "The art alone, floating on the scene."},
    "inventory": {"outer": 36, "inset": 2, "locked": "#3b3b3b",
                  "name": "Inventory slot",
                  "note": "gui/sprites/container/slot.png, 18x18 scaled 2x. The "
                          "light grey slot from the inventory and chest screens."},
    "hotbar": {"outer": 40, "inset": 4, "locked": "#555555",
               "name": "Hotbar slot",
               "note": "One 20x20 slot cut from the hotbar sprite, scaled 2x. "
                       "Dark and translucent rather than light grey."},
}

LAYOUTS = {"row4": (4, "Four across"), "grid2": (2, "2x2 grid")}

SETS = {"faces": "Set 1 - Mojang's own faces",
        "drawn": "Set 2 - drawn from scratch"}

# The drawn art has a real silhouette to flatten. The face crops fill their
# whole square, so flattening them gives a blank rectangle - they get dimmed.
LOCKED_STYLE = {"faces": "dim", "drawn": "silhouette"}

# Take one boss from the other set without rebuilding anything else.
MIX = {"dragon": "faces", "wither": "drawn", "warden": "faces", "elder": "drawn"}

MIXED_STATES = ["unlocked", "unlocked", "locked", "locked"]


def run(*args):
    subprocess.run(["convert", *[str(a) for a in args]], check=True)


def ensure_jar():
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.exists(JAR):
        print("downloading client jar (38 MB)...")
        urllib.request.urlretrieve(JAR_URL, JAR)
    h = hashlib.sha1(open(JAR, "rb").read()).hexdigest()
    assert h == JAR_SHA1, "client jar sha1 mismatch: %s" % h


def r(name):
    return os.path.join(RAW, name + ".png")


def extract():
    os.makedirs(RAW, exist_ok=True)
    with zipfile.ZipFile(JAR) as z:
        for name, path in TEX.items():
            with z.open(path) as src, open(r(name), "wb") as fh:
                shutil.copyfileobj(src, fh)


def build_faces():
    """Set 1: crop each boss's face out of its entity texture, up to 32x32."""
    run(r("dragon_src"), "-crop", "16x16+128+46", "+repage",
        "-filter", "point", "-resize", "200%", r("faces_dragon"))
    run(r("wither_src"), "-crop", "8x8+8+8", "+repage",
        "-filter", "point", "-resize", "400%", r("faces_wither"))
    run(r("warden_src"), r("warden_glow"), "-composite",
        "-crop", "16x16+10+44", "+repage",
        "-channel", "RGB", "-evaluate", "multiply", "1.9", "+channel",
        "-filter", "point", "-resize", "200%", r("faces_warden"))
    run(r("elder_src"), "-crop", "8x8+0+0", "+repage", r("_eye"))
    run(r("elder_src"), "-crop", "12x12+16+16", "+repage",
        "-background", "none", "-gravity", "center", "-extent", "16x16",
        "(", r("_eye"), ")", "-gravity", "center", "-composite",
        "-filter", "point", "-resize", "200%", r("faces_elder"))


def build_drawn():
    boss_art.write_all(DRAWN)
    for b in ORDER:
        shutil.copy(os.path.join(DRAWN, b + ".png"), r("drawn_" + b))


def sprite(boss, set_id, state, frame, tmp):
    src = r("%s_%s" % (set_id, boss))
    if state == "unlocked":
        return src
    if LOCKED_STYLE[set_id] == "silhouette":
        run(src, "-channel", "RGB", "-fill", FRAMES[frame]["locked"],
            "-colorize", "100", "+channel", tmp)
    else:
        # Face crops are full-bleed squares, so a flat silhouette would be a
        # featureless grey rectangle. Desaturate and darken instead, which is
        # the same treatment make-icons.sh already uses for its grey variants.
        run(src, "-colorspace", "Gray", "-colorspace", "sRGB",
            "-channel", "RGB", "-evaluate", "multiply", "0.45", "+channel", tmp)
    return tmp


def frame_tile(frame, dest):
    f = FRAMES[frame]
    if frame == "inventory":
        run(r("slot"), "-filter", "point", "-resize", "200%", dest)
    elif frame == "hotbar":
        run(r("hotbar"), "-crop", "20x20+1+1", "+repage",
            "-filter", "point", "-resize", "200%", dest)
    else:
        run("-size", "%dx%d" % (f["outer"], f["outer"]), "xc:none", dest)


def make_cluster(dest, set_id, frame, layout, states, mixed=False):
    f = FRAMES[frame]
    outer, inset = f["outer"], f["inset"]
    cols = LAYOUTS[layout][0]
    rows = -(-len(ORDER) // cols)
    tile = r("_frame_" + frame)
    frame_tile(frame, tile)

    args = ["-size", "%dx%d" % (outer * cols, outer * rows), "xc:none"]
    if frame != "none":
        for i in range(len(ORDER)):
            args += ["(", tile, ")", "-geometry",
                     "+%d+%d" % ((i % cols) * outer, (i // cols) * outer),
                     "-composite"]
    for i, boss in enumerate(ORDER):
        sid = MIX[boss] if mixed else set_id
        sp = sprite(boss, sid, states[i], frame, r("_sp%d" % i))
        args += ["(", sp, ")", "-geometry",
                 "+%d+%d" % ((i % cols) * outer + inset,
                             (i // cols) * outer + inset), "-composite"]
    run(*args, dest)
    return outer * cols, outer * rows


# Screen geometry: the hotbar is 182 wide and centred, so it spans +-91; the
# offhand slot sits just past its right edge; the cluster starts at +125, i.e.
# hotbar_left + 216.
PAD = 24
ROW_DX = 216
MOCK_H = 128
HOTBAR_Y = 96


def make_bg(dest, scene, w, h):
    if scene == "dark":
        run("-size", "%dx%d" % (w, h), "gradient:#31465e-#0a0e13",
            "-attenuate", "0.4", "+noise", "Gaussian",
            "-depth", "8", "-colors", "24", dest)
    else:
        # Real grass_block_top with the biome tint multiplied in, the way the
        # game tints it. -colorize would flatten it and hide the texture noise
        # this bright-background test exists to check against.
        run(r("grass_block_top"),
            "(", "+clone", "-fill", "#91BD59", "-colorize", "100", ")",
            "-compose", "multiply", "-composite", "-compose", "over",
            "-filter", "point", "-resize", "400%",
            "-write", "mpr:tile", "+delete",
            "-size", "%dx%d" % (w, h), "tile:mpr:tile",
            "-depth", "8", "-colors", "32", dest)


def make_mock(dest, set_id, frame, layout, scene, mixed=False):
    cluster = r("_cluster")
    cw, ch = make_cluster(cluster, set_id, frame, layout, MIXED_STATES, mixed)
    w = PAD + ROW_DX + max(cw, BUDGET) + PAD
    bg = r("_bg")
    make_bg(bg, scene, w, MOCK_H)
    run(bg,
        "(", r("hotbar"), ")", "-geometry", "+%d+%d" % (PAD, HOTBAR_Y), "-composite",
        "(", r("hotbar_offhand_right"), ")",
        "-geometry", "+%d+%d" % (PAD + 182, HOTBAR_Y - 1), "-composite",
        "(", cluster, ")",
        # bottom-aligned with the hotbar, so both sit on one baseline
        "-geometry", "+%d+%d" % (PAD + ROW_DX, HOTBAR_Y + 22 - ch), "-composite",
        "-depth", "8", "-strip", dest)
    return w, MOCK_H, cw, ch


def uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def main():
    ensure_jar()
    extract()
    build_faces()
    build_drawn()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)

    icons, sils, opts, dims = {}, {}, {}, []

    for set_id in SETS:
        for boss in ORDER:
            for frame in FRAMES:
                for state in ("unlocked", "locked"):
                    d = os.path.join(OUT, "%s_%s_%s_%s.png"
                                     % (set_id, boss, frame, state))
                    make_cluster(d, set_id, frame, "row4", [state] * 4)
                    # a single icon is just a 1-wide cluster; crop it back out
                    f = FRAMES[frame]
                    run(d, "-crop", "%dx%d+0+0" % (f["outer"], f["outer"]),
                        "+repage", d)
                    icons[(set_id, boss, frame, state)] = uri(d)

    for boss in ORDER:
        sils[boss] = uri(os.path.join(DRAWN, boss + "_silhouette.png"))

    combos = [(s, f, l) for s in SETS for f in FRAMES for l in LAYOUTS]
    combos += [("mixed", f, l) for f in FRAMES for l in LAYOUTS]
    for set_id, frame, layout in combos:
        mixed = set_id == "mixed"
        key = "%s_%s_%s" % (set_id, frame, layout)
        c = os.path.join(OUT, "cluster_%s.png" % key)
        cw, ch = make_cluster(c, set_id if not mixed else "faces", frame, layout,
                              MIXED_STATES, mixed)
        e = {"w": cw, "h": ch, "cluster": uri(c), "fits": cw <= BUDGET}
        for scene in ("dark", "grass"):
            m = os.path.join(OUT, "mock_%s_%s.png" % (key, scene))
            mw, mh, _, _ = make_mock(m, set_id if not mixed else "faces", frame,
                                     layout, scene, mixed)
            e[scene] = uri(m)
            e["mock_w"], e["mock_h"] = mw, mh
        opts[key] = e
        if set_id != "mixed":
            dims.append((set_id, frame, layout, cw, ch, cw <= BUDGET))

    print("%-8s %-10s %-7s %9s  %s" % ("set", "frame", "layout", "size", "fits"))
    for set_id, frame, layout, cw, ch, fits in dims:
        print("%-8s %-10s %-7s %4dx%-4d  %s"
              % (set_id, frame, layout, cw, ch, "yes" if fits else "NO"))

    with open(PREVIEW, "w") as fh:
        fh.write(build_html(icons, sils, opts))
    print("wrote %s" % PREVIEW)


CSS = """
:root {
  --bg: #f5f6f8; --panel: #ffffff; --panel-2: #eef0f3; --border: #d6d9df;
  --text: #15171c; --muted: #5b6270;
  --warn-bg: #fdf3e3; --warn-text: #7a5410; --warn-border: #e8cf9c;
  --ok: #2f6f3f; --ok-bg: #e6f3e9;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0e1015; --panel: #171a21; --panel-2: #1e222b; --border: #2a2f39;
    --text: #e6e8ec; --muted: #99a1ae;
    --warn-bg: #2a2113; --warn-text: #e0bd76; --warn-border: #4a3a1c;
    --ok: #7fd694; --ok-bg: #17301e;
  }
}
:root[data-theme="dark"] {
  --bg: #0e1015; --panel: #171a21; --panel-2: #1e222b; --border: #2a2f39;
  --text: #e6e8ec; --muted: #99a1ae;
  --warn-bg: #2a2113; --warn-text: #e0bd76; --warn-border: #4a3a1c;
  --ok: #7fd694; --ok-bg: #17301e;
}
body {
  margin: 0; padding: 24px 16px 72px; background: var(--bg); color: var(--text);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  overflow-x: hidden;
}
.wrap { max-width: 1020px; margin: 0 auto; }
h1 { font-size: 23px; margin: 0 0 6px; }
h2 { font-size: 20px; margin: 38px 0 4px; }
h3 { font-size: 12px; margin: 22px 0 8px; color: var(--muted); font-weight: 700;
     text-transform: uppercase; letter-spacing: .06em; }
p { margin: 6px 0; }
.muted { color: var(--muted); }
img { image-rendering: pixelated; image-rendering: crisp-edges; display: block; }
.scroller { overflow-x: auto; max-width: 100%; padding-bottom: 8px; }
.panel { background: var(--panel); border: 1px solid var(--border);
         border-radius: 10px; padding: 14px 16px 16px; margin: 14px 0; }
.row { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; }
.cell { text-align: center; }
.cell .sz { font-size: 10px; color: var(--muted); margin-top: 4px; }
.cell .nm { font-size: 12px; color: var(--muted); margin-bottom: 5px; }
.tag { font-size: 11px; padding: 1px 7px; border-radius: 20px;
       border: 1px solid var(--border); color: var(--muted);
       background: var(--panel-2); }
.tag.ok { color: var(--ok); border-color: var(--ok); background: transparent; }
.tag.no { color: var(--warn-text); border-color: var(--warn-border);
          background: var(--warn-bg); }
.head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
        margin-bottom: 4px; }
.title { font-weight: 650; font-size: 15px; }
.warn { font-size: 13px; background: var(--warn-bg); color: var(--warn-text);
        border: 1px solid var(--warn-border); border-radius: 8px;
        padding: 9px 11px; margin: 10px 0; }
.mock { margin-top: 12px; }
.mock .cap { font-size: 12px; color: var(--muted); margin-bottom: 5px; }
table { border-collapse: collapse; font-size: 13px; margin-top: 8px; }
th, td { border: 1px solid var(--border); padding: 4px 9px; text-align: left; }
th { background: var(--panel-2); font-weight: 600; }
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def img(u, w, h, label=None, note=None):
    o = '<div class="cell">'
    if label:
        o += '<div class="nm">%s</div>' % label
    o += '<img style="width:%dpx;height:%dpx" src="%s" alt="">' % (w, h, u)
    if note:
        o += '<div class="sz">%s</div>' % note
    return o + "</div>"


def build_html(icons, sils, opts):
    o = ["<title>Boss icons - two 32px sets</title>",
         "<style>%s</style>" % CSS, '<div class="wrap">']

    o.append("<h1>Boss checklist - two sets of 32&times;32 art</h1>")
    o.append('<p class="muted">Both sets depict the bosses themselves. Set 1 is '
             "their real faces lifted out of Mojang's entity textures and scaled "
             "up. Set 2 is drawn from scratch, following the conventions vanilla "
             "item art uses: a dark outline, a light source fixed to the top-left, "
             "dithered shading instead of flat fills, and a desaturated palette. "
             "Everything is shown at actual size - that is the only size that "
             "decides anything.</p>")
    o.append('<p class="muted">The two sets need different locked treatments. '
             "The drawn art has a real silhouette, so locked flattens it to one "
             "tone. The face crops fill their whole square, so flattening them "
             "gives a featureless grey rectangle - those are desaturated and "
             "darkened instead, keeping the face readable. The tone also flips "
             "with the frame: dark on the light inventory slot, light on the dark "
             "hotbar slot.</p>")

    for set_id, set_name in SETS.items():
        o.append("<h2>%s</h2>" % esc(set_name))
        if set_id == "faces":
            o.append('<p class="muted">Cropped straight from the entity textures. '
                     "The crops are listed under each boss.</p>")
        else:
            o.append('<p class="muted">Shapes are authored as a mirrored half so '
                     "they stay symmetric; the outline, the top-left light source "
                     "and the dither are applied by code so all four are "
                     "consistent.</p>")
        for frame in FRAMES:
            f = FRAMES[frame]
            o.append('<div class="panel">')
            o.append('<div class="head"><span class="title">%s</span>'
                     '<span class="tag">%d&times;%d per icon</span></div>'
                     % (esc(f["name"]), f["outer"], f["outer"]))
            o.append('<p class="muted" style="margin-top:0;font-size:13px">%s</p>'
                     % esc(f["note"]))
            for state in ("unlocked", "locked"):
                o.append('<h3 style="margin:14px 0 6px">%s</h3>' % state)
                o.append('<div class="row">')
                for boss in ORDER:
                    u = icons[(set_id, boss, frame, state)]
                    o.append(img(u, f["outer"] * 3, f["outer"] * 3,
                                 esc(LABEL[boss]), "3x"))
                    o.append(img(u, f["outer"], f["outer"], "&nbsp;", "actual"))
                o.append("</div>")
            o.append("</div>")
        if set_id == "faces":
            o.append('<div class="panel"><div class="title">Crops used</div>'
                     '<table><tr><th>Boss</th><th>Crop</th></tr>')
            for boss in ORDER:
                o.append("<tr><td>%s</td><td>%s</td></tr>"
                         % (esc(LABEL[boss]), esc(FACE_CROPS[boss])))
            o.append("</table></div>")
        else:
            o.append('<div class="panel"><div class="title">Black-silhouette test'
                     "</div>")
            o.append('<p class="muted" style="font-size:13px">Each shape as a flat '
                     "cutout. If it is not identifiable here, no amount of colour "
                     "will save it.</p>")
            o.append('<div class="row">')
            for boss in ORDER:
                o.append(img(sils[boss], 96, 96, esc(LABEL[boss]), "3x"))
            o.append("</div></div>")

    o.append("<h2>Size, framing and layout</h2>")
    o.append('<p class="muted">Usable width per side is %dpx (+125 to +240). '
             "Four 32px icons only fit if they carry no frame at all - and even "
             "then it is 128px, still over. Every 2x2 fits comfortably. A second "
             "row costs nothing but a codepoint, since the same image registered "
             "at a different <code>ascent</code> draws higher up.</p>" % BUDGET)

    o.append('<table><tr><th>Set</th><th>Frame</th><th>Layout</th><th>Size</th>'
             "<th>Fits %dpx</th></tr>" % BUDGET)
    for set_id in SETS:
        for frame in FRAMES:
            for layout in LAYOUTS:
                e = opts["%s_%s_%s" % (set_id, frame, layout)]
                o.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%d&times;%d</td>"
                         '<td>%s</td></tr>'
                         % (set_id, esc(FRAMES[frame]["name"]),
                            esc(LAYOUTS[layout][1]), e["w"], e["h"],
                            "yes" if e["fits"] else "no"))
    o.append("</table>")

    o.append("<h2>In game, at actual size</h2>")
    o.append('<p class="muted">Real geometry, hotbar next to it at true scale. '
             "Same mixed state everywhere: dragon and wither unlocked, warden and "
             "elder still locked. The bright grass scene is the one that matters - "
             "that is what the user actually plays on.</p>")

    for set_id in list(SETS) + ["mixed"]:
        name = SETS.get(set_id, "Mixed - dragon and warden from set 1, "
                                "wither and elder from set 2")
        o.append("<h3>%s</h3>" % esc(name))
        for frame in FRAMES:
            for layout in LAYOUTS:
                e = opts["%s_%s_%s" % (set_id, frame, layout)]
                o.append('<div class="panel">')
                o.append('<div class="head"><span class="title">%s, %s</span>'
                         '<span class="tag">%d&times;%d</span>'
                         '<span class="tag %s">%s</span></div>'
                         % (esc(FRAMES[frame]["name"]), esc(LAYOUTS[layout][1]),
                            e["w"], e["h"], "ok" if e["fits"] else "no",
                            "fits" if e["fits"] else "over budget"))
                for scene, cap in (("dark", "Dark scene"),
                                   ("grass", "Daylight on grass")):
                    o.append('<div class="mock"><div class="cap">%s</div>' % cap)
                    o.append('<div class="scroller">'
                             '<img style="width:%dpx;height:%dpx" src="%s" alt="">'
                             "</div>" % (e["mock_w"], e["mock_h"], e[scene]))
                    o.append("</div>")
                o.append("</div>")

    o.append('<p class="muted" style="margin-top:32px">Pick a set, a frame and a '
             "layout - they are independent. Individual bosses can also be taken "
             "from the other set; the mixed row above shows that working.</p>")
    o.append("</div>")
    return "\n".join(o)


if __name__ == "__main__":
    sys.exit(main())
