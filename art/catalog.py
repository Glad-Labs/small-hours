"""Render a quick preview of library models on a neutral stage, and report their real dimensions.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/catalog.py -- slug1 slug2 ... [--out DIR] [--size 384]

Writes DIR/<slug>.png for each model and DIR/dimensions.json (width, depth, height in metres), so furniture
can be chosen by how it looks and laid out to scale. Models not in the library yet are skipped.
"""
import json
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import ph  # noqa: E402

args = lib.script_args()
size = int(args[args.index("--size") + 1]) if "--size" in args else 384
out_dir = args[args.index("--out") + 1] if "--out" in args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "catalog")
slugs = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--out", "--size"))]
os.makedirs(out_dir, exist_ok=True)
dims = {}

for slug in slugs:
    if not ph.available(slug):
        print("SKIP (not downloaded):", slug)
        continue
    lib.reset()
    scene = bpy.context.scene
    try:
        root, meshes = ph.load_model(slug)
    except Exception as e:
        print("FAILED", slug, e)
        continue
    lo, hi = ph.bounds(meshes)
    w, d, h = hi - lo
    dims[slug] = {"width": round(w, 3), "depth": round(d, 3), "height": round(h, 3)}
    centre = (lo + hi) / 2
    reach = max(w, d, h) * 1.35
    lib.world_gradient("#7d8190", "#3c4150", strength=0.9)
    lib.light("key", "AREA", (centre.x - reach, centre.y - reach * 1.4, centre.z + reach), 300 * reach ** 2, "#fff1de", size=reach, target=centre)
    lib.light("fill", "AREA", (centre.x + reach, centre.y - reach, centre.z + reach * 0.3), 120 * reach ** 2, "#cfdcff", size=reach, target=centre)
    lib.camera((centre.x + reach * 0.8, centre.y - reach * 1.7, centre.z + reach * 0.45), tuple(centre), lens=50)
    lib.box("floor", (reach * 6, reach * 6, 0.02), (centre.x, centre.y, lo.z - 0.01), lib.material("floor", "#9aa0a8", rough=0.8), bevel=0)
    lib.setup_render(size, size, 24, exposure=0.0)
    lib.render(os.path.join(out_dir, slug + ".png"))

json.dump(dims, open(os.path.join(out_dir, "dimensions.json"), "w"), indent=1)
print("DIMS", json.dumps(dims))
