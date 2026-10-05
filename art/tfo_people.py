"""Ten Forty-One characters: MPFB (MakeHuman) people, posed and rendered as transparent sprites.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/tfo_people.py -- --person webb|nell [--pose NAME|all] [--fast]

Generalised from elena_real.py: each person is a config (body, skin, hair, clothes, tints, face) and each pose
is elbow/wrist targets RELATIVE TO THAT BODY'S SHOULDERS (so one pose fits a tall man and a short woman), a
head tilt, and ARKit face-unit weights. Writes art/out/tfo/<person>_<pose>.png at 1050x1400.
Coordinates: x is the viewer's right, y away from the camera, z up; people face -y.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import mpfb_helpers as mh  # noqa: E402

args = lib.script_args()
fast = "--fast" in args
who = args[args.index("--person") + 1] if "--person" in args else "webb"
which = args[args.index("--pose") + 1] if "--pose" in args else "all"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "tfo")
THREADS = int(args[args.index("--threads") + 1]) if "--threads" in args else 12

_both = lambda name, v: {"l-" + name: v, "r-" + name: v}

# Arm shapes, as offsets from the shoulder joint (upperarm01 head) in metres. "L" is the character's own left
# arm (the viewer's right). Derived from Elena's tuned poses.
ARMS = {
    "folded":  {"L": dict(elbow=(0.015, -0.09, -0.275), wrist=(-0.29, -0.175, -0.275)),
                "R": dict(elbow=(-0.015, -0.09, -0.275), wrist=(0.29, -0.215, -0.31))},
    "clasped": {"L": dict(elbow=(0.03, -0.06, -0.29), wrist=(-0.16, -0.2, -0.45)),
                "R": dict(elbow=(-0.03, -0.06, -0.29), wrist=(0.16, -0.21, -0.45))},
    "behind":  {"L": dict(elbow=(0.06, 0.08, -0.27), wrist=(-0.08, 0.17, -0.48)),
                "R": dict(elbow=(-0.06, 0.08, -0.27), wrist=(0.08, 0.17, -0.48))},
}

PEOPLE = {
    # Marcus Webb, 51: lean, silver-grey suit, salt-and-pepper hair. Charming, a performer.
    "webb": dict(
        gender=1.0, age=0.82, weight=0.3, muscle=0.45, height=0.62,
        race={"caucasian": 0.85, "asian": 0.05, "african": 0.1},
        skin="middleage_caucasian_male", hair="short02", hair_tint=("#6e6862", 0.45),
        eyebrows="eyebrow001", eyelashes="eyelashes01",
        clothes=[("toigo_male_suit_3", ("#7c8188", 0.5))],
        details={**_both("eye-height1-incr", 0.1), **_both("cheek-bones-incr", 0.3), "chin-width-decr": 0.1,
                 "nose-width1-decr": 0.2, "head-oval": 0.2},
        turn=12,
        poses={
            "calm": dict(arms="behind", head=(-2, 0, -4), lift=0.0,
                         face=dict(mouthSmileLeft=0.7, mouthSmileRight=0.6, cheekSquintLeft=0.4, cheekSquintRight=0.35,
                                   eyeSquintLeft=0.2, eyeSquintRight=0.2, browOuterUpLeft=0.35, browInnerUp=0.15)),
            "pressed": dict(arms="folded", head=(4, 3, -6), lift=0.0,
                            face=dict(mouthSmileLeft=0.35, mouthPressLeft=0.3, mouthPressRight=0.3, browDownLeft=0.35,
                                      browDownRight=0.2, eyeSquintLeft=0.4, eyeSquintRight=0.3)),
        }),
    # Nell Ashby, 34: freckles, auburn bob, sage sweater. Wry, tired, warm underneath.
    "nell": dict(
        gender=0.0, age=0.57, weight=0.4, muscle=0.35, height=0.5,
        race={"caucasian": 0.9, "asian": 0.05, "african": 0.05},
        skin="toigo_light_skin_female_freckles", hair="toigo_curled_under_bob", hair_tint=("#5e2a17", 0.65),
        eyebrows="eyebrow006", eyelashes="eyelashes02", brow_tint=("#7a4a32", 0.6),
        clothes=[("mindfront_knitted_sweater_01", ("#7f8c6c", 0.35)), ("mindfront_female_trousers_1", ("#2e2b29", 0.5))],
        details={**_both("eye-height1-incr", 0.35), **_both("eye-height2-incr", 0.25), **_both("eye-bag-decr", 0.3),
                 "mouth-lowerlip-height-incr": 0.3, "mouth-cupidsbow-incr": 0.3, **_both("cheek-bones-incr", 0.35),
                 "chin-width-decr": 0.3, "head-oval": 0.35, "nose-width1-decr": 0.25},
        turn=-12,
        poses={
            "calm": dict(arms="folded", head=(2, -4, 4), lift=0.0,
                         face=dict(mouthSmileLeft=0.55, mouthSmileRight=0.4, browOuterUpRight=0.3, browInnerUp=0.35,
                                   eyeSquintLeft=0.1)),
            "warm": dict(arms="clasped", head=(-3, 6, 5), lift=0.0,
                         face=dict(mouthSmileLeft=0.95, mouthSmileRight=0.9, cheekSquintLeft=0.5, cheekSquintRight=0.5,
                                   browInnerUp=0.35, eyeSquintLeft=0.15, eyeSquintRight=0.15)),
            "rattled": dict(arms="clasped", head=(-2, -3, 3), lift=0.025,
                            face=dict(browInnerUp=0.9, browOuterUpLeft=0.3, browOuterUpRight=0.3, eyeWideLeft=0.45,
                                      eyeWideRight=0.45, mouthPressLeft=0.25, mouthPressRight=0.25, mouthFrownLeft=0.15,
                                      mouthFrownRight=0.15)),
        }),
}


def recolour(obj, hex_colour, factor):
    """Blend an asset's colour TOWARD a colour (unlike mh.tint_object, which can only darken by multiplying).
    Keeps some of the texture's detail at factors below 1."""
    for slot in obj.material_slots:
        nt = slot.material.node_tree if slot.material else None
        if not nt:
            continue
        for node in nt.nodes:
            if node.type == "BSDF_PRINCIPLED":
                sock = node.inputs["Base Color"]
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                mix.blend_type = "MIX"
                mix.inputs["Factor"].default_value = factor
                mix.inputs["B"].default_value = lib.rgb(hex_colour)
                if sock.links:
                    nt.links.new(sock.links[0].from_socket, mix.inputs["A"])
                else:
                    mix.inputs["A"].default_value = sock.default_value
                nt.links.new(mix.outputs["Result"], sock)
                break


def aim(rig, bone_name, target):
    """Rotate a pose bone so it points from its own head toward `target` (world space)."""
    pb = rig.pose.bones[bone_name]
    bpy.context.view_layer.update()
    m = rig.matrix_world @ pb.matrix
    head = m.translation.copy()
    d0 = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
    d1 = (Vector(target) - head).normalized()
    q = d0.rotation_difference(d1)
    new = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ m
    pb.matrix = rig.matrix_world.inverted() @ new
    bpy.context.view_layer.update()


def create(svc, p):
    human, target, *_ = svc
    macros = target.get_default_macro_info_dict()
    macros.update(gender=p["gender"], age=p["age"], muscle=p["muscle"], weight=p["weight"], proportions=0.5,
                  height=p["height"])
    macros["race"] = p["race"]
    return human.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True,
                              feet_on_ground=True, scale=0.1, macro_detail_dict=macros)


def build(p, pose):
    lib.reset()
    svc = mh.enable()
    human_svc, target_svc, face_svc, _ = svc
    base = create(svc, p)
    target_svc.bulk_load_targets(base, [{"target": t, "value": v} for t, v in p["details"].items()])
    mh.set_skin(svc, base, p["skin"])
    rig = human_svc.add_builtin_rig(base, "default")
    mh.add(svc, base, "eyes/high-poly/high-poly", "Eyes")
    mh.add(svc, base, "eyebrows/%s/%s" % (p["eyebrows"], p["eyebrows"]), "Eyebrows")
    mh.add(svc, base, "eyelashes/%s/%s" % (p["eyelashes"], p["eyelashes"]), "Eyelashes")
    mh.add(svc, base, "teeth/teeth_base/teeth_base", "Teeth")
    mh.add(svc, base, "hair/%s/%s" % (p["hair"], p["hair"]), "Hair")
    for name, _tint in p["clothes"]:
        mh.add(svc, base, "clothes/%s/%s" % (name, name), "Clothes")
    for o in mh.assets(base):
        if o.name == base.name + "." + p["hair"]:
            recolour(o, *p["hair_tint"])
        for name, tint in p["clothes"]:
            if name in o.name and tint:
                recolour(o, *tint)
        if p.get("brow_tint") and o.name == base.name + "." + p["eyebrows"]:
            recolour(o, *p["brow_tint"])

    face_svc.load_targets(base, load_microsoft_visemes=False, load_arkit_faceunits=True)
    face_svc.interpolate_targets(base)
    face_svc.clear_expression(base)
    face_svc.set_expression(base, pose["face"])

    bpy.context.view_layer.update()
    shoulders = {s: (rig.matrix_world @ rig.pose.bones["upperarm01." + s].head).copy() for s in ("L", "R")}
    for side, joints in ARMS[pose["arms"]].items():
        sh = shoulders[side]
        aim(rig, "upperarm01." + side, sh + Vector(joints["elbow"]))
        aim(rig, "lowerarm01." + side, sh + Vector(joints["wrist"]))
    if pose["lift"]:
        for side in ("L", "R"):
            pb = rig.pose.bones["clavicle." + side]
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (0, 0, math.radians(18 * pose["lift"] / 0.025) * (1 if side == "L" else -1))
    head = rig.pose.bones["head"]
    head.rotation_mode = "XYZ"
    pitch, roll, yaw = pose["head"]
    head.rotation_euler = (math.radians(pitch), math.radians(yaw), math.radians(roll))
    bpy.context.view_layer.update()
    rig.rotation_euler = (0, 0, math.radians(p["turn"]))
    bpy.context.view_layer.update()
    return (shoulders["L"].z + shoulders["R"].z) / 2


def light_and_render(name, shoulder_z):
    lib.world_gradient("#222a42", "#141a2c", strength=0.55)
    lib.light("key", "AREA", (-1.6, -2.0, shoulder_z + 0.55), 260, "#ffd9b0", size=2.2, target=(0, 0, shoulder_z + 0.05))
    lib.light("rim", "AREA", (1.6, 1.3, shoulder_z + 0.75), 330, "#7f9cff", size=0.9, target=(0, 0, shoulder_z + 0.15))
    lib.light("fill", "AREA", (1.4, -2.0, shoulder_z), 55, "#a9b8ff", size=2.0, target=(0, 0, shoulder_z - 0.05))
    lib.light("top", "AREA", (0, -1.2, shoulder_z + 1.6), 45, "#ffffff", size=2.0, target=(0, 0, shoulder_z - 0.05))
    cz = shoulder_z - 0.10                # same framing as Elena: head and torso
    cam = lib.camera((0, -5.0, cz), (0, 0, cz), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.16
    w, h, samples = (525, 700, 40) if fast else (1050, 1400, 128)
    lib.setup_render(w, h, samples, transparent=True, exposure=0.15)
    sc = bpy.context.scene
    sc.render.threads_mode = "FIXED"
    sc.render.threads = THREADS
    os.makedirs(OUT, exist_ok=True)
    lib.render(os.path.join(OUT, "%s_%s%s.png" % (who, name, "_fast" if fast else "")))


p = PEOPLE[who]
for pose_name in (p["poses"] if which == "all" else [which]):
    sz = build(p, p["poses"][pose_name])
    light_and_render(pose_name, sz)
