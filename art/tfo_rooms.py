"""Ten Forty-One backgrounds: the rooms of the Harrow Gallery, built from Poly Haven (CC0) props and materials.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/tfo_rooms.py -- --room hall|vault|cellar|study|office|bridge [--fast]

Writes art/out/tfo/bg_<room>.png (1920x1080; --fast gives a 960x540 draft). Composition rule for every
room: the left half stays fairly calm and dark (menus sit there), there is clear floor at about a quarter and
three quarters of the width (where people stand), and the story's detail sits centre-right.
Coordinates: x right, y away from the camera, z up. Blender is capped at 20 threads so a game that is
running its model on the same PC stays responsive.
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
room = args[args.index("--room") + 1] if "--room" in args else "hall"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "tfo")
rnd = random.Random(1041)


# --- shared helpers --------------------------------------------------------------------------
def surface(name, size, loc, mat, tile=1.5):
    o = box(name, size, loc, None, bevel=0)
    ph.apply_material(o, mat)
    ph.world_uv(o, tile)
    return o


def tex(slug, tint=None, strength=1.0):
    m = ph.load_material(slug)
    if tint:
        ph.tint(m, tint, strength)
    return m


def matte(mat, specular=0.25, rough_add=0.25):
    """Make a scanned material less mirror-like (Poly Haven floors are shot for close-ups)."""
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = specular
    sock = bsdf.inputs["Roughness"]
    if sock.links:
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        add.use_clamp = True
        add.inputs[1].default_value = rough_add
        nt.links.new(sock.links[0].from_socket, add.inputs[0])
        nt.links.new(add.outputs[0], sock)
    else:
        sock.default_value = min(1.0, sock.default_value + rough_add)
    return mat


def sign(text, loc, rot_z, size, mat, depth=0.004):
    """Flat lettering, e.g. a sale sign."""
    bpy.ops.object.text_add(location=loc, rotation=(math.pi / 2, 0, rot_z))
    t = bpy.context.active_object
    t.data.body = text
    t.data.size = size
    t.data.align_x = "CENTER"
    t.data.extrude = depth
    t.data.materials.append(mat)
    return t


def easel(x, y, rot, wood):
    """A simple wooden display easel; returns the height of its ledge."""
    for dx in (-0.35, 0.35):
        box("easel_leg", (0.05, 0.05, 1.9), (x + dx * math.cos(rot), y + dx * math.sin(rot), 0.95), wood,
            rot=(math.radians(-8), 0, rot))
    box("easel_ledge", (0.9, 0.08, 0.05), (x, y - 0.12, 0.9), wood, rot=(0, 0, rot))
    return 0.93


def place(slug, x, y, z=0.0, rot=0.0, scale=1.0):
    root, meshes = ph.load_model(slug, loc=(x, y, z), rot_z=rot, scale=scale)
    lo, hi = ph.bounds(meshes)
    print("PLACED %-30s %.2f x %.2f x %.2f m at (%.2f, %.2f, %.2f)" % (slug, *(hi - lo), x, y, z))
    return root, meshes


def shell(w, d, h, floor, wall, ceiling, y0=-3.0, window_wall=None):
    """Floor, ceiling and three walls (left, right, back) of a w x d x h room whose front edge is y0.
    window_wall: list of (x0, x1, z0, z1) openings cut into the back wall."""
    yc = y0 + d / 2
    back = y0 + d
    surface("floor", (w + 0.4, d + 0.4, 0.06), (0, yc, -0.03), floor, tile=1.6)
    surface("ceiling", (w + 0.4, d + 0.4, 0.2), (0, yc, h + 0.1), ceiling, tile=2.0)
    surface("left_wall", (0.2, d, h), (-w / 2 - 0.1, yc, h / 2), wall, tile=1.8)
    surface("right_wall", (0.2, d, h), (w / 2 + 0.1, yc, h / 2), wall, tile=1.8)
    if not window_wall:
        surface("back_wall", (w, 0.2, h), (0, back + 0.1, h / 2), wall, tile=1.8)
        return back
    # Cut the openings by building the back wall from strips between them.
    xs = sorted(window_wall)
    cursor = -w / 2
    for (x0, x1, z0, z1) in xs:
        if x0 > cursor:
            surface("bw_strip", (x0 - cursor, 0.2, h), ((cursor + x0) / 2, back + 0.1, h / 2), wall, tile=1.8)
        surface("bw_under", (x1 - x0, 0.2, z0), ((x0 + x1) / 2, back + 0.1, z0 / 2), wall, tile=1.8)
        surface("bw_over", (x1 - x0, 0.2, h - z1), ((x0 + x1) / 2, back + 0.1, (z1 + h) / 2), wall, tile=1.8)
        cursor = x1
    if cursor < w / 2:
        surface("bw_strip", (w / 2 - cursor, 0.2, h), ((cursor + w / 2) / 2, back + 0.1, h / 2), wall, tile=1.8)
    return back


def window_frame(x0, x1, z0, z1, y, mat, mullions=2, transoms=1):
    t = 0.07
    box("fr_top", (x1 - x0 + 0.14, 0.16, t), ((x0 + x1) / 2, y, z1 + t / 2), mat)
    box("fr_sill", (x1 - x0 + 0.26, 0.26, 0.06), ((x0 + x1) / 2, y - 0.06, z0 - 0.03), mat)
    for x in (x0 - t / 2, x1 + t / 2):
        box("fr_side", (t, 0.16, z1 - z0 + 0.14), (x, y, (z0 + z1) / 2), mat)
    for k in range(1, mullions + 1):
        box("mullion", (0.04, 0.1, z1 - z0), (x0 + k * (x1 - x0) / (mullions + 1), y, (z0 + z1) / 2), mat)
    for k in range(1, transoms + 1):
        box("transom", (x1 - x0, 0.1, 0.04), ((x0 + x1) / 2, y, z0 + k * (z1 - z0) / (transoms + 1)), mat)


def storm_outside(y, width=40.0):
    """Night sky with weather: a dark gradient world, a faint distant flash, and rain streaks on a sheet."""
    lib.world_gradient("#1d2433", "#06080e", strength=0.6)
    light("lightning", "AREA", (6, y + 25, 14), 2500, "#b9c8ff", size=12, target=(0, y, 2))
    rain = M("rain", "#b8c6dc", rough=0.2, alpha=0.18, emit="#8fa3c4", emit_strength=0.15)
    for _ in range(260):
        x = rnd.uniform(-width / 2, width / 2)
        z = rnd.uniform(-1.0, 8.0)
        box("rain", (0.006, 0.006, rnd.uniform(0.25, 0.6)), (x, y + rnd.uniform(1.5, 6.0), z), rain, bevel=0,
            rot=(0, math.radians(8), 0))


def finish(cam_loc, cam_target, lens, exposure, samples=(40, 180)):
    lib.camera(cam_loc, cam_target, lens=lens)
    w, h, spp = (960, 540, samples[0]) if fast else (1920, 1080, samples[1])
    lib.setup_render(w, h, spp, transparent=False, exposure=exposure)
    sc = bpy.context.scene
    sc.render.threads_mode = "FIXED"
    sc.render.threads = 20
    os.makedirs(OUT, exist_ok=True)
    lib.render(os.path.join(OUT, "bg_%s%s.png" % (room, "_fast" if fast else "")))


# --- the Great Hall: the auction room ---------------------------------------------------------
def hall():
    W, D, H, Y0 = 14.0, 13.0, 5.6, -6.5
    floor = matte(tex("herringbone_parquet"), specular=0.3, rough_add=0.3)
    wall = tex("painted_plaster_wall", "#4a6655")            # deep gallery green
    ceiling = tex("white_plaster_02", "#cfc6b4")
    panel = tex("dark_paneled_wood")
    gilt = M("gilt", "#b08a4a", rough=0.35, metal=0.9)
    frame_mat = M("window_frame", "#1a1714", rough=0.5)
    wins = [(-5.2, -3.2, 1.2, 4.6), (-1.0, 1.0, 1.2, 4.6), (3.2, 5.2, 1.2, 4.6)]
    back = shell(W, D, H, floor, wall, ceiling, y0=Y0, window_wall=wins)
    for (x0, x1, z0, z1) in wins:
        window_frame(x0, x1, z0, z1, back - 0.02, frame_mat, mullions=1, transoms=2)
    storm_outside(back)
    # Dado panelling and a gilt picture rail on the side walls.
    for side in (-1, 1):
        surface("dado", (0.06, D, 1.15), (side * (W / 2 - 0.03), Y0 + D / 2, 0.575), panel, tile=1.2)
        box("rail", (0.05, D, 0.05), (side * (W / 2 - 0.05), Y0 + D / 2, 3.3), gilt, bevel=0.005)
    surface("dado_back", (W, 0.06, 1.15), (0, back - 0.03, 0.575), panel, tile=1.2)
    box("cornice", (W, 0.3, 0.25), (0, back - 0.15, H - 0.12), M("cornice", "#d8cfbd", rough=0.6), bevel=0.02)

    # Paintings on the right wall, lit like a gallery; the Calder lots.
    for i, (y, slug) in enumerate(((-1.5, "fancy_picture_frame_01"), (1.8, "fancy_picture_frame_02"), (4.6, "fancy_picture_frame_01"))):
        r, _ = place(slug, W / 2 - 0.08, y, 1.7, rot=-math.pi / 2, scale=2.4)
        light("picture_light_%d" % i, "SPOT", (W / 2 - 1.4, y, 4.6), 220, "#ffd9a0", size=0.1, target=(W / 2, y, 2.4), spot=45)
    # Left wall: a big painting high up and a grandfather clock (stopped, like every clock tonight).
    place("fancy_picture_frame_02", -W / 2 + 0.08, 1.0, 1.9, rot=math.pi / 2, scale=2.4)
    light("picture_light_l", "SPOT", (-W / 2 + 1.2, 1.0, 4.6), 120, "#ffd9a0", size=0.1, target=(-W / 2, 1.0, 2.6), spot=40)
    place("vintage_grandfather_clock_01", -W / 2 + 0.45, 4.2, 0.0, rot=math.pi / 2)

    # The rostrum, right of centre and close enough to read, with lot nine on an easel beside it.
    wood = M("rostrum_wood", "#3a2216", rough=0.45)
    RX, RY = 1.6, 4.4
    box("rostrum_step", (2.6, 1.8, 0.22), (RX + 0.3, RY + 0.2, 0.11), M("dais", "#2b1a12", rough=0.6), bevel=0.01)
    box("rostrum_base", (1.1, 0.75, 1.15), (RX, RY, 0.22 + 0.575), wood, bevel=0.02)
    box("rostrum_top", (1.25, 0.85, 0.06), (RX, RY, 0.22 + 1.18), wood, bevel=0.01)
    box("rostrum_badge", (0.5, 0.01, 0.3), (RX, RY - 0.38, 0.95), M("brass", "#a8823e", rough=0.3, metal=1.0), bevel=0.004)
    place("vintage_oil_lamp", RX + 0.4, RY + 0.1, 1.43, scale=0.9)
    light("rostrum_lamp", "POINT", (RX + 0.4, RY + 0.1, 1.8), 40, "#ffb866", size=0.05)
    ledge = easel(3.6, 4.6, -0.15, wood)
    place("fancy_picture_frame_02", 3.6, 4.55, ledge, rot=-0.15, scale=2.0)      # lot nine
    light("lot_nine", "SPOT", (2.8, 1.8, 4.6), 320, "#ffe3b8", size=0.15, target=(3.6, 4.6, 1.6), spot=28)
    sign_mat = M("sign_board", "#151515", rough=0.5)
    box("sign_board", (1.3, 0.04, 0.8), (-0.9, 5.2, 1.55), sign_mat, bevel=0.01)
    ledge2 = easel(-0.9, 5.3, 0.0, wood)
    sign("HARROW GALLERY\nTHE CALDER LATE WORKS\nPRIVATE SALE", (-0.9, 5.17, 1.72), 0.0, 0.11,
         M("sign_text", "#d7b874", rough=0.4, metal=0.6))

    # Rows of chairs, some knocked askew by people leaving in a hurry.
    for row in range(3):
        for col in range(5):
            x = -1.2 + col * 1.1
            y = 2.4 - row * 1.3
            place("dining_chair_02", x + rnd.uniform(-0.08, 0.08), y, 0.0, rot=math.pi + rnd.uniform(-0.25, 0.25))
    # A marble bust on a plinth, left, and the bar table behind it.
    box("plinth", (0.6, 0.6, 1.2), (-4.6, 2.6, 0.6), M("plinth_marble", "#d9d4cc", rough=0.25), bevel=0.01)
    place("marble_bust_01", -4.6, 2.6, 1.2, rot=math.pi * 0.85, scale=1.1)
    place("WoodenTable_02", -5.4, 5.0, 0.0, rot=0.0)

    # Chandeliers and a warm, slightly dim interior (the power is on, just about).
    for x, y in ((-3.0, 1.5), (3.0, 1.5)):
        place("Chandelier_01", x, y, H - 1.4, scale=1.2)
        light("chandelier", "POINT", (x, y, H - 1.6), 380, "#ffcf8f", size=0.4)
    light("ceiling_fill", "AREA", (0, 0.5, H - 0.2), 260, "#c7b08a", size=8.0, target=(0, 0.5, 0))
    light("window_cold", "AREA", (0, back - 0.8, 3.0), 120, "#7d93c8", size=9.0, size_y=3.0, target=(0, 0, 0.5))
    finish((-3.6, -5.6, 1.7), (2.2, 3.0, 1.55), lens=24, exposure=0.1)


# --- the vault: a small strongroom, cold light, one way in (officially) ----------------------
def vault():
    W, D, H, Y0 = 5.0, 5.0, 2.8, -2.0
    concrete = matte(tex("concrete_wall_004", "#9aa3a8"), specular=0.3, rough_add=0.15)
    floor = matte(tex("concrete_floor_02", "#8e9295"))
    back = shell(W, D, H, floor, concrete, concrete, y0=Y0)
    steel = M("steel", "#5b6268", rough=0.35, metal=0.9)
    # Shelving along the back wall with framed works wrapped or stacked.
    place("steel_frame_shelves_03", -1.3, back - 0.35)
    place("steel_frame_shelves_03", 0.25, back - 0.35)
    for x in (-1.6, -1.1, 0.0, 0.5):
        place("standing_picture_frame_01", x, back - 0.38, 0.86, rot=math.pi + rnd.uniform(-0.1, 0.1), scale=1.4)
    for i, x in enumerate((-2.1, -1.95, -1.8)):
        box("wrapped_canvas", (0.06, 1.0 - i * 0.1, 0.8 - i * 0.08), (x, back - 0.9, 0.42 - i * 0.04),
            M("kraft", "#9b7d55", rough=0.9), bevel=0.01, rot=(0, math.radians(-8), 0))
    # The duct grille, low on the back wall right, off its screws and leaning.
    gx = 1.6
    box("duct_hole", (0.62, 0.05, 0.46), (gx, back - 0.005, 0.42), M("duct_dark", "#050505", rough=1.0), bevel=0)
    grille = M("grille", "#7a7f80", rough=0.5, metal=0.8)
    for k in range(7):
        box("grille_slat", (0.6, 0.02, 0.03), (gx + 0.05, back - 0.3, 0.2 + k * 0.06), grille, bevel=0,
            rot=(math.radians(-14), 0, 0))
    box("grille_rim", (0.64, 0.03, 0.5), (gx + 0.05, back - 0.31, 0.38), grille, bevel=0.004, rot=(math.radians(-14), 0, 0))
    light("grille_light", "SPOT", (gx - 0.6, back - 1.6, 1.6), 60, "#c6d3ff", size=0.1, target=(gx, back, 0.4), spot=35)
    # A table with the climate recorder (a clockwork drum) and a lamp.
    box("table_top", (1.2, 0.7, 0.05), (-1.6, 0.6, 0.78), M("table", "#3f3d3a", rough=0.5), bevel=0.01)
    for dx in (-0.55, 0.55):
        for dy in (-0.3, 0.3):
            box("table_leg", (0.04, 0.04, 0.78), (-1.6 + dx, 0.6 + dy, 0.39), steel, bevel=0)
    box("recorder_case", (0.34, 0.22, 0.22), (-1.85, 0.62, 0.92), M("recorder", "#2a3a33", rough=0.4), bevel=0.01)
    lib.cylinder("recorder_drum", 0.07, 0.24, (-1.85, 0.57, 0.95), M("paper", "#e9e4d6", rough=0.8), rot=(0, math.pi / 2, 0))
    # The vault door, swung open, at the left.
    door = M("vault_door", "#4d5357", rough=0.3, metal=0.95)
    lib.cylinder("vault_door", 0.95, 0.35, (-W / 2 + 0.3, 1.2, 1.05), door, rot=(0, math.pi / 2, 0), verts=64)
    lib.cylinder("door_hub", 0.22, 0.45, (-W / 2 + 0.3, 1.2, 1.05), steel, rot=(0, math.pi / 2, 0), verts=32)
    for a in range(6):
        ang = a * math.pi / 3
        lib.cylinder("door_spoke", 0.025, 0.6, (-W / 2 + 0.55, 1.2 + 0.28 * math.cos(ang), 1.05 + 0.28 * math.sin(ang)),
                     steel, rot=(ang, 0, 0))
    # Cold light: a caged lamp and a hard work light from the doorway.
    place("industrial_caged_sconce", 0.0, back - 0.05, 2.2, rot=math.pi)
    light("sconce", "POINT", (0.0, back - 0.25, 2.1), 90, "#d9e4ff", size=0.08)
    light("door_spill", "AREA", (-W / 2 + 0.6, Y0 + 0.4, 2.2), 180, "#c6d3ff", size=1.4, target=(0.6, back, 0.4))
    light("fill", "AREA", (0.5, Y0 + 0.5, H - 0.1), 80, "#9fb2d8", size=3.0, target=(0.5, 1.5, 0))
    # Riveted steel bands so it reads as a strongroom, not a garage.
    for z in (0.6, 1.4, 2.2):
        box("band_back", (W, 0.02, 0.06), (0, back - 0.01, z), steel, bevel=0.004)
        box("band_right", (0.02, D, 0.06), (W / 2 - 0.01, Y0 + D / 2, z), steel, bevel=0.004)
    finish((-0.8, Y0 + 0.2, 1.5), (0.9, back, 0.8), lens=18, exposure=0.2)


# --- the cellar: brick, wine, the fuse cupboard and the other end of the duct --------------------
def cellar():
    W, D, H, Y0 = 7.0, 6.0, 2.7, -2.5
    brick = matte(tex("castle_brick_02_red", "#b8a08a"), specular=0.2)
    floor = matte(tex("brick_floor_02", "#a99a88"))
    back = shell(W, D, H, floor, brick, brick, y0=Y0)
    # Wine racks against the back wall, left of the barrels.
    rack = M("rack", "#3b2a1c", rough=0.7)
    for k in range(6):
        box("rack_shelf", (2.0, 0.45, 0.03), (-1.4, back - 0.25, 0.25 + k * 0.32), rack, bevel=0.003)
    for j in range(4):
        box("rack_post", (0.04, 0.04, 2.0), (-2.4 + j * 0.66, back - 0.48, 1.0), rack, bevel=0)
    for k in range(5):
        for j in range(3):
            place("wine_bottles_01", -2.0 + j * 0.6, back - 0.25, 0.27 + k * 0.32, rot=0.0, scale=0.95)
    # Barrels and crates at the back.
    place("wine_barrel_01", 0.4, back - 0.75, 0.0, rot=-0.2)
    place("wine_barrel_01", 1.15, back - 0.8, 0.0, rot=0.5)
    place("wooden_crate_01", 2.3, back - 0.6, 0.0, rot=0.15)
    place("wooden_crate_02", 2.3, back - 0.6, 0.55, rot=-0.2)
    # The duct's cellar end: low on the right wall, grille back on its screws but only just.
    gy = 0.5
    grille = M("grille", "#6e7273", rough=0.55, metal=0.8)
    box("duct_rim", (0.04, 0.66, 0.5), (W / 2 - 0.02, gy, 0.42), grille, bevel=0.004)
    for k in range(7):
        box("slat", (0.03, 0.62, 0.025), (W / 2 - 0.05, gy, 0.22 + k * 0.06), grille, bevel=0, rot=(0, math.radians(12), 0))
    # The fuse cupboard on the right wall, door ajar, with a small amber light inside.
    cx = 1.6
    box("fuse_back", (0.08, 0.7, 0.9), (W / 2 - 0.04, cx, 1.55), M("fuse_box", "#4a4f45", rough=0.5, metal=0.3), bevel=0.01)
    box("fuse_door", (0.03, 0.7, 0.9), (W / 2 - 0.36, cx - 0.32, 1.55), M("fuse_door", "#566050", rough=0.5, metal=0.3),
        bevel=0.01, rot=(0, 0, math.radians(-50)))
    box("timer", (0.05, 0.1, 0.12), (W / 2 - 0.1, cx + 0.1, 1.45), M("timer_body", "#e6e1d3", rough=0.4), bevel=0.01)
    light("timer_glow", "POINT", (W / 2 - 0.15, cx + 0.1, 1.5), 4, "#ffae4a", size=0.02)
    place("hanging_industrial_lamp", 0.6, 0.6, H - 0.05, scale=1.0)
    light("bulb", "POINT", (0.6, 0.6, H - 0.75), 420, "#ffb46b", size=0.06)
    light("bulb2", "POINT", (2.4, -0.4, H - 0.5), 160, "#ffb46b", size=0.06)
    light("stair_light", "AREA", (-1.5, Y0 + 0.2, H - 0.2), 140, "#9db0d6", size=1.2, target=(0, 1.5, 0))
    light("rack_fill", "AREA", (-1.6, 0.4, H - 0.2), 90, "#ffcf9a", size=1.5, target=(-W / 2, 0.4, 0.8))
    finish((-1.4, Y0 + 0.25, 1.55), (1.0, back - 0.8, 0.85), lens=18, exposure=0.6)


# --- Harrow's study: panelled, a dying fire, the burnt letter ---------------------------------------
def study():
    W, D, H, Y0 = 6.0, 5.5, 3.1, -2.5
    panel = matte(tex("dark_paneled_wood"), specular=0.35, rough_add=0.1)
    floor = matte(tex("oak_wood_planks", "#9a7a5a"))
    ceiling = tex("white_plaster_02", "#bdb4a3")
    wins = [(1.2, 2.6, 1.0, 2.6)]
    back = shell(W, D, H, floor, panel, ceiling, y0=Y0, window_wall=wins)
    window_frame(1.2, 2.6, 1.0, 2.6, back - 0.02, M("frame", "#1a1410", rough=0.5), mullions=1, transoms=1)
    storm_outside(back, width=12)
    # Bookcases on the left wall.
    for y in (-0.6, 0.6):
        place("wooden_bookshelf_worn", -W / 2 + 0.3, y, 0.0, rot=math.pi / 2)
    # The fireplace, back wall left of the window, with embers and a mantel clock stopped at 10:41.
    marble = M("mantel_marble", "#6f665c", rough=0.3)
    fx = -0.9
    box("fp_left", (0.25, 0.35, 1.15), (fx - 0.7, back - 0.18, 0.575), marble, bevel=0.01)
    box("fp_right", (0.25, 0.35, 1.15), (fx + 0.7, back - 0.18, 0.575), marble, bevel=0.01)
    box("fp_mantel", (1.8, 0.45, 0.12), (fx, back - 0.22, 1.2), marble, bevel=0.01)
    box("fp_hole", (1.15, 0.1, 0.95), (fx, back - 0.02, 0.475), M("soot", "#080605", rough=1.0), bevel=0)
    box("embers", (0.7, 0.25, 0.08), (fx, back - 0.2, 0.08), M("embers", "#3a1206", emit="#ff5a1a", emit_strength=6.0), bevel=0.02)
    light("fire_glow", "POINT", (fx, back - 0.5, 0.35), 60, "#ff7a2a", size=0.3)
    place("mantel_clock_01", fx, back - 0.25, 1.26, rot=math.pi)
    # The desk in the middle, a lamp, a leather chair behind it.
    place("ClassicConsole_01", 0.9, 0.9, 0.0, rot=math.pi)
    place("ArmChair_01", 0.9, 1.9, 0.0, rot=math.pi)
    place("vintage_oil_lamp", 1.45, 0.85, 0.82, scale=0.9)
    light("desk_lamp", "POINT", (1.45, 0.85, 1.15), 45, "#ffb866", size=0.05)
    box("letter_ash", (0.24, 0.3, 0.004), (0.6, 0.75, 0.83), M("ash_paper", "#d8cfbd", rough=0.9), bevel=0)
    place("fancy_picture_frame_01", W / 2 - 0.06, 0.3, 1.3, rot=-math.pi / 2, scale=2.0)
    light("fill", "AREA", (0, Y0 + 0.5, H - 0.2), 60, "#b0a088", size=3.0, target=(0, 1, 0))
    light("window_cold", "AREA", (1.9, back - 0.6, 1.8), 40, "#7d93c8", size=1.6, target=(0.5, 0, 0.5))
    finish((-0.6, Y0 + 0.3, 1.6), (0.5, back, 1.1), lens=21, exposure=0.55)


# --- the registrar's office: tidy, labelled, one gap on the shelf ---------------------------------
def office():
    W, D, H, Y0 = 5.5, 5.0, 3.0, -2.5
    wall = tex("painted_plaster_wall", "#d8cfb8")
    floor = matte(tex("wood_floor_worn", "#a08060"))
    ceiling = tex("white_plaster_02", "#d4ccbc")
    wins = [(1.4, 2.4, 1.1, 2.5)]
    back = shell(W, D, H, floor, wall, ceiling, y0=Y0, window_wall=wins)
    window_frame(1.4, 2.4, 1.1, 2.5, back - 0.02, M("frame", "#2a241e", rough=0.5), mullions=1, transoms=1)
    storm_outside(back, width=12)
    # Card catalogue drawers and labelled shelving along the back wall.
    place("vintage_wooden_drawer_01", -1.9, back - 0.3)
    place("wooden_display_shelves_01", -0.3, back - 0.25, 0.0)
    for k in range(7):
        if k == 3:
            continue        # the gap where the Calder sales ledger should be
        place("binder_notebook", -0.75 + k * 0.12, back - 0.3, 1.05, rot=math.pi / 2, scale=1.0)
    label = M("label", "#f2ecd8", rough=0.8)
    for k in range(5):
        box("shelf_label", (0.14, 0.005, 0.04), (-0.85 + k * 0.22, back - 0.47, 0.98), label, bevel=0)
    # The desk under the window, neat stacks, a green-shaded lamp.
    place("WoodenTable_01", 1.7, back - 0.9, 0.0, rot=0.0)
    place("dining_chair_02", 1.6, back - 1.55, 0.0, rot=math.pi * 0.9)
    place("desk_lamp_arm_01", 2.2, back - 0.75, 0.76, rot=3.6)
    light("desk_lamp", "SPOT", (2.05, back - 0.9, 1.25), 60, "#ffd28a", size=0.05, target=(1.6, back - 0.9, 0.76), spot=70)
    place("stationery_supplies", 1.3, back - 0.85, 0.76)
    place("drawer_cabinet", W / 2 - 0.35, 0.9, 0.0, rot=-math.pi / 2, scale=0.85)
    place("potted_plant_02", -W / 2 + 0.4, 0.4, 0.0)
    light("ceiling", "AREA", (0, 0.3, H - 0.1), 140, "#fff1d6", size=2.5, target=(0, 0.3, 0))
    light("window_cold", "AREA", (1.9, back - 0.6, 1.8), 30, "#7d93c8", size=1.2, target=(1.0, 0, 0.5))
    finish((-0.4, Y0 + 0.3, 1.6), (0.4, back, 1.05), lens=21, exposure=0.2)


ROOMS = {"hall": hall, "vault": vault, "cellar": cellar, "study": study, "office": office}

if __name__ == "__main__":
    lib.reset()
    ROOMS[room]()
