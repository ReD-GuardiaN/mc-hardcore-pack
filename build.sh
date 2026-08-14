#!/usr/bin/env bash
# Rebuild icons -> validate -> zip -> print sha1.
set -euo pipefail
cd "$(dirname "$0")"
ZIP=dist/hcpack.zip

./src/tools/make-icons.sh >/dev/null
python3 src/tools/font.py

python3 - <<'EOF'
import json, struct, sys, pathlib
root = pathlib.Path("pack")
mcmeta = json.loads((root / "pack.mcmeta").read_text())
p = mcmeta["pack"]
assert "pack_format" not in p, "pack_format is deprecated at format 84, use min_format/max_format"
assert p["min_format"] == 84 and p["max_format"] == 84, p

font = json.loads((root / "assets/hcpack/font/hud.json").read_text())
expected = {
    0xE000: "dragon_grey", 0xE001: "dragon",
    0xE002: "wither_grey", 0xE003: "wither",
    0xE004: "warden_grey", 0xE005: "warden",
    0xE006: "elder_grey",  0xE007: "elder",
}
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
assert seen == expected, f"codepoint contract broken: {seen}"

def png_size(path):
    b = path.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", b[16:24])

for name in expected.values():
    f = root / f"assets/hcpack/textures/hud/{name}.png"
    assert png_size(f) == (16, 16), (f, png_size(f))
for c in ("pink_background", "pink_progress"):
    f = root / f"assets/minecraft/textures/gui/sprites/boss_bar/{c}.png"
    assert png_size(f) == (182, 5), (f, png_size(f))
# nothing else in the pack may shadow a vanilla boss bar sprite
bars = sorted(x.name for x in (root / "assets/minecraft/textures/gui/sprites/boss_bar").iterdir())
assert bars == ["pink_background.png", "pink_progress.png"], bars
print("validated: format 84, 8 icons, negative space, pink-only bar override")
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
