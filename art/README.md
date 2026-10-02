# art/ — the game's 3D art, built from code

Every image the game shows is rendered headless in Blender from a script. The art is **realistic**: scanned
props and materials from Poly Haven (CC0) and a character built with MPFB (MakeHuman for Blender, CC0 assets).
An older low-poly "stylised" version of the same scenes is kept alongside it. A full rebuild takes a few minutes.

| File | What it makes |
|---|---|
| `office_real.py` | The night archive office, 1920x1080, as `bg_office` |
| `elena_real.py` | Elena Voss in three poses (`guarded`, `tense`, `broken`) as transparent 1050x1400 sprites |
| `office.py`, `elena.py` | The older stylised low-poly versions (`--stylised`), output as `*_stylised` and not used by the game |
| `lib.py` | Shared helpers: materials, boxes, limbs, curves, lights, camera, render setup |
| `ph.py` | Loads Poly Haven models and materials from the asset library; tints materials; maps UVs in metres |
| `mpfb_helpers.py` | Builds characters with the MPFB add-on: body, skin, clothes, hair, glasses |
| `catalog.py`, `swatch.py` | Render preview sheets of library models and textures, with real dimensions, to choose by eye |
| `fetch_assets.py` | Downloads the shared asset library (below) |
| `install_mpfb_assets.py` | Unpacks the MPFB asset packs where the add-on reads them |
| `finalize.py` | Converts renders in `art/out/` to WebP in `orchard-street/game/images/` (about 60 KB each) |
| `build.sh` | Runs the render scripts and `finalize.py` |

## The shared asset library

Free 3D assets live outside any project, in `/store/asset-library` (override with `ASSET_LIBRARY`), so every
game can use them. `LICENSES.md` there says what each folder allows.

```
python3 art/fetch_assets.py --models 2k --hdris 2k --textures 1k --mpfb all   # about 28 GB, resumable
python3 art/install_mpfb_assets.py                                             # after the MPFB packs arrive
```

- **Poly Haven** (CC0, no credit needed): 521 models at 2k, 997 HDRI skies at 2k, 864 material textures at 1k.
  `polyhaven/index.json` lists every asset with categories and tags.
- **MPFB asset packs** (MakeHuman community): 476 clothing items, 71 hairstyles, 79 skins, 41 poses, face rigs.
  Packs in `mpfb/asset_packs/cc0/` need no credit. **`cc-by/` packs require crediting the author** in any game that
  ships them; the elegant suit, hair and glasses used for Elena are CC0.
- The MPFB add-on itself (GPL-3.0) is installed in Blender from extensions.blender.org; characters it exports are not
  covered by that licence.

To choose furniture, render a preview sheet instead of guessing from names:
`blender -b --factory-startup --python /abs/path/art/catalog.py -- slug1 slug2 ... --out DIR`.

## Rebuilding

```
art/build.sh            # full quality: renders to art/out/, then writes game/images/*.webp
art/build.sh --fast     # quick low-resolution drafts (written next to the full renders, not copied to the game)
art/build.sh --stylised # the older low-poly art, which needs no asset library
```

It drives Blender headless through the Flatpak (`org.blender.Blender`, Blender 5.2 LTS with the MPFB 2.0.17 extension
installed). For another install set `BLENDER_CMD`. Renders use Cycles on the CPU with the OpenImageDenoise denoiser,
so no GPU is needed. **Script paths must be absolute**: Blender resolves relative ones inside its Flatpak sandbox.

After changing art, rebuild the browser package too, or the phone keeps the old images:
`renpy.sh launcher web_build orchard-street --destination orchard-street/build/web`.

## Art direction

- **Mood:** night, a cool moonlit window against one warm desk lamp, in a dark room; a wall clock stopped at 10:41,
  the time in the intro.
- **Layout:** the game's menu sits on the left and Elena at the right, so the left third of the background is kept dark
  and calm, and the lamp and terminal sit either side of where she stands.
- **Sizes:** the background is 1920x1080 (shown at zoom 2/3); sprites are 1050x1400 (shown at zoom 1/2). Rendering larger
  than the screen keeps them sharp on big monitors and phones.
- **Poses:** each pose in `elena_real.py` is a dictionary: elbow and wrist targets that the arm bones are aimed at, a
  head tilt, and ARKit-style face weights (`browInnerUp`, `eyeBlinkLeft`, `mouthFrownRight`...). Adding an expression is
  adding an entry plus an `image elena <name>` line in `script.rpy`.

## Changing Elena's look

- **Hair:** `art/build.sh --hair long01` is not wired through; run the script directly:
  `blender -b --factory-startup --python /abs/path/art/elena_real.py -- --hair long01` (also `bob02`, `short02`, ...;
  see `ls /store/asset-library/mpfb/data/hair`). It is tinted dark brown in the script.
- **Skin and makeup:** the skin is `toigo_light_skin_female_bronze_with_makeup` (CC0). Other skins are in
  `mpfb/data/skins`; the `*_with_makeup` ones are warmer and more finished than the bare skins.
- **Face:** `FACE_DETAILS` in `elena_real.py` nudges MakeHuman's face sliders (eye height, lips, cheekbones, chin,
  head shape). Every slider is a file in the add-on's `data/targets/`; add an entry to try another.
- A tweak test is cheap: it showed that makeup skin plus those slider changes make the stock face noticeably softer
  and more feminine, and loose hair that frames the face is more flattering than a tight ponytail.

## MPFB gotchas (learned the hard way)

- Create the human with `detailed_helpers=True`. The rig is fitted from the joint helper vertices; without them the
  bones land in the wrong places (shoulders at a third of the right height).
- Add the rig before the clothes and hair so each asset is rigged as it is fitted.
- Once a rig exists MPFB parents assets to the rig, not the body, so find them by name (`mpfb_helpers.assets`).
- A factory-startup Blender has user extensions disabled; enable the add-on in the script (`mpfb_helpers.enable`).
- Colour changes (dark hair, dark glasses) work by multiplying the base colour node; see `mpfb_helpers.tint_object`.

## Known limits

The character is a game-quality MakeHuman figure, not a hand-sculpted portrait: stock face shapes, simple hair, and
hands that are a little stiff (they are posed by aiming bones, with straight fingers). Sprites use an orthographic
camera, so they look slightly flatter than the perspective background. One room and one character exist so far.
