"""The night archive office, rendered as the game's background.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python art/office.py -- [--fast] [--out PATH]

Mood: a moonlit window and one warm desk lamp against a dark room. The left third is kept calm and
dark because the game's menu buttons sit there; the interesting detail is behind where Elena stands.
"""
import math
import os
import random
import sys

import bpy  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import box, cylinder, light, material as M  # noqa: E402

args = lib.script_args()
fast = "--fast" in args
out = args[args.index("--out") + 1] if "--out" in args else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "out", "bg_office_stylised.png")

rnd = random.Random(11)
lib.reset()

# --- Materials -----------------------------------------------------------------------
wall = M("wall", "#33433f", rough=0.9)
trim = M("trim", "#1f2a28", rough=0.6)
floor_a = M("floor_a", "#4a3220", rough=0.5)
floor_b = M("floor_b", "#3d2a1b", rough=0.5)
wood = M("wood", "#6a4426", rough=0.45)
dark_wood = M("dark_wood", "#3a2415", rough=0.5)
metal = M("metal", "#56626b", rough=0.4, metal=0.6)
card = M("card", "#a78c62", rough=0.9)
paper = M("paper", "#d9d2bd", rough=0.9)
rug = M("rug", "#3a1a1e", rough=1.0)
brass = M("brass", "#b08a3c", rough=0.3, metal=1.0)
lamp_shade = M("lamp_shade", "#2f6f4e", rough=0.4, emit="#ff9f4a", emit_strength=0.8)
screen = M("screen", "#0a1a14", rough=0.2, emit="#5affc8", emit_strength=0.9)
clock_face = M("clock_face", "#e8e2cf", rough=0.7, emit="#e8e2cf", emit_strength=0.25)
frame_mat = M("frame_mat", "#141b1a", rough=0.5)
city = M("city", "#0b1020", rough=1.0)
city_win = M("city_win", "#ffd58a", rough=0.5, emit="#ffd58a", emit_strength=5.0)
cup = M("cup", "#cfd3cf", rough=0.3)
book_colours = ["#6b2d2d", "#2d4a6b", "#3f5a3a", "#7a6034", "#4a3a5e", "#5e3a2d", "#2d5e5a", "#8a7a5a", "#3b3b44"]

W, D, H = 6.0, 6.0, 3.0           # room: x -3..3, y -3.8..2.2, z 0..3
BACK = 2.2

# --- Shell -----------------------------------------------------------------------------
for i in range(24):                                          # floorboards
    box("board%d" % i, (0.26, D + 0.2, 0.04), (-2.9 + i * 0.25, -0.8, -0.02), floor_a if i % 2 else floor_b, bevel=0.004)
box("left_wall", (0.2, D, H), (-W / 2 - 0.1, -0.8, H / 2), wall, bevel=0)
box("right_wall", (0.2, D, H), (W / 2 + 0.1, -0.8, H / 2), wall, bevel=0)
box("ceiling", (W, D, 0.2), (0, -0.8, H + 0.1), trim, bevel=0)
box("skirting_back", (W, 0.04, 0.16), (0, BACK - 0.02, 0.08), trim, bevel=0.004)

# Window in the back wall: the wall is built as four pieces around the opening.
wx0, wx1, wz0, wz1 = 0.55, 2.65, 0.95, 2.55
box("bw_left", (wx0 + W / 2, 0.2, H), ((-W / 2 + wx0) / 2, BACK + 0.1, H / 2), wall, bevel=0)
box("bw_right", (W / 2 - wx1, 0.2, H), ((wx1 + W / 2) / 2, BACK + 0.1, H / 2), wall, bevel=0)
box("bw_under", (wx1 - wx0, 0.2, wz0), ((wx0 + wx1) / 2, BACK + 0.1, wz0 / 2), wall, bevel=0)
box("bw_over", (wx1 - wx0, 0.2, H - wz1), ((wx0 + wx1) / 2, BACK + 0.1, (wz1 + H) / 2), wall, bevel=0)
# frame and mullions
t = 0.06
box("fr_top", (wx1 - wx0 + 0.12, 0.14, t), ((wx0 + wx1) / 2, BACK - 0.02, wz1 + t / 2), frame_mat)
box("fr_bot", (wx1 - wx0 + 0.2, 0.2, 0.07), ((wx0 + wx1) / 2, BACK - 0.05, wz0 - 0.03), frame_mat)
for x in (wx0 - 0.03, wx1 + 0.03):
    box("fr_side", (t, 0.14, wz1 - wz0 + 0.1), (x, BACK - 0.02, (wz0 + wz1) / 2), frame_mat)
for k in range(1, 3):
    box("mullion_v", (0.035, 0.1, wz1 - wz0), (wx0 + k * (wx1 - wx0) / 3, BACK - 0.02, (wz0 + wz1) / 2), frame_mat)
box("mullion_h", (wx1 - wx0, 0.1, 0.035), ((wx0 + wx1) / 2, BACK - 0.02, (wz0 + wz1) / 2 + 0.1), frame_mat)

# City outside the window: dark towers with a scatter of lit windows.
for i in range(16):
    bw, bd, bh = rnd.uniform(0.9, 1.8), rnd.uniform(0.8, 1.5), rnd.uniform(1.0, 4.2)
    bx, by = rnd.uniform(-2.5, 6.0), rnd.uniform(5.5, 12.0)
    box("tower%d" % i, (bw, bd, bh), (bx, by, bh / 2 - 1.2), city, bevel=0)
    for _ in range(int(bw * bh * 3)):
        if rnd.random() < 0.55:
            box("lit", (0.07, 0.02, 0.1), (bx + rnd.uniform(-bw / 2 + 0.1, bw / 2 - 0.1), by - bd / 2 - 0.01,
                                            rnd.uniform(-1.0, bh - 1.4)), city_win, bevel=0)

# --- Back wall furniture: archive shelving on the left, desk under the window ----------------
def shelf_unit(x, y, width, height, depth=0.4, rows=5, facing=-1.0):
    """Open shelving filled with archive boxes and books. Facing the camera (-y)."""
    box("shelf_back", (width, 0.03, height), (x, y + facing * -depth / 2, height / 2), dark_wood, bevel=0)
    for side in (-1, 1):
        box("shelf_side", (0.04, depth, height), (x + side * (width / 2 - 0.02), y, height / 2), dark_wood, bevel=0.004)
    for r in range(rows + 1):
        z = 0.12 + r * (height - 0.14) / rows
        box("shelf_plank", (width, depth, 0.035), (x, y, z), dark_wood, bevel=0.004)
        if r == rows:
            continue
        cursor = x - width / 2 + 0.06
        gap_h = (height - 0.14) / rows - 0.05
        while cursor < x + width / 2 - 0.15:
            if rnd.random() < 0.45:                         # an archive box
                bw = rnd.uniform(0.26, 0.36)
                bh = min(gap_h - 0.02, rnd.uniform(0.24, 0.3))
                if cursor + bw > x + width / 2 - 0.05:
                    break
                box("arch_box", (bw, depth - 0.08, bh), (cursor + bw / 2, y, z + 0.0175 + bh / 2), card, bevel=0.006)
                box("label", (bw * 0.5, 0.01, bh * 0.28), (cursor + bw / 2, y - (depth - 0.08) / 2 - 0.004, z + 0.0175 + bh * 0.62), paper, bevel=0)
                cursor += bw + 0.012
            else:                                           # a run of books
                for _ in range(rnd.randint(4, 9)):
                    bw = rnd.uniform(0.028, 0.06)
                    bh = min(gap_h - 0.02, rnd.uniform(0.2, 0.3))
                    if cursor + bw > x + width / 2 - 0.05:
                        break
                    box("book", (bw, depth - 0.12, bh), (cursor + bw / 2, y, z + 0.0175 + bh / 2),
                        M("book_%s" % rnd.choice(book_colours), rnd.choice(book_colours), rough=0.8),
                        bevel=0.003, rot=(0, rnd.uniform(-0.03, 0.03) if rnd.random() < 0.15 else 0, 0))
                    cursor += bw + 0.004
                cursor += 0.02


shelf_unit(-2.25, BACK - 0.22, 1.5, 2.6)
shelf_unit(-0.65, BACK - 0.22, 1.5, 2.1, rows=4)

# Filing cabinet and the wall clock stopped at 10:41
box("cabinet", (0.55, 0.6, 1.25), (-0.1, BACK - 0.32, 0.625), metal, bevel=0.012)
for r in range(4):
    box("drawer", (0.5, 0.02, 0.27), (-0.1, BACK - 0.63, 0.17 + r * 0.3), M("drawer", "#4c5860", rough=0.4, metal=0.5), bevel=0.006)
    box("handle", (0.14, 0.03, 0.02), (-0.1, BACK - 0.65, 0.17 + r * 0.3 + 0.04), brass, bevel=0.004)
cx, cz = 0.0, 2.15
cylinder("clock_rim", 0.27, 0.05, (cx, BACK - 0.03, cz), brass, rot=(math.pi / 2, 0, 0))
cylinder("clock_face", 0.24, 0.05, (cx, BACK - 0.06, cz), clock_face, rot=(math.pi / 2, 0, 0))
for tick in range(12):
    a = tick * math.pi / 6
    box("tick", (0.012, 0.01, 0.035), (cx + math.sin(a) * 0.205, BACK - 0.09, cz + math.cos(a) * 0.205), frame_mat, bevel=0, rot=(0, a, 0))
for length, angle, thick in ((0.13, math.radians((10 + 41 / 60) * 30), 0.02), (0.19, math.radians(41 * 6), 0.014)):
    box("hand", (thick, 0.012, length), (cx + math.sin(angle) * length / 2, BACK - 0.095, cz + math.cos(angle) * length / 2),
        frame_mat, bevel=0, rot=(0, angle, 0))

# Desk under the window with lamp, terminal, folders and a cup of tea
dx0, dx1, dy0, dy1, dz = 0.45, 2.75, 1.25, 2.1, 0.76
box("desk_top", (dx1 - dx0, dy1 - dy0, 0.05), ((dx0 + dx1) / 2, (dy0 + dy1) / 2, dz), wood, bevel=0.01)
for lx in (dx0 + 0.08, dx1 - 0.08):
    for ly in (dy0 + 0.08, dy1 - 0.08):
        box("desk_leg", (0.07, 0.07, dz), (lx, ly, dz / 2), dark_wood, bevel=0.006)
box("desk_drawers", (0.5, dy1 - dy0 - 0.1, 0.55), (dx1 - 0.35, (dy0 + dy1) / 2, dz - 0.3), dark_wood, bevel=0.008)
LX, TX = 0.62, 2.4                 # lamp and terminal sit either side of where Elena stands
# banker's lamp
box("lamp_base", (0.14, 0.14, 0.03), (LX, 1.75, dz + 0.04), brass, bevel=0.006)
cylinder("lamp_stem", 0.012, 0.28, (LX, 1.75, dz + 0.2), brass)
box("lamp_shade", (0.34, 0.2, 0.14), (LX, 1.7, dz + 0.4), lamp_shade, bevel=0.03, rot=(0.25, 0, 0))
# terminal
box("term_body", (0.46, 0.36, 0.4), (TX, 1.7, dz + 0.25), M("term", "#8b8f84", rough=0.6), bevel=0.02)
box("term_screen", (0.36, 0.02, 0.28), (TX, 1.51, dz + 0.27), screen, bevel=0.005)
box("term_base", (0.3, 0.26, 0.05), (TX, 1.7, dz + 0.04), M("term", "#8b8f84", rough=0.6), bevel=0.01)
box("keyboard", (0.42, 0.14, 0.025), (TX, 1.38, dz + 0.04), M("kbd", "#74786f", rough=0.5), bevel=0.006)
# papers, folders, cup
for i in range(5):
    box("folder", (0.3, 0.22, 0.012), (1.45, 1.55, dz + 0.03 + i * 0.013), M("folder%d" % (i % 3), ["#8a6d3b", "#5e7a4a", "#7a4a3a"][i % 3], rough=0.8),
        bevel=0.002, rot=(0, 0, rnd.uniform(-0.15, 0.15)))
box("blotter", (0.55, 0.36, 0.01), (1.5, 1.35, dz + 0.03), M("blotter", "#2b3330", rough=0.9), bevel=0.003)
cylinder("cup", 0.045, 0.08, (LX + 0.3, 1.45, dz + 0.065), cup)
box("cup_handle", (0.03, 0.012, 0.04), (LX + 0.35, 1.45, dz + 0.065), cup, bevel=0.004)

# Right side: coat stand and a second shelf in perspective
# A potted plant in the dark right-hand corner
from lib import sphere  # noqa: E402
cylinder("pot", 0.2, 0.34, (2.65, 0.9, 0.17), M("pot", "#7a4a35", rough=0.7))
cylinder("soil", 0.185, 0.02, (2.65, 0.9, 0.34), M("soil", "#1f1610", rough=1.0))
leaf = M("leaf", "#3f7a4a", rough=0.6)
for i in range(14):
    ang = i * (2 * math.pi / 14) + rnd.uniform(-0.2, 0.2)
    lean = rnd.uniform(0.5, 0.95)
    h = rnd.uniform(0.35, 0.7)
    sphere("leaf", 0.1, (2.65 + math.cos(ang) * 0.12 * lean, 0.9 + math.sin(ang) * 0.12 * lean, 0.34 + h / 2),
           leaf, scale=(0.35, 0.12, h / 0.2 * 0.5), segments=12, rings=8)
    bpy.context.active_object.rotation_euler = (math.sin(ang) * -lean * 0.6, math.cos(ang) * lean * 0.6, ang)
box("rug", (3.2, 2.4, 0.01), (0.5, -0.4, 0.005), rug, bevel=0.003)
box("rug_edge", (3.0, 2.2, 0.012), (0.5, -0.4, 0.008), M("rug2", "#52272a", rough=1.0), bevel=0.003)

# --- Lighting ----------------------------------------------------------------------------------
lib.world_gradient("#35466e", "#080b18", strength=1.0)
light("moon", "SUN", (0, 8, 6), 1.7, "#7f9cff", size=2.5, target=(1.6, 0.5, 0.8))
light("window_glow", "AREA", (1.6, BACK + 0.6, 1.75), 110, "#6f8cff", size=2.0, size_y=1.4, target=(1.2, -1.0, 0.7))
light("lamp_warm", "POINT", (LX, 1.62, 1.3), 140, "#ffb866", size=0.12)
light("lamp_pool", "SPOT", (LX, 1.62, 1.25), 220, "#ffb060", size=0.1, target=(LX + 0.1, 1.35, 0.7), spot=75)
light("screen_glow", "AREA", (TX - 0.2, 1.2, 1.0), 4, "#5affc8", size=0.4, target=(TX - 0.2, -0.5, 0.6))
light("fill_left", "AREA", (-2.4, -2.5, 2.5), 90, "#4b5e9a", size=2.5, target=(-1.5, 1.5, 1.2))
light("ceiling_fill", "AREA", (0.2, -0.5, 2.9), 22, "#c7b08a", size=2.5, target=(0.2, -0.5, 0.0))

# --- Camera and render -------------------------------------------------------------------------
lib.camera((0.1, -3.55, 1.38), (0.35, 1.2, 1.2), lens=26)
w, h, samples = (960, 540, 48) if fast else (1920, 1080, 160)
lib.setup_render(w, h, samples, transparent=False, exposure=0.6)
os.makedirs(os.path.dirname(out), exist_ok=True)
lib.render(out)
