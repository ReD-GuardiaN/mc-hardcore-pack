#!/usr/bin/env python3
"""Boss checklist icons composed from vanilla textures, not hand-drawn.

Each icon is a real hotbar slot from the vanilla hotbar sprite with a real
vanilla item sprite centred in it, so the row reads as extra hotbar slots.

  unlocked  the item sprite, untouched, full colour
  locked    the same sprite as a flat #555555 silhouette - the exact tone
            vanilla uses for its empty-armour-slot placeholders, which is
            the game's own "nothing here yet" language and the only grey
            that stays readable on the dark slot fill

Swapping which item represents a boss is a one-line edit in CHOSEN.

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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.expanduser("~/.cache/mc-jars")
JAR = os.path.join(CACHE, "client-26.1.2.jar")
JAR_URL = ("https://piston-data.mojang.com/v1/objects/"
           "4e618f09a0c649dde3fdf829df443ce0b8831e65/client.jar")
JAR_SHA1 = "4e618f09a0c649dde3fdf829df443ce0b8831e65"

RAW = os.path.join(CACHE, "raw")             # textures straight out of the jar
OUT = os.path.join(ROOT, "src", "icons", "slots")
PREVIEW = os.path.join(ROOT, "preview", "icons.html")

# The classic inventory/chest slot: gui/sprites/container/slot.png, exactly
# 18x18 - a 16x16 interior plus a 1px bevel, dark on the top-left and white on
# the bottom-right. Measured from the texture, not assumed.
SLOT = 18
BEVEL = 1
# Dark silhouette, the recipe-book "not discovered yet" treatment. It reads on
# this frame because the slot interior is light grey (#8B8B8B).
LOCKED_GREY = "#3b3b3b"

# scale -> (interior px, label). 1.5 is deliberately included even though it is
# not an integer multiple; see SCALE_NOTE.
SIZES = [(1, 16), (1.5, 24), (2, 32)]
SCALE_NOTE = ("1.5x cannot map pixels evenly - some source pixels become 2 wide "
              "and some stay 1, so the art comes out visibly lumpy. 1x and 2x "
              "are clean.")

ITEM = "assets/minecraft/textures/item/%s.png"
BLOCK = "assets/minecraft/textures/block/%s.png"

# id -> (jar path, first_frame_only). Animated block textures are vertical
# strips, so only the top 16px is a usable frame.
TEX = {
    "end_crystal": (ITEM % "end_crystal", False),
    "dragon_breath": (ITEM % "dragon_breath", False),
    "ender_dragon_spawn_egg": (ITEM % "ender_dragon_spawn_egg", False),
    "elytra": (ITEM % "elytra", False),
    "dragon_egg": (BLOCK % "dragon_egg", False),
    "nether_star": (ITEM % "nether_star", False),
    "wither_spawn_egg": (ITEM % "wither_spawn_egg", False),
    "echo_shard": (ITEM % "echo_shard", False),
    "warden_spawn_egg": (ITEM % "warden_spawn_egg", False),
    "sculk_shrieker_top": (BLOCK % "sculk_shrieker_top", False),
    "sculk_shrieker_inner_top": (BLOCK % "sculk_shrieker_inner_top", True),
    "sculk_catalyst_top": (BLOCK % "sculk_catalyst_top", False),
    "sculk_catalyst_top_bloom": (BLOCK % "sculk_catalyst_top_bloom", True),
    "prismarine_shard": (ITEM % "prismarine_shard", False),
    "prismarine_crystals": (ITEM % "prismarine_crystals", False),
    "elder_guardian_spawn_egg": (ITEM % "elder_guardian_spawn_egg", False),
    "wet_sponge": (BLOCK % "wet_sponge", False),
    "sponge": (BLOCK % "sponge", False),
    "hotbar": ("assets/minecraft/textures/gui/sprites/hud/hotbar.png", False),
    "hotbar_offhand_right": (
        "assets/minecraft/textures/gui/sprites/hud/hotbar_offhand_right.png", False),
    "slot": ("assets/minecraft/textures/gui/sprites/container/slot.png", False),
    "grass_block_top": (BLOCK % "grass_block_top", False),
}

# Sprites we build by compositing two vanilla layers (base + emissive bloom).
COMPOSED = {
    "sculk_shrieker": ("sculk_shrieker_top", "sculk_shrieker_inner_top"),
    "sculk_catalyst": ("sculk_catalyst_top", "sculk_catalyst_top_bloom"),
}

BLOCK_WARNING = ("Block texture, not an item sprite. In game this item is drawn "
                 "as a 3D cube in the slot, so a flat face does not match what "
                 "the player actually sees - and it is authored to tile, not to "
                 "read as an icon.")

CANDIDATES = {
    "dragon": ("Ender Dragon", [
        ("end_crystal", "End crystal", "item",
         "Brightest option and unmistakably End. Its white glass frame gives a "
         "hard silhouette that survives the grey locked treatment.", None),
        ("dragon_breath", "Dragon's breath", "item",
         "Literally a dragon drop. Downside: reads as \"a potion\" first, "
         "dragon second.", None),
        ("ender_dragon_spawn_egg", "Ender dragon spawn egg", "item",
         "Names the exact mob, and the whole set could be spawn eggs. Dark, "
         "and spawn eggs feel like a creative-mode item.", None),
        ("elytra", "Elytra", "item",
         "Strong silhouette, but it is an End-city drop, not a dragon drop.", None),
        ("dragon_egg", "Dragon egg", "block",
         "The obvious thematic pick and the worst-reading one: near-black with "
         "faint purple specks, it vanishes into the dark slot.", BLOCK_WARNING),
    ]),
    "wither": ("Wither", [
        ("nether_star", "Nether star", "item",
         "The wither's only drop, bright, high contrast, unique silhouette. "
         "Hard to argue with.", None),
        ("wither_spawn_egg", "Wither spawn egg", "item",
         "Only if you want a matching spawn-egg set. Dark grey on dark grey, "
         "it reads muddy next to the star.", None),
    ]),
    "warden": ("Warden", [
        ("echo_shard", "Echo shard", "item",
         "Ancient-city loot, so it is warden territory. Bright cyan on the dark "
         "slot, clean diagonal shape.", None),
        ("warden_spawn_egg", "Warden spawn egg", "item",
         "Names the mob outright and carries the warden's teal and cyan.", None),
        ("sculk_shrieker", "Sculk shrieker", "block",
         "The block that summons it. Composited base + glowing inner ring. Pale "
         "rim reads, but the middle is murky.", BLOCK_WARNING),
        ("sculk_catalyst", "Sculk catalyst", "block",
         "Composited with its bloom layer. Mostly dark noise at this size - "
         "weakest of the four.", BLOCK_WARNING),
    ]),
    "elder": ("Elder Guardian", [
        ("prismarine_shard", "Prismarine shard", "item",
         "Clean teal triangle, best-reading of the ocean-monument items. Caveat: "
         "normal guardians drop it too, so it says \"monument\", not \"elder\".", None),
        ("elder_guardian_spawn_egg", "Elder guardian spawn egg", "item",
         "The only candidate that is unambiguously the elder guardian and "
         "nothing else.", None),
        ("prismarine_crystals", "Prismarine crystals", "item",
         "Pale and low contrast; the locked silhouette turns into a shapeless "
         "blob.", None),
        ("wet_sponge", "Wet sponge", "block",
         "Elder-guardian exclusive, which is the appeal. But the flat texture is "
         "a solid yellow square edge to edge - no silhouette at all.", BLOCK_WARNING),
    ]),
}

# --- the current pick. One line per boss; change the id and re-run. ---
CHOSEN = {
    "dragon": "end_crystal",
    "wither": "nether_star",
    "warden": "echo_shard",
    "elder": "prismarine_shard",
}

ORDER = ["dragon", "wither", "warden", "elder"]


def run(*args):
    subprocess.run(["convert", *[str(a) for a in args]], check=True)


def ensure_jar():
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.exists(JAR):
        print("downloading client jar (38 MB)...")
        urllib.request.urlretrieve(JAR_URL, JAR)
    h = hashlib.sha1(open(JAR, "rb").read()).hexdigest()
    assert h == JAR_SHA1, "client jar sha1 mismatch: %s" % h


def extract():
    os.makedirs(RAW, exist_ok=True)
    with zipfile.ZipFile(JAR) as z:
        for name, (path, first_frame) in TEX.items():
            dest = os.path.join(RAW, name + ".png")
            with z.open(path) as src, open(dest, "wb") as fh:
                shutil.copyfileobj(src, fh)
            if first_frame:
                run(dest, "-crop", "16x16+0+0", "+repage", dest)
    for name, (base, over) in COMPOSED.items():
        run(os.path.join(RAW, base + ".png"),
            os.path.join(RAW, over + ".png"), "-composite",
            os.path.join(RAW, name + ".png"))


def sprite_path(item, state, scale, tmp):
    """The item sprite, greyed if locked and scaled if the option asks for it."""
    src = os.path.join(RAW, item + ".png")
    if state == "unlocked" and scale == 1:
        return src
    args = [src]
    if state == "locked":
        args += ["-channel", "RGB", "-fill", LOCKED_GREY, "-colorize", "100", "+channel"]
    if scale != 1:
        args += ["-filter", "point", "-resize", "%d%%" % round(scale * 100)]
    run(*args, tmp)
    return tmp


def make_icon(item, state, dest, scale=1):
    """One inventory slot with the sprite centred in it, at the given scale."""
    slot = os.path.join(RAW, "_slot%s.png" % scale)
    run(os.path.join(RAW, "slot.png"), "-filter", "point",
        "-resize", "%d%%" % round(scale * 100), slot)
    sprite = sprite_path(item, state, scale, os.path.join(RAW, "_sp.png"))
    inset = round(BEVEL * scale)
    run(slot, "(", sprite, ")", "-geometry", "+%d+%d" % (inset, inset),
        "-composite", dest)


def make_cluster(items_states, dest, scale=1, cols=4):
    """The four slots laid out adjacent, cols per row."""
    outer = round(SLOT * scale)
    inset = round(BEVEL * scale)
    rows = -(-len(items_states) // cols)
    slot = os.path.join(RAW, "_slot%s.png" % scale)
    run(os.path.join(RAW, "slot.png"), "-filter", "point",
        "-resize", "%d%%" % round(scale * 100), slot)
    args = ["-size", "%dx%d" % (outer * cols, outer * rows), "xc:none"]
    for i in range(len(items_states)):
        x, y = (i % cols) * outer, (i // cols) * outer
        args += ["(", slot, ")", "-geometry", "+%d+%d" % (x, y), "-composite"]
    for i, (item, state) in enumerate(items_states):
        sp = sprite_path(item, state, scale, os.path.join(RAW, "_sp%d.png" % i))
        x, y = (i % cols) * outer + inset, (i // cols) * outer + inset
        args += ["(", sp, ")", "-geometry", "+%d+%d" % (x, y), "-composite"]
    run(*args, dest)
    return outer * cols, outer * rows


# Screen mock geometry, in GUI pixels. The hotbar is 182 wide and centred, so
# it spans +-91 from screen centre; the offhand slot sits just past its right
# edge; the cluster starts at +125, i.e. hotbar_left + 216. That gap is the
# reserved offhand space, which is why the cluster can never touch the hotbar.
PAD = 20
ROW_DX = 216
BUDGET = 115          # +125 to +240, the usable width per side
MOCK_H = 96
HOTBAR_Y = 66


def make_bg(dest, scene, w, h):
    if scene == "dark":
        run("-size", "%dx%d" % (w, h), "gradient:#31465e-#0a0e13",
            "-attenuate", "0.4", "+noise", "Gaussian",
            "-depth", "8", "-colors", "24", dest)
    else:
        # Real grass_block_top, biome-tinted the way the game tints it and
        # scaled to a plausible on-screen block size. A light grey frame on
        # bright grass is the failure mode worth seeing before shipping.
        run(os.path.join(RAW, "grass_block_top.png"),
            "-fill", "#91BD59", "-colorize", "100%",
            "-filter", "point", "-resize", "400%",
            "-write", "mpr:tile", "+delete",
            "-size", "%dx%d" % (w, h), "tile:mpr:tile",
            "-depth", "8", "-colors", "32", dest)


def make_mock(items_states, dest, scale=1, cols=4, scene="dark"):
    cluster = os.path.join(RAW, "_cluster.png")
    cw, ch = make_cluster(items_states, cluster, scale, cols)
    w = PAD + ROW_DX + max(cw, BUDGET) + PAD
    bg = os.path.join(RAW, "_bg.png")
    make_bg(bg, scene, w, MOCK_H)
    # Bottom-align the cluster with the hotbar so both sit on the same baseline.
    y = HOTBAR_Y + 22 - ch
    run(bg,
        "(", os.path.join(RAW, "hotbar.png"), ")",
        "-geometry", "+%d+%d" % (PAD, HOTBAR_Y), "-composite",
        "(", os.path.join(RAW, "hotbar_offhand_right.png"), ")",
        "-geometry", "+%d+%d" % (PAD + 182, HOTBAR_Y - 1), "-composite",
        "(", cluster, ")",
        "-geometry", "+%d+%d" % (PAD + ROW_DX, y), "-composite",
        "-depth", "8", "-strip", dest)
    return w, MOCK_H, cw, ch


def make_mock(items_states, dest):
    row = os.path.join(RAW, "_row.png")
    make_row(items_states, row)
    # Background gets quantised on its own: Gaussian noise over a full-depth
    # gradient is ~180 KB of incompressible dither, and this page inlines
    # every image as a data URI.
    bg = os.path.join(RAW, "_bg.png")
    run("-size", "%dx%d" % (MOCK_W, MOCK_H), "gradient:#31465e-#0a0e13",
        "-attenuate", "0.4", "+noise", "Gaussian",
        "-depth", "8", "-colors", "24", bg)
    run(bg,
        "(", os.path.join(RAW, "hotbar.png"), ")",
        "-geometry", "+%d+%d" % (PAD, HOTBAR_Y), "-composite",
        "(", os.path.join(RAW, "hotbar_offhand_right.png"), ")",
        "-geometry", "+%d+%d" % (PAD + 182, HOTBAR_Y - 1), "-composite",
        "(", row, ")",
        "-geometry", "+%d+%d" % (PAD + ROW_DX, HOTBAR_Y + 1), "-composite",
        "-depth", "8", "-strip", dest)


def uri(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def main():
    ensure_jar()
    extract()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)

    icons = {}
    for boss, (_label, cands) in CANDIDATES.items():
        for item, _n, _kind, _why, _warn in cands:
            for state in ("unlocked", "locked"):
                dest = os.path.join(OUT, "%s_%s.png" % (item, state))
                make_icon(item, state, dest)
                icons[(item, state)] = uri(dest)

    mocks = {}
    combos = {
        "locked": [(CHOSEN[b], "locked") for b in ORDER],
        "mixed": [(CHOSEN["dragon"], "unlocked"), (CHOSEN["wither"], "unlocked"),
                  (CHOSEN["warden"], "locked"), (CHOSEN["elder"], "locked")],
        "unlocked": [(CHOSEN[b], "unlocked") for b in ORDER],
    }
    for name, combo in combos.items():
        dest = os.path.join(OUT, "mock_%s.png" % name)
        make_mock(combo, dest)
        mocks[name] = uri(dest)

    with open(PREVIEW, "w") as fh:
        fh.write(build_html(icons, mocks))
    print("wrote %d slot PNGs + 3 mocks to %s" % (len(icons), OUT))
    print("wrote %s" % PREVIEW)


CSS = """
:root {
  --bg: #f5f6f8;
  --panel: #ffffff;
  --panel-2: #eef0f3;
  --border: #d6d9df;
  --text: #15171c;
  --muted: #5b6270;
  --warn-bg: #fdf3e3;
  --warn-text: #7a5410;
  --warn-border: #e8cf9c;
  --pick: #2f6f3f;
  --pick-bg: #e6f3e9;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0e1015;
    --panel: #171a21;
    --panel-2: #1e222b;
    --border: #2a2f39;
    --text: #e6e8ec;
    --muted: #99a1ae;
    --warn-bg: #2a2113;
    --warn-text: #e0bd76;
    --warn-border: #4a3a1c;
    --pick: #7fd694;
    --pick-bg: #17301e;
  }
}
:root[data-theme="dark"] {
  --bg: #0e1015;
  --panel: #171a21;
  --panel-2: #1e222b;
  --border: #2a2f39;
  --text: #e6e8ec;
  --muted: #99a1ae;
  --warn-bg: #2a2113;
  --warn-text: #e0bd76;
  --warn-border: #4a3a1c;
  --pick: #7fd694;
  --pick-bg: #17301e;
}
body {
  margin: 0;
  padding: 24px 16px 72px;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  overflow-x: hidden;
}
.wrap { max-width: 1020px; margin: 0 auto; }
h1 { font-size: 23px; margin: 0 0 6px; }
h2 { font-size: 19px; margin: 36px 0 6px; }
h3 { font-size: 12px; margin: 0 0 8px; color: var(--muted); font-weight: 700;
     text-transform: uppercase; letter-spacing: .06em; }
p { margin: 6px 0; }
.muted { color: var(--muted); }
img { image-rendering: pixelated; image-rendering: crisp-edges; display: block; }
.scroller { overflow-x: auto; max-width: 100%; padding-bottom: 8px; }

.hero {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px 18px 18px;
  margin: 18px 0 8px;
}
.mock { margin-bottom: 14px; }
.mock:last-child { margin-bottom: 0; }
.mock .cap { font-size: 13px; color: var(--muted); margin-bottom: 6px; }
.mock img { border-radius: 4px; }
.mock-actual { width: 336px; height: 72px; }
.mock-zoom { width: 672px; height: 144px; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
        padding: 12px 14px 14px; }
.card.pick { border-color: var(--pick); background: var(--pick-bg); }
.card .head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.card .title { font-weight: 650; font-size: 15px; }
.tag { font-size: 11px; padding: 1px 7px; border-radius: 20px; border: 1px solid var(--border);
       color: var(--muted); background: var(--panel-2); }
.tag.pick { color: var(--pick); border-color: var(--pick); background: transparent; font-weight: 650; }
.card .why { font-size: 13px; color: var(--muted); margin: 6px 0 10px; }
.warn { font-size: 12px; background: var(--warn-bg); color: var(--warn-text);
        border: 1px solid var(--warn-border); border-radius: 6px; padding: 7px 9px;
        margin: 0 0 10px; }
.shots { display: flex; gap: 18px; flex-wrap: wrap; }
.shot { text-align: center; }
.shot .lbl { font-size: 11px; color: var(--muted); margin-bottom: 5px; }
.shot .pair { display: flex; align-items: flex-end; gap: 9px; }
.z6 { width: 120px; height: 120px; }
.a1 { width: 20px; height: 20px; }
.shot .sz { font-size: 10px; color: var(--muted); margin-top: 4px; }
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(icons, mocks):
    o = ["<title>Boss slots from vanilla textures</title>",
         "<style>%s</style>" % CSS, '<div class="wrap">']

    o.append("<h1>Boss checklist, built from the game's own art</h1>")
    o.append('<p class="muted">No drawing this time. Every icon is a real hotbar '
             "slot cut from the vanilla hotbar sprite with a real vanilla item "
             "sprite centred in it. Locked is that same sprite as a flat "
             "<code>#555555</code> silhouette, which is exactly the grey vanilla "
             "uses for the empty armour-slot placeholders in your inventory.</p>")

    o.append('<div class="hero">')
    o.append("<h3>The test that matters: does it sit next to the hotbar?</h3>")
    o.append('<p class="muted" style="margin-top:0">Actual size, real geometry. The '
             "hotbar spans &plusmn;91 from screen centre, the offhand slot sits just "
             "past it, and the boss row occupies &plusmn;125 to &plusmn;205 - so it "
             "cannot touch the hotbar, but it should read as the same furniture. "
             "Zoomed 2x underneath each.</p>")
    for name, cap in (("locked", "Fresh world - all four locked"),
                      ("mixed", "Mid run - dragon and wither down"),
                      ("unlocked", "Done - all four unlocked")):
        o.append('<div class="mock"><div class="cap">%s</div>' % cap)
        o.append('<div class="scroller">')
        o.append('<img class="mock-actual" src="%s" alt="">' % mocks[name])
        o.append("</div><div class=\"scroller\" style=\"margin-top:6px\">")
        o.append('<img class="mock-zoom" src="%s" alt="">' % mocks[name])
        o.append("</div></div>")
    o.append("</div>")
    o.append('<p class="muted">Those use the current pick: %s. '
             "Everything below is the menu - pick per boss, not per set.</p>"
             % esc(", ".join("%s = %s" % (CANDIDATES[b][0], CHOSEN[b]) for b in ORDER)))

    for boss in ORDER:
        label, cands = CANDIDATES[boss]
        o.append("<h2>%s</h2>" % esc(label))
        o.append('<div class="grid">')
        for item, name, kind, why, warn in cands:
            picked = CHOSEN[boss] == item
            o.append('<div class="card%s">' % (" pick" if picked else ""))
            o.append('<div class="head"><span class="title">%s</span>' % esc(name))
            o.append('<span class="tag">%s texture</span>' % kind)
            if picked:
                o.append('<span class="tag pick">current pick</span>')
            o.append("</div>")
            o.append('<div class="why">%s</div>' % esc(why))
            if warn:
                o.append('<div class="warn">%s</div>' % esc(warn))
            o.append('<div class="shots">')
            for state in ("unlocked", "locked"):
                o.append('<div class="shot"><div class="lbl">%s</div><div class="pair">'
                         % state)
                o.append('<div><img class="z6" src="%s" alt="">'
                         '<div class="sz">6x</div></div>' % icons[(item, state)])
                o.append('<div><img class="a1" src="%s" alt="">'
                         '<div class="sz">actual</div></div>' % icons[(item, state)])
                o.append("</div></div>")
            o.append("</div></div>")
        o.append("</div>")

    o.append('<p class="muted" style="margin-top:32px">Reply with one item per boss, '
             "e.g. &ldquo;dragon: dragon's breath, keep the rest&rdquo;. Swapping one "
             "is a one-line change in the generator.</p>")
    o.append("</div>")
    return "\n".join(o)


if __name__ == "__main__":
    sys.exit(main())
