# Hand-tuning the characters in Blender

The build scripts (`art/tfo_daz.py` realistic, `art/tfo_toon.py` toon) can save a ready-made scene instead of only
rendering. Four are already built in `art/scenes/`:

| File | What |
|---|---|
| `nell_realistic.blend` | Nell on Daz Kat (Amala face shape), grown auburn hair, chunky knit, makeup |
| `webb_realistic.blend` | Webb on Daz Matt (masculine shapes), silver crop, shirt, tie, waistcoat, ageing |
| `nell_toon.blend` | Nell on the Genesis 9 Toon figure, anime hair, cel shading, ink outlines |
| `webb_toon.blend` | Webb on the Genesis 9 Toon figure |

They are not in git: they contain Daz meshes, which the licence lets us render but not redistribute.

## Once: let the Blender app see the asset library

The scenes use textures from `/store/asset-library`. The Flatpak Blender cannot read `/store` unless allowed:

```bash
flatpak override --user --filesystem=/store org.blender.Blender
```

## Opening a scene

```bash
flatpak run org.blender.Blender ~/glad-labs-products/small-hours/art/scenes/nell_toon.blend
```

When Blender shows a bar saying automatic script execution is disabled, click **Allow Execution**. The face
expressions and fitted clothes are driven by small scripts; without them the face goes blank.

- **Look through the game camera:** Numpad 0. The frame is exactly the sprite (head to hips, 1050×1400).
- **Preview:** viewport shading set to *Rendered* (Z, then 8), or F12 for a full render. The toon scenes use EEVEE
  and are quick; the realistic ones use Cycles and take a minute or two.
- **Pose:** select the rig (named "... for Genesis 9" or "Genesis 9 Base Anime ..."), Ctrl+Tab for Pose Mode,
  rotate bones with R. Arm bones are `l_upperarm`, `l_forearm`, `l_hand` (and `r_`).
- **Face and expression:** with the rig selected, Object properties › Custom Properties lists the `facs_ctrl_*`
  sliders (smile, brows, eyes wide, …). The DAZ Runtime tab in the N sidebar has the same controls, grouped.
- **Lights:** realistic scenes have area lights named `key`, `fill`, `rim`, `rim2`, `hair`. In the toon scenes the one
  light that matters is the sun `DAZ Toon Light`: its angle decides where the cel shadow falls.
- **Materials:** hair, sweater, waistcoat and skin are ordinary node materials (Shading workspace).

Change anything you like and save. Don't rename the rig: the renderer finds the expression sliders on it.

## Turning your scene into game sprites

Tell me which file you changed and I render every expression from it. Under the hood:

```bash
flatpak run --command=blender --filesystem=/store org.blender.Blender -b -y art/scenes/nell_toon.blend \
    --python art/render_scene.py -- art/out/tfo_daz/nell_warm.png --expr warm
```

Expressions: `calm`, `warm`, `rattled` (Nell), `charm`, `pressed` (Webb). Your pose, camera, lights and materials
are kept; only the face sliders change.

## Adding Daz assets you downloaded

Put the zips in `~/Downloads` and tell me, or run `python3 art/daz_unpack.py ~/Downloads/*.zip` yourself.
It unpacks them into `/store/asset-library/daz` and lists what each contains, including which figure generation it
is for (Genesis 9 fits our figures directly; Genesis 8 items need a Genesis 8 figure).
