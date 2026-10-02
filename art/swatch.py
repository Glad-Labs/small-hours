"""Render preview swatches of Poly Haven texture sets (a tiled plane plus a sphere) to choose materials by eye.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/swatch.py -- slug1 slug2 ... [--out DIR] [--size 288]
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import ph  # noqa: E402

args = lib.script_args()
size = int(args[args.index("--size") + 1]) if "--size" in args else 288
out_dir = args[args.index("--out") + 1] if "--out" in args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "swatches")
slugs = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--out", "--size"))]
os.makedirs(out_dir, exist_ok=True)
for slug in slugs:
    lib.reset()
    try:
        mat = ph.load_material(slug)
    except Exception as e:
        print("SKIP", slug, e)
        continue
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, 0), rotation=(1.2, 0, 0))
    plane = bpy.context.active_object
    ph.apply_material(plane, mat)
    lib.world_gradient("#8a8f9c", "#4a5060", strength=1.0)
    lib.light("key", "AREA", (-1.5, -2.5, 2.5), 250, "#fff1de", size=2.0, target=(0, 0, 0))
    lib.camera((0, -2.8, 0.9), (0, 0, 0), lens=45)
    lib.setup_render(size, size, 16)
    lib.render(os.path.join(out_dir, slug + ".png"))
