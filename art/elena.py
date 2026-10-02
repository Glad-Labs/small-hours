"""Elena Voss, the night archivist: a stylised 3D character rendered as transparent sprites.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python art/elena.py -- [--fast] [--pose guarded|tense|broken|all]

She is built from smooth primitives and posed by joint positions; her expression is a handful of numbers
(brow angles, eyelid openness, mouth curve), so each pose below is a small dictionary.
Coordinates: x is the viewer's right, y points away from the camera, z is up; she faces -y.
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import cone, group, limb, sphere, tube  # noqa: E402
from lib import material as M  # noqa: E402

args = lib.script_args()
fast = "--fast" in args
which = args[args.index("--pose") + 1] if "--pose" in args else "all"
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
if "--out-dir" in args:
    out_dir = args[args.index("--out-dir") + 1]

ARM_X = 0.88                     # pulls the arms in toward the body
HEAD_SCALE = 1.2                 # a slightly large head reads better at sprite size
HEAD = (0.0, 0.0, 1.62)          # centre of the head
NECK = (0.0, 0.0, 1.50)          # the head pivots here
HIPS = (0.0, 0.0, 1.05)          # the upper body leans from here

# Each pose: joint positions for both arms, body lean, head tilt (pitch, roll, yaw in degrees) and the face.
POSES = {
    # Arms folded, chin slightly down, one brow raised: she is not going to volunteer anything.
    "guarded": dict(
        lean=2, head=(-4, 3, 6), lift=0.0,
        arms=dict(
            left=dict(shoulder=(-0.2, 0, 1.40), elbow=(-0.255, -0.07, 1.16), wrist=(0.10, -0.165, 1.215)),
            right=dict(shoulder=(0.2, 0, 1.40), elbow=(0.255, -0.07, 1.16), wrist=(-0.11, -0.205, 1.17))),
        brow=dict(inner=-0.004, outer=0.003, raise_right=0.010),
        eyes=0.72, mouth=dict(width=0.05, curve=-0.003, open=0.0), tear=False),
    # Shoulders up, hands clasped, wide eyes, worried brows: the badge log has just been put in front of her.
    "tense": dict(
        lean=-1, head=(2, -4, -4), lift=0.022,
        arms=dict(
            left=dict(shoulder=(-0.2, 0, 1.42), elbow=(-0.25, -0.03, 1.16), wrist=(-0.035, -0.17, 1.06)),
            right=dict(shoulder=(0.2, 0, 1.42), elbow=(0.25, -0.03, 1.16), wrist=(0.035, -0.175, 1.065))),
        brow=dict(inner=0.016, outer=-0.002, raise_right=0.0),
        eyes=1.0, mouth=dict(width=0.036, curve=-0.001, open=0.004), tear=False),
    # Bowed head, eyes shut, hand at her mouth, shoulders slumped: she has been caught.
    "broken": dict(
        lean=9, head=(18, -7, 10), lift=-0.015,
        arms=dict(
            left=dict(shoulder=(-0.2, 0, 1.385), elbow=(-0.265, -0.12, 1.2), wrist=(-0.055, -0.155, 1.46)),
            right=dict(shoulder=(0.2, 0, 1.385), elbow=(0.255, -0.03, 1.15), wrist=(0.215, -0.07, 0.98))),
        brow=dict(inner=0.020, outer=-0.006, raise_right=0.0),
        eyes=0.0, mouth=dict(width=0.044, curve=-0.007, open=0.0), tear=True),
}


def build(pose):
    lib.reset()
    skin = M("skin", "#d9a98a", rough=0.55)
    skin_dark = M("skin_dark", "#b8806a", rough=0.6)
    hair = M("hair", "#1c110d", rough=0.45)
    cardigan = M("cardigan", "#6b7a3e", rough=0.85)
    blouse = M("blouse", "#ece6d6", rough=0.7)
    skirt = M("skirt", "#262b36", rough=0.8)
    wire = M("wire", "#b99a4b", rough=0.3, metal=1.0)
    ink = M("ink", "#1d120e", rough=0.4)
    white = M("eye_white", "#f4f0e6", rough=0.3)
    iris = M("iris", "#3a2a1c", rough=0.2)
    lip = M("lip", "#9c4a4a", rough=0.5)
    inside = M("mouth_inside", "#3a1414", rough=0.6)
    glint = M("glint", "#ffffff", rough=0.1, emit="#ffffff", emit_strength=3.0)
    tear_m = M("tear", "#bcd8ff", rough=0.05, emit="#bcd8ff", emit_strength=0.6)
    badge = M("badge", "#eeeeea", rough=0.5)
    strap = M("strap", "#a33a2e", rough=0.6)
    lift = pose["lift"]

    # ---- Lower body (does not move) ----
    cone("skirt", 0.225, 0.14, 0.56, (0, 0, 0.83), skirt)

    # ---- Upper body ----
    upper = []
    upper.append(sphere("cardigan", 1.0, (0, 0, 1.265), cardigan, scale=(0.165, 0.108, 0.2)))
    upper.append(cone("cardigan_waist", 0.128, 0.15, 0.2, (0, 0, 1.12), cardigan))
    upper.append(sphere("blouse", 1.0, (0, -0.012, 1.28), blouse, scale=(0.062, 0.12, 0.17)))
    for side in (-1, 1):                                              # collar points
        upper.append(lib.box("collar", (0.05, 0.012, 0.03), (side * 0.03, -0.1, 1.475), blouse, bevel=0.004,
                             rot=(0, side * 0.5, 0)))
    for i in range(3):                                                # buttons
        upper.append(sphere("button", 0.009, (0.0, -0.131, 1.34 - i * 0.07), M("button", "#d8c9a0", rough=0.3)))
    # lanyard and the security badge (the one on the vault door log)
    upper.append(tube("lanyard", [(-0.05, -0.095, 1.49), (0.0, -0.128, 1.21), (0.05, -0.095, 1.49)], 0.004, strap))
    upper.append(lib.box("badge", (0.06, 0.006, 0.085), (0, -0.132, 1.185), badge, bevel=0.003))
    upper.append(lib.box("badge_stripe", (0.044, 0.002, 0.014), (0, -0.136, 1.21), strap, bevel=0.0))
    upper.append(lib.box("badge_photo", (0.026, 0.002, 0.026), (-0.009, -0.136, 1.172), skin_dark, bevel=0.0))

    # Arms: capsules between shoulder, elbow and wrist, plus a rounded hand.
    for side, joints in pose["arms"].items():
        sh, el, wr = ([j[0] * ARM_X, j[1], j[2]] for j in (joints["shoulder"], joints["elbow"], joints["wrist"]))
        sh[2] += lift
        upper += limb("upper_arm_" + side, sh, el, 0.037, cardigan)
        upper += limb("forearm_" + side, el, wr, 0.032, cardigan, cap0=False)
        upper.append(sphere("hand_" + side, 0.033, wr, skin, scale=(1.0, 0.85, 1.15)))

    # ---- Head ----
    head = []
    head.append(sphere("neck", 1.0, (0, 0.0, 1.51), skin, scale=(0.042, 0.042, 0.06)))
    head.append(sphere("head", 1.0, HEAD, skin, scale=(0.1, 0.108, 0.118)))
    head.append(sphere("jaw", 1.0, (0, -0.012, 1.565), skin, scale=(0.08, 0.088, 0.07)))
    for side in (-1, 1):
        head.append(sphere("ear", 0.02, (side * 0.098, 0.0, 1.615), skin, scale=(0.5, 0.8, 1.2)))
    head.append(sphere("nose", 0.016, (0, -0.116, 1.607), skin, scale=(0.8, 0.9, 1.0)))

    # hair: a cap that sits back and up so the face shows, a bun, a swept fringe and two side locks
    head.append(sphere("hair_back", 1.0, (0, 0.024, 1.648), hair, scale=(0.115, 0.122, 0.124)))
    head.append(sphere("bun", 0.05, (0, 0.108, 1.69), hair))
    head.append(sphere("fringe", 1.0, (0.018, -0.099, 1.722), hair, scale=(0.092, 0.03, 0.036)))
    head[-1].rotation_euler = (0, math.radians(-20), 0)
    for side in (-1, 1):
        head.append(sphere("lock", 1.0, (side * 0.098, -0.04, 1.64), hair, scale=(0.013, 0.034, 0.055)))

    # eyes, lids, glasses
    eye_z, eye_y = HEAD[2] + 0.014, -0.098
    openness = pose["eyes"]
    for side in (-1, 1):
        ex = side * 0.042
        if openness > 0.12:
            head.append(sphere("eye", 1.0, (ex, eye_y, eye_z), white, scale=(0.02, 0.008, 0.024)))
            head.append(sphere("iris", 1.0, (ex, eye_y - 0.0042, eye_z - 0.001), iris, scale=(0.0118, 0.005, 0.015)))
            head.append(sphere("glint", 0.0035, (ex - 0.003, eye_y - 0.0085, eye_z + 0.005), glint))
            if openness < 0.95:                                        # upper lid comes down over the eye
                top = eye_z + 0.036
                bottom = eye_z + 0.024 - (1 - openness) * 0.048
                head.append(sphere("lid", 1.0, (ex, eye_y - 0.0025, (top + bottom) / 2), skin,
                                   scale=(0.0225, 0.0105, (top - bottom) / 2)))
        else:                                                          # closed: a soft downward arc and lashes
            head.append(tube("closed_eye", [(ex - 0.02, eye_y - 0.004, eye_z - 0.002), (ex, eye_y - 0.0075, eye_z - 0.011),
                                            (ex + 0.02, eye_y - 0.004, eye_z - 0.002)], 0.0026, ink))
        head.append(lib.torus("rim", 0.031, 0.0026, (ex, -0.121, eye_z + 0.001), wire, rot=(math.pi / 2, 0, 0)))
        head.append(limb("temple", (side * 0.073, -0.118, eye_z + 0.006), (side * 0.108, -0.01, eye_z + 0.004), 0.0022, wire, False, False)[0])
    head.append(lib.box("bridge", (0.02, 0.004, 0.004), (0, -0.123, eye_z + 0.008), wire, bevel=0.0008))

    # brows
    b = pose["brow"]
    for side in (-1, 1):
        extra = b["raise_right"] if side == 1 else 0.0
        z0 = HEAD[2] + 0.056 + extra
        head.append(tube("brow", [(side * 0.07, -0.108, z0 + b["outer"]), (side * 0.043, -0.113, z0 + 0.006 + (b["inner"] + b["outer"]) / 2),
                                  (side * 0.014, -0.114, z0 + b["inner"])], 0.0042, hair))

    # mouth
    m = pose["mouth"]
    mz, my = HEAD[2] - 0.054, -0.108
    w, c = m["width"] / 2, m["curve"]
    head.append(tube("mouth", [(-w, my + 0.004, mz + c), (0, my - 0.004, mz - c * 0.4), (w, my + 0.004, mz + c)], 0.0032, lip))
    if m["open"]:
        head.append(sphere("mouth_inside", 1.0, (0, my - 0.001, mz - 0.001), inside, scale=(w * 0.55, 0.004, m["open"])))
    if pose["tear"]:
        head.append(sphere("tear", 1.0, (-0.05, -0.1, HEAD[2] - 0.012), tear_m, scale=(0.0045, 0.0035, 0.012)))

    # ---- Hierarchy and pose ----
    head_pivot = group("head_pivot", NECK, head)
    upper_pivot = group("upper_pivot", HIPS, upper + [head_pivot])
    head_pivot.rotation_euler = [math.radians(a) for a in pose["head"]]
    head_pivot.scale = (HEAD_SCALE,) * 3
    upper_pivot.rotation_euler = (math.radians(pose["lean"]), 0, 0)
    # shoulders: lift is applied to the arm joints; turn the whole figure a little toward the detective
    root = group("root", (0, 0, 0), [upper_pivot] + [o for o in bpy.data.objects if o.name.startswith("skirt")])
    root.rotation_euler = (0, 0, math.radians(-10))


def light_and_render(name):
    lib.world_gradient("#222a42", "#141a2c", strength=0.55)
    lib.light("key", "AREA", (-1.4, -1.7, 1.9), 190, "#ffcf9a", size=1.2, target=(0, 0, 1.4))
    lib.light("rim", "AREA", (1.6, 1.3, 2.1), 330, "#7f9cff", size=0.9, target=(0, 0, 1.5))
    lib.light("fill", "AREA", (1.4, -2.0, 1.3), 55, "#a9b8ff", size=2.0, target=(0, 0, 1.3))
    lib.light("top", "AREA", (0, -1.2, 3.0), 45, "#ffffff", size=2.0, target=(0, 0, 1.3))
    cam = lib.camera((0, -5.0, 1.27), (0, 0, 1.27), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.42
    w, h, samples = (525, 700, 40) if fast else (1050, 1400, 128)
    lib.setup_render(w, h, samples, transparent=True, exposure=0.15)
    os.makedirs(out_dir, exist_ok=True)
    lib.render(os.path.join(out_dir, "elena_stylised_%s%s.png" % (name, "_fast" if fast else "")))


for name in (POSES if which == "all" else [which]):
    build(POSES[name])
    light_and_render(name)
