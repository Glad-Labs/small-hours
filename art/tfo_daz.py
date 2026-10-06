"""Build a Daz Genesis 9 character in Blender from downloaded Daz content (Diffeomorphic DAZ Importer), then render a portrait.

    blender -b --factory-startup --python daz_char.py -- <character name e.g. Laura> <out.png> [--fast] [--hair] [--shirt]
"""
import os
import sys
import time

sys.path.insert(0, "/home/mattm/ai-interrogation/art")
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import lib  # noqa: E402

args = lib.script_args()
name, out = args[0], args[1]
fast = "--fast" in args
LIB = "/store/asset-library/daz"
G9 = LIB + "/People/Genesis 9"
ANAT = G9 + "/Anatomy/Daz Originals/Base Anatomy"
MATS = G9 + "/Characters/Daz Originals/%s G9/Materials" % name

lib.reset()
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.import_daz")
from bl_ext.user_default.import_daz import api  # noqa: E402
api.set_silent_mode(True)
api.set_global_setting("contentDirs", [LIB])
api.set_global_setting("onlyDbz", False)
api.set_global_setting("viewportColors", "ORIGINAL")   # the colour guess crashes on some assets; preview only


def load(files, **kw):
    api.set_selection(files)
    t0 = time.time()
    res = bpy.ops.daz.easy_import_daz(fitMeshes="MORPHED", useEliminateEmpties=True, useMergeRigs=True, useUpdateErcBones=True, **kw)
    print("STEP import %s %s %.1fs %s" % ([os.path.basename(f) for f in files], res, time.time() - t0, api.get_error_message()[:200]))


extras = []
if "--hair" in args:
    extras.append(G9 + "/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf")
if "--shirt" in args:
    extras.append(G9 + "/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf")
extras.append(ANAT + "/Eyebrows Card/Style 03/" + sorted(os.listdir(ANAT + "/Eyebrows Card/Style 03"))[0]) if os.path.isdir(ANAT + "/Eyebrows Card/Style 03") else None
load([G9 + "/Characters/%s for Genesis 9.duf" % name] +
     [ANAT + "/Genesis 9 %s.duf" % part for part in ("Eyes", "Mouth", "Tear", "Eyelashes")] + extras)

# The anatomy pieces arrive twice; keep the first copy of each.
for o in list(bpy.data.objects):
    if o.name.endswith(".001"):
        bpy.data.objects.remove(o, do_unlink=True)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in bpy.context.view_layer.objects:
    o.select_set(o.type == "MESH")
body = next(o for o in meshes if o.name.startswith("%s for Genesis 9" % name))
bpy.context.view_layer.objects.active = body
def apply_preset(preset, target):
    if not os.path.exists(preset) or target is None:
        return
    for o in bpy.context.view_layer.objects:
        o.select_set(o == target)
    bpy.context.view_layer.objects.active = target
    api.set_selection([preset])
    res = bpy.ops.daz.import_daz_materials()
    print("STEP preset %s -> %s %s %s" % (os.path.basename(preset), target.name, res, api.get_error_message()[:200]))


def find(word):
    return next((o for o in bpy.data.objects if o.type == "MESH" and word in o.name), None)


apply_preset(MATS + "/%s G9 All MAT.duf" % name, body)
apply_preset(MATS + "/%s G9 Eyes.duf" % name, find("Eyes"))
apply_preset(MATS + "/%s G9 Eyelashes.duf" % name, find("Eyelashes"))
apply_preset(ANAT + "/Eyebrows Card/Materials/G9 Eyebrows Color Brown.duf", find("Eyebrows"))
hair = find("Pixie Cut")
if hair:
    apply_preset(G9 + "/Hair/Daz Originals/Base Hair/Materials/G9 Base dForce Pixie Hair Auburn.duf", hair)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (hair, body))
    bpy.context.view_layer.objects.active = hair
    try:
        res = bpy.ops.daz.make_hair(strandType="LINE", output="HAIR_CURVES", keepMaterial=True)
        print("STEP make_hair", res, api.get_error_message()[:300])
    except Exception as e:
        print("STEP make_hair failed", str(e)[:400])
TEX = LIB + "/Runtime/Textures/DAZ/Characters/Genesis9/Base/Eyes/"


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def image_node(m, path, colour=True):
    n = m.node_tree.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    if not colour:
        n.image.colorspace_settings.name = "Non-Color"
    return n


# Eyes: the importer leaves Genesis 9's layered iris/sclera shader blank, so use the combined eye texture.
EYE_TEX = TEX + "G9_Eyes09_D.jpg"
eyes = find("Eyes")
for slot in (eyes.material_slots if eyes else []):
    m = slot.material
    b = principled(m)
    if "Moisture" in m.name:
        b.inputs["Alpha"].default_value = 0.0          # the clear wet layer over the eye: reflections only
        b.inputs["Roughness"].default_value = 0.02
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat Roughness"].default_value = 0.01
        m.surface_render_method = "BLENDED" if hasattr(m, "surface_render_method") else m.surface_render_method
        continue
    # Project the iris from the front, centred on this eye: the imported UVs do not match the texture.
    idx = [i for i, sl in enumerate(eyes.material_slots) if sl.material == m]
    pts = [eyes.matrix_world @ eyes.data.vertices[vi].co for poly in eyes.data.polygons if poly.material_index in idx
           for vi in poly.vertices]
    cx = sum(p.x for p in pts) / len(pts)
    cz = sum(p.z for p in pts) / len(pts)
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    K = 0.11 / 0.0115                       # texture units per metre: iris 0.11 wide on the map, 11.5 mm in life
    mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY_ADD"
    mu.inputs[1].default_value = K; mu.inputs[2].default_value = 0.25 - cx * K
    mv = nt.nodes.new("ShaderNodeMath"); mv.operation = "MULTIPLY_ADD"
    mv.inputs[1].default_value = K; mv.inputs[2].default_value = 0.75 - cz * K
    nt.links.new(sep.outputs["X"], mu.inputs[0])
    nt.links.new(sep.outputs["Z"], mv.inputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mu.outputs[0], comb.inputs["X"])
    nt.links.new(mv.outputs[0], comb.inputs["Y"])
    tex = image_node(m, EYE_TEX)
    tex.extension = "EXTEND"
    nt.links.new(comb.outputs[0], tex.inputs["Vector"])
    m.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    if "Subsurface Weight" in b.inputs:
        b.inputs["Subsurface Weight"].default_value = 0.0
BASE = LIB + "/Runtime/Textures/DAZ/Characters/Genesis9/Base/"


def cutout(m, alpha_path, colour=None, colour_path=None):
    """Card hair (lashes, brows): colour from a value or texture, see-through where the mask is dark."""
    b = principled(m)
    for l in list(b.inputs["Base Color"].links) + list(b.inputs["Alpha"].links):
        m.node_tree.links.remove(l)
    mask = image_node(m, alpha_path, colour=False)
    m.node_tree.links.new(mask.outputs["Color"], b.inputs["Alpha"])
    if colour_path:
        c = image_node(m, colour_path)
        m.node_tree.links.new(c.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = colour
    b.inputs["Roughness"].default_value = 0.5
    for key in ("Subsurface Weight", "Coat Weight", "Sheen Weight", "Transmission Weight", "Emission Strength"):
        if key in b.inputs:
            b.inputs[key].default_value = 0.0
    # Anything else wired into the shader output (translucency layers etc.) would bypass the cut-out.
    out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
    m.node_tree.links.new(b.outputs[0], out.inputs["Surface"])


lashes = find("Eyelashes")
for slot in (lashes.material_slots if lashes else []):
    cutout(slot.material, BASE + "Eyelashes/Genesis9_Eyelashes01_C.jpg", colour=(0.015, 0.01, 0.008, 1))
brows = find("Eyebrows")
for slot in (brows.material_slots if brows else []):
    cutout(slot.material, BASE + "Eyebrows/OpacityCutout02_Thick.jpg", colour=(0.045, 0.028, 0.02, 1))

tear = find("Tear")
for slot in (tear.material_slots if tear else []):
    principled(slot.material).inputs["Alpha"].default_value = 0.0

# Skin: the Iray-to-Cycles translation over-weights subsurface scattering, which reads as orange.
for slot in body.material_slots:
    m = slot.material
    if not m or not m.node_tree:
        continue
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if b and "Subsurface Weight" in b.inputs:
        print("SKIN", m.name, "sss weight", round(b.inputs["Subsurface Weight"].default_value, 2),
              "scale", round(b.inputs["Subsurface Scale"].default_value, 4) if "Subsurface Scale" in b.inputs else None,
              "radius", tuple(round(x, 2) for x in b.inputs["Subsurface Radius"].default_value))
        b.inputs["Subsurface Weight"].default_value = min(b.inputs["Subsurface Weight"].default_value, 0.35)
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.4, 0.25)
        if "Subsurface Scale" in b.inputs:
            b.inputs["Subsurface Scale"].default_value = 0.004
print("OBJECTS", sorted(o.name for o in bpy.data.objects if o.type == "MESH"))
for m in bpy.data.materials:
    imgs = [n.image.name for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image] if m.node_tree else []
    if any(k in m.name for k in ("Eye", "Iris", "Sclera", "Lash", "Head")):
        print("MAT", m.name, len(imgs), imgs[:4])

bpy.context.view_layer.update()
zs = [(body.matrix_world @ Vector(c)).z for c in body.bound_box]
top = max(zs)
eye = Vector((0, 0, top - 0.11))
lib.world_gradient("#2a2f44", "#0d1018", strength=0.5)
lib.light("key", "AREA", (eye.x - 1.1, eye.y - 1.4, eye.z + 0.6), 160, "#ffe0c4", size=1.4, target=tuple(eye))
lib.light("fill", "AREA", (eye.x + 1.3, eye.y - 1.2, eye.z - 0.1), 35, "#b9c6ff", size=1.6, target=tuple(eye))
lib.light("rim", "AREA", (eye.x + 0.9, eye.y + 1.1, eye.z + 0.5), 140, "#9fb4ff", size=0.6, target=tuple(eye))
lib.light("hair", "AREA", (eye.x - 0.4, eye.y + 0.6, eye.z + 1.1), 60, "#ffe9d0", size=0.6, target=tuple(eye))
dist, aim_drop = (0.45, 0.0) if "--close" in args else (1.25, 0.1)
cam = lib.camera((eye.x + 0.04, eye.y - dist, eye.z + 0.02), (eye.x, eye.y, eye.z - aim_drop), lens=85)
cam.data.dof.use_dof = "--close" not in args
cam.data.dof.focus_distance = (cam.location - eye).length
cam.data.dof.aperture_fstop = 2.8
w, h, spp = (540, 675, 96) if fast else (1080, 1350, 200)
lib.setup_render(w, h, spp, transparent=False, exposure=0.1)
bpy.context.scene.render.threads_mode = "FIXED"
bpy.context.scene.render.threads = 16
lib.render(out)

if "--diag" in args:
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 270, 338
    sc.cycles.samples = 24
    for word in ("Tear", "Eyelashes", "Mouth Mesh", "Hair Cap", "Eyebrows"):
        hidden = [o for o in bpy.data.objects if word in o.name and o.type == "MESH"]
        for o in hidden:
            o.hide_render = True
        lib.render(out.replace(".png", "_no_%s.png" % word.split()[0].lower()))
        for o in hidden:
            o.hide_render = False

if "--uvdiag" in args:
    for o in (find("Eyes"), find("Eyebrows")):
        for layer in o.data.uv_layers:
            us = [d.uv[0] for d in layer.data]
            vs = [d.uv[1] for d in layer.data]
            print("UVDIAG", o.name, layer.name, "active" if layer.active_render else "", "u %.2f..%.2f v %.2f..%.2f" % (min(us), max(us), min(vs), max(vs)))
        for slot in o.material_slots:
            m = slot.material
            print("UVDIAG mat", m.name, [(n.bl_idname, n.uv_map if n.bl_idname == "ShaderNodeUVMap" else "") for n in m.node_tree.nodes if n.bl_idname in ("ShaderNodeUVMap", "ShaderNodeTexImage")])

if "--eyediag" in args:
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    print("EYEDIAG armatures", [a.name for a in arms])
    main = next(a for a in arms if a.name.startswith(name))
    for b in ("l_eye", "r_eye"):
        if b in main.data.bones:
            print("EYEDIAG", b, "bone head", tuple(round(x, 3) for x in (main.matrix_world @ main.data.bones[b].head_local)))
    e = find("Eyes")
    import statistics
    for side, sign in (("left", 1), ("right", -1)):
        vs = [e.matrix_world @ v.co for v in e.data.vertices if (v.co.x * sign) > 0]
        c = [round(statistics.mean(p[i] for p in vs), 3) for i in range(3)]
        print("EYEDIAG eye mesh", side, "centre", c, "parent", e.parent.name if e.parent else None)

if "--frontuv" in args:
    e = find("Eyes")
    uvl = e.data.uv_layers.active.data
    best = {}
    for poly in e.data.polygons:
        mname = e.material_slots[poly.material_index].material.name
        for li in poly.loop_indices:
            v = e.data.vertices[e.data.loops[li].vertex_index]
            w = e.matrix_world @ v.co
            if mname not in best or w.y < best[mname][0]:
                best[mname] = (w.y, tuple(round(x, 3) for x in uvl[li].uv), tuple(round(x, 3) for x in w))
    for k, v in best.items():
        print("FRONTUV", k, "front y %.3f uv %s at %s" % v)
