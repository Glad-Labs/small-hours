"""Materials for Daz card hair (meshes of strips with strand textures), built in Blender instead of converted.

Daz hair shaders put the colour in Iray-only layers (translucency, dual-lobe gloss, top coat), which the
importer cannot translate: the result is white or grey hair. This rebuilds each hair material from the asset's
own maps: the cut-out (opacity) map for the strand edges, a strand texture for light and dark detail, and a colour
we choose.

    import dazhair
    dazhair.recolour(hair_object, "#7a3418", detail="Hair1.jpg")
"""
import os

import bpy

import lib

TEX = "/store/asset-library/daz/Runtime/Textures"


def _image(nt, path, colour=False):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return n


def _find(name):
    for root, _, files in os.walk(TEX):
        for f in files:
            if f.replace("%20", " ").lower() == name.replace("%20", " ").lower():
                return os.path.join(root, f)
    return None


def recolour(ob, colour, cutouts=None, detail=None, folder=None, darken=0.55, rough=0.42):
    """Replace every material on a Daz hair mesh.

    cutouts: {material name fragment: opacity map file name}; read from the material's existing image nodes when
    omitted (the importer does load the cut-out maps even when the colour is lost). detail: a strand texture whose
    brightness modulates the colour (dark roots and gaps, light strands). folder: where to look for the files."""
    def path(name):
        if folder and os.path.exists(os.path.join(folder, name)):
            return os.path.join(folder, name)
        return _find(name)

    base = lib.rgb(colour)
    for sl in ob.material_slots:
        old = sl.material
        if old is None:
            continue
        cut = None
        if cutouts:
            for frag, f in cutouts.items():
                if frag.lower() in old.name.lower():
                    cut = path(f)
        if cut is None and old.node_tree:
            for n in old.node_tree.nodes:      # the importer's cut-out image feeds Alpha somewhere
                if n.bl_idname == "ShaderNodeTexImage" and n.image and any(
                        l.to_socket.name in ("Alpha", "Fac") for l in old.node_tree.links if l.from_node == n):
                    cut = bpy.path.abspath(n.image.filepath)
        m = bpy.data.materials.new(old.name + "_hair")
        m.use_nodes = True
        nt = m.node_tree
        b = nt.nodes["Principled BSDF"]
        b.inputs["Roughness"].default_value = rough
        if "Anisotropic" in b.inputs:
            b.inputs["Anisotropic"].default_value = 0.6
        if "Specular IOR Level" in b.inputs:
            b.inputs["Specular IOR Level"].default_value = 0.35
        col = b.inputs["Base Color"]
        if detail and path(detail):
            d = _image(nt, path(detail))
            ramp = nt.nodes.new("ShaderNodeMapRange")
            ramp.inputs[3].default_value = darken          # darkest strand: this share of the colour
            nt.links.new(d.outputs["Color"], ramp.inputs[0])
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            mul.inputs["A"].default_value = base
            gray = nt.nodes.new("ShaderNodeCombineColor")
            for ch in ("Red", "Green", "Blue"):
                nt.links.new(ramp.outputs[0], gray.inputs[ch])
            nt.links.new(gray.outputs[0], mul.inputs["B"])
            nt.links.new(mul.outputs["Result"], col)
        else:
            col.default_value = base
        if cut and os.path.exists(cut):
            c = _image(nt, cut)
            nt.links.new(c.outputs["Color"], b.inputs["Alpha"])
            if hasattr(m, "surface_render_method"):
                m.surface_render_method = "DITHERED"
        sl.material = m
        print("HAIRMAT", old.name, "cutout", os.path.basename(cut) if cut else None)
