"""Load Poly Haven models and materials from the shared asset library into a Blender scene.

The library is filled by art/fetch_assets.py (default /store/asset-library, override with ASSET_LIBRARY).
Models are CC0 .blend files that carry their own materials and reference textures next to the file.
"""
import os

import bpy
from mathutils import Vector

LIB = os.environ.get("ASSET_LIBRARY", "/store/asset-library")


def model_path(slug, res="2k"):
    return os.path.join(LIB, "polyhaven", "models", slug, "%s_%s.blend" % (slug, res))


def texture_path(slug, res="1k"):
    return os.path.join(LIB, "polyhaven", "textures", slug, "%s_%s.blend" % (slug, res))


def available(slug, res="2k"):
    return os.path.exists(model_path(slug, res))


def bounds(objs):
    """World-space (min, max) corners of the mesh objects in `objs`."""
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def load_model(slug, loc=(0, 0, 0), rot_z=0.0, scale=1.0, res="2k"):
    """Append a model and return (root empty, mesh objects). Move the model by moving the root.

    Poly Haven models sit on the floor with their origin at the base, so `loc` is where the base goes.
    """
    path = model_path(slug, res)
    if not os.path.exists(path):
        raise FileNotFoundError("model not in the library yet: %s" % path)
    scene = bpy.context.scene
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = list(src.collections)
    new = []
    for coll in dst.collections:
        scene.collection.children.link(coll)
        new += list(coll.all_objects)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(slug + "_root", None)
    scene.collection.objects.link(root)
    for o in new:
        if o.parent is None:
            o.parent = root
    root.location = loc
    root.rotation_euler = (0, 0, rot_z)
    root.scale = (scale,) * 3
    bpy.context.view_layer.update()
    return root, [o for o in new if o.type == "MESH"]


def load_material(slug, res="1k"):
    """Append the material of a Poly Haven texture set (walls, floors and so on)."""
    path = texture_path(slug, res)
    if not os.path.exists(path):
        raise FileNotFoundError("texture not in the library yet: %s" % path)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.materials = [m for m in src.materials if m == slug] or list(src.materials)[:1]
    return dst.materials[0]


def apply_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def tint(mat, hex_colour, strength=1.0):
    """Multiply a material's base colour by a tint (e.g. to push plaster toward archive green)."""
    import lib
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    sock = bsdf.inputs["Base Color"]
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = strength
    mix.inputs["B"].default_value = lib.rgb(hex_colour)
    if sock.links:
        src = sock.links[0].from_socket
        nt.links.new(src, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = sock.default_value
    nt.links.new(mix.outputs["Result"], sock)


def world_uv(obj, metres=1.0):
    """Cube-project UVs so one texture tile covers `metres` of surface (apply the object's scale first)."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=metres)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
