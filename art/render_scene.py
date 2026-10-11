"""Render a saved character scene (art/scenes/*.blend), optionally in another expression.

    blender -b -y art/scenes/nell_toon.blend --python art/render_scene.py -- <out.png> [--expr warm] [--fast]

This is how hand-tuned scenes become game sprites: whatever was changed by hand in the file (pose, camera, lights,
materials) is kept; only the face's expression sliders are set, from the same table the build scripts use.
-y (auto-run) is needed: the face is driven by scripted drivers, which Blender disables in opened files otherwise.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import lib  # noqa: E402

args = lib.script_args()
out = args[0]


def opt(flag, default=None):
    return args[args.index(flag) + 1] if flag in args else default


EXPRESSIONS = {
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

bpy.ops.preferences.addon_enable(module="bl_ext.user_default.import_daz")
if opt("--expr"):
    from bl_ext.user_default.import_daz import api
    # The figure's own rig carries the expression controls; hair, brows and lashes keep small rigs of their own.
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and any(k.startswith("facs_ctrl_") for k in o.keys()))
    for k in list(rig.keys()):
        if k.startswith("facs_") and isinstance(rig[k], float):
            rig[k] = 0.0                                  # clear whatever expression the file was saved with
    for prop, val in EXPRESSIONS[opt("--expr")].items():
        try:
            api.set_slider(rig, prop, val)
        except Exception as e:
            print("EXPR could not set", prop, str(e)[:80])
    api.update_drivers(rig)
    print("EXPR", opt("--expr"))
sc = bpy.context.scene
if "--fast" in args:
    sc.render.resolution_percentage = 50
lib.render(out)
