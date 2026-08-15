#!/usr/bin/env bash
# Crops vanilla boss faces -> 16x16 colour + grey icons.
# Source PNGs in src/icons/px_*.png were extracted from the 26.1.2 client jar.
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=src/icons
OUT=pack/assets/hcpack/textures/hud
mkdir -p "$OUT"

# Boss heads are NOT generated here any more. They are the user's own artwork,
# extracted by src/tools/boss_upload.py and committed under pack/. Regenerating
# them from the old entity crops would overwrite it.

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

# --- hide the vanilla armor row -----------------------------------------
# Our armor icons replace it, so blank the three 9x9 sprites the armor bar is
# drawn from. Sprite-per-file since 1.20.5, so this touches nothing else:
# hearts, hunger, air, xp and the hotbar all live in their own files.
HUD=pack/assets/minecraft/textures/gui/sprites/hud
mkdir -p "$HUD"
for f in armor_full armor_half armor_empty; do
  convert -size 9x9 xc:none -alpha set "$HUD/$f.png"
done

# Pin every glyph to a 17 px advance.
# A bitmap font glyph does NOT advance by its image width: the client scans for the
# rightmost non-transparent column and advances that + 2. Vanilla armor art stops at
# column 12 (helmets, leggings) or 14 (chestplates, boots), so glyphs advanced 14 or 16
# and the plugin's uniform -17 back-up threw every durability bar 1-3 px left of its
# icon, differently per slot. One alpha-1 pixel in the last column makes the scan
# return 15 for every glyph, so all of them advance 17 and the arithmetic holds.
# Alpha 1/255 is invisible; alpha 0 would not count.
for f in "$OUT"/*.png; do
  convert "$f" -alpha set -fill 'rgba(0,0,0,0.004)' -draw 'point 15,15' "$f"
done

# -strip drops ImageMagick's date chunks, which would otherwise change the
# zip's sha1 on every rebuild and force every client to re-download
for f in $(ls "$OUT"/*.png "$HUD"/*.png); do convert "$f" -strip -define png:exclude-chunk=tIME PNG32:"$f"; done
identify "$OUT"/*.png "$HUD"/*.png
