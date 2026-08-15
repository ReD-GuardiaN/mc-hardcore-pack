# mc-hardcore-pack

HUD resource pack for a small private Minecraft server (26.1.2, pack format 84).
It contains boss face icons and armor icons derived from the vanilla Minecraft
client textures, durability bar glyphs, and blanked vanilla armor bar sprites so
the plugin's own armor icons can take that row on the action bar.

Not affiliated with Mojang. The derived textures are Mojang's; this is only
useful to players who already own the game.

## Contract

Font `hcpack:hud`, all glyphs 16x16, `height` 16, `ascent` 12.

**[CODEPOINTS.md](CODEPOINTS.md) is the authoritative table.** Summary:

| Range | Contents |
|---|---|
| `U+E000`..`U+E007` | boss heads, grey/colour pairs: dragon, wither, warden, elder guardian |
| `U+E100`..`U+E118` | space advances, negative and positive |
| `U+E200`..`U+E223` | armor, `0xE200 + material*4 + slot` |
| `U+E230`..`U+E23D` | durability bar, `0xE230 + filled` (0..13) |

The vanilla armor row (`gui/sprites/hud/armor_{full,half,empty}.png`) is blanked, so the
plugin's own armor icons replace it. Hearts, hunger, air, XP and the hotbar are untouched.

## Build and publish

```bash
./build.sh      # rebuild icons + zip, prints the sha1
./publish.sh    # build, commit, cut a new tag, upload the release asset
```

`publish.sh` prints the download URL and sha1, and writes both to
`dist/LATEST.txt`.

## Tuning

`height` and `ascent` live in `src/tools/font.py` — edit, then `./publish.sh`.
Raising `ascent` moves the icon up.
