# mc-hardcore-pack

HUD resource pack for a small private Minecraft server (26.1.2, pack format 84).
It contains four boss face icons cropped from the vanilla Minecraft client
textures, plus a fully transparent PINK boss bar sprite so a plugin can use a
PINK boss bar purely as a text anchor.

Not affiliated with Mojang. The derived textures are Mojang's; this is only
useful to players who already own the game.

## Contract

Font `hcpack:hud`, icons 16x16, `height` 16, `ascent` 12.

| Codepoint | Icon |
|---|---|
| `U+E000` / `U+E001` | ender dragon - grey / colour |
| `U+E002` / `U+E003` | wither - grey / colour |
| `U+E004` / `U+E005` | warden - grey / colour |
| `U+E006` / `U+E007` | elder guardian - grey / colour |

Negative space: `U+E100..U+E107` = -1, -2, -3, -4, -8, -16, -32, -64 px.
Positive space: `U+E110..U+E117` = the same values, positive.

The PINK boss bar (`Overlay.PROGRESS` only) draws nothing. GREEN / YELLOW / RED
and the notched overlays are untouched.

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
