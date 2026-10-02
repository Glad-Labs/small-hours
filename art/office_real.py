"""The night archive office, realistic version: Poly Haven (CC0) props and materials, rendered with Cycles.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/office_real.py -- [--fast] [--out PATH]

Same composition as office.py (calm, dark left third for the menu; window and desk behind Elena), but with
scanned furniture and real materials. Needs the library filled by art/fetch_assets.py.
"""
import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
import ph  # noqa: E402
from lib import box, light, material as M  # noqa: E402

args = lib.script_args()
fast = "--fast" in args
out = args[args.index("--out") + 1] if "--out" in args else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "out", "bg_office.png")
rnd = random.Random(21)
lib.reset()

W, D, H, BACK = 6.0, 6.0, 3.0, 2.2          # room x -3..3, y -3.8..2.2, z 0..3

# --- Materials from the library --------------------------------------------------------------
floor_mat = ph.load_material("dark_wooden_planks")
wall_mat = ph.load_material("painted_plaster_wall")
ph.tint(wall_mat, "#8fa397")                  # push the off-white plaster toward a muted archive green
ceil_mat = ph.load_material("ceiling_interior")
ph.tint(ceil_mat, "#a9a59a")
rug_mat = ph.load_material("dirty_carpet")
trim = M("trim", "#1b1714", rough=0.5)
frame_mat = M("frame_mat", "#16130f", rough=0.5)
city = M("city", "#0b1020", rough=1.0)
city_win = M("city_win", "#ffd58a", rough=0.5, emit="#ffd58a", emit_strength=5.0)


def surface(name, size, loc, mat, tile=1.5):
    o = box(name, size, loc, None, bevel=0)
    ph.apply_material(o, mat)
    ph.world_uv(o, tile)
    return o


# --- Shell -------------------------------------------------------------------------------------
surface("floor", (W + 0.2, D + 0.2, 0.06), (0, -0.8, -0.03), floor_mat, tile=1.6)
surface("ceiling", (W, D, 0.2), (0, -0.8, H + 0.1), ceil_mat, tile=1.6)
surface("left_wall", (0.2, D, H), (-W / 2 - 0.1, -0.8, H / 2), wall_mat, tile=1.8)
surface("right_wall", (0.2, D, H), (W / 2 + 0.1, -0.8, H / 2), wall_mat, tile=1.8)
wx0, wx1, wz0, wz1 = 0.55, 2.65, 0.95, 2.55
surface("bw_left", (wx0 + W / 2, 0.2, H), ((-W / 2 + wx0) / 2, BACK + 0.1, H / 2), wall_mat, tile=1.8)
surface("bw_right", (W / 2 - wx1, 0.2, H), ((wx1 + W / 2) / 2, BACK + 0.1, H / 2), wall_mat, tile=1.8)
surface("bw_under", (wx1 - wx0, 0.2, wz0), ((wx0 + wx1) / 2, BACK + 0.1, wz0 / 2), wall_mat, tile=1.8)
surface("bw_over", (wx1 - wx0, 0.2, H - wz1), ((wx0 + wx1) / 2, BACK + 0.1, (wz1 + H) / 2), wall_mat, tile=1.8)
box("skirting_back", (W, 0.04, 0.14), (0, BACK - 0.02, 0.07), trim, bevel=0.004)
box("skirting_left", (0.04, D, 0.14), (-W / 2 + 0.02, -0.8, 0.07), trim, bevel=0.004)
box("skirting_right", (0.04, D, 0.14), (W / 2 - 0.02, -0.8, 0.07), trim, bevel=0.004)
surface("rug", (3.3, 2.5, 0.012), (0.5, -0.4, 0.006), rug_mat, tile=1.2)

# Window frame, sill and mullions
t = 0.06
box("fr_top", (wx1 - wx0 + 0.12, 0.14, t), ((wx0 + wx1) / 2, BACK - 0.02, wz1 + t / 2), frame_mat)
box("fr_sill", (wx1 - wx0 + 0.24, 0.24, 0.05), ((wx0 + wx1) / 2, BACK - 0.08, wz0 - 0.02), frame_mat)
for x in (wx0 - 0.03, wx1 + 0.03):
    box("fr_side", (t, 0.14, wz1 - wz0 + 0.1), (x, BACK - 0.02, (wz0 + wz1) / 2), frame_mat)
for k in range(1, 3):
    box("mullion_v", (0.035, 0.1, wz1 - wz0), (wx0 + k * (wx1 - wx0) / 3, BACK - 0.02, (wz0 + wz1) / 2), frame_mat)
box("mullion_h", (wx1 - wx0, 0.1, 0.035), ((wx0 + wx1) / 2, BACK - 0.02, (wz0 + wz1) / 2 + 0.1), frame_mat)

# City outside the window: dark towers with scattered lit windows
for i in range(16):
    bw, bd, bh = rnd.uniform(0.9, 1.8), rnd.uniform(0.8, 1.5), rnd.uniform(1.0, 4.2)
    bx, by = rnd.uniform(-2.5, 6.0), rnd.uniform(5.5, 12.0)
    box("tower%d" % i, (bw, bd, bh), (bx, by, bh / 2 - 1.2), city, bevel=0)
    for _ in range(int(bw * bh * 3)):
        if rnd.random() < 0.55:
            box("lit", (0.07, 0.02, 0.1), (bx + rnd.uniform(-bw / 2 + 0.1, bw / 2 - 0.1), by - bd / 2 - 0.01,
                                            rnd.uniform(-1.0, bh - 1.4)), city_win, bevel=0)


# --- Furniture: Poly Haven models ---------------------------------------------------------------
def place(slug, x, y, z=0.0, rot=0.0, scale=1.0):
    root, meshes = ph.load_model(slug, loc=(x, y, z), rot_z=rot, scale=scale)
    lo, hi = ph.bounds(meshes)
    print("PLACED %-26s %.2f x %.2f x %.2f m at (%.2f, %.2f)" % (slug, *(hi - lo), x, y))
    return root, meshes


# Archive shelving along the back wall, filled with boxes and books
SHELF_Y = BACK - 0.27
for sx in (-2.55, -1.4):
    place("steel_frame_shelves_01", sx, SHELF_Y)
for sx in (-2.55, -1.4):
    for z in (0.17, 0.64, 1.1, 1.56):
        cursor = sx - 0.45
        while cursor < sx + 0.4:
            if rnd.random() < 0.55:
                place("cardboard_box_01", cursor + 0.2, SHELF_Y, z, rot=rnd.choice((0, math.pi / 2)) + rnd.uniform(-0.05, 0.05), scale=rnd.uniform(0.8, 0.95))
                cursor += 0.42
            else:
                place("book_encyclopedia_set_01", cursor + 0.28, SHELF_Y, z, scale=1.0)
                cursor += 0.58
place("steel_frame_shelves_02", -0.55, SHELF_Y)

place("vintage_wooden_drawer_01", -0.1, BACK - 0.3, 0.0)         # card-catalogue drawers
place("metal_office_desk", 1.6, 1.55, 0.0)                         # steel pedestal desk under the window
DZ = 0.788                                                          # desk-top height
place("industrial_pipe_lamp", 0.85, 1.5, DZ)
place("Television_01", 2.2, 1.62, DZ, rot=0.0, scale=0.85)          # the archive terminal
place("binder_notebook", 1.45, 1.4, DZ, rot=0.3)
place("clipboard", 1.7, 1.3, DZ + 0.01, rot=-0.2)
place("GreenChair_01", -0.7, 0.75, 0.0, rot=0.75)
place("potted_plant_01", 2.72, 0.95, 0.0)
for bx, by, bz, br in ((-2.6, 0.9, 0.0, 0.2), (-2.55, 0.35, 0.0, -0.1), (-2.62, 0.62, 0.34, 0.05)):
    place("cardboard_box_01", bx, by, bz, rot=br)

# Wall clock on the back wall; the model shows 10:10, so turn its hands to 10:41 (the time in the intro)
clock_root, clock_meshes = place("wall_clock", -0.12, BACK - 0.04, 2.15, rot=0.0)
for m in clock_meshes:
    if m.name.endswith("hours_hand"):
        m.rotation_euler.y += math.radians((10 + 41 / 60) * 30 - (10 + 10 / 60) * 30)
    elif m.name.endswith("minute_hand"):
        m.rotation_euler.y += math.radians(41 * 6 - 10 * 6)
    elif m.name.endswith("second_hand"):
        m.rotation_euler.y += math.radians(200)

# --- Lighting ------------------------------------------------------------------------------------
lib.world_gradient("#35466e", "#080b18", strength=1.0)
light("moon", "SUN", (0, 8, 6), 1.7, "#7f9cff", size=2.5, target=(1.6, 0.5, 0.8))
light("window_glow", "AREA", (1.6, BACK + 0.6, 1.75), 110, "#6f8cff", size=2.0, size_y=1.4, target=(1.2, -1.0, 0.7))
light("lamp_warm", "POINT", (0.85, 1.5, DZ + 0.3), 70, "#ffb866", size=0.06)
light("lamp_pool", "SPOT", (0.85, 1.5, DZ + 0.32), 160, "#ffb060", size=0.05, target=(0.95, 1.3, DZ), spot=80)
light("shelf_glow", "AREA", (-1.5, 0.6, 2.7), 35, "#ffc98a", size=1.5, target=(-1.5, 2.0, 1.0))
light("screen_glow", "AREA", (2.0, 1.1, 1.05), 5, "#5affc8", size=0.4, target=(2.0, -0.5, 0.6))
light("fill_left", "AREA", (-2.4, -2.5, 2.5), 80, "#4b5e9a", size=2.5, target=(-1.5, 1.5, 1.2))
light("ceiling_fill", "AREA", (0.2, -0.5, 2.9), 22, "#c7b08a", size=2.5, target=(0.2, -0.5, 0.0))

# --- Camera and render ----------------------------------------------------------------------------
lib.camera((0.1, -3.55, 1.38), (0.35, 1.2, 1.2), lens=26)
w, h, samples = (960, 540, 40) if fast else (1920, 1080, 160)
lib.setup_render(w, h, samples, transparent=False, exposure=0.6)
os.makedirs(os.path.dirname(out), exist_ok=True)
lib.render(out)
