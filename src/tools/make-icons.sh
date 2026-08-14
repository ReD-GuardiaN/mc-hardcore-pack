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

# --- armor ---------------------------------------------------------------
# Item textures are already 16x16, so they are copied, not scaled.
for m in netherite diamond iron golden chainmail copper; do
  for s in helmet chestplate leggings boots; do
    cp "$SRC/it_${m}_${s}.png" "$OUT/armor_${m}_${s}.png"
  done
done
cp "$SRC/it_turtle_helmet.png" "$OUT/armor_turtle_helmet.png"

# leather: the base layer is the dyeable one. Tint it with vanilla's default
# leather colour, then lay the undyed overlay on top - same as the item renderer.
for s in helmet chestplate leggings boots; do
  convert "$SRC/it_leather_${s}.png" \
    \( +clone -fill '#A06540' -colorize 100% \) \
    -compose multiply -composite \
    -alpha set \
    "$SRC/it_leatherov_${s}.png" -compose over -composite \
    "$OUT/armor_leather_${s}.png"
done

# empty slot outlines, from the vanilla inventory slot sprites
for s in helmet chestplate leggings boots; do
  cp "$SRC/it_empty_${s}.png" "$OUT/armor_empty_${s}.png"
done

# --- durability bars -----------------------------------------------------
# 14 glyphs, 0..13 filled pixels, drawn where vanilla draws the item bar:
# black 13x2 trough at y=13, then the fill in vanilla's hue = ratio/3 colour.
for n in $(seq 0 13); do
  hex=$(python3 -c "
import colorsys,sys
n=$n
r,g,b=colorsys.hsv_to_rgb(n/13/3,1,1)
print('#%02X%02X%02X'%(round(r*255),round(g*255),round(b*255)))")
  fill=()
  [ "$n" -gt 0 ] && fill=(-fill "$hex" -draw "rectangle 2,13 $((1 + n)),13")
  convert -size 16x16 xc:none \
    -fill '#000000' -draw 'rectangle 2,13 14,14' \
    "${fill[@]}" \
    -alpha set "$OUT/bar_${n}.png"
done

# fully transparent PINK boss bar (host bar for the HUD); other colours untouched
BB=pack/assets/minecraft/textures/gui/sprites/boss_bar
mkdir -p "$BB"
for f in pink_background pink_progress; do
  convert -size 182x5 xc:none -alpha set "$BB/$f.png"
done

# -strip drops ImageMagick's date chunks, which would otherwise change the
# zip's sha1 on every rebuild and force every client to re-download
for f in $(ls "$OUT"/*.png "$BB"/*.png); do convert "$f" -strip -define png:exclude-chunk=tIME PNG32:"$f"; done
identify "$OUT"/*.png "$BB"/*.png
