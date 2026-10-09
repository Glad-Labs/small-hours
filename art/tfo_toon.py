"""Build a Genesis 9 Toon (anime-style) character in Blender from the Daz content pack and render a sprite or portrait.

    blender -b --factory-startup --python tfo_toon.py -- <feminine|masculine> <out.png> [--fast] [--sprite] [options]

Reuses the Diffeomorphic DAZ Importer set-up from tfo_daz.py. Options are read with opt(); see below.
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import lib  # noqa: E402

sys.stdout.reconfigure(line_buffering=True)
args = lib.script_args()
kind, out = args[0], args[1]
fast = "--fast" in args


def opt(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default


LIB = "/store/asset-library/daz"
T = LIB + "/People/Genesis 9 Toon"
ANAT = T + "/Anatomy/Daz Originals/Toon Anatomy"
MAT = T + "/Materials/Daz Originals/Anime Materials"
HAIR = T + "/Hair/Daz Originals/Base Anime Hair"
CLOTH = T + "/Clothing/Daz Originals/Base Clothing"
BASE = T + "/Genesis 9 Base Anime %s.duf" % kind.capitalize()

lib.reset()
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.import_daz")
from bl_ext.user_default.import_daz import api  # noqa: E402
api.set_silent_mode(True)
api.set_global_setting("contentDirs", [LIB])
api.set_global_setting("onlyDbz", False)
api.set_global_setting("viewportColors", "ORIGINAL")


# The importer's toon step needs a collection to put its light in; there is none when merging rigs headless.
from bl_ext.user_default.import_daz import toon as _toon  # noqa: E402
from bl_ext.user_default.import_daz.utils import LS  # noqa: E402
_orig_add = _toon.addToons


def _add_toons(context):
    if LS.collection is None:
        LS.collection = bpy.context.scene.collection
    return _orig_add(context)


_toon.addToons = _add_toons
import bl_ext.user_default.import_daz.main as _main  # noqa: E402
if hasattr(_main, "addToons"):
    _main.addToons = _add_toons


def load(files):
    api.set_selection(files)
    t0 = time.time()
    res = bpy.ops.daz.easy_import_daz(fitMeshes="MORPHED", useEliminateEmpties=True, useMergeRigs=True, useUpdateErcBones=True)
    print("STEP import %s %s %.1fs %s" % ([os.path.basename(f) for f in files], res, time.time() - t0, api.get_error_message()[:300]))


parts = ["Floating Iris", "Eye Socket", "Eyelashes", "Brows Paint", "Mouth"]
extras = [HAIR + "/Genesis 9 Toon Base Anime Hair.duf"] if "--hair" in args else []
load([BASE] + [ANAT + "/Genesis 9 Toon %s.duf" % p for p in parts] + extras)
for o in list(bpy.data.objects):
    if o.name.endswith(".001"):
        bpy.data.objects.remove(o, do_unlink=True)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_set(False)
print("OBJECTS", [(o.name, len(o.data.vertices), [s.material.name if s.material else None for s in o.material_slots][:6]) for o in meshes])
body = next(o for o in meshes if "Anime" in o.name and "Hair" not in o.name and "Mesh" in o.name or o.name.startswith("Genesis 9 Base Anime"))
bpy.context.view_layer.update()
pts = [body.matrix_world @ v.co for v in body.data.vertices]
top = max(p.z for p in pts)
print("BODY", body.name, "top %.3f" % top)


def apply_preset(path, target=None):
    """Apply a Daz material preset (.duf) to the object it names, or to `target` when given."""
    if target is not None:
        for o in bpy.context.view_layer.objects:
            o.select_set(o == target)
        bpy.context.view_layer.objects.active = target
    api.set_selection([path])
    res = bpy.ops.daz.import_daz_manually()  if False else bpy.ops.daz.easy_import_daz(fitMeshes="MORPHED")
    print("PRESET", os.path.basename(path), res, api.get_error_message()[:120])


def find(word):
    return next((o for o in bpy.data.objects if o.type == "MESH" and word in o.name), None)


# --- the light: the toon shader makes everything below a small light level a flat shadow, so its direction
# is the art direction. Aim it from the front, up and to the camera's left (classic anime key).
toon_light = next((o for o in bpy.data.objects if o.type == "LIGHT" and "Toon Light" in o.name), None)
az, el = math.radians(float(opt("--lightaz", -25))), math.radians(float(opt("--lightel", 30)))
if toon_light:
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))   # toward the light
    toon_light.rotation_mode = "QUATERNION"
    toon_light.rotation_quaternion = (-d).to_track_quat("-Z", "Y")
    toon_light.data.energy = 3.0
    toon_light.data.angle = 0.0                    # a point-like sun: crisp shadow edges, no grain
for o in bpy.data.objects:                         # hair, lashes and brows do not shade the face
    if o.type == "MESH":                       # anime faces are shaded by surface direction only, no cast shadows
        o.visible_shadow = False
print("LIGHT toon sun from", tuple(round(x, 2) for x in d)) if toon_light else None


# --- ink outlines: an inverted hull (a slightly larger copy facing inward, back faces culled) drawn in dark ink.
def outline(ob, width, colour=(0.06, 0.035, 0.03)):
    # The importer subdivides the body 4 times for rendering; under an outline shell that subdivision runs on the
    # CPU (millions of faces, tens of GB). Flat toon shading needs one level at most.
    for md in ob.modifiers:
        if md.type == "SUBSURF":
            md.render_levels = min(md.render_levels, 1)
    m = bpy.data.materials.new(ob.name + "_ink")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*colour, 1)
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    m.use_backface_culling = True
    ob.data.materials.append(m)
    sol = ob.modifiers.new("ink", "SOLIDIFY")
    sol.thickness = width
    sol.offset = 1.0
    sol.use_flip_normals = True
    sol.use_rim = False
    sol.material_offset = len(ob.material_slots) - 1
    sol.material_offset_rim = len(ob.material_slots) - 1
    # the original surfaces must also cull back faces, or the hull's inside shows through thin parts
    for sl in ob.material_slots[:-1]:
        if sl.material:
            sl.material.use_backface_culling = True



# --- hair styling morphs (the anime hair's own sliders), e.g. --hairstyle "Longer Style 01=1,Bangs Side=0.5".
# Read straight from the .dsf files (vertex offsets in cm, Y up) and added as shape keys: the importer's own
# morph loader is slow, memory-hungry, and drives the keys from rig properties we would then have to chase.
if "--earlyink" in args:
    outline(body, float(opt("--ink")))
    _h = find("Hair Mesh")
    if _h:
        outline(_h, float(opt("--ink")) * 0.8)
HAIR_MORPHS = LIB + "/data/Daz 3D/Genesis 9 Starter Essentials/Genesis 9 Toon Hair/Morphs/Daz 3D/Base/"


def dsf_morph(ob, path, value):
    import gzip
    import json
    raw = open(path, "rb").read()
    try:
        raw = gzip.decompress(raw)
    except OSError:
        pass
    mod = next(m for m in json.loads(raw)["modifier_library"] if "morph" in m)
    deltas = mod["morph"]["deltas"]["values"]
    if not ob.data.shape_keys:
        ob.shape_key_add(name="Basis", from_mix=False)
    key = ob.shape_key_add(name=os.path.basename(path)[:-4], from_mix=False)
    inv = ob.matrix_world.inverted().to_3x3()
    n = len(ob.data.vertices)
    for idx, dx, dy, dz in deltas:
        if idx < n:
            key.data[idx].co += inv @ (Vector((dx, -dz, dy)) * 0.01)     # Daz cm, Y up -> Blender metres, Z up
    key.slider_min, key.slider_max = -2.0, 2.0
    key.value = value
    return key


hair_ob = find("Hair Mesh")
if hair_ob and opt("--hairstyle"):
    for item in opt("--hairstyle").split(","):
        k, val = item.rsplit("=", 1)
        dsf_morph(hair_ob, HAIR_MORPHS + k + ".dsf", float(val))
        print("HAIRSTYLE", k, val)

# --- cel shadow: where the toon shader switches from lit to shadow, as a fraction of full sun light
threshold = float(opt("--cel", 0.25))
for ng in bpy.data.node_groups:
    for n in ng.nodes:
        if n.label == "HDRI Threshold":
            n.outputs["Value"].default_value = threshold * (toon_light.data.energy if toon_light else 1.0)

def apply_preset(path, target):
    for o in bpy.context.view_layer.objects:
        o.select_set(o == target)
    bpy.context.view_layer.objects.active = target
    api.set_selection([path])
    res = bpy.ops.daz.import_daz_materials()
    print("PRESET", os.path.basename(path), "->", target.name, res, api.get_error_message()[:120])


def toon_material(name, colour, shadow=(0.80, 0.77, 0.88), pattern=None, axis=None, round_=0.75):
    """Flat cel material built from the importer's own toon groups, so clothes shade exactly like the skin.
    pattern: (scale, strength) for faint vertical knit ribs drawn into the colour."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    dif = nt.nodes.new("ShaderNodeGroup")
    dif.node_tree = bpy.data.node_groups["DAZ Toon Diffuse"]
    lit = nt.nodes.new("ShaderNodeGroup")
    lit.node_tree = bpy.data.node_groups["DAZ Toon Light"]
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = lib.rgb(colour)
    col = rgb.outputs[0]
    if pattern:
        coord = nt.nodes.new("ShaderNodeTexCoord")
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = pattern[0]
        nt.links.new(coord.outputs["Object"], wave.inputs["Vector"])
        step = nt.nodes.new("ShaderNodeMapRange")
        step.inputs[1].default_value, step.inputs[2].default_value = 0.55, 0.62
        nt.links.new(wave.outputs["Fac"], step.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        nt.links.new(step.outputs["Result"], mix.inputs["Factor"])
        mix.inputs["Factor"].default_value = 0.0
        nt.links.new(col, mix.inputs["A"])
        mix.inputs["B"].default_value = (1 - pattern[1], 1 - pattern[1], 1 - pattern[1], 1)
        col = mix.outputs["Result"]
    nt.links.new(col, dif.inputs["Color"])
    dif.inputs["Ambience"].default_value = (*shadow, 1.0)
    if axis is not None:
        # Shade cloth as a smooth cylinder round the body's vertical axis (mixed with a little of the real normal):
        # one clean light/shadow edge down the side, instead of shadows that trace the muscles underneath.
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        rel = nt.nodes.new("ShaderNodeVectorMath"); rel.operation = "SUBTRACT"
        nt.links.new(geo.outputs["Position"], rel.inputs[0]); rel.inputs[1].default_value = axis
        flat = nt.nodes.new("ShaderNodeVectorMath"); flat.operation = "MULTIPLY"
        nt.links.new(rel.outputs[0], flat.inputs[0]); flat.inputs[1].default_value = (1.0, 1.0, 0.0)
        cyl = nt.nodes.new("ShaderNodeVectorMath"); cyl.operation = "NORMALIZE"
        nt.links.new(flat.outputs[0], cyl.inputs[0])
        mixn = nt.nodes.new("ShaderNodeMix"); mixn.data_type = "VECTOR"
        mixn.inputs["Factor"].default_value = 1.0 - round_
        nt.links.new(cyl.outputs[0], mixn.inputs["A"]); nt.links.new(geo.outputs["Normal"], mixn.inputs["B"])
        nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
        nt.links.new(mixn.outputs["Result"], nrm.inputs[0])
        nt.links.new(nrm.outputs[0], dif.inputs["Normal"])
        inner = [n for n in dif.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfDiffuse"]
        print("TOONMAT", name, "normal linked; inner diffuse normal links:",
              [l.from_node.bl_idname for n in inner for l in dif.node_tree.links if l.to_node == n and l.to_socket.name == "Normal"])
    nt.links.new(dif.outputs["Output"], lit.inputs["Input"])
    nt.links.new(lit.outputs["Output"], o.inputs["Surface"])
    return m


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
        for axis in range(3):
            for sign in (1, -1):
                e = [0.0, 0.0, 0.0]
                e[axis] = sign * math.radians(30)
                ub.rotation_euler = e
                drop = base.z - reach().z
                if best is None or drop > best[0]:
                    best = (drop, axis, sign)
        _, axis, sign = best
        for deg in range(0, 91, 3):
            e = [0.0, 0.0, 0.0]
            e[axis] = sign * math.radians(deg)
            ub.rotation_euler = e
            v = reach()
            if math.degrees(math.acos(max(-1.0, min(1.0, -v.z / v.length)))) <= hang_deg:
                break


rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if opt("--mat"):
    apply_preset(MAT + "/G9 Anime All MAT %s.duf" % opt("--mat"), body)
for o in bpy.data.objects:                        # the hair asset brings earrings along; hide them
    if o.type == "MESH" and "arring" in o.name:
        o.hide_render = True
if "--arms" in args:
    lower_arms(rig, float(opt("--arms")))

# hair colour preset (one of the pack's 25), eye colour by hue shift of the iris
if hair_ob and opt("--haircolor"):
    apply_preset(HAIR + "/Materials/G9 Anime Hair %s.duf" % opt("--haircolor"), hair_ob)
if hair_ob and (opt("--hairval") or opt("--hairsat") or opt("--hairhue")):
    for sl in hair_ob.material_slots:
        nt = sl.material.node_tree if sl.material else None
        if not nt:
            continue
        for l in list(nt.links):
            if l.to_node.bl_idname == "ShaderNodeGroup" and l.to_socket.name == "Color" and "Diffuse" in l.to_node.node_tree.name:
                hsv = nt.nodes.new("ShaderNodeHueSaturation")
                hsv.inputs["Hue"].default_value = float(opt("--hairhue", 0.5))
                hsv.inputs["Value"].default_value = float(opt("--hairval", 1.0))
                hsv.inputs["Saturation"].default_value = float(opt("--hairsat", 1.0))
                nt.links.new(l.from_socket, hsv.inputs["Color"])
                nt.links.new(hsv.outputs["Color"], l.to_socket)
                print("HAIRTINT", sl.material.name)
                break
        else:
            print("HAIRTINT no diffuse link in", sl.material.name, [(l.from_node.name, l.to_node.name, l.to_socket.name) for l in nt.links][:12])
iris = find("Iris")
if iris and opt("--irishue"):
    for sl in iris.material_slots:
        m = sl.material
        if not m or "Highlight" in m.name:
            continue
        nt = m.node_tree
        for l in list(nt.links):
            if l.to_node.bl_idname == "ShaderNodeGroup" and l.to_socket.name == "Color" and "Diffuse" in l.to_node.node_tree.name:
                hsv = nt.nodes.new("ShaderNodeHueSaturation")
                hsv.inputs["Hue"].default_value = float(opt("--irishue"))
                hsv.inputs["Saturation"].default_value = float(opt("--irissat", 1.0))
                hsv.inputs["Value"].default_value = float(opt("--irisval", 1.0))
                nt.links.new(l.from_socket, hsv.inputs["Color"])
                nt.links.new(hsv.outputs["Color"], l.to_socket)
                print("IRIS hue", opt("--irishue"), "on", m.name)
                break

# clothes: our garment builder, in toon materials
bpy.context.view_layer.update()
e_o = find("Iris")
eye_z = sum((e_o.matrix_world @ v.co).z for v in e_o.data.vertices) / len(e_o.data.vertices)
cloth = []
AXIS = None if "--noaxis" in args else (sum((rig.matrix_world @ b.head).x for b in rig.pose.bones if b.name.startswith("spine")) / 4.0,
        sum((rig.matrix_world @ b.head).y for b in rig.pose.bones if b.name.startswith("spine")) / 4.0, 0.0)
if "--sweater" in args:
    import garments
    sw = garments.sweater(body, colour="#5f6f55", neck_z=eye_z - 0.115, hem_z=eye_z - 0.745)
    sw.data.materials.clear()
    sw.data.materials.append(toon_material("sweater_toon", opt("--sweater"), pattern=(70.0, 0.08), axis=AXIS))
    cloth.append(sw)
if "--waistcoat" in args:
    import garments
    sh = garments.shirt(body, neck_z=eye_z - 0.13, hem_z=eye_z - 0.745)
    sh.data.materials.clear()
    sh.data.materials.append(toon_material("shirt_toon", "#e9e4d8", axis=AXIS))
    cloth.append(sh)
    if opt("--tie"):
        bpy.context.view_layer.update()
        co, to, kn = garments.collar_and_tie(body, sh, eye_z - 0.13, tie_colour=opt("--tie"), tie_bottom_z=eye_z - 0.375)
        co.data.materials.clear(); co.data.materials.append(toon_material("collar_toon", "#f1ede4"))
        for t in (to, kn):
            t.data.materials.clear(); t.data.materials.append(toon_material("tie_toon", opt("--tie")))
        cloth += [co, to, kn]
    wc = garments.waistcoat(body, colour="#2d3238", v_bottom_z=eye_z - 0.34, hem_z=eye_z - 0.745)
    wc.data.materials.clear()
    wc.data.materials.append(toon_material("waistcoat_toon", opt("--waistcoat"), axis=AXIS))
    cloth.append(wc)
    for o in bpy.data.objects:
        if o.name.startswith("button"):
            o.data.materials.clear(); o.data.materials.append(toon_material("button_toon", "#1e1c1a"))
# The importer links its toon sun to a collection of toon objects only; our clothes must join it to be lit.
recv = toon_light.light_linking.receiver_collection if toon_light and hasattr(toon_light, "light_linking") else None
for o in cloth:
    if recv is not None and o.name not in recv.objects:
        recv.objects.link(o)
# Freeze the clothes' fit to the skin before the body gets its ink shell (the shell would confuse the fit).
for o in cloth:
    o.visible_shadow = False
    if o.type == "MESH" and o.modifiers.get("outside_skin"):
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
            bpy.ops.object.modifier_apply(modifier="outside_skin")
if "--ink" in args and "--earlyink" not in args:
    w_ink = float(opt("--ink"))
    outline(body, w_ink)
    if hair_ob:
        outline(hair_ob, w_ink * 0.8)
    for o in cloth:
        if o.type == "MESH":
            outline(o, w_ink * 0.9)

# --- expression: the pack's FACS controls (same names as the realistic figures)
EXPRESSIONS = {
    "calm": {"facs_ctrl_MouthSmile": 0.3, "facs_ctrl_CheekSquint": 0.1, "facs_ctrl_BrowInnerUp": 0.2},
    "warm": {"facs_ctrl_MouthSmile": 0.8, "facs_ctrl_MouthSmileWiden": 0.3, "facs_ctrl_CheekSquint": 0.35,
             "facs_ctrl_EyesSquint": 0.2, "facs_ctrl_BrowInnerUp": 0.25},
    "rattled": {"facs_ctrl_BrowInnerUp": 1.0, "facs_ctrl_EyeWide": 0.6, "facs_ctrl_MouthPress": 0.3,
                "facs_ctrl_MouthFrown": 0.45},
    "charm": {"facs_ctrl_MouthSmile": 0.7, "facs_ctrl_CheekSquint": 0.35, "facs_ctrl_EyesSquint": 0.2,
              "facs_BrowOuterUpLeft": 0.55},
    "pressed": {"facs_ctrl_MouthPress": 0.6, "facs_ctrl_EyesSquint": 0.45, "facs_BrowDownLeft": 0.6,
                "facs_BrowDownRight": 0.5},
}
expr = opt("--expr")
if expr:
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.context.view_layer.objects.active = rig
    try:
        print("FACS import", bpy.ops.daz.import_facs(), api.get_error_message()[:160])
    except Exception as e:
        print("FACS import failed", str(e)[:300])
    for prop, val in EXPRESSIONS[expr].items():
        try:
            api.set_slider(rig, prop, val)
        except Exception as e:
            print("EXPR could not set", prop, str(e)[:80])
    api.update_drivers(rig)
    print("EXPR", expr)
print("EARRINGS?", [o.name for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and "Hair" not in o.name and "Anime" not in o.name and "Toon" not in o.name and o not in cloth])

# --- camera
bpy.context.view_layer.update()
evs = [e_o.matrix_world @ v.co for v in e_o.data.vertices]
eye = sum(evs, Vector((0, 0, 0))) / len(evs)
yaw = math.radians(float(opt("--yaw", 0)))
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
lib.world_gradient("#3a3f55", "#171a26", strength=float(opt("--world", 0.0)))
sprite = "--sprite" in args
if sprite:
    cz = eye.z - 0.2
    cam = lib.camera((eye.x + math.sin(yaw) * 5.0, eye.y - math.cos(yaw) * 5.0, cz), (eye.x, eye.y, cz), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.0
    w, h = (525, 700) if fast else (1050, 1400)
else:
    dist = 0.9 if "--close" in args else 1.6
    cam = lib.camera((eye.x + math.sin(yaw) * dist, eye.y - math.cos(yaw) * dist, eye.z - 0.03), (eye.x, eye.y, eye.z - 0.05), lens=85)
    w, h = (540, 675) if fast else (1080, 1350)
sc.render.resolution_x, sc.render.resolution_y = w, h
sc.render.resolution_percentage = 100
sc.render.film_transparent = sprite
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA" if sprite else "RGB"
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = float(opt("--exposure", -0.15))
sc.eevee.taa_render_samples = 32 if fast else 64
for l in bpy.data.lights:
    if hasattr(l, "use_soft_shadows"):
        l.use_soft_shadows = False
print("RENDER start", time.strftime("%H:%M:%S"))
for o in bpy.data.objects:
    if o.type == "MESH" and not o.hide_render:
        print("MODS", o.name, len(o.data.vertices), [(m.type, getattr(m, "render_levels", None), getattr(m, "levels", None), getattr(m, "thickness", None)) for m in o.modifiers])
if "--dryrun" in args:
    sys.exit(0)
lib.render(out)
