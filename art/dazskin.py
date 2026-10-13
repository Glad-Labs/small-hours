"""Fill in Daz skin materials the importer leaves out.

Some characters (EG Kin, and any that use Daz Studio's built-in PBRSkin shader, which content packs do not include)
come in with only the first few of the figure's seven skin materials; the faces of the rest (head, arms, body,
mouth) point at slots that do not exist and render black. This copies a skin material that did come through and
points the copy's texture nodes at the matching region's maps (Head_D_1001, Body_NM_1002, …), which every Genesis 9
character ships under the same naming.

    import dazskin
    dazskin.complete(body_object, "/store/asset-library/daz/Runtime/Textures/Ergou/Kin")
"""
import os
import re

import bpy

# Genesis 9's skin slots in face-index order, with the UDIM tile each region's maps are numbered by.
REGIONS = [("Fingernails", "Nails", 1005), ("Toenails", "Nails", 1005), ("Legs", "Legs", 1003),
           ("Mouth Cavity", "Mouth", 1001), ("Arms", "Arms", 1004), ("Head", "Head", 1001), ("Body", "Body", 1002)]


def _retarget(mat, folder, region, tile):
    """Point every image node of `mat` at `region`'s version of the same map, if the folder has one."""
    for n in mat.node_tree.nodes:                           # node groups are shared between copies: unshare them
        if n.bl_idname == "ShaderNodeGroup" and n.node_tree and any(x.bl_idname == "ShaderNodeTexImage" for x in n.node_tree.nodes):
            n.node_tree = n.node_tree.copy()
    trees = [mat.node_tree] + [n.node_tree for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeGroup"
                               and n.node_tree and any(x.bl_idname == "ShaderNodeTexImage" for x in n.node_tree.nodes)]
    for tree in trees:
      for n in tree.nodes:
        if n.bl_idname != "ShaderNodeTexImage" or not n.image:
            continue
        m = re.match(r"(.*?)([A-Za-z]+)_([A-Z]+)_(\d{4})", os.path.basename(n.image.filepath))
        if not m:
            print("SKIN   keep", region, os.path.basename(n.image.filepath))
            continue
        kind = m.group(3)                                   # D, NM, R, SO, SSS
        for name in os.listdir(folder):
            if re.fullmatch(r"(Genesis9_)?%s_%s_%d\.\w+" % (region, kind, tile), name, re.I):
                cs = n.image.colorspace_settings.name
                print("SKIN   swap", region, os.path.basename(n.image.filepath), "->", name)
                n.image = bpy.data.images.load(os.path.join(folder, name), check_existing=True)
                n.image.colorspace_settings.name = cs
                break
        else:
            print("SKIN   no match", region, kind, tile)


def complete(body, folder):
    have = {sl.material.name.split(".")[0]: sl.material for sl in body.material_slots if sl.material}
    template = have.get("Legs") or next(iter(have.values()))
    for i, (slot, region, tile) in enumerate(REGIONS):
        if i < len(body.material_slots) and body.material_slots[i].material:
            continue
        mat = template.copy()
        mat.name = slot
        _retarget(mat, folder, region, tile)
        while len(body.material_slots) <= i:
            body.data.materials.append(None)
        body.material_slots[i].material = mat
        print("SKIN filled", slot, "from", template.name)
