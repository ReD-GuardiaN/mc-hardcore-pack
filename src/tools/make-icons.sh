#!/usr/bin/env bash
# Crops vanilla boss faces -> 16x16 colour + grey icons.
# Source PNGs in src/icons/px_*.png were extracted from the 26.1.2 client jar.
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=src/icons
OUT=pack/assets/hcpack/textures/hud
mkdir -p "$OUT"

# nearest-neighbour only; smooth scaling destroys pixel art
SCALE=(-filter point -resize 16x16!)

crop() { convert "$1" -crop "$2" +repage -background none -alpha set "${@:3}"; }

# dragon: head front face, already 16x16
crop "$SRC/px_dragon.png" 16x16+128+46 "$OUT/dragon.png"

# wither: 8x8 skull -> 16x16
crop "$SRC/px_wither.png" 8x8+8+8 "${SCALE[@]}" "$OUT/wither.png"

# warden: composite the emissive layers first (the base face is near-black and
# unreadable at 16px), crop the mouth region, brighten, pad to 16x16 so every
# icon shares one height/ascent
convert "$SRC/px_warden.png" "$SRC/px_warden_biolum.png" -composite \
        "$SRC/px_warden_spots.png" -composite \
  -crop 16x12+10+46 +repage \
  -channel RGB -evaluate multiply 2.2 +channel \
  -background none -gravity center -extent 16x16 \
  -alpha set "$OUT/warden.png"

# elder guardian: 12x12 face -> 16x16
crop "$SRC/px_guardian_elder.png" 12x12+16+16 "${SCALE[@]}" "$OUT/elder.png"

# Grey variants must be baked: component colour MULTIPLIES the texture, so a
# colour icon can never be tinted grey at runtime. Desaturate + darken so the
# "off" state reads instantly next to its colour twin.
for n in dragon wither warden elder; do
  convert "$OUT/$n.png" \
    -colorspace Gray -colorspace sRGB \
    -channel RGB -evaluate multiply 0.45 +channel \
    -alpha set "$OUT/${n}_grey.png"
done

# fully transparent PINK boss bar (host bar for the HUD); other colours untouched
BB=pack/assets/minecraft/textures/gui/sprites/boss_bar
mkdir -p "$BB"
for f in pink_background pink_progress; do
  convert -size 182x5 xc:none -alpha set "$BB/$f.png"
done

for f in $(ls "$OUT"/*.png "$BB"/*.png); do convert "$f" PNG32:"$f"; done
identify "$OUT"/*.png "$BB"/*.png
