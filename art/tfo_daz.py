"""Build a Daz Genesis 9 character in Blender from downloaded Daz content (Diffeomorphic DAZ Importer), then render a portrait.

    blender -b --factory-startup --python daz_char.py -- <character name e.g. Laura> <out.png> [--fast] [--hair] [--shirt]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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

# --- our own auto-fit: what Daz Studio does when a character shape changes -------------------------------
# The character's shape arrives as shape keys over the default Genesis 9 body. Every separate piece
# (clothes, lashes, brows, eyes, teeth) was modelled for the default body, so move each of its points by
# however much the skin under it moved. Eyeballs and teeth move as rigid blocks so they keep their shape.
def auto_fit(body, followers):
    from mathutils.bvhtree import BVHTree
    keys = body.data.shape_keys
    if not keys:
        return
    basis = [v.co.copy() for v in keys.key_blocks["Basis"].data]
    dg = bpy.context.evaluated_depsgraph_get()
    em = body.evaluated_get(dg).to_mesh()
    morphed = [v.co.copy() for v in em.vertices]
    body.evaluated_get(dg).to_mesh_clear()
    polys = [tuple(p.vertices) for p in body.data.polygons]
    tree_basis = BVHTree.FromPolygons(basis, polys)
    tree_morph = BVHTree.FromPolygons(morphed, polys)
    to_body = body.matrix_world.inverted()

    def displacement(local):
        hit = tree_basis.find_nearest(local)
        if hit[0] is None:
            return Vector((0, 0, 0))
        _, _, fi, _ = hit
        idx = polys[fi]
        ws = [1.0 / max((basis[i] - local).length, 1e-6) for i in idx]
        tot = sum(ws)
        return sum(((morphed[i] - basis[i]) * (w / tot) for i, w in zip(idx, ws)), Vector((0, 0, 0)))

    for ob, rigid in followers:
        if ob is None:
            continue
        mw = ob.matrix_world
        pts = [to_body @ (mw @ v.co) for v in ob.data.vertices]
        # Already fitted? Compare how snugly it sits on each version of the body.
        sample = pts[:: max(1, len(pts) // 400)]
        d_basis = sum((tree_basis.find_nearest(p)[3] or 0) for p in sample) / len(sample)
        d_morph = sum((tree_morph.find_nearest(p)[3] or 0) for p in sample) / len(sample)
        if d_morph < d_basis * 0.8:
            print("FIT skip (already fitted)", ob.name)
            continue
        if rigid:
            groups = {}
            for i, p in enumerate(pts):
                groups.setdefault(p.x > 0 if rigid == "pair" else 0, []).append(i)
            disp = [None] * len(pts)
            for g, idxs in groups.items():
                c = sum((pts[i] for i in idxs), Vector((0, 0, 0))) / len(idxs)
                d = displacement(c)
                for i in idxs:
                    disp[i] = d
        else:
            disp = [displacement(p) for p in pts]
        inv = (to_body @ mw).inverted().to_3x3()        # body-space offsets back into the piece's own space
        offs = [inv @ d for d in disp]
        blocks = ob.data.shape_keys.key_blocks if ob.data.shape_keys else None
        for i, v in enumerate(ob.data.vertices):
            v.co += offs[i]
        if blocks:
            for kb in blocks:
                for i, pt in enumerate(kb.data):
                    pt.co += offs[i]
        ob.data.update()
        print("FIT moved %s (%s), mean shift %.1f mm" % (ob.name, rigid or "soft", 1000 * sum(d.length for d in disp) / len(disp)))


meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in bpy.context.view_layer.objects:
    o.select_set(o.type == "MESH")
body = next(o for o in meshes if o.name.startswith("%s for Genesis 9" % name))
auto_fit(body, [(o, "pair" if "Eyes" in o.name else ("block" if "Mouth" in o.name else None))
                for o in meshes if o is not body])
# Clothes made for a slimmer figure can still sit partly inside the skin: push those parts just outside it.
for o in meshes:
    if "Shirt" in o.name or "Shorts" in o.name:
        m = o.modifiers.new("stay_outside_skin", "SHRINKWRAP")
        m.target = body
        m.wrap_method = "NEAREST_SURFACEPOINT"
        m.wrap_mode = "OUTSIDE"
        m.offset = 0.003
        o.modifiers.move(o.modifiers.find("stay_outside_skin"), 0) if hasattr(o.modifiers, "move") else None
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


# --- our own hair: a MakeHuman hairstyle shell, wrapped onto the Daz head, grown into real strands ---------
def head_metrics(ob):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    top = max(p.z for p in pts)
    band = [p for p in pts if top - 0.15 < p.z < top - 0.05]
    cap = [p for p in pts if p.z > top - 0.10]
    return top, max(p.x for p in band) - min(p.x for p in band), sum(p.y for p in cap) / len(cap)


if "--bob" in args:
    os.environ["TFO_PEOPLE_IMPORT"] = "1"
    import tfo_lab
    import tfo_people
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath="/store/asset-library/mpfb/data/hair/toigo_curled_under_bob/bob_curled_under.obj")
    shell = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    shell.scale = (0.1, 0.1, 0.1)                       # MakeHuman works in decimetres
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = shell
    for o in bpy.context.view_layer.objects:
        o.select_set(o == shell)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    htop, hwidth, hy = head_metrics(body)
    stop, swidth, sy = head_metrics(shell)
    k = (hwidth + 0.014) / swidth                      # the shell sits about 7 mm off each side of the head
    shell.scale = (k, k, k)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    stop, swidth, sy = head_metrics(shell)
    shell.location = (0.0, hy - sy, htop + 0.006 - stop)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    # Real hair lies on the crown and only gains volume lower down: pull the top of the shell onto the scalp,
    # fading back to the hairstyle's own shape between the temples and the ears.
    crown = shell.vertex_groups.new(name="crown")
    for v in shell.data.vertices:
        z = (shell.matrix_world @ v.co).z
        w = min(1.0, max(0.0, (z - (htop - 0.19)) / 0.12)) ** 1.5
        if w > 0:
            crown.add([v.index], w, "REPLACE")
    hug = shell.modifiers.new("hug_crown", "SHRINKWRAP")
    hug.target = body
    hug.wrap_method = "NEAREST_SURFACEPOINT"
    hug.wrap_mode = "ON_SURFACE"
    hug.offset = 0.0035
    hug.vertex_group = "crown"
    wrap = shell.modifiers.new("keep_off_scalp", "SHRINKWRAP")
    wrap.target = body
    wrap.wrap_method = "NEAREST_SURFACEPOINT"
    wrap.wrap_mode = "OUTSIDE"
    wrap.offset = 0.004                                 # never closer than 4 mm to the skin
    print("BOB fitted: head width %.3f, scale %.3f" % (hwidth, k))
    tfo_lab.strand_hair(shell, melanin=0.75, redness=0.8, per_gap=1500, thickness=0.008, radius=0.00006)
    cap = bpy.data.materials.new("hair_cap")
    cap.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = lib.rgb("#4a2716")
    cap.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    shell.data.materials.clear()
    shell.data.materials.append(cap)

# --- a knitted look for the shirt -----------------------------------------------------------------------
if "--knit" in args and find("Shirt"):
    knit = bpy.data.materials.new("knit")
    nt = knit.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lib.rgb("#7f8c6c")
    b.inputs["Roughness"].default_value = 0.88
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.4
    ribs = nt.nodes.new("ShaderNodeTexWave")
    ribs.bands_direction = "X"
    ribs.inputs["Scale"].default_value = 90.0
    ribs.inputs["Distortion"].default_value = 2.0
    fuzz = nt.nodes.new("ShaderNodeTexNoise")
    fuzz.inputs["Scale"].default_value = 600.0
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "ADD"
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    nt.links.new(ribs.outputs["Fac"], mix.inputs[0])
    nt.links.new(fuzz.outputs["Fac"], mix.inputs[1])
    nt.links.new(mix.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    for shirt in [o for o in bpy.data.objects if o.type == "MESH" and "Shirt" in o.name]:
        shirt.data.materials.clear()
        shirt.data.materials.append(knit)
        for poly in shirt.data.polygons:
            poly.material_index = 0
        print("KNIT on", shirt.name)
    for o in bpy.data.objects:
        if o.type == "MESH" and any(sl.material and ("Shirt" in sl.material.name or "Trim" in sl.material.name) for sl in o.material_slots):
            print("KNIT still-shirt-material on", o.name, [sl.material.name for sl in o.material_slots])

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
