# art/ — the game's 3D art, built from code

Every image the game shows is rendered from a 3D scene that a short Blender script builds from
primitives. There is no hand-modelled or hand-painted asset, so anything can be changed by editing a
number and re-rendering (a full rebuild takes about a minute on a 16-core CPU).

| File | What it makes |
|---|---|
| `office.py` | The night archive office, rendered at 1920x1080 as `bg_office` |
| `elena.py` | Elena Voss in three poses (`guarded`, `tense`, `broken`), rendered as transparent 1050x1400 sprites |
| `lib.py` | Shared helpers: materials, beveled boxes, limbs, curves, lights, camera, render setup |
| `finalize.py` | Converts the renders in `art/out/` to WebP in `orchard-street/game/images/` (about 60 KB each) |
| `build.sh` | Runs all of the above |

## Rebuilding

```
art/build.sh            # full quality: renders to art/out/, then writes game/images/*.webp
art/build.sh --fast     # quick low-resolution drafts (written next to the full renders, not copied to the game)
```

It drives Blender headless through the Flatpak (`org.blender.Blender`, tested with Blender 5.2 LTS). For
another install set `BLENDER_CMD`, for example `BLENDER_CMD=/opt/blender/blender art/build.sh`. Renders use
Cycles on the CPU with the OpenImageDenoise denoiser, so no GPU is needed. Scripts take absolute paths
(Blender resolves relative ones inside its Flatpak sandbox).

After changing art, rebuild the browser package too, or the phone keeps the old images:
`renpy.sh launcher web_build orchard-street --destination orchard-street/build/web`.

## Art direction

- **Mood:** night, a cool moonlit window against one warm desk lamp, in a dark room. Soft global
  illumination, beveled low-poly shapes, flat-ish colours, and a stopped wall clock showing 10:41, the
  time in the intro.
- **Layout:** the game's menu buttons sit on the left and Elena stands at the right (`transform stage` in
  `script.rpy`), so the left third of the background is kept dark and calm, and the lamp and terminal sit
  either side of where she stands so neither is hidden.
- **Sizes:** the background is 1920x1080 and shown at zoom 2/3; the sprites are 1050x1400 and shown at
  zoom 1/2 (525x700). Rendering larger than the screen keeps them sharp on big monitors and phones.
- **Poses:** each pose in `elena.py` is a dictionary of joint positions, a body lean, a head tilt and a
  few face numbers (brow angles, eyelid openness, mouth curve). Adding an expression is adding an entry,
  then an `image elena <name>` line in `script.rpy`.

## Known limits

The character is stylised and toy-like, not an illustrator's work: hands are rounded mitts, the hair is a
few simple shapes, and there is no cloth detail or hand-painted texture. Procedural models are strong at
rooms, props and clean shapes, and weak at organic detail. Sprites use an orthographic camera, so they
look slightly flatter than the perspective background. Only one room and one character exist so far.
