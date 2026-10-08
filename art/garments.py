"""Clothes built from the body itself: take the skin a garment covers, inflate it, smooth away the anatomy,
give it thickness and a fabric. Works on any figure, so it needs no clothing assets.

    import garments
    garments.sweater(body, colour="#7f8c6c")
    garments.shirt(body); garments.waistcoat(body, colour="#9aa0a6")

The body's bone weights say which skin belongs to which part (spine, pectorals, upper arms, forearms...).
Edges of the garment (hem, cuffs, neckline) get a ribbed band, found by walking inward from the open edges.
"""
import math
from collections import deque

import bmesh
import bpy
from mathutils import Vector

import lib

TORSO = ("spine1", "spine2", "spine3", "spine4", "l_pectoral", "r_pectoral", "pelvis", "hip", "abdomen", "chest")
SHOULDERS = ("l_shoulder", "r_shoulder", "l_collar", "r_collar")
UPPER_ARMS = ("l_upperarm", "r_upperarm", "l_upperarmtwist1", "l_upperarmtwist2", "r_upperarmtwist1", "r_upperarmtwist2")
FOREARMS = ("l_forearm", "r_forearm", "l_forearmtwist1", "l_forearmtwist2", "r_forearmtwist1", "r_forearmtwist2")
NECK = ("neck1",)


def _dominant_groups(body):
    names = {vg.index: vg.name for vg in body.vertex_groups}
    dom = []
    for v in body.data.vertices:
        best, bw = None, 0.0
        for g in v.groups:
            if g.weight > bw:
                best, bw = names.get(g.group), g.weight
        dom.append(best)
    return dom


def _skin_positions(body):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    pos = [body.matrix_world @ v.co for v in me.vertices]
    nor = [(body.matrix_world.to_3x3() @ v.normal).normalized() for v in me.vertices]
    ev.to_mesh_clear()
    return pos, nor


def _flatten_front(bm, body_pts, margin, drape=0):
    """Tailored garments hold a straight front instead of following the chest: for each height, push the cloth out to
    the most forward point of the body there (plus margin), fading out toward the sides. Never moves cloth inward."""
    step = 0.02
    prof = {}
    for p in body_pts:
        if abs(p.x) < 0.17:
            b = int(round(p.z / step))
            prof[b] = min(prof.get(b, 9.0), p.y)
    keys = sorted(prof)
    # running minimum: never cut in. With drape, cloth also hangs from the fullest point up to `drape` steps above.
    run = {b: min(prof.get(b + d, 9.0) for d in range(-2, 3 + drape)) for b in keys}
    smooth = {b: sum(run.get(b + d, run[b]) for d in range(-2, 3)) / 5.0 for b in keys}
    for v in bm.verts:
        b = v.co.z / step
        lo, hi = int(b // 1), int(b // 1) + 1
        if lo not in smooth or hi not in smooth or v.co.y > 0.0:
            continue
        t = b - lo
        target = smooth[lo] * (1 - t) + smooth[hi] * t - margin
        w = max(0.0, min(1.0, (0.19 - abs(v.co.x)) / 0.09))
        w = w * w * (3 - 2 * w)
        v.co.y = min(v.co.y, v.co.y + (target - v.co.y) * w)


def build(body, parts, name, offset=0.006, smooth_iters=12, thickness=0.0025, keep=None, band_width=0.03,
          planes=(), boundary_smooth=12, flatten=None, drape=0):
    """Make a garment mesh from the body faces whose vertices all belong to `parts`.

    keep(position) -> bool can trim further (hem height, neckline, V-neck). Returns the new object; its
    vertex attribute 'band' is 1 near the garment's open edges (for cuffs, hems and collars)."""
    dom = _dominant_groups(body)
    pos, nor = _skin_positions(body)
    inside = [g in parts and (keep is None or keep(pos[i])) for i, g in enumerate(dom)]
    faces = [p for p in body.data.polygons if all(inside[v] for v in p.vertices)]
    used = sorted({v for f in faces for v in f.vertices})
    remap = {v: i for i, v in enumerate(used)}
    verts = [pos[v] + nor[v] * offset for v in used]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [[remap[v] for v in f.vertices] for f in faces])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)

    bm = bmesh.new()
    bm.from_mesh(me)
    # Clean cuts (neckline, hem): slice the mesh with planes; everything behind a plane's normal goes.
    for co, no in planes:
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_inner=True, clear_outer=False)
    for e in [e for e in bm.edges if not e.link_faces]:
        bm.edges.remove(e)
    for v in [v for v in bm.verts if not v.link_edges]:
        bm.verts.remove(v)
    # Cut edges inherit the body mesh's zigzag; relax each boundary vertex toward its boundary neighbours.
    for _ in range(boundary_smooth):
        moves = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
                if len(nb) == 2:
                    moves[v] = (nb[0].co + nb[1].co) / 2 * 0.6 + v.co * 0.4
        for v, c in moves.items():
            v.co = c
    # Fabric does not follow every dip of the body: smooth the surface, then keep it outside the skin.
    for _ in range(smooth_iters):
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5,
                              use_axis_x=True, use_axis_y=True, use_axis_z=True)
    if flatten is not None:
        _flatten_front(bm, [pos[i] for i in used], flatten, drape)
    # Distance (in edges) from the open edges, for ribbed bands.
    dist = {v: (0 if v.is_boundary else None) for v in bm.verts}
    q = deque(v for v in bm.verts if v.is_boundary)
    while q:
        v = q.popleft()
        for e in v.link_edges:
            o = e.other_vert(v)
            if dist[o] is None:
                dist[o] = dist[v] + 1
                q.append(o)
    bm.to_mesh(me)
    bm.free()
    # Band strength from distance to the nearest open edge, measured in metres along the surface (approx).
    band = me.attributes.new("band", "FLOAT", "POINT")
    edge_len = sum((me.vertices[e.vertices[0]].co - me.vertices[e.vertices[1]].co).length for e in me.edges) / max(1, len(me.edges))
    steps = max(1, int(band_width / max(edge_len, 1e-4)))
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    vals = []
    dist2 = {v.index: (0 if v.is_boundary else None) for v in bm2.verts}
    q = deque(v for v in bm2.verts if v.is_boundary)
    while q:
        v = q.popleft()
        for e in v.link_edges:
            o = e.other_vert(v)
            if dist2[o.index] is None:
                dist2[o.index] = dist2[v.index] + 1
                q.append(o)
    for v in bm2.verts:
        d = dist2[v.index]
        vals.append(1.0 if d is not None and d <= steps else 0.0)
    bm2.free()
    band.data.foreach_set("value", vals)

    wrap = ob.modifiers.new("outside_skin", "SHRINKWRAP")
    wrap.target = body
    wrap.wrap_method = "NEAREST_SURFACEPOINT"
    wrap.wrap_mode = "OUTSIDE"
    wrap.offset = offset * 0.8
    sol = ob.modifiers.new("cloth_thickness", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = 1.0
    sub = ob.modifiers.new("smooth_surface", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    for p in me.polygons:
        p.use_smooth = True
    print("GARMENT %s: %d faces" % (name, len(me.polygons)))
    return ob


def _fabric(name, colour, rib_scale, rib_strength, band_rib_scale, rough=0.85, sheen=0.4, fuzz=600.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lib.rgb(colour)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.2        # cloth hardly reflects: keeps dark colours dark
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ribs = nt.nodes.new("ShaderNodeTexWave")
    ribs.bands_direction = "X"
    ribs.inputs["Scale"].default_value = rib_scale
    band_ribs = nt.nodes.new("ShaderNodeTexWave")
    band_ribs.bands_direction = "X"
    band_ribs.inputs["Scale"].default_value = band_rib_scale
    nt.links.new(coord.outputs["Object"], ribs.inputs["Vector"])
    nt.links.new(coord.outputs["Object"], band_ribs.inputs["Vector"])
    band = nt.nodes.new("ShaderNodeAttribute")
    band.attribute_name = "band"
    pick = nt.nodes.new("ShaderNodeMix")
    pick.data_type = "FLOAT"
    nt.links.new(band.outputs["Fac"], pick.inputs["Factor"])
    nt.links.new(ribs.outputs["Fac"], pick.inputs["A"])
    nt.links.new(band_ribs.outputs["Fac"], pick.inputs["B"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = fuzz
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = rib_strength
    nt.links.new(pick.outputs["Result"], add.inputs[0])
    nt.links.new(noise.outputs["Fac"], add.inputs[2])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def _assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def _neck_hem(neck_z, hem_z, dip=0.25):
    """Planes for a crew neckline (lower at the front, y < 0) and a flat hem, plus a coarse pre-filter."""
    planes = []
    if neck_z is not None:
        planes.append(((0, 0, neck_z), (0.0, dip, -1.0)))
    if hem_z is not None:
        planes.append(((0, 0, hem_z), (0.0, 0.0, 1.0)))
    keep = lambda p: (neck_z is None or p.z < neck_z + 0.08) and (hem_z is None or p.z > hem_z - 0.06)
    return planes, keep


def _cable_knit(name, colour):
    """A chunky cable knit: wide vertical ribs, plaited cables between them, a fuzzy surface."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lib.rgb(colour)
    b.inputs["Roughness"].default_value = 0.95
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.15
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = 0.12
        b.inputs["Sheen Roughness"].default_value = 0.5
    coord = nt.nodes.new("ShaderNodeTexCoord")
    # Ribs: straight columns, 22 per metre of width, rounded.
    ribs = nt.nodes.new("ShaderNodeTexWave")
    ribs.bands_direction = "X"
    ribs.wave_profile = "SIN"
    ribs.inputs["Scale"].default_value = 70.0
    ribs.inputs["Distortion"].default_value = 0.0
    nt.links.new(coord.outputs["Object"], ribs.inputs["Vector"])
    # Cables: every third column braids; a diagonal wave on the vertical axis makes the plait.
    cab = nt.nodes.new("ShaderNodeTexWave")
    cab.bands_direction = "DIAGONAL"
    cab.inputs["Scale"].default_value = 160.0
    cab.inputs["Distortion"].default_value = 3.0
    cab.inputs["Detail"].default_value = 1.0
    nt.links.new(coord.outputs["Object"], cab.inputs["Vector"])
    zone = nt.nodes.new("ShaderNodeTexWave")
    zone.bands_direction = "X"
    zone.inputs["Scale"].default_value = 23.0
    zone.inputs["Distortion"].default_value = 0.0
    nt.links.new(coord.outputs["Object"], zone.inputs["Vector"])
    zmap = nt.nodes.new("ShaderNodeMapRange")
    zmap.interpolation_type = "SMOOTHSTEP"
    zmap.inputs[1].default_value, zmap.inputs[2].default_value = 0.55, 0.8
    nt.links.new(zone.outputs["Fac"], zmap.inputs[0])
    mixh = nt.nodes.new("ShaderNodeMix")
    mixh.data_type = "FLOAT"
    nt.links.new(zmap.outputs["Result"], mixh.inputs["Factor"])
    nt.links.new(ribs.outputs["Fac"], mixh.inputs["A"])
    nt.links.new(cab.outputs["Fac"], mixh.inputs["B"])
    band = nt.nodes.new("ShaderNodeAttribute")
    band.attribute_name = "band"
    cuff = nt.nodes.new("ShaderNodeWave") if False else nt.nodes.new("ShaderNodeTexWave")
    cuff.bands_direction = "X"
    cuff.inputs["Scale"].default_value = 210.0
    nt.links.new(coord.outputs["Object"], cuff.inputs["Vector"])
    pick = nt.nodes.new("ShaderNodeMix")
    pick.data_type = "FLOAT"
    nt.links.new(band.outputs["Fac"], pick.inputs["Factor"])
    nt.links.new(mixh.outputs["Result"], pick.inputs["A"])
    nt.links.new(cuff.outputs["Fac"], pick.inputs["B"])
    fuzz = nt.nodes.new("ShaderNodeTexNoise")
    fuzz.inputs["Scale"].default_value = 500.0
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY_ADD"
    add.inputs[1].default_value = 2.2
    nt.links.new(pick.outputs["Result"], add.inputs[0])
    nt.links.new(fuzz.outputs["Fac"], add.inputs[2])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(add.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # Light and shade in the grooves: a little darker where the height is low.
    dark = nt.nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.blend_type = "MULTIPLY"
    dark.inputs["B"].default_value = (0.55, 0.55, 0.55, 1.0)
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(pick.outputs["Result"], inv.inputs[1])
    nt.links.new(inv.outputs[0], dark.inputs["Factor"])
    dark.inputs["A"].default_value = lib.rgb(colour)
    nt.links.new(dark.outputs["Result"], b.inputs["Base Color"])
    return m


def sweater(body, colour="#7f8c6c", neck_z=None, hem_z=None, chunky=False):
    """A long-sleeved knit sweater with ribbed cuffs, hem and crew neck. chunky: cable knit, thicker and softer."""
    planes, keep = _neck_hem(neck_z, hem_z, dip=0.3)
    ob = build(body, TORSO + SHOULDERS + UPPER_ARMS + FOREARMS + NECK, "sweater", offset=0.02, smooth_iters=30,
               thickness=0.006 if chunky else 0.004, keep=keep, planes=planes, flatten=0.004, drape=3,
               band_width=0.04 if chunky else 0.03)
    _assign(ob, _cable_knit("cable_knit", colour) if chunky else
            _fabric("knit", colour, rib_scale=120.0, rib_strength=1.0, band_rib_scale=260.0, sheen=0.05))
    return ob


def shirt(body, colour="#7d7769", neck_z=None, hem_z=None):
    planes, keep = _neck_hem(neck_z, hem_z, dip=0.15)
    ob = build(body, TORSO + SHOULDERS + UPPER_ARMS + FOREARMS + NECK, "shirt", offset=0.011, smooth_iters=18,
               thickness=0.0015, keep=keep, band_width=0.02, planes=planes, flatten=0.002)
    _assign(ob, _fabric("cotton", colour, rib_scale=900.0, rib_strength=0.05, band_rib_scale=900.0, rough=0.6,
                        sheen=0.05, fuzz=1500.0))
    return ob


def waistcoat(body, colour="#4d535a", v_bottom_z=None, hem_z=None, buttons=5):
    """A sleeveless V-neck waistcoat in fine wool, worn over the shirt, with a row of buttons."""
    def keep(p):
        if hem_z is not None and p.z < hem_z:
            return False
        if v_bottom_z is not None and p.y < -0.02:
            # the V: open in front above a line rising from the V's point toward the shoulders
            if p.z > v_bottom_z + abs(p.x) * 3.4:
                return False
        return True
    ob = build(body, TORSO + SHOULDERS, "waistcoat", offset=0.011, smooth_iters=16, thickness=0.003, keep=keep,
               band_width=0.012, flatten=0.012)
    _assign(ob, _fabric("waistcoat_wool", colour, rib_scale=700.0, rib_strength=0.15, band_rib_scale=700.0,
                        rough=0.55, sheen=0.05, fuzz=1200.0))
    if v_bottom_z is not None and hem_z is not None and buttons:
        btn = lib.material("button", "#2a2826", rough=0.25, metal=0.2)
        me = ob.data
        front = [ob.matrix_world @ v.co for v in me.vertices if abs(v.co.x) < 0.006 and v.co.y < 0]
        for k in range(buttons):
            z = v_bottom_z - 0.01 - k * (v_bottom_z - hem_z - 0.03) / max(1, buttons - 1)
            near = [p for p in front if abs(p.z - z) < 0.01]
            y = min(p.y for p in near) - 0.003 if near else -0.12
            lib.cylinder("button", 0.0055, 0.003, (0.0, y, z), btn, rot=(math.pi / 2, 0, 0))
    return ob


LEGS = ("pelvis", "l_thightwist1", "l_thightwist2", "r_thightwist1", "r_thightwist2")


def _hull_object(points, name, offset, mat):
    """A closed solid around a point cloud: its convex hull, pushed outward along the normals by `offset`."""
    bm = bmesh.new()
    for pt in points:
        bm.verts.new(pt)
    res = bmesh.ops.convex_hull(bm, input=bm.verts, use_existing_faces=False)
    stray = list({v for v in res["geom_interior"] + res.get("geom_unused", []) if isinstance(v, bmesh.types.BMVert)})
    bmesh.ops.delete(bm, geom=stray, context="VERTS")
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts:
        v.co += v.normal * offset
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sub = ob.modifiers.new("round_off", "SUBSURF")
    sub.levels = 2
    sub.render_levels = 2
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    return ob


def trousers(body, colour="#2d3238", top_z=None, bottom_z=None, offset=0.016):
    """Tailored trousers: one convex hull per leg, so the cloth bridges the crotch and falls straight instead of
    clinging to the skin. Top and bottom heights bound the hulls."""
    dom = _dominant_groups(body)
    pos, _ = _skin_positions(body)
    pts = [pos[i] for i, g in enumerate(dom) if g in LEGS
           and (top_z is None or pos[i].z <= top_z) and (bottom_z is None or pos[i].z >= bottom_z)]
    mat = _fabric("trouser_wool", colour, rib_scale=700.0, rib_strength=0.1, band_rib_scale=700.0,
                  rough=0.6, sheen=0.05, fuzz=1200.0)
    obs = []
    for sign, nm in ((-1, "trouser_leg_L"), (1, "trouser_leg_R")):
        half = [p for p in pts if p.x * sign >= -0.012]            # each leg's hull includes a little of the middle
        obs.append(_hull_object(half, nm, offset, mat))
    print("GARMENT trousers: %d points" % len(pts))
    return obs


def collar_and_tie(body, shirt_obj, neck_z, collar_colour="#d8d3c6", tie_colour="#5a1c26", tie_bottom_z=None):
    """A turned-down shirt collar and a necktie lying on the shirt front. The tie is placed against the shirt's
    actual surface, so it sits flat whatever the body shape; garments outside the shirt (the waistcoat) cover it."""
    from mathutils.bvhtree import BVHTree
    dom = _dominant_groups(body)
    pos, _ = _skin_positions(body)
    ring = [pos[i] for i, g in enumerate(dom) if g in ("neck1", "neck2") and abs(pos[i].z - neck_z) < 0.012]
    cx = sum(p.x for p in ring) / len(ring)
    cy = sum(p.y for p in ring) / len(ring)
    rx = max(abs(p.x - cx) for p in ring)
    ry = max(abs(p.y - cy) for p in ring)
    mat = _fabric("collar_cotton", collar_colour, rib_scale=900.0, rib_strength=0.05, band_rib_scale=900.0, rough=0.6,
                  sheen=0.05, fuzz=1500.0)
    # --- collar: a band that stands around the neck, with points that fall forward over the shirt front
    n = 72
    rows = 3
    verts, faces = [], []
    gap = 0.20                                          # radians left open at the front for the knot
    for r in range(rows):
        for k in range(n + 1):
            th = -math.pi + gap + (2 * math.pi - 2 * gap) * k / n          # -pi.. pi, 0 at the back
            close = max(0.0, 1.0 - (math.pi - abs(th)) / (math.pi * 0.55))   # 1 at the front, 0 a little way round
            pt = close * close * (3 - 2 * close)                             # the points: only near the front
            t = r / (rows - 1)
            drop = 0.040 * pt * t                                            # points fall toward the chest
            out = 0.013 + 0.012 * t + 0.014 * pt * t
            x = cx + (rx + out) * math.sin(th)
            y = cy + (ry + out) * math.cos(th)                               # th = +-pi is the front (-y)
            verts.append((x, y, neck_z - 0.006 + 0.026 * (1 - t) - drop - 0.002 * t))
    for r in range(rows - 1):
        for k in range(n):
            a = r * (n + 1) + k
            faces.append((a, a + 1, a + n + 2, a + n + 1))
    me = bpy.data.meshes.new("collar")
    me.from_pydata(verts, [], faces)
    co = bpy.data.objects.new("collar", me)
    bpy.context.scene.collection.objects.link(co)
    sol = co.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.0025
    sub = co.modifiers.new("smooth", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)

    # --- tie
    dg = bpy.context.evaluated_depsgraph_get()
    ev = shirt_obj.evaluated_get(dg)
    sm = ev.to_mesh()
    sverts = [shirt_obj.matrix_world @ v.co for v in sm.vertices]
    sm.calc_loop_triangles()
    tree = BVHTree.FromPolygons(sverts, [tuple(t.vertices) for t in sm.loop_triangles])
    ev.to_mesh_clear()

    def front_y(x, z):
        hit = tree.ray_cast((x, cy - 0.4, z), (0.0, 1.0, 0.0))
        return hit[0].y if hit[0] is not None else cy - ry - 0.02

    bottom = tie_bottom_z if tie_bottom_z is not None else neck_z - 0.36
    top = neck_z - 0.004
    tmat = _fabric("tie_silk", tie_colour, rib_scale=500.0, rib_strength=0.12, band_rib_scale=500.0, rough=0.5,
                   sheen=0.0, fuzz=2500.0)
    steps = 40
    tv, tf = [], []
    for k in range(steps + 1):
        t = k / steps
        z = top - (top - bottom) * t
        w = 0.011 + 0.014 * min(1.0, t * 2.0) if t < 0.99 else 0.0       # narrow under the knot, widening to the blade
        if t > 0.94:
            w *= max(0.0, (1.0 - t) / 0.06)                              # pointed tip
        y = front_y(0.0, z) - 0.0022 - 0.0012 * math.sin(t * math.pi)
        for sd in (-1, 1):
            tv.append((sd * w, y, z))
    for k in range(steps):
        a = 2 * k
        tf.append((a, a + 1, a + 3, a + 2))
    tm = bpy.data.meshes.new("tie")
    tm.from_pydata(tv, [], tf)
    to = bpy.data.objects.new("tie", tm)
    bpy.context.scene.collection.objects.link(to)
    s2 = to.modifiers.new("thick", "SOLIDIFY")
    s2.thickness = 0.004
    for p in tm.polygons:
        p.use_smooth = True
    tm.materials.append(tmat)
    # knot: a squashed rounded wedge at the collar
    ky = front_y(0.0, top) - 0.005
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0155, segments=24, ring_count=16, location=(0.0, ky, top - 0.004))
    kn = bpy.context.active_object
    kn.name = "tie_knot"
    kn.scale = (1.0, 0.6, 0.9)
    kn.data.materials.append(tmat)
    for p in kn.data.polygons:
        p.use_smooth = True
    print("COLLAR+TIE neck %.3f,%.3f r %.3f/%.3f" % (cx, cy, rx, ry))
    return co, to, kn
