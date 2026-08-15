#!/usr/bin/env bash
# Rebuild icons -> validate -> zip -> print sha1.
set -euo pipefail
cd "$(dirname "$0")"
ZIP=dist/hcpack.zip

./src/tools/make-icons.sh >/dev/null

# Both of these normalise geometry and must run after the icons are regenerated, or make-icons.sh
# overwrites them. center_glyphs widens the durability bars to the armor icons' 7.5 centre so the
# two stack with a zero offset; pad_advance gives every glyph the same 17px advance.
python3 src/tools/center_glyphs.py
python3 src/tools/pad_advance.py

python3 src/tools/font.py

python3 - <<'EOF'
import json, pathlib, struct, subprocess
root = pathlib.Path("pack")
mcmeta = json.loads((root / "pack.mcmeta").read_text())
p = mcmeta["pack"]
assert "pack_format" not in p, "pack_format is deprecated at format 84, use min_format/max_format"
assert p["min_format"] == 84 and p["max_format"] == 84, p

font = json.loads((root / "assets/hcpack/font/hud.json").read_text())
# The contract, restated independently of font.py so a bug in the generator
# cannot quietly rewrite it.
expected = {
    0xE000: "dragon_grey", 0xE001: "dragon",
    0xE002: "wither_grey", 0xE003: "wither",
    0xE004: "warden_grey", 0xE005: "warden",
    0xE006: "elder_grey",  0xE007: "elder",
}
# every boss head again one row lower, for the 2x2 cluster
for cp in list(expected):
    expected[cp + 0x10] = expected[cp]
materials = ["netherite", "diamond", "iron", "golden",
             "chainmail", "copper", "leather", "turtle", "empty"]
slots = ["helmet", "chestplate", "leggings", "boots"]
for mi, m in enumerate(materials):
    for si, s in enumerate(slots):
        if m == "turtle" and s != "helmet":
            continue
        expected[0xE200 + mi * 4 + si] = f"armor_{m}_{s}"
for n in range(14):
    expected[0xE230 + n] = f"bar_{n}"
seen = {}
spaces = 0
for prov in font["providers"]:
    if prov["type"] == "space":
        spaces += sum(1 for v in prov["advances"].values() if v < 0)
        continue
    assert prov["ascent"] <= prov["height"], prov
    (cp,) = [ord(c) for line in prov["chars"] for c in line]
    seen[cp] = prov["file"].split("/")[-1].removesuffix(".png")
assert spaces, "no negative space advances"
assert seen == expected, ("codepoint contract broken",
                          sorted(set(seen) ^ set(expected)))
# -17 is what backs up exactly one 16x16 glyph
assert -17 in [v for p in font["providers"] if p["type"] == "space"
               for v in p["advances"].values()], "missing -17 advance"

def png_size(path):
    b = path.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", b[16:24])

boss_names = {v for k, v in expected.items() if k < 0xE100}
for name in expected.values():
    f = root / f"assets/hcpack/textures/hud/{name}.png"
    # Boss heads ship their own stone slot at 54x54, displayed at 27; everything else is 16.
    want = (54, 54) if name in boss_names else (16, 16)
    assert png_size(f) == want, (f, png_size(f), want)
    # a silently blank 16x16 is the easy failure to ship
    colours = int(subprocess.run(["identify", "-format", "%k", str(f)],
                                 capture_output=True, text=True, check=True).stdout)
    assert colours >= 2, f"blank or uniform icon: {f}"
    # THE advance contract: the client derives a glyph's advance from its rightmost
    # non-transparent column, so every glyph must reach its own last column or the
    # advance is wrong and durability bars drift off their icons.
    last = max(int(line.split(",")[0])
               for line in subprocess.run(["convert", str(f), "-alpha", "extract", "txt:-"],
                                          capture_output=True, text=True, check=True
                                          ).stdout.splitlines()[1:]
               if not line.split(":")[1].strip().startswith("(0)"))
    edge = want[0] - 1
    assert last == edge, f"{f} last opaque column is {last}, must be {edge} (advance would be {last + 2})"
# The vanilla armor row must be blanked, and nothing else in gui/sprites/hud may be.
hud = root / "assets/minecraft/textures/gui/sprites/hud"
overrides = sorted(x.name for x in hud.iterdir())
assert overrides == ["armor_empty.png", "armor_full.png", "armor_half.png"], overrides
for name in overrides:
    f = hud / name
    assert png_size(f) == (9, 9), (f, png_size(f))
    # a sprite that is not fully transparent would leave the vanilla row showing through
    alpha = subprocess.run(["convert", str(f), "-alpha", "extract", "-format", "%[fx:maxima]", "info:"],
                           capture_output=True, text=True, check=True).stdout
    assert float(alpha) == 0.0, f"{f} is not fully transparent (max alpha {alpha})"
# the PINK boss bar override is gone: nothing hosts a boss bar any more
assert not (root / "assets/minecraft/textures/gui/sprites/boss_bar").exists(), "stale boss bar override"
print(f"validated: format 84, {len(expected)} glyphs, negative space, armor row blanked")
EOF

rm -rf dist && mkdir -p dist
python3 - "$ZIP" <<'EOF'
import pathlib, sys, zipfile
zippath, root = sys.argv[1], pathlib.Path("pack")
# arcnames are relative to pack/, so pack.mcmeta lands at the archive root.
# fixed timestamps -> same content gives the same sha1 on every rebuild.
with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        info = zipfile.ZipInfo(str(f.relative_to(root)), (2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, f.read_bytes())
names = zipfile.ZipFile(zippath).namelist()
assert "pack.mcmeta" in names, names
assert not any(n.startswith("pack/") for n in names), "wrapper directory in zip"
EOF

SHA=$(sha1sum "$ZIP" | cut -d' ' -f1)
echo "$SHA" > dist/hcpack.zip.sha1
echo "zip:  $PWD/$ZIP  ($(stat -c%s "$ZIP") bytes)"
echo "sha1: $SHA"
