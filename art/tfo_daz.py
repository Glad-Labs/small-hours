"""Build a Daz Genesis 9 character in Blender from downloaded Daz content (Diffeomorphic DAZ Importer), then render a portrait.

    blender -b --factory-startup --python daz_char.py -- <character name e.g. Laura> <out.png> [--fast] [--hair] [--shirt]
"""
import math
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


def opt(flag, default=None):
    """The value after a --flag, or the default."""
    return args[args.index(flag) + 1] if flag in args else default

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
BROW_STYLE = "Style %02d" % int(opt("--browstyle", 3))
extras.append(ANAT + "/Eyebrows Card/%s/" % BROW_STYLE + sorted(os.listdir(ANAT + "/Eyebrows Card/%s" % BROW_STYLE))[0]) if os.path.isdir(ANAT + "/Eyebrows Card/%s" % BROW_STYLE) else None
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
def apply_shapes(spec):
    """Blend whole-head shapes from the pack's characters, e.g. 'BaseFeminine=1.0,Laura=0.25,Amala=0.2'. Shapes the
    character does not have yet are loaded from the pack first."""
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
    folder = "/store/asset-library/daz/data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9/"
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    for item in spec.split(","):
        key, val = item.split("=")
        prop = key if "_bs_" in key else key + "_head_bs_Head"
        try:
            if prop not in rig.keys():
                fname = prop + ".dsf"
                bpy.ops.daz.import_custom_morphs(filepath=folder + fname, directory=folder, files=[{"name": fname}],
                                                 bodypart="Face")
            api.set_slider(rig, prop, float(val))
            print("SHAPE", prop, val, "(present)" if prop in rig.keys() else "(MISSING)")
        except Exception as e:
            print("SHAPE could not apply", prop, str(e)[:120])
    api.update_drivers(rig)
    bpy.context.view_layer.update()


if opt("--shape"):
    apply_shapes(opt("--shape"))

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
EYE_TEX = TEX + "G9_Eyes%02d_D.jpg" % int(opt("--eyetex", 9))
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
    GAZE_DOWN = float(args[args.index("--gaze") + 1]) if "--gaze" in args else 0.0015   # metres
    mv.inputs[1].default_value = K; mv.inputs[2].default_value = 0.75 - (cz - GAZE_DOWN) * K
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


def cutout(m, alpha_path, colour=None, colour_path=None, strength=1.0):
    """Card hair (lashes, brows): colour from a value or texture, see-through where the mask is dark."""
    b = principled(m)
    for l in list(b.inputs["Base Color"].links) + list(b.inputs["Alpha"].links):
        m.node_tree.links.remove(l)
    mask = image_node(m, alpha_path, colour=False)
    if strength != 1.0:                                  # thin out the card: fewer, fainter hairs
        sc = m.node_tree.nodes.new("ShaderNodeMath")
        sc.operation = "MULTIPLY"
        sc.inputs[1].default_value = strength
        m.node_tree.links.new(mask.outputs["Color"], sc.inputs[0])
        m.node_tree.links.new(sc.outputs[0], b.inputs["Alpha"])
    else:
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
    cutout(slot.material, BASE + "Eyelashes/Genesis9_Eyelashes0%d_C.jpg" % int(opt("--lashes", 1)), colour=(0.015, 0.01, 0.008, 1),
           strength=float(opt("--lashfade", 1.0)))
brows = find("Eyebrows")
for slot in (brows.material_slots if brows else []):
    cutout(slot.material, BASE + ("Eyebrows/OpacityCutout01_Thin.jpg" if opt("--browcut", "thick") == "thin" else "Eyebrows/OpacityCutout02_Thick.jpg"), colour=((tuple(float(x) for x in args[args.index("--brow") + 1].split(",")) + (1,)) if "--brow" in args else (0.045, 0.028, 0.02, 1)))

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


# --- arms down: Daz characters arrive in an A-pose; rotate each upper arm until the arm hangs ---------------
def lower_arms(rig, hang_deg=14.0):
    for side in ("l", "r"):
        ub = rig.pose.bones[side + "_upperarm"]
        hand = rig.pose.bones[side + "_hand"]
        ub.rotation_mode = "XYZ"

        def reach():
            bpy.context.view_layer.update()
            return (rig.matrix_world @ hand.head) - (rig.matrix_world @ ub.head)
        ub.rotation_euler = (0, 0, 0)
        base = reach()
        best = None
        for axis in range(3):                              # which way does this bone swing the hand downward?
            for sign in (1, -1):
                e = [0.0, 0.0, 0.0]
                e[axis] = sign * math.radians(30)
                ub.rotation_euler = e
                drop = base.z - reach().z
                if best is None or drop > best[0]:
                    best = (drop, axis, sign)
        _, axis, sign = best
        ang = 90.0
        for deg in range(0, 91, 3):
            e = [0.0, 0.0, 0.0]
            e[axis] = sign * math.radians(deg)
            ub.rotation_euler = e
            v = reach()
            ang = math.degrees(math.acos(max(-1.0, min(1.0, -v.z / v.length))))
            if ang <= hang_deg:
                break
        print("ARMS %s axis %d sign %+d -> %d deg, arm now %.0f deg from vertical" % (side, axis, sign, deg, ang))


if "--arms" in args:
    lower_arms(next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name)),
               hang_deg=float(args[args.index("--arms") + 1]))

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
    cap.use_nodes = True   # new materials ignore their nodes otherwise
    cap.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = lib.rgb("#4a2716")
    cap.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    shell.data.materials.clear()
    shell.data.materials.append(cap)

if "--combbob" in args:
    import hairgen
    e = find("Eyes")
    ev = [e.matrix_world @ v.co for v in e.data.vertices]
    eye_mid = sum(ev, Vector((0, 0, 0))) / len(ev)
    chin = min((body.matrix_world @ v.co).z for v in body.data.vertices
               if abs((body.matrix_world @ v.co).x) < 0.02 and (body.matrix_world @ v.co).y < eye_mid.y - 0.02
               and eye_mid.z - 0.16 < (body.matrix_world @ v.co).z < eye_mid.z)
    style = hairgen.Style(cut="bob", part_x=0.006, length_z=chin - float(opt("--hairlen", 0.005)),
                          strands=50000 if fast else 90000, clumps=900 if fast else 1500, taper=0.16, hang_volume=0.006,
                          frame=42.0, comb_back=0.3, hairline_up=-0.012,
                          wave=float(opt("--waves", 0.0)), shine=float(opt("--shine", 0.0)),
                          melanin=float(opt("--haircolor", "0.86,0.5").split(",")[0]),
                          redness=float(opt("--haircolor", "0.86,0.5").split(",")[1]))
    hairgen.grow(body, eye_mid, style, name="nell_hair")

if "--crop" in args:
    import hairgen
    e = find("Eyes")
    ev = [e.matrix_world @ v.co for v in e.data.vertices]
    eye_mid = sum(ev, Vector((0, 0, 0))) / len(ev)
    style = hairgen.Style(cut="crop", part_x=0.025, strands=40000 if fast else 80000, clumps=1200 if fast else 2000,
                          color=(0.012, 0.012, 0.0135), radius=0.00007, lift=0.0025, volume=0.012, hairline_exp=0.6,
                          top_len=float(opt("--toplen", 0.06)), side_len=0.012, sweep=1.0, cap_shade=0.08,
                          frizz=float(opt("--frizz", 1.0)), clump=float(opt("--clump", 0.35)), lift_up=float(opt("--liftup", 1.0)),
                          color2=(tuple(float(x) for x in opt("--haircolor2").split(",")) if opt("--haircolor2") else None),
                          mix=float(opt("--hairmix", 0.5)), hairline_up=0.012 + float(opt("--recede", 0.0)), step=0.004)
    hairgen.grow(body, eye_mid, style, name="webb_hair")

# --- clothes made from the body (art/garments.py) ---------------------------------------------------------
if "--sweater" in args or "--waistcoat" in args:
    import garments
    pts = [body.matrix_world @ v.co for v in body.data.vertices]
    e_o = find("Eyes")
    eye_z = sum((e_o.matrix_world @ v.co).z for v in e_o.data.vertices) / len(e_o.data.vertices)
    neck_z = eye_z - 0.145                  # a crew neckline just below the throat
    hem_z = eye_z - 0.745                   # hip length: just below a sprite's bottom edge (eye - 0.73)
    if "--sweater" in args:
        garments.sweater(body, colour=opt("--sweatercolor", "#3f4d3c"), neck_z=neck_z + (0.03 if "--chunky" in args else 0.0),
                         hem_z=hem_z, chunky="--chunky" in args)
    if "--waistcoat" in args:
        shirt_ob = garments.shirt(body, neck_z=eye_z - 0.13, hem_z=hem_z)
        if "--tie" in args:
            bpy.context.view_layer.update()
            garments.collar_and_tie(body, shirt_ob, eye_z - 0.13, tie_colour=opt("--tie"), tie_bottom_z=eye_z - 0.375)
        garments.waistcoat(body, colour="#2d3238", v_bottom_z=eye_z - 0.34, hem_z=eye_z - 0.745)

if "--trousers" in args:
    import garments
    e_o = find("Eyes")
    eye_z = sum((e_o.matrix_world @ v.co).z for v in e_o.data.vertices) / len(e_o.data.vertices)
    tcol = args[args.index("--trousers") + 1]
    garments.trousers(body, colour=tcol, top_z=eye_z - 0.60, bottom_z=eye_z - 1.05)

# --- a knitted look for the shirt -----------------------------------------------------------------------
if "--knit" in args and find("Shirt"):
    knit = bpy.data.materials.new("knit")
    knit.use_nodes = True   # new materials ignore their nodes otherwise
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
# --- skin: ageing and makeup, anchored to the neutral face --------------------------------------------------
if opt("--age") or opt("--makeup") or opt("--stubble") or opt("--smooth"):
    import skinfx
    bpy.context.view_layer.update()
    lms = skinfx.landmarks(body)
    if opt("--age"):
        skinfx.age(body, lms, amount=float(opt("--age")))
    if opt("--makeup"):
        e_obj = find("Eyes")
        eye_cz = sum((e_obj.matrix_world @ v.co).z for v in e_obj.data.vertices) / len(e_obj.data.vertices)
        skinfx.makeup(body, lms, amount=float(opt("--makeup")), eye_z=eye_cz)
    if opt("--stubble"):
        skinfx.stubble(body, lms, amount=float(opt("--stubble")))
    if opt("--smooth"):
        skinfx.smooth(body, float(opt("--smooth")))
    print("SKINFX age", opt("--age"), "makeup", opt("--makeup"))

# --- expression: Daz's FACS controls, the same face units the MakeHuman characters used ------------------
EXPRESSIONS = {
    "neutral": {},
    "calm": {"facs_ctrl_MouthSmile": 0.3, "facs_ctrl_CheekSquint": 0.15, "facs_ctrl_BrowInnerUp": 0.2,
             "facs_ctrl_EyesSquint": 0.1},
    "warm": {"facs_ctrl_MouthSmile": 0.8, "facs_ctrl_MouthSmileWiden": 0.35, "facs_ctrl_CheekSquint": 0.3,
             "facs_ctrl_EyesSquint": 0.2, "facs_ctrl_BrowInnerUp": 0.22, "facs_ctrl_MouthDimple": 0.35},
    "rattled": {"facs_ctrl_BrowInnerUp": 1.0, "facs_ctrl_EyeWide": 0.85, "facs_ctrl_MouthPress": 0.3,
                "facs_ctrl_MouthFrown": 0.45, "facs_BrowOuterUpLeft": 0.5, "facs_BrowOuterUpRight": 0.5},
    "charm": {"facs_ctrl_MouthSmile": 0.8, "facs_ctrl_MouthSmileWiden": 0.2, "facs_ctrl_CheekSquint": 0.45,
              "facs_ctrl_EyesSquint": 0.22, "facs_BrowOuterUpLeft": 0.55, "facs_ctrl_BrowInnerUp": 0.15},
    "pressed": {"facs_ctrl_MouthSmile": 0.1, "facs_ctrl_MouthPress": 0.6, "facs_ctrl_EyesSquint": 0.45,
                "facs_BrowDownLeft": 0.6, "facs_BrowDownRight": 0.5, "facs_ctrl_JawClench": 0.3},
}
expr = args[args.index("--expr") + 1] if "--expr" in args else "calm"
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
if opt("--eyewide"):                                  # a permanent openness of the eyes, under every expression
    base_wide = float(opt("--eyewide"))
    EXPRESSIONS.setdefault(expr, {})
    EXPRESSIONS[expr]["facs_ctrl_EyeWide"] = max(EXPRESSIONS[expr].get("facs_ctrl_EyeWide", 0.0), base_wide)
    for side in ("Left", "Right"):                    # lids open further than a plain stare: bigger-looking eyes
        EXPRESSIONS[expr]["facs_bs_EyelidOpenUpper" + side] = base_wide * 1.6
        EXPRESSIONS[expr]["facs_bs_EyelidOpenLower" + side] = base_wide * 1.2
if EXPRESSIONS.get(expr):
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.daz.import_facs()
    for prop, val in EXPRESSIONS[expr].items():
        try:
            api.set_slider(rig, prop, val)
        except Exception as e:
            print("EXPR could not set", prop, str(e)[:80])
    api.update_drivers(rig)
    print("EXPR", expr)

# --- portrait camera and lighting ------------------------------------------------------------------------
bpy.context.view_layer.update()
e_obj = find("Eyes")
evs = [e_obj.matrix_world @ v.co for v in e_obj.data.vertices]
eye = sum(evs, Vector((0, 0, 0))) / len(evs)
yaw = math.radians(float(args[args.index("--yaw") + 1]) if "--yaw" in args else 18.0)   # three-quarter view
dist, aim_drop = (0.45, 0.0) if "--close" in args else (1.3, 0.12)
off = Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, 0.03))
lighting = opt("--light", "moody")
LP = float(opt("--lightpower", 1.0))
if lighting == "soft":
    # Beauty-portrait lighting: one big soft key close to the lens axis, a real fill, a gentle kicker, and a hair light.
    lib.world_gradient("#3a3f55", "#171a26", strength=0.7)
    key_dir = Vector((-math.sin(yaw + 0.8), -math.cos(yaw + 0.8), 0))
    lib.light("key", "AREA", tuple(eye + key_dir * 1.4 + Vector((0, 0, 0.62))), 440 * LP, "#fff0e2", size=1.6, target=tuple(eye))
    lib.light("fill", "AREA", tuple(eye + Vector((math.sin(yaw) * 1.4 + 0.9, -1.4, -0.1))), 120 * LP, "#d9e2ff", size=2.4,
              target=tuple(eye))
    lib.light("rim", "AREA", tuple(eye + Vector((0.8, 0.9, 0.4))), 90, "#b5c6ff", size=0.6, target=tuple(eye))
    lib.light("rim2", "AREA", tuple(eye + Vector((-0.85, 0.8, 0.35))), 45, "#ffdcc0", size=0.6, target=tuple(eye))
    lib.light("hair", "AREA", tuple(eye + Vector((0.0, 0.6, 1.1))), 14, "#fff0dc", size=0.9, target=tuple(eye))
else:
    lib.world_gradient("#262b3d", "#0b0d14", strength=0.45)
    key_dir = Vector((-math.sin(yaw + 0.75), -math.cos(yaw + 0.75), 0))        # from the camera's left
    lib.light("key", "AREA", tuple(eye + key_dir * 1.3 + Vector((0, 0, 0.55))), 210, "#ffe2c8", size=1.1, target=tuple(eye))
    lib.light("fill", "AREA", tuple(eye + Vector((math.sin(yaw) * 1.4 + 0.6, -1.2, -0.15))), 28, "#c4ceff", size=1.8,
              target=tuple(eye))
    lib.light("rim", "AREA", tuple(eye + Vector((0.75, 0.9, 0.45))), 110, "#a9bcff", size=0.5, target=tuple(eye))
    lib.light("rim2", "AREA", tuple(eye + Vector((-0.8, 0.8, 0.35))), 55, "#ffd9b8", size=0.5, target=tuple(eye))
    lib.light("hair", "AREA", tuple(eye + Vector((0.0, 0.6, 1.1))), 18, "#fff0dc", size=0.9, target=tuple(eye))
sprite = "--sprite" in args
if sprite:
    # Same framing as the game's existing character sprites: orthographic, head and torso, 1050x1400, transparent.
    cz = eye.z - 0.2
    cam = lib.camera((eye.x + math.sin(yaw) * 5.0, eye.y - math.cos(yaw) * 5.0, cz), (eye.x, eye.y, cz), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.0           # head to hips: ends above the leg openings, so no trousers are needed
    w, h, spp = (525, 700, 48) if fast else (1050, 1400, 160)
else:
    cam = lib.camera(tuple(eye + off), (eye.x, eye.y, eye.z - aim_drop), lens=85)
    cam.data.dof.use_dof = "--close" not in args
    cam.data.dof.focus_distance = (cam.location - eye).length
    cam.data.dof.aperture_fstop = 2.8
    w, h, spp = (540, 675, 96) if fast else (1080, 1350, 200)
lib.setup_render(w, h, spp, transparent=sprite, exposure=float(opt("--exposure", -0.85)))
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

if "--facsdiag" in args:
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    try:
        print("FACS import", bpy.ops.daz.import_facs(), api.get_error_message()[:200])
    except Exception as e:
        print("FACS import failed", str(e)[:300])
    for cat in ("Facs", "FacsDetails", "Expressions", "Units", "Standard", "Visemes", "Head"):
        try:
            ms = api.get_morphs(rig, cat)
            print("FACS", cat, len(ms), " ".join(sorted(ms)) if ms else ms)
        except Exception as e:
            print("FACS", cat, "error", str(e)[:120])

if "--hairdiag" in args:
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 270, 338
    sc.cycles.samples = 32
    for o in bpy.data.objects:
        if o.type in ("MESH", "CURVES") and ("hair" in o.name.lower()):
            print("HAIRDIAG obj", o.type, o.name, [sl.material.name for sl in o.material_slots if sl.material])
    hair_o = bpy.data.objects.get("nell_hair")
    cap_o = bpy.data.objects.get("nell_hair_cap")
    for label, hide in (("nohair", [hair_o]), ("nocap", [cap_o]), ("nodenoise", [])):
        for o in hide:
            if o:
                o.hide_render = True
        sc.cycles.use_denoising = label != "nodenoise"
        lib.render(out.replace(".png", "_%s.png" % label))
        for o in hide:
            if o:
                o.hide_render = False
    sc.cycles.use_denoising = True

if "--matdiag" in args:
    for nm in ("nell_hair", "nell_hair_cap"):
        o = bpy.data.objects.get(nm)
        if not o:
            continue
        for sl in o.material_slots:
            m = sl.material
            print("MATDIAG", nm, "slot link", sl.link, "mat", m.name, "use_nodes", getattr(m, "use_nodes", None))
            for n in m.node_tree.nodes:
                vals = {i.name: tuple(round(x, 3) for x in i.default_value) if hasattr(i.default_value, "__len__") else round(i.default_value, 3)
                        for i in n.inputs if hasattr(i, "default_value") and i.name in ("Base Color", "Melanin", "Melanin Redness", "Color", "Roughness")}
                print("MATDIAG   node", n.bl_idname, vals)
            print("MATDIAG   links", [(l.from_node.bl_idname, l.to_node.bl_idname, l.to_socket.name) for l in m.node_tree.links])

if "--captest" in args:
    cap_o = bpy.data.objects.get("nell_hair_cap")
    cap_o.material_slots[0].material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0, 1, 0, 1)
    bpy.data.objects["nell_hair"].hide_render = True
    print("CAPTEST faces", len(cap_o.data.polygons), "hide_render", cap_o.hide_render, "visible", cap_o.visible_get())
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 270, 338
    sc.cycles.samples = 16
    lib.render(out.replace(".png", "_captest.png"))

if "--vgdiag" in args:
    print("VG", sorted(vg.name for vg in body.vertex_groups)[:120])

if "--hairmat" in args:
    m = bpy.data.materials["webb_hair_mat"]
    for n in m.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfHairPrincipled":
            print("HAIRMAT", n.parametrization, n.model, {i.name: (tuple(round(x, 3) for x in i.default_value) if hasattr(i.default_value, "__len__") else round(i.default_value, 3)) for i in n.inputs if hasattr(i, "default_value") and i.enabled})

if "--vgdiag2" in args:
    names = sorted(vg.name for vg in body.vertex_groups)
    print("VG2", len(names), [n for n in names if not n.startswith(("l_", "r_")) or any(k in n for k in ("thigh", "shin", "upperarm", "forearm", "shoulder", "pectoral", "collar"))])


if "--bones" in args:
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
    print("BONES", [b.name for b in rig.pose.bones if any(k in b.name for k in ("upperarm", "forearm", "hand", "shoulder", "collar", "clavicle"))][:40])

if "--inspect" in args:
    print("INSPECT slots", [(i, sl.material.name if sl.material else None) for i, sl in enumerate(body.material_slots)])
    sk = body.data.shape_keys
    if sk:
        print("INSPECT keys", len(sk.key_blocks))
        print("INSPECT shape", " ".join("%s=%.2f" % (k.name, k.value) for k in sk.key_blocks if k.name != "Basis" and not k.name.startswith("facs_")))

if "--morphtest" in args:
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    before = {k.name for k in body.data.shape_keys.key_blocks}
    d = "/store/asset-library/daz/data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9/"
    try:
        r = bpy.ops.daz.import_custom_morphs(filepath=d + "Amala_head_bs_Head.dsf", directory=d,
                                             files=[{"name": "Amala_head_bs_Head.dsf"}], bodypart="Face")
        print("MORPHTEST op", r, api.get_error_message()[:300])
    except Exception as e:
        print("MORPHTEST failed", str(e)[:400])
    after = {k.name for k in body.data.shape_keys.key_blocks}
    print("MORPHTEST new keys", sorted(after - before))
    print("MORPHTEST rig props", [k for k in rig.keys() if "mala" in k][:10])

if "--skindiag" in args:
    m = body.material_slots[5].material
    nt = m.node_tree
    print("SKIN nodes", [(n.bl_idname.replace("ShaderNode", ""), n.name, n.label) for n in nt.nodes][:60])
    for l in nt.links:
        if l.to_node.bl_idname in ("ShaderNodeBsdfPrincipled", "ShaderNodeOutputMaterial") or "Group" in l.to_node.bl_idname:
            print("SKIN link", l.from_node.name, l.from_socket.name, "->", l.to_node.name, l.to_socket.name)
    bsdf = [n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"]
    print("SKIN bsdf count", len(bsdf))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg); me = ev.to_mesh()
    names = {vg.index: vg.name for vg in body.vertex_groups}
    for g in ("l_lipcorner", "r_lipcorner", "lipuppermiddle", "liplowermiddle", "l_nostril", "r_nostril", "l_cheek", "l_eyelidupper", "l_eyelidlower", "l_browinner", "l_browouter", "centerbrow", "chin", "l_infraorbital", "l_squint"):
        pts = [body.matrix_world @ me.vertices[v.index].co for v in body.data.vertices if any(names.get(x.group) == g and x.weight > 0.5 for x in v.groups)]
        if pts:
            c = sum(pts, Vector((0, 0, 0))) / len(pts)
            print("LM %s n=%d x=%.3f y=%.3f z=%.3f" % (g, len(pts), c.x, c.y, c.z))
    ev.to_mesh_clear()
    e_o = find("Eyes"); evs = [e_o.matrix_world @ v.co for v in e_o.data.vertices]
    em = sum(evs, Vector((0, 0, 0))) / len(evs); print("LM eyes mid x=%.3f y=%.3f z=%.3f" % (em.x, em.y, em.z))

if "--rigkeys" in args:
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
    print("RIGKEYS", [k for k in rig.keys() if any(w in k for w in ("Matt", "Masculine", "Feminine", "Character", "Head", "Daz"))][:40])
    print("RIGKEYS body", [k for k in body.keys()][:20])
    print("RIGKEYS sk", [k.name for k in body.data.shape_keys.key_blocks if "Masculine" in k.name or "Matt" in k.name or "Square" in k.name or "Round" in k.name][:20])

if "--rigkeys2" in args:
    print("RK2", " ".join("%s=%.2f" % (k.name, k.value) for k in body.data.shape_keys.key_blocks if k.name != "Basis" and not k.name.startswith(("facs_", "pJCM", "head_bs_Mouth", "pCTRL"))) [:3000])
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.startswith(name))
    print("RK2 ctrl", rig.get("Matt_figure_ctrl_Character"))
