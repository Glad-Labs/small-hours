"""Character look experiments: one person, the same pose and framing, rendered in several looks for comparison.

    flatpak run --command=blender org.blender.Blender -b --factory-startup \
        --python /abs/path/art/tfo_lab.py -- --person nell --look baseline|real|toon|paint [--fast]

    baseline  today's sprite pipeline (MakeHuman hair cards, stock skin), with portrait lighting
    real      strand hair grown along the hairstyle, skin pore detail, a soft-focus portrait lens
    toon      cel shading in EEVEE: banded light, flat colour, ink outlines
    paint     the 'real' render, then a Kuwahara filter (flattens detail into brush-like patches)

Writes art/out/lab/<person>_<look>.png (1080x1350 portrait; --fast halves it).
"""
import math
import os
import random
import sys

os.environ["TFO_PEOPLE_IMPORT"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib  # noqa: E402
import tfo_people as tp  # noqa: E402

args = lib.script_args()
fast = "--fast" in args
who = args[args.index("--person") + 1] if "--person" in args else "nell"
look = args[args.index("--look") + 1] if "--look" in args else "real"
pose_name = args[args.index("--pose") + 1] if "--pose" in args else "warm"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "lab")
rnd = random.Random(7)


# --- strand hair -------------------------------------------------------------------------------
def strand_hair(card_obj, melanin=0.6, redness=0.95, per_gap=700, layers=3, thickness=0.012):
    """Grow real strands along a MakeHuman hair shell.

    The shell's UV layout is a grid whose columns run root to tip, so each column of vertices is a strand
    path. Strands are interpolated between neighbouring columns, pushed off the surface in layers to give
    the hair volume, and jittered so they do not look combed by a robot."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = card_obj.evaluated_get(dg).to_mesh()
    mw = card_obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    uvl = bm.loops.layers.uv.active
    uv = {}
    for f in bm.faces:
        for loop in f.loops:
            uv[loop.vert.index] = tuple(loop[uvl].uv)
    # Walk each column from its top vertex down through neighbours with the same u and lower v.
    tops = []
    for v in bm.verts:
        u0, v0 = uv[v.index]
        if not any(abs(uv[e.other_vert(v).index][0] - u0) < 1e-3 and uv[e.other_vert(v).index][1] > v0 + 1e-4
                   for e in v.link_edges):
            tops.append(v)
    columns = []
    for top in tops:
        path, cur = [top], top
        while True:
            u0, v0 = uv[cur.index]
            nxt = [e.other_vert(cur) for e in cur.link_edges
                   if abs(uv[e.other_vert(cur).index][0] - u0) < 1e-3 and uv[e.other_vert(cur).index][1] < uv[cur.index][1] - 1e-4]
            if not nxt:
                break
            cur = min(nxt, key=lambda x: uv[x.index][1] - v0)    # nearest step down
            path.append(cur)
        if len(path) >= 4:
            columns.append((uv[top.index][0], [(mw @ v.co, (mw.to_3x3() @ v.normal).normalized()) for v in path]))
    columns.sort(key=lambda c: c[0])
    # Pair columns with their nearest neighbour (by root position) to fill the gaps between them.
    def resample(col, n):
        out = []
        for i in range(n):
            t = i / (n - 1) * (len(col) - 1)
            a = int(t)
            b = min(a + 1, len(col) - 1)
            f = t - a
            out.append((col[a][0].lerp(col[b][0], f), col[a][1].lerp(col[b][1], f).normalized()))
        return out
    N = 24
    cols = [resample(c, N) for _, c in columns]
    strands = []
    # Fill only between columns that are neighbours in the texture AND close on the head, so no strand
    # ever bridges the face from one side of the parting to the other.
    us = [u for u, _ in columns]
    steps = sorted(b - a for a, b in zip(us, us[1:]) if b - a > 1e-4)
    step = steps[len(steps) // 2] if steps else 0.02
    pairs = []
    for i in range(len(cols)):
        cands = [j for j in range(len(cols)) if 1e-4 < us[j] - us[i] < 2.6 * step]
        cands = [j for j in cands if (cols[i][0][0] - cols[j][0][0]).length < 0.06
                 and (cols[i][-1][0] - cols[j][-1][0]).length < 0.07]
        if cands:
            pairs.append((i, min(cands, key=lambda j: (cols[i][len(cols[i]) // 2][0] - cols[j][len(cols[j]) // 2][0]).length)))
    for i, j in pairs:
        c, d = cols[i], cols[j]
        for _ in range(per_gap):
            t = rnd.random()
            depth = rnd.random() ** 1.5                       # more strands near the surface
            layer_off = depth * thickness
            jit = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 1))) * 0.0012
            tip_len = rnd.uniform(0.88, 1.0)                   # uneven ends
            pts = []
            for k in range(N):
                if k / (N - 1) > tip_len:
                    break
                p = c[k][0].lerp(d[k][0], t)
                n = c[k][1].lerp(d[k][1], t).normalized()
                s_ = k / (N - 1)
                wave = math.sin(s_ * 9.0 + t * 6.0) * 0.0008
                pts.append(p + n * (layer_off + 0.0008) + jit * (0.3 + s_) + n * wave)
            if len(pts) >= 4:
                strands.append(pts)
    print("PAIRS", len(pairs), "of", len(cols) - 1)
    bm.free()
    curves = bpy.data.hair_curves.new("strand_hair")
    curves.add_curves([len(s) for s in strands])
    flat = [x for s in strands for p in s for x in p]
    curves.position_data.foreach_set("vector", flat)
    rad = curves.attributes.new("radius", "FLOAT", "POINT") if "radius" not in curves.attributes else curves.attributes["radius"]
    radii = []
    for s in strands:
        for k in range(len(s)):
            radii.append(0.00009 * (1.0 - 0.6 * k / len(s)))
    rad.data.foreach_set("value", radii)
    obj = bpy.data.objects.new("strand_hair", curves)
    bpy.context.scene.collection.objects.link(obj)
    m = bpy.data.materials.new("hair_strands")
    nt = m.node_tree if m.node_tree else None
    if nt is None:
        m.use_nodes = True
        nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    hb.parametrization = "MELANIN"
    hb.inputs["Melanin"].default_value = melanin
    hb.inputs["Melanin Redness"].default_value = redness
    hb.inputs["Roughness"].default_value = 0.28
    hb.inputs["Radial Roughness"].default_value = 0.45
    if "Random Color" in hb.inputs:
        hb.inputs["Random Color"].default_value = 0.12
    if "Random Roughness" in hb.inputs:
        hb.inputs["Random Roughness"].default_value = 0.15
    nt.links.new(hb.outputs[0], out.inputs["Surface"])
    curves.materials.append(m)
    print("STRANDS", len(strands), "from", len(columns), "columns")
    return obj


# --- skin detail -------------------------------------------------------------------------------
def skin_pores(base):
    """Fine procedural bump on the skin so it catches light like skin and not like wax."""
    for slot in base.material_slots:
        nt = slot.material.node_tree if slot.material else None
        if not nt:
            continue
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            continue
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 900.0
        noise.inputs["Detail"].default_value = 4.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.06
        bump.inputs["Distance"].default_value = 0.0004
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        n_in = bsdf.inputs["Normal"]
        if n_in.links:
            nt.links.new(n_in.links[0].from_socket, bump.inputs["Normal"])
        nt.links.new(bump.outputs["Normal"], n_in)
        if "Coat Weight" in bsdf.inputs:
            bsdf.inputs["Coat Weight"].default_value = 0.05     # a faint oily sheen on the high points
        return


# --- cel shading -------------------------------------------------------------------------------
def toonify(objs):
    """Replace every material with banded EEVEE toon shading that keeps the original colour or texture."""
    for o in objs:
        for slot in o.material_slots:
            m = slot.material
            if not m or not m.node_tree:
                continue
            nt = m.node_tree
            bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if not bsdf:
                continue
            col_src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
            col_val = tuple(bsdf.inputs["Base Color"].default_value)
            alpha_src = bsdf.inputs["Alpha"].links[0].from_socket if bsdf.inputs["Alpha"].links else None
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
            s2r = nt.nodes.new("ShaderNodeShaderToRGB")
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.interpolation = "CONSTANT"
            ramp.color_ramp.elements[0].position = 0.0
            ramp.color_ramp.elements[0].color = (0.55, 0.47, 0.52, 1)
            ramp.color_ramp.elements[1].position = 0.12
            ramp.color_ramp.elements[1].color = (0.74, 0.68, 0.70, 1)
            e = ramp.color_ramp.elements.new(0.42)
            e.color = (0.88, 0.85, 0.84, 1)
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            if col_src:
                nt.links.new(col_src, mul.inputs["A"])
            else:
                mul.inputs["A"].default_value = col_val
            emit = nt.nodes.new("ShaderNodeEmission")
            nt.links.new(diff.outputs[0], s2r.inputs[0])
            nt.links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
            nt.links.new(ramp.outputs["Color"], mul.inputs["B"])
            nt.links.new(mul.outputs["Result"], emit.inputs["Color"])
            final = emit.outputs[0]
            if alpha_src:
                transp = nt.nodes.new("ShaderNodeBsdfTransparent")
                mix = nt.nodes.new("ShaderNodeMixShader")
                nt.links.new(alpha_src, mix.inputs["Fac"])
                nt.links.new(transp.outputs[0], mix.inputs[1])
                nt.links.new(emit.outputs[0], mix.inputs[2])
                final = mix.outputs[0]
            nt.links.new(final, out.inputs["Surface"])


# --- painterly post ----------------------------------------------------------------------------
def kuwahara(path, radius):
    """Classic Kuwahara filter with summed-area tables: each pixel takes the mean of whichever of its four
    neighbouring windows is flattest, which keeps edges and turns texture into brush-like patches."""
    import numpy as np
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    rgb, a = px[..., :3], px[..., 3:]
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    r = radius

    def sat(x):
        s = np.zeros((x.shape[0] + 1, x.shape[1] + 1) + x.shape[2:], dtype=np.float64)
        s[1:, 1:] = np.cumsum(np.cumsum(x, 0), 1)
        return s

    pad = lambda x: np.pad(x, ((r, r), (r, r)) + ((0, 0),) * (x.ndim - 2), mode="edge")
    P, L = pad(rgb), pad(lum)
    S, S2, SL = sat(P), sat(L ** 2), sat(L)
    best_var = np.full((h, w), np.inf)
    out = np.zeros_like(rgb)
    n = (r + 1) ** 2
    for dy, dx in ((0, 0), (0, r), (r, 0), (r, r)):
        y0, x0 = dy, dx
        ys, xs = np.arange(h)[:, None] + y0, np.arange(w)[None, :] + x0

        def box(T):
            return T[ys + r + 1, xs + r + 1] - T[ys, xs + r + 1] - T[ys + r + 1, xs] + T[ys, xs]
        mean_l = box(SL) / n
        var = box(S2) / n - mean_l ** 2
        mean_c = box(S) / n
        better = var < best_var
        best_var = np.where(better, var, best_var)
        out = np.where(better[..., None], mean_c, out)
    px2 = np.concatenate([out.astype(np.float32), a], axis=2).ravel()
    img.pixels[:] = px2.tolist()
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()


# --- portrait camera and lights ----------------------------------------------------------------
def portrait(rig, engine):
    bpy.context.view_layer.update()
    head = rig.matrix_world @ rig.pose.bones["head"].head
    eye = head + Vector((0, 0, 0.09))
    lib.world_gradient("#2a2f44", "#0d1018", strength=0.5)
    lib.light("key", "AREA", (eye.x - 1.1, eye.y - 1.4, eye.z + 0.6), 160, "#ffe0c4", size=1.4, target=tuple(eye))
    lib.light("fill", "AREA", (eye.x + 1.3, eye.y - 1.2, eye.z - 0.1), 35, "#b9c6ff", size=1.6, target=tuple(eye))
    lib.light("rim", "AREA", (eye.x + 0.9, eye.y + 1.1, eye.z + 0.5), 140, "#9fb4ff", size=0.6, target=tuple(eye))
    lib.light("hair", "AREA", (eye.x - 0.4, eye.y + 0.6, eye.z + 1.1), 60, "#ffe9d0", size=0.6, target=tuple(eye))
    cam = lib.camera((eye.x + 0.04, eye.y - 1.25, eye.z + 0.02), (eye.x, eye.y, eye.z - 0.1), lens=85)
    if engine == "CYCLES" and look != "baseline":
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = (cam.location - eye).length
        cam.data.dof.aperture_fstop = 2.8
    w, h = (540, 675) if fast else (1080, 1350)
    sc = bpy.context.scene
    if engine == "CYCLES":
        lib.setup_render(w, h, 96 if fast else 200, transparent=False, exposure=0.1)
        sc.render.threads_mode = "FIXED"
        sc.render.threads = 16
    else:
        sc.render.engine = "BLENDER_EEVEE"
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.image_settings.file_format = "PNG"
        sc.view_settings.view_transform = "Standard"
        sc.render.use_freestyle = True
        sc.render.line_thickness_mode = "ABSOLUTE"
        sc.render.line_thickness = 1.2 if fast else 2.2
        ls = bpy.context.view_layer.freestyle_settings.linesets[0] if bpy.context.view_layer.freestyle_settings.linesets else bpy.context.view_layer.freestyle_settings.linesets.new("lines")
        if ls.linestyle is None:
            ls.linestyle = bpy.data.linestyles.new("ink")
        ls.linestyle.color = (0.16, 0.09, 0.08)
        ls.select_by_visibility = True
        ls.select_by_edge_types = True
        ls.select_silhouette = True
        ls.select_border = False
        ls.select_crease = False
        # Ink the outline of the figure and the hair, not the small face parts (they turn into dotted noise).
        quiet = bpy.data.collections.new("no_ink")
        sc.collection.children.link(quiet)
        for o in bpy.data.objects:
            if any(k in o.name.lower() for k in ("eyebrow", "eyelash", ".high-poly", "teeth", "tongue")):
                quiet.objects.link(o)
        ls.select_by_collection = True
        ls.collection = quiet
        ls.collection_negation = "EXCLUSIVE"
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "%s_%s%s.png" % (who, look, "_fast" if fast else ""))
    lib.render(path)
    return path


if __name__ == "__main__" and os.environ.get("TFO_LAB_FILTER"):
    # Painterly pass on an existing render, without re-rendering: TFO_LAB_FILTER=src.png:dst.png
    import shutil
    src, dst = os.environ["TFO_LAB_FILTER"].split(":")
    shutil.copy(src, dst)
    kuwahara(dst, 3 if fast else 6)
    print("PAINTED", dst)
elif __name__ == "__main__":
    p = tp.PEOPLE[who]
    tp.build(p, p["poses"][pose_name])
    base = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Human") and "." not in o.name)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    hair_cards = next(o for o in bpy.data.objects if o.name.endswith("." + p["hair"]))
    if look in ("real", "paint"):
        strand_hair(hair_cards)
        # Keep the original shell underneath as a dark 'hair cap' so no scalp shows between strands.
        for slot in hair_cards.material_slots:
            tp.recolour(hair_cards, "#2a130a", 0.75)
            break
        skin_pores(base)
    if look == "toon":
        toonify([o for o in bpy.data.objects if o.type == "MESH"])
    path = portrait(rig, "BLENDER_EEVEE" if look == "toon" else "CYCLES")
    if look == "paint":
        kuwahara(path, 3 if fast else 6)
        print("PAINTED", path)
