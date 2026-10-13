"""Eyes for imported Daz Genesis 9 figures.

The importer leaves Genesis 9's layered iris/sclera shader blank, and the eyeball UVs do not line up with the eye
textures. So each eye gets the texture projected from the front, centred on that eyeball: the left iris sits at
(0.25, 0.75) of the map and the right at (0.75, 0.75) in every Genesis 9 eye texture.

    import dazeyes
    dazeyes.project(eyes_object, "/store/.../G9_Eyes09_D.jpg")                    # standard Genesis 9 eyes
    dazeyes.project(eyes_object, ".../Ergou/Kin/EyesColorD 04.jpg", iris=0.82)    # a character with smaller irises
"""
import bpy

K_STANDARD = 0.11 / 0.0115     # texture units per metre: the standard iris is 0.11 wide on the map, 11.5 mm in life


def _principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def project(eyes, tex, iris=1.0, gaze_down=0.0015):
    """iris: how wide this texture's iris is relative to the standard map (Kin's are 0.82). gaze_down in metres."""
    k = K_STANDARD * iris
    # Measure the eyes where they will render: some characters place them with the skeleton, not in the mesh data.
    bpy.context.view_layer.update()
    ev = eyes.evaluated_get(bpy.context.evaluated_depsgraph_get())
    em = ev.to_mesh()
    posed = [eyes.matrix_world @ v.co for v in em.vertices]
    ev.to_mesh_clear()
    for slot in eyes.material_slots:
        m = slot.material
        if m is None:
            continue
        b = _principled(m)
        if "Moisture" in m.name:
            b.inputs["Alpha"].default_value = 0.0          # the clear wet layer over the eye: reflections only
            b.inputs["Roughness"].default_value = 0.02
            b.inputs["Coat Weight"].default_value = 1.0
            b.inputs["Coat Roughness"].default_value = 0.01
            # Some characters bring a refraction group for this layer instead; it renders milky over the iris.
            out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
            m.node_tree.links.new(b.outputs[0], out.inputs["Surface"])
            for l in list(out.inputs["Volume"].links) + list(out.inputs["Thickness"].links if "Thickness" in out.inputs else []):
                m.node_tree.links.remove(l)
            continue
        idx = [i for i, sl in enumerate(eyes.material_slots) if sl.material == m]
        pts = [posed[vi] for poly in eyes.data.polygons if poly.material_index in idx for vi in poly.vertices]
        if not pts:
            continue
        cx = sum(p.x for p in pts) / len(pts)
        cz = sum(p.z for p in pts) / len(pts)
        nt = m.node_tree
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY_ADD"
        mu.inputs[1].default_value = k; mu.inputs[2].default_value = 0.25 - cx * k
        mv = nt.nodes.new("ShaderNodeMath"); mv.operation = "MULTIPLY_ADD"
        mv.inputs[1].default_value = k; mv.inputs[2].default_value = 0.75 - (cz - gaze_down) * k
        nt.links.new(sep.outputs["X"], mu.inputs[0])
        nt.links.new(sep.outputs["Z"], mv.inputs[0])
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(mu.outputs[0], comb.inputs["X"])
        nt.links.new(mv.outputs[0], comb.inputs["Y"])
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(tex, check_existing=True)
        t.extension = "EXTEND"
        nt.links.new(comb.outputs[0], t.inputs["Vector"])
        for l in list(b.inputs["Base Color"].links):
            nt.links.remove(l)
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.3
        if "Subsurface Weight" in b.inputs:
            b.inputs["Subsurface Weight"].default_value = 0.0
        print("EYES", m.name, "<-", tex.split("/")[-1], "centre x %.4f z %.4f" % (cx, cz))
