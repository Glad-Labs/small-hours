"""Grow hair the way hair grows: roots on the scalp inside a hairline, combed along the head, falling with gravity.

Used from Blender (art/tfo_daz.py). Works on any head mesh, so it does not depend on a hairstyle asset:

    import hairgen
    style = hairgen.Style(cut="bob", part_x=0.008, length_z=..., ...)
    hairgen.grow(body, eyes_centre, style)       # returns the hair curves object

How a strand is made: start at a root, comb away from the parting along the scalp's surface, keep a small gap
above everything beneath it (hair from higher up lies on top, so its gap is larger), and once it leaves the
head, hang with gravity until the cut line. Strands near each other share a 'clump' guide toward their tips,
which is what makes real hair read as locks rather than as a smooth sheet.
"""
import math
import random

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


class Style:
    def __init__(self, cut="bob", part_x=0.008, length_z=None, strands=30000, clumps=900, step=0.005,
                 melanin=0.86, redness=0.5, radius=0.00005, lift=0.003, volume=0.006, hang_volume=0.012,
                 curl_under=0.02, back_shorter=0.015, fringe=False, seed=11,
                 top_len=0.055, side_len=0.014, sweep=0.9, cap_shade=None, hairline_up=0.0, hairline_exp=1.35,
                 tint=None, color=None, taper=0.0):
        self.cut, self.part_x, self.length_z = cut, part_x, length_z
        self.strands, self.clumps, self.step = strands, clumps, step
        self.melanin, self.redness, self.radius = melanin, redness, radius
        self.lift, self.volume, self.hang_volume = lift, volume, hang_volume
        self.curl_under, self.back_shorter, self.fringe = curl_under, back_shorter, fringe
        self.seed = seed
        self.top_len, self.side_len, self.sweep = top_len, side_len, sweep      # 'crop' cut: lengths in metres
        self.cap_shade, self.hairline_up, self.hairline_exp, self.tint = cap_shade, hairline_up, hairline_exp, tint
        self.taper = taper                                      # fraction the drape narrows by toward the ends
        self.color = color                                       # linear RGB; overrides melanin (for grey/white/dyed hair)


def _surface(body):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    mw = body.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles] if me.loop_triangles else None
    if tris is None:
        me.calc_loop_triangles()
        tris = [tuple(t.vertices) for t in me.loop_triangles]
    ev.to_mesh_clear()
    return verts, tris, BVHTree.FromPolygons(verts, tris)


def _hairline(eye, c, p, fringe, up=0.0, exp=1.35):
    """Height of the hairline at the head azimuth of point p: forehead high, temples lower, nape lowest."""
    r = p - c
    a = abs(math.atan2(r.x, -r.y)) / math.pi            # 0 = straight ahead, 1 = straight behind
    front = eye.z + (0.06 if fringe else 0.077) + up
    return front - (front - (eye.z - 0.065)) * (a ** exp)


def grow(body, eye, style, name="hair"):
    """Create and return a hair-curves object for `body`. `eye` is the midpoint between the eyeballs (world)."""
    rnd = random.Random(style.seed)
    verts, tris, bvh = _surface(body)
    c = Vector((0.0, eye.y + 0.075, eye.z + 0.01))       # roughly the centre of the skull
    # --- scalp: triangles above the hairline and close enough to the skull centre to be head, not shoulder
    scalp, areas = [], []
    for t in tris:
        a, b, d = verts[t[0]], verts[t[1]], verts[t[2]]
        m = (a + b + d) / 3
        if (m - c).length > 0.15 or m.z < eye.z - 0.09:
            continue
        if m.z < _hairline(eye, c, m, style.fringe, style.hairline_up, style.hairline_exp) - 0.012:
            continue
        if style.cut == "crop":                         # ears: a box around them, not the whole side of the head
            if abs(m.x) > 0.066 and abs(m.y - c.y) < 0.05 and eye.z - 0.07 < m.z < eye.z + 0.03:
                continue
        elif abs(m.x) > 0.072 and m.z < eye.z + 0.03:   # ears
            continue
        area = (b - a).cross(d - a).length / 2
        scalp.append((a, b, d))
        areas.append(area)
    if not scalp:
        raise RuntimeError("no scalp found")
    cum, tot = [], 0.0
    for ar in areas:
        tot += ar
        cum.append(tot)

    def sample_root():
        x = rnd.random() * tot
        lo, hi = 0, len(cum) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        a, b, d = scalp[lo]
        u, v = rnd.random(), rnd.random()
        if u + v > 1:
            u, v = 1 - u, 1 - v
        q = a + (b - a) * u + (d - a) * v
        # feathered hairline: the line is a soft edge, thinning out over about 12 mm instead of stopping dead
        edge = q.z - _hairline(eye, c, q, style.fringe, style.hairline_up, style.hairline_exp)
        if edge < 0.0 and rnd.random() > (edge + 0.012) / 0.012 * 0.55:
            return sample_root()
        return q

    top = max(p.z for tri in scalp for p in tri)
    # A smooth egg around skull and ears: hair drapes over it instead of tracing the ears, so no ledge.
    band = [v for v in verts if abs(v.z - eye.z) < 0.03 and (v - c).length < 0.14]
    ear_x = max(abs(v.x) for v in band) if band else 0.08
    radii = Vector((ear_x + 0.002, 0.102, (top - c.z) + 0.004))

    def outside_egg(p):
        q = Vector(((p.x - c.x) / radii.x, (p.y - c.y) / radii.y, (p.z - c.z) / radii.z))
        if q.length < 1.0 and q.length > 1e-6:
            q = q / q.length
            return Vector((c.x + q.x * radii.x, c.y + q.y * radii.y, c.z + q.z * radii.z))
        return p
    cut = style.length_z if style.length_z is not None else eye.z - 0.11

    def strand(root):
        """One strand from a root; returns a list of points.

        Phase 1, on the skull: comb away from the parting along the scalp, sideways and back off the face.
        Phase 2, below the skull's widest line: drape down a smooth oval that continues the skull's shape,
        keeping the same angle around the head, so the hair curves around the face instead of hanging in walls.
        """
        side = 1.0 if root.x >= style.part_x else -1.0
        layer = max(0.0, min(1.0, (root.z - (eye.z - 0.06)) / (top - (eye.z - 0.06))))
        gap = style.lift + style.volume * layer           # higher roots lie on top of lower ones
        p = root.copy()
        _, n, _, _ = bvh.find_nearest(p)
        p = p + n * 0.0015
        pts = [p.copy()]
        backness = max(0.0, (p - c).y) / 0.1
        cut_here = cut + style.back_shorter * min(1.0, backness) + rnd.gauss(0, 0.004)
        z_eq = c.z - 0.005                                 # the skull's widest line, about ear-top height
        front, keep_clear = -math.pi / 2, math.radians(58)

        def drape_point(q, rho_min):
            r = q - c
            th = math.atan2(r.y / radii.y, r.x / radii.x)
            df = math.atan2(math.sin(th - front), math.cos(th - front))
            if abs(df) < keep_clear:
                th = front + math.copysign(keep_clear, df if abs(df) > 1e-3 else side)
            rho = max(rho_min, math.hypot(r.x / radii.x, r.y / radii.y))
            return Vector((c.x + math.cos(th) * radii.x * rho, c.y + math.sin(th) * radii.y * rho, q.z)), th, rho

        for k in range(140):                               # phase 1
            if p.z <= z_eq - 0.02:
                break
            loc, n, _, dist = bvh.find_nearest(p)
            rel = p - c
            topness = max(0.0, min(1.0, (p.z - (eye.z + 0.03)) / (top - (eye.z + 0.03) + 1e-6)))
            frontness = max(0.0, -rel.y) / 0.1
            want = Vector((side * 1.2 * topness, -0.25 * frontness * topness, -(0.35 + 0.65 * (1 - topness))))
            if style.fringe and frontness > 0.6 and topness > 0.3:
                want = Vector((side * 0.3, -1.0, -0.6))
            if not style.fringe and rel.y < 0.0 and abs(p.x) < radii.x + 0.004:
                want = Vector((side * 0.8, 0.65, -0.3 * (1 - topness) - 0.05))
            d = want.normalized()
            if dist is not None and dist < 0.03:
                d = (d - n * d.dot(n)).normalized()      # slide along the surface
            p = p + d * style.step
            loc, n, _, dist = bvh.find_nearest(p)
            if dist is not None and dist < gap:
                p = loc + n * gap
            # Over the last few centimetres before the skull's widest line, ease onto the drape surface.
            w = max(0.0, min(1.0, (z_eq + 0.075 - p.z) / 0.095))
            if w > 0:
                target, _, _ = drape_point(p, 1.0 + gap / radii.x)
                w = w * w                                # gentle at first: the bob widens like a dome
                p = p.lerp(target, w)
            pts.append(p.copy())
        # phase 2: drape
        _, theta, rho0 = drape_point(p, 1.0 + gap / radii.x)
        span = max(0.02, z_eq - cut_here)
        z = p.z
        while z > cut_here + style.curl_under:
            z -= style.step
            f = max(0.0, min(1.0, (z_eq - z) / span))
            bulge = style.hang_volume / radii.x * math.sin(math.pi * min(1.0, f * 1.4))   # fullest near the jaw
            theta += rnd.gauss(0, 0.0025)
            rho = (rho0 + bulge) * (1.0 - style.taper * f)
            q = Vector((c.x + math.cos(theta) * radii.x * rho, c.y + math.sin(theta) * radii.y * rho, z))
            loc, n, _, dist = bvh.find_nearest(q)
            if dist is not None and dist < gap:            # jaw and neck must not poke through
                q = loc + n * gap
            pts.append(q)
        p = pts[-1]
        inward = Vector((-(p - c).x, -(p - c).y, 0.0))
        if inward.length > 1e-6:
            inward.normalize()
        for j in range(1, 6):                              # the 'curled under' ends
            p = p + (Vector((0, 0, -1)) * (1 - j / 6) + inward * (j / 6)).normalized() * (style.curl_under / 5)
            pts.append(p.copy())
        return pts


    def crop_strand(root):
        """A short cut: no drape. Length depends on where the root is (long on top, short at the sides and back);
        the top is swept back and to the side of the parting with a little lift, the sides lie down and back."""
        side = 1.0 if root.x >= style.part_x else -1.0
        topness = max(0.0, min(1.0, (root.z - (eye.z + 0.025)) / (top - (eye.z + 0.025) + 1e-6)))
        frontness = max(0.0, -(root - c).y) / 0.1
        length = style.side_len + (style.top_len - style.side_len) * topness ** 1.3 + rnd.gauss(0, 0.003)
        length = max(0.008, length)
        p = root.copy()
        _, n, _, _ = bvh.find_nearest(p)
        p = p + n * 0.0015
        pts = [p.copy()]
        walked = 0.0
        while walked < length:
            loc, n, _, dist = bvh.find_nearest(p)
            t = walked / length
            if topness > 0.25:
                lift = (0.15 + 0.6 * frontness) * (1 - t * 0.4)
                want = Vector((side * 0.45, style.sweep, lift))
            else:
                want = Vector((side * 0.4, 0.35, -1.0))
            d = want.normalized()
            if dist is not None and dist < 0.03 and topness <= 0.25:
                d = (d - n * d.dot(n)).normalized()
            elif dist is not None and dist < 0.012:
                d = ((d - n * d.dot(n)) * 0.8 + n * 0.2 * (1 + frontness)).normalized()
            p = p + d * style.step
            walked += style.step
            loc, n, _, dist = bvh.find_nearest(p)
            gap = style.lift + (style.volume * topness) * (walked / max(length, 1e-6)) ** 0.7
            if dist is not None and dist < gap:
                p = loc + n * gap
            pts.append(p.copy())
        if len(pts) < 4:                                   # very short sides: pad with one more sample
            pts.append(pts[-1] + (pts[-1] - pts[-2]))
        return pts

    make = crop_strand if style.cut == "crop" else strand
    # --- clump guides first, then every strand blends toward its nearest guide toward the tip
    roots = [sample_root() for _ in range(style.strands)]
    guide_roots = [sample_root() for _ in range(style.clumps)]
    guides = [make(r) for r in guide_roots]
    out = []
    for r in roots:
        s = make(r)
        g = min(range(len(guides)), key=lambda i: (guide_roots[i] - r).length_squared)
        gd = guides[g]
        if len(gd) > 2:
            n = len(s)
            for i in range(n):
                t = i / max(1, n - 1)
                gi = min(len(gd) - 1, int(t * (len(gd) - 1)))
                pull = 0.35 * t * t
                s[i] = s[i].lerp(gd[gi] + (r - guide_roots[g]) * (1 - t), pull)
        fz = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.3))) * rnd.uniform(0.0004, 0.0016)
        n = len(s)
        for i in range(n):
            s[i] = s[i] + fz * (i / max(1, n - 1)) ** 1.5
        if len(s) >= 4:
            out.append(s)

    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([len(s) for s in out])
    curves.position_data.foreach_set("vector", [x for s in out for p in s for x in p])
    rad = curves.attributes["radius"] if "radius" in curves.attributes else curves.attributes.new("radius", "FLOAT", "POINT")
    rad.data.foreach_set("value", [style.radius * (1.0 - 0.7 * k / len(s)) for s in out for k in range(len(s))])
    obj = bpy.data.objects.new(name, curves)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True   # new materials ignore their nodes otherwise
    nt = mat.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    h = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    if style.color is not None:
        h.parametrization = "COLOR"
        h.inputs["Color"].default_value = (*style.color, 1.0)
    else:
        h.parametrization = "MELANIN"
        h.inputs["Melanin"].default_value = style.melanin
        h.inputs["Melanin Redness"].default_value = style.redness
    if style.tint is not None and "Tint" in h.inputs:
        h.inputs["Tint"].default_value = (*style.tint, 1.0)
    h.inputs["Roughness"].default_value = 0.3
    h.inputs["Radial Roughness"].default_value = 0.45
    for key, val in (("Random Color", 0.12), ("Random Roughness", 0.15)):
        if key in h.inputs:
            h.inputs[key].default_value = val
    nt.links.new(h.outputs[0], o.inputs["Surface"])
    curves.materials.append(mat)

    # A thin cap on the scalp in the hair's colour, so the parting and gaps read as hair, not as bald skin.
    cap_me = bpy.data.meshes.new(name + "_cap")
    cv, cf = [], []
    for (a, b, d) in scalp:
        m = (a + b + d) / 3
        if m.z < _hairline(eye, c, m, style.fringe, style.hairline_up, style.hairline_exp) + 0.006:   # keep the cap's edge under the hair
            continue
        i = len(cv)
        for q in (a, b, d):
            _, n, _, _ = bvh.find_nearest(q)
            cv.append(q + n * 0.0005)
        cf.append((i, i + 1, i + 2))
    cap_me.from_pydata(cv, [], cf)
    cap = bpy.data.objects.new(name + "_cap", cap_me)
    bpy.context.scene.collection.objects.link(cap)
    cm = bpy.data.materials.new(name + "_cap_mat")
    cm.use_nodes = True   # new materials ignore their nodes otherwise
    b = cm.node_tree.nodes["Principled BSDF"]
    shade = style.cap_shade if style.cap_shade is not None else 0.02 + 0.05 * (1 - style.melanin)
    b.inputs["Base Color"].default_value = (shade * (1 + 0.8 * style.redness), shade * 0.75, shade * 0.5, 1)
    b.inputs["Roughness"].default_value = 0.7
    cap_me.materials.append(cm)
    print("HAIRGEN %d strands, %d clumps, %d scalp triangles" % (len(out), len(guides), len(scalp)))
    return obj
