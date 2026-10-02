"""Elena Voss, realistic version: an MPFB (MakeHuman) character posed and rendered as transparent sprites.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/elena_real.py -- [--fast] [--pose guarded|tense|broken|all] [--out-dir DIR]

Needs MPFB installed in Blender and its asset packs in the shared library (see art/mpfb_helpers.py).
Poses are targets for the elbows and wrists (the arm bones are aimed at them); expressions are ARKit-style
face-unit weights; the whole thing is a dictionary per pose, so adding an expression is adding an entry.
Coordinates: x is the viewer's right, y points away from the camera, z is up; she faces -y.
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
which = args[args.index("--pose") + 1] if "--pose" in args else "all"
HAIR = args[args.index("--hair") + 1] if "--hair" in args else "ponytail01"      # ponytail01, long01, bob02, ...
out_dir = args[args.index("--out-dir") + 1] if "--out-dir" in args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# Each pose: where the elbows and wrists go (character's own left arm = viewer's right, bones ".L"),
# how the head tilts (pitch, roll, yaw in degrees), and the face as ARKit face-unit weights 0..1.
POSES = {
    # Arms folded across her chest, chin slightly down, one brow raised: she will not volunteer anything.
    "guarded": dict(
        arms={"L": dict(elbow=(0.185, -0.09, 1.075), wrist=(-0.12, -0.175, 1.075)),
              "R": dict(elbow=(-0.185, -0.09, 1.075), wrist=(0.12, -0.215, 1.04))},
        head=(4, 2, -5), lift=0.0,
        face=dict(browOuterUpRight=0.55, browDownLeft=0.3, eyeSquintLeft=0.2, eyeSquintRight=0.15,
                  mouthPressLeft=0.45, mouthPressRight=0.45, mouthFrownLeft=0.12, mouthFrownRight=0.12)),
    # Hands clasped, shoulders up, wide eyes and worried brows: the badge log has just been put in front of her.
    "tense": dict(
        arms={"L": dict(elbow=(0.175, -0.055, 1.115), wrist=(0.015, -0.205, 1.105)),
              "R": dict(elbow=(-0.175, -0.055, 1.115), wrist=(-0.015, -0.22, 1.10))},
        head=(-2, -3, 4), lift=0.025,
        face=dict(browInnerUp=0.8, browOuterUpLeft=0.2, browOuterUpRight=0.2, eyeWideLeft=0.55, eyeWideRight=0.55,
                  mouthPressLeft=0.3, mouthPressRight=0.3, mouthFrownLeft=0.25, mouthFrownRight=0.25, jawOpen=0.04)),
    # Head bowed, eyes shut, one hand at her mouth, shoulders slumped: she has been caught.
    "broken": dict(
        arms={"L": dict(elbow=(0.20, -0.075, 1.07), wrist=(0.075, -0.16, 1.01)),
              "R": dict(elbow=(-0.215, -0.14, 1.17), wrist=(-0.055, -0.17, 1.40))},
        head=(22, -6, 8), lift=-0.02,
        face=dict(browInnerUp=0.95, browDownLeft=0.2, browDownRight=0.2, eyeBlinkLeft=1.0, eyeBlinkRight=1.0,
                  mouthFrownLeft=0.85, mouthFrownRight=0.85, mouthPressLeft=0.2, mouthPressRight=0.2, mouthLowerDownLeft=0.2,
                  mouthLowerDownRight=0.2, cheekSquintLeft=0.4, cheekSquintRight=0.4)),
}


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


# Face adjustments that make the stock MakeHuman face softer and more feminine: larger, lifted eyes, fuller lips,
# higher cheekbones and a slimmer chin (values 0..1; "l-"/"r-" prefixes are the two sides).
_both = lambda name, v: {"l-" + name: v, "r-" + name: v}
FACE_DETAILS = {**_both("eye-height1-incr", 0.35), **_both("eye-height2-incr", 0.25), **_both("eye-bag-decr", 0.3),
                **_both("eye-eyefold-angle-up", 0.2), "mouth-lowerlip-height-incr": 0.35, "mouth-upperlip-height-incr": 0.25,
                "mouth-cupidsbow-incr": 0.3, "mouth-angles-up": 0.15, **_both("cheek-bones-incr", 0.4),
                "chin-width-decr": 0.3, "chin-height-decr": 0.15, "head-oval": 0.35, "nose-width1-decr": 0.25}


def build(pose):
    lib.reset()
    svc = mh.enable()
    human_svc, _target_svc, face_svc, _rig_svc = svc
    base = mh.create_woman(svc, age=0.58)
    svc[1].bulk_load_targets(base, [{"target": t, "value": v} for t, v in FACE_DETAILS.items()])   # before the assets, so they fit the new face
    mh.set_skin(svc, base, "toigo_light_skin_female_bronze_with_makeup")
    rig = human_svc.add_builtin_rig(base, "default")           # the rig first, so every asset fitted next is rigged
    mh.add(svc, base, "eyes/high-poly/high-poly", "Eyes")
    mh.add(svc, base, "eyebrows/eyebrow004/eyebrow004", "Eyebrows")
    mh.add(svc, base, "eyelashes/eyelashes02/eyelashes02", "Eyelashes")
    mh.add(svc, base, "teeth/teeth_base/teeth_base", "Teeth")
    mh.add(svc, base, "hair/%s/%s" % (HAIR, HAIR), "Hair")
    mh.add(svc, base, "clothes/female_elegantsuit01/female_elegantsuit01", "Clothes")
    mh.add(svc, base, "clothes/spamrakuen_sagerfrogs_glasses_01/spamrakuen_sagerfrogs_glasses_01", "Clothes")
    for o in mh.assets(base):
        if o.name == base.name + "." + HAIR:
            mh.tint_object(o, "#2a1810")           # blonde-to-dark-brown hair
        elif "glasses" in o.name:
            mh.tint_object(o, "#2b1f14")           # dark tortoise frames instead of the red ones
        elif "elegantsuit" in o.name:
            mh.tint_object(o, "#b9a78a")           # mute the loud red stripes toward the game's olive/brown palette

    # Facial expression: load the ARKit face units, copy them onto the fitted assets, then set the weights.
    face_svc.load_targets(base, load_microsoft_visemes=False, load_arkit_faceunits=True)
    face_svc.interpolate_targets(base)
    face_svc.clear_expression(base)
    face_svc.set_expression(base, pose["face"])

    # Body: aim the arm bones at the pose targets, then tilt the head.
    for side, joints in pose["arms"].items():
        aim(rig, "upperarm01." + side, joints["elbow"])
        aim(rig, "lowerarm01." + side, joints["wrist"])
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
    rig.rotation_euler = (0, 0, math.radians(-10))               # turn her a little toward the detective
    return base, rig


def light_and_render(name):
    lib.world_gradient("#222a42", "#141a2c", strength=0.55)
    lib.light("key", "AREA", (-1.6, -2.0, 1.9), 260, "#ffd9b0", size=2.2, target=(0, 0, 1.4))      # large, warm, soft
    lib.light("rim", "AREA", (1.6, 1.3, 2.1), 330, "#7f9cff", size=0.9, target=(0, 0, 1.5))
    lib.light("fill", "AREA", (1.4, -2.0, 1.3), 55, "#a9b8ff", size=2.0, target=(0, 0, 1.3))
    lib.light("top", "AREA", (0, -1.2, 3.0), 45, "#ffffff", size=2.0, target=(0, 0, 1.3))
    cam = lib.camera((0, -5.0, 1.25), (0, 0, 1.25), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.16          # tight on head and torso so her expression reads at sprite size
    w, h, samples = (525, 700, 40) if fast else (1050, 1400, 128)
    lib.setup_render(w, h, samples, transparent=True, exposure=0.15)
    os.makedirs(out_dir, exist_ok=True)
    lib.render(os.path.join(out_dir, "elena_%s%s.png" % (name, "_fast" if fast else "")))


for pose_name in (POSES if which == "all" else [which]):
    build(POSES[pose_name])
    light_and_render(pose_name)
