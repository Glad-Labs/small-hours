"""Skin effects for Daz Genesis 9 heads, built into the head material's node tree: ageing (creases, folds, eye bags,
a ruddier tone) and makeup (lips, blush, eyeshadow). Everything is anchored to facial landmarks found from the mesh's
bone-weight groups, so it follows whichever face the morphs produced.

    import skinfx
    lm = skinfx.landmarks(body)
    skinfx.age(body, lm, amount=1.0)
    skinfx.makeup(body, lm, amount=1.0)

World space is used for all patterns, so the figure must not be moved or rotated after this (a camera turn is fine).
Left is +x (the character's left), the face looks toward -y, z is up.
"""
import bpy
from mathutils import Vector

WANT = ("l_lipcorner", "r_lipcorner", "lipuppermiddle", "liplowermiddle", "l_nostril", "r_nostril", "l_cheek", "r_cheek",
        "l_eyelidupper", "l_eyelidlower", "l_browinner", "l_browouter", "centerbrow", "chin", "l_squint", "l_infraorbital")


def landmarks(body):
    """Weighted centres of the face's bone-weight groups, in world space."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    names = {vg.index: vg.name for vg in body.vertex_groups}
    acc = {}
    for v in body.data.vertices:
        co = None
        for g in v.groups:
            n = names.get(g.group)
            if n in WANT and g.weight > 0.05:
                if co is None:
                    co = body.matrix_world @ me.vertices[v.index].co
                a = acc.setdefault(n, [Vector((0, 0, 0)), 0.0])
                a[0] += co * g.weight
                a[1] += g.weight
    ev.to_mesh_clear()
    return {n: a[0] / a[1] for n, a in acc.items()}


class _Nodes:
    """Small helpers for building the maths of a mask out of shader nodes."""

    def __init__(self, nt):
        self.nt = nt
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        self.P = geo.outputs["Position"]

    def _in(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        else:
            sock.default_value = v

    def vmath(self, op, a, b=None, scale=None):
        n = self.nt.nodes.new("ShaderNodeVectorMath")
        n.operation = op
        self._in(n.inputs[0], a)
        if b is not None:
            self._in(n.inputs[1], b)
        if scale is not None:
            self._in(n.inputs[3], scale)
        return n.outputs["Value"] if op in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else n.outputs["Vector"]

    def math(self, op, a, b=None, clamp=False):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        self._in(n.inputs[0], a)
        if b is not None:
            self._in(n.inputs[1], b)
        return n.outputs["Value"]

    def mapr(self, v, lo, hi, out_lo=0.0, out_hi=1.0, smooth=True):
        n = self.nt.nodes.new("ShaderNodeMapRange")
        n.data_type = "FLOAT"
        n.interpolation_type = "SMOOTHSTEP" if smooth else "LINEAR"
        n.clamp = True
        self._in(n.inputs[0], v)
        n.inputs[1].default_value, n.inputs[2].default_value = lo, hi
        n.inputs[3].default_value, n.inputs[4].default_value = out_lo, out_hi
        return n.outputs["Result"]

    def jittered(self, amount=0.0035, scale=70.0):
        """The world position nudged up and down by noise, so lines wander like real creases."""
        noise = self.nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = 2.0
        self._in(noise.inputs["Vector"], self.P)
        centred = self.math("SUBTRACT", noise.outputs["Fac"], 0.5)
        dz = self.math("MULTIPLY", centred, amount)
        comb = self.nt.nodes.new("ShaderNodeCombineXYZ")
        self._in(comb.inputs["Z"], dz)
        return self.vmath("ADD", self.P, comb.outputs["Vector"])

    def seg_dist(self, p, a, b, planar=True):
        """Distance from point p to the segment a-b. planar: ignore depth (y), which suits a face seen from the front."""
        a, b = Vector(a), Vector(b)
        ab = b - a
        ap = self.vmath("SUBTRACT", p, tuple(a))
        t = self.math("DIVIDE", self.vmath("DOT_PRODUCT", ap, tuple(ab)), max(ab.length_squared, 1e-9), clamp=True)
        off = self.vmath("SCALE", tuple(ab), scale=t)
        d = self.vmath("SUBTRACT", ap, off)
        if planar:
            d = self.vmath("MULTIPLY", d, (1.0, 0.0, 1.0))
        return self.vmath("LENGTH", d)

    def groove(self, d, width, soft=1.0):
        return self.mapr(d, 0.0, width, 1.0, 0.0, smooth=True) if soft else self.mapr(d, 0.0, width, 1.0, 0.0, False)

    def blob(self, p, centre, radii, sharp=0.0):
        """1 at the centre falling to 0 at the ellipsoid with the given radii. sharp > 0 steepens the edge."""
        d = self.vmath("SUBTRACT", p, tuple(centre))
        d = self.vmath("MULTIPLY", d, tuple(1.0 / r for r in radii))
        length = self.vmath("LENGTH", d)
        return self.mapr(length, sharp, 1.0, 1.0, 0.0)

    def maxof(self, items):
        out = items[0]
        for it in items[1:]:
            out = self.math("MAXIMUM", out, it)
        return out


def _head_material(body):
    for sl in body.material_slots:
        if sl.material and sl.material.name.startswith("Head"):
            return sl.material
    raise RuntimeError("no Head material")


def _tint(nt, colour_in, colour, factor, blend="MIX"):
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = blend
    nt.links.new(colour_in, mix.inputs["A"])
    mix.inputs["B"].default_value = (*colour, 1.0)
    if isinstance(factor, bpy.types.NodeSocket):
        nt.links.new(factor, mix.inputs["Factor"])
    else:
        mix.inputs["Factor"].default_value = factor
    return mix.outputs["Result"]


def _base_color_source(nt):
    bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    return bsdf, bsdf.inputs["Base Color"].links[0].from_socket


def _add_bump(nt, height, strength, distance=0.0008):
    """Insert a bump on top of the existing normal map, for both the principled and the dual-lobe specular."""
    nm = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeNormalMap")
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(nm.outputs["Normal"], bump.inputs["Normal"])
    for l in list(nt.links):
        if l.from_node == nm and l.to_node != bump:
            nt.links.new(bump.outputs["Normal"], l.to_socket)


def age(body, lm, amount=1.0):
    """Lines, folds, bags and a ruddier tone, scaled by amount (1.0 is a man of about 50)."""
    nt = _head_material(body).node_tree
    bsdf, src = _base_color_source(nt)
    nb = _Nodes(nt)
    p = nb.jittered(0.0055, 45.0)

    mid_x = 0.0
    brow_z = lm["centerbrow"].z
    eye_lo = lm["l_eyelidlower"]
    eye_up = lm["l_eyelidupper"]
    outer = lm["l_browouter"]
    nostril = lm["l_nostril"]
    corner = lm.get("l_lipcorner", Vector((0.027, -0.097, lm["lipuppermiddle"].z - 0.006)))
    lip_z = (lm["lipuppermiddle"].z + lm["liplowermiddle"].z) / 2
    corner = Vector((max(corner.x, 0.024), corner.y, lip_z))
    chin = lm["chin"]

    lines = []
    # Forehead: three wandering horizontal lines, shorter toward the temples.
    for i, (dz, half) in enumerate(((0.024, 0.042), (0.037, 0.04), (0.05, 0.034))):
        z = brow_z + dz
        lines.append(nb.groove(nb.seg_dist(p, (-half, 0, z), (half, 0, z + 0.001 * (i - 1))), 0.0034))
    # Between the brows.
    for s in (-1, 1):
        lines.append(nb.math("MULTIPLY", nb.groove(nb.seg_dist(p, (s * 0.0065, 0, brow_z + 0.005), (s * 0.0072, 0, brow_z + 0.016)),
                                                    0.0030), 0.45))
    deep = []
    for s in (-1, 1):
        # Nasolabial folds, wing of the nose to the mouth corner (and a little beyond).
        a = (s * (nostril.x + 0.008), 0, nostril.z - 0.002)
        b = (s * (corner.x + 0.008), 0, corner.z + 0.007)
        deep.append(nb.groove(nb.seg_dist(p, a, b), 0.0052))
        # Marionette lines, from the corner of the mouth down toward the chin.
        deep.append(nb.mapr(nb.seg_dist(p, (s * (corner.x + 0.001), 0, corner.z - 0.002),
                                        (s * (corner.x - 0.002), 0, corner.z - 0.026)), 0.0, 0.0034, 0.7, 0.0))
        # Crow's feet, three lines fanning out from the outer corner of the eye.
        ex, ez = outer.x - 0.001, (eye_up.z + eye_lo.z) / 2
        for dx, dz in ((0.020, 0.008), (0.022, 0.0), (0.019, -0.008)):
            lines.append(nb.groove(nb.seg_dist(p, (s * ex, 0, ez), (s * (ex + dx), 0, ez + dz)), 0.0024))
        # Tear trough: the crease under each eye, and the bag it holds up.
        tz = eye_lo.z - 0.007
        deep.append(nb.groove(nb.seg_dist(p, (s * (eye_lo.x - 0.016), 0, tz + 0.001), (s * (eye_lo.x + 0.014), 0, tz - 0.002)),
                              0.0036))
    creases = nb.maxof(lines + deep)
    # Real creases are broken and uneven: let a slow noise fade them in and out along their length.
    fade = nt.nodes.new("ShaderNodeTexNoise")
    fade.inputs["Scale"].default_value = 26.0
    fade.inputs["Detail"].default_value = 1.0
    nt.links.new(nb.P, fade.inputs["Vector"])
    creases = nb.math("MULTIPLY", creases, nb.mapr(fade.outputs["Fac"], 0.3, 0.62, 0.3, 1.0))

    # Eye bags: a soft mauve-brown shadow under each eye.
    bags = nb.maxof([nb.blob(nb.P, (s * eye_lo.x, eye_lo.y, eye_lo.z - 0.011), (0.017, 1.0, 0.0085)) for s in (-1, 1)])
    # Jowl shadow: along the jaw, either side of the chin.
    jowls = nb.maxof([nb.blob(nb.P, (s * 0.042, chin.y, chin.z + 0.012), (0.014, 1.0, 0.010)) for s in (-1, 1)])

    # Colour, by multiplying (so the skin's own detail shows through): crease shading, bags, jowls, a ruddy mottle.
    out = _tint(nt, src, (0.30, 0.20, 0.18), nb.math("MULTIPLY", creases, 0.85 * amount), "MULTIPLY")
    out = _tint(nt, out, (0.58, 0.44, 0.50), nb.math("MULTIPLY", bags, 0.9 * amount), "MULTIPLY")
    out = _tint(nt, out, (0.62, 0.52, 0.50), nb.math("MULTIPLY", jowls, 0.6 * amount), "MULTIPLY")
    mott = nt.nodes.new("ShaderNodeTexNoise")
    mott.inputs["Scale"].default_value = 11.0
    mott.inputs["Detail"].default_value = 3.0
    nt.links.new(nb.P, mott.inputs["Vector"])
    ruddy = nb.mapr(mott.outputs["Fac"], 0.35, 0.7, 0.0, 0.4 * amount)
    out = _tint(nt, out, (1.25, 0.82, 0.78), ruddy, "MULTIPLY")
    nt.links.new(out, bsdf.inputs["Base Color"])

    # Relief: creases and folds cut into the surface, the bags and jowls stand out a little.
    relief = nb.math("SUBTRACT", nb.math("MULTIPLY", bags, 0.35), creases)
    _add_bump(nt, relief, 0.55 * amount)
    return creases


def makeup(body, lm, amount=1.0, lip=(0.46, 0.08, 0.11), blush=(0.88, 0.30, 0.30), shadow=(0.30, 0.15, 0.14)):
    """Lipstick, blush and eyeshadow, with a little shine on the lips."""
    nt = _head_material(body).node_tree
    bsdf, src = _base_color_source(nt)
    nb = _Nodes(nt)
    p = nb.P
    lip_up, lip_lo = lm["lipuppermiddle"], lm["liplowermiddle"]
    lip_z = (lip_up.z + lip_lo.z) / 2
    corner_x = max(lm["l_lipcorner"].x if "l_lipcorner" in lm else 0.026, 0.022)
    lips = nb.blob(p, (0.0, lip_up.y, lip_z), (corner_x + 0.001, 1.0, 0.0118), sharp=0.35)
    # Only where the skin is already lip-red: the texture draws the lip line, the mask just limits the region.
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(src, sep.inputs["Color"])
    redness = nb.mapr(nb.math("SUBTRACT", sep.outputs["Red"], sep.outputs["Green"]), 0.05, 0.11, 0.0, 1.0)
    lip_mask = nb.math("MULTIPLY", lips, redness)
    cheek = lm["l_cheek"]
    blush_m = nb.maxof([nb.blob(p, (s * (cheek.x - 0.004), cheek.y, cheek.z - 0.006), (0.034, 1.0, 0.024)) for s in (-1, 1)])
    up = lm["l_eyelidupper"]
    lid_m = nb.maxof([nb.blob(p, (s * (up.x + 0.001), up.y, up.z + 0.0045), (0.019, 1.0, 0.0085)) for s in (-1, 1)])

    out = _tint(nt, src, blush, nb.math("MULTIPLY", blush_m, 0.20 * amount))
    out = _tint(nt, out, shadow, nb.math("MULTIPLY", lid_m, 0.34 * amount))
    out = _tint(nt, out, lip, nb.math("MULTIPLY", lip_mask, 0.62 * amount))
    nt.links.new(out, bsdf.inputs["Base Color"])
    return lip_mask


def stubble(body, lm, amount=1.0, colour=(0.55, 0.52, 0.5)):
    """A short grey-flecked beard shadow over the lower face: fine speckle, darkest on the chin, jaw and upper lip,
    absent from the lips themselves, with a slightly raised grain."""
    nt = _head_material(body).node_tree
    bsdf, src = _base_color_source(nt)
    nb = _Nodes(nt)
    p = nb.P
    nostril, chin = lm["l_nostril"], lm["chin"]
    lip_up, lip_lo = lm["lipuppermiddle"], lm["liplowermiddle"]
    # The beard area: below the cheekbones, around and below the mouth, along the jaw, blending out over the cheeks.
    cheek_z = lm["l_cheek"].z
    lower = nb.mapr(nb.vmath("DOT_PRODUCT", p, (0.0, 0.0, 1.0)), chin.z - 0.012, cheek_z + 0.005, 1.0, 0.0)
    wide = nb.mapr(nb.math("ABSOLUTE", nb.vmath("DOT_PRODUCT", p, (1.0, 0.0, 0.0))), 0.052, 0.07, 1.0, 0.0)
    jaw_edge = nb.mapr(nb.vmath("DOT_PRODUCT", p, (0.0, 0.0, 1.0)), chin.z - 0.05, chin.z - 0.014, 0.0, 1.0)
    area = nb.math("MULTIPLY", nb.math("MULTIPLY", lower, wide), jaw_edge)
    # Not on the lips: carve out the mouth.
    lips = nb.blob(p, (0.0, lip_up.y, (lip_up.z + lip_lo.z) / 2), (0.030, 1.0, 0.0105), sharp=0.55)
    area = nb.math("MULTIPLY", area, nb.math("SUBTRACT", 1.0, lips))
    # The speckle itself: each noise cell is a hair. Threshold two scales of noise for a fine, uneven grain.
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 900.0
    grain.inputs["Detail"].default_value = 0.0
    grain.inputs["Roughness"].default_value = 1.0
    nt.links.new(p, grain.inputs["Vector"])
    patch = nt.nodes.new("ShaderNodeTexNoise")
    patch.inputs["Scale"].default_value = 18.0
    nt.links.new(p, patch.inputs["Vector"])
    fleck = nb.mapr(grain.outputs["Fac"], 0.42, 0.58, 0.0, 1.0, smooth=False)
    density = nb.mapr(patch.outputs["Fac"], 0.3, 0.7, 0.55, 1.0)
    hairs = nb.math("MULTIPLY", nb.math("MULTIPLY", fleck, density), area)
    # Under the speckle, a soft shadow so the lower face reads darker overall.
    shadow = nb.math("MULTIPLY", area, 0.22 * amount)
    out = _tint(nt, src, (0.55, 0.45, 0.42), shadow, "MULTIPLY")
    out = _tint(nt, out, colour, nb.math("MULTIPLY", hairs, 0.85 * amount), "MULTIPLY")
    nt.links.new(out, bsdf.inputs["Base Color"])
    _add_bump(nt, nb.math("MULTIPLY", hairs, 1.0), 0.25 * amount, distance=0.0004)
    return area
