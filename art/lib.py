"""Small helpers shared by the Blender scripts that build the game's art.

Run through Blender, for example:
    flatpak run --command=blender org.blender.Blender -b --factory-startup --python art/office.py -- --fast
Everything is built from code, so every model is reproducible and easy to tweak.
"""
import math
import sys

import bpy
from mathutils import Vector


_materials = {}


def script_args():
    """Arguments after the `--` that separates Blender's own flags from ours."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _materials.clear()
    return bpy.context.scene


def rgb(hex_colour):
    """'#rrggbb' to a linear RGBA tuple (Blender colour inputs are linear)."""
    h = hex_colour.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)



def material(name, colour, rough=0.6, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0):
    """A Principled BSDF material, cached by name."""
    if name in _materials:
        return _materials[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True     # deprecated no-op on recent Blender, needed on older ones
    except Exception:
        pass
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgb(colour)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    if emit:
        b.inputs["Emission Color"].default_value = rgb(emit)
        b.inputs["Emission Strength"].default_value = emit_strength
    _materials[name] = m
    return m


def _finish(o, name, mat, bevel, smooth=False):
    o.name = name
    if mat is not None:
        o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    if smooth:
        bpy.ops.object.shade_smooth()
    return o


def box(name, size, loc, mat, bevel=0.012, rot=(0, 0, 0)):
    """A box centred on `loc`; `size` is (x, y, z) in metres."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, name, mat, bevel)


def cylinder(name, radius, depth, loc, mat, rot=(0, 0, 0), bevel=0.0, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc, rotation=rot)
    return _finish(bpy.context.active_object, name, mat, bevel, smooth=True)


def sphere(name, radius, loc, mat, scale=(1, 1, 1), segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments, ring_count=rings, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    return _finish(o, name, mat, 0.0, smooth=True)


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=35, shift_y=0.0):
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    cam.data.lens = lens
    cam.data.shift_y = shift_y
    look_at(cam, target)
    bpy.context.scene.camera = cam
    return cam


def light(name, kind, loc, energy, colour="#ffffff", size=1.0, size_y=None, target=None, spot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = rgb(colour)[:3]
    if kind == "AREA":
        ld.shape = "RECTANGLE" if size_y else "SQUARE"
        ld.size = size
        if size_y:
            ld.size_y = size_y
    elif kind == "POINT":
        ld.shadow_soft_size = size
    elif kind == "SPOT":
        ld.shadow_soft_size = size
        ld.spot_size = math.radians(spot or 60)
        ld.spot_blend = 0.5
    elif kind == "SUN":
        ld.angle = math.radians(size)
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if target is not None:
        look_at(o, target)
    return o


def world_gradient(horizon, zenith, strength=1.0):
    """A sky that fades from `horizon` to `zenith`; it is what you see through the window."""
    scene = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapn = nt.nodes.new("ShaderNodeMapRange")
    bg.inputs["Strength"].default_value = strength
    ramp.color_ramp.elements[0].color = rgb(horizon)
    ramp.color_ramp.elements[1].color = rgb(zenith)
    mapn.inputs["From Min"].default_value = -0.05
    mapn.inputs["From Max"].default_value = 0.6
    # In a world shader, "Generated" is the view direction, so its Z is how high the ray points.
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapn.inputs["Value"])
    nt.links.new(mapn.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_render(width, height, samples, transparent=False, exposure=0.0):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"             # works the same everywhere; the denoiser keeps low sample counts clean
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.cycles.denoiser = "OPENIMAGEDENOISE"
    s.render.resolution_x = width
    s.render.resolution_y = height
    s.render.resolution_percentage = 100
    s.render.film_transparent = transparent
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    s.view_settings.view_transform = "AgX"
    s.view_settings.exposure = exposure


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("WROTE", path)


# --- Shapes used for characters --------------------------------------------------------------
def cone(name, r_bottom, r_top, depth, loc, mat, verts=32):
    bpy.ops.mesh.primitive_cone_add(radius1=r_bottom, radius2=r_top, depth=depth, vertices=verts, location=loc)
    return _finish(bpy.context.active_object, name, mat, 0.0, smooth=True)


def torus(name, major, minor, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=32, minor_segments=8,
                                     location=loc, rotation=rot)
    return _finish(bpy.context.active_object, name, mat, 0.0, smooth=True)


def limb(name, p0, p1, radius, mat, cap0=True, cap1=True):
    """A capsule between two points; poses are just joint positions."""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    parts = []
    if d.length > 1e-6:
        mid = (a + b) / 2
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=d.length, vertices=24, location=mid)
        c = bpy.context.active_object
        c.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        parts.append(_finish(c, name, mat, 0.0, smooth=True))
    for flag, pt in ((cap0, a), (cap1, b)):
        if flag:
            parts.append(sphere(name + "_cap", radius, tuple(pt), mat, segments=24, rings=12))
    return parts


def tube(name, points, radius, mat):
    """A smooth rounded line through `points`; used for brows, mouths and eyelids."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    sp = curve.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, pt in zip(sp.bezier_points, points):
        bp.co = pt
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def group(name, pivot, objs):
    """Parent `objs` to a new empty at `pivot`, so rotating the empty bends that part of the body."""
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = pivot
    bpy.context.view_layer.update()
    inv = e.matrix_world.inverted()
    for o in objs:
        o.parent = e
        o.matrix_parent_inverse = inv
    return e
