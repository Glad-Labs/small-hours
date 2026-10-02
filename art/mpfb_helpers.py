"""Thin helpers around the MPFB Blender add-on (MakeHuman for Blender) for building characters from the library.

MPFB must be installed in Blender (Extensions: MPFB 2) and the asset packs unpacked into the shared library
(art/fetch_assets.py then art/install_mpfb_assets.py). Characters built from the CC0 assets are CC0.
"""
import os

import bpy

import lib

DATA = os.environ.get("MPFB_DATA", "/store/asset-library/mpfb/data")


def enable():
    """Turn the add-on on (a factory-startup Blender has user extensions disabled) and return its services."""
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    from bl_ext.user_default.mpfb.services.faceservice import FaceService
    from bl_ext.user_default.mpfb.services.rigservice import RigService
    return HumanService, TargetService, FaceService, RigService


def path(rel):
    return os.path.join(DATA, rel)


def create_woman(svc, age=0.62, muscle=0.4, weight=0.38, height=0.55, race=None):
    """A female base mesh. Macro values run 0..1; age 0.5 is 25 and 1.0 is 90, so 0.62 is about 41."""
    human, target, *_ = svc
    macros = target.get_default_macro_info_dict()
    macros.update(gender=0.0, age=age, muscle=muscle, weight=weight, proportions=0.5, height=height)
    macros["race"] = race or {"asian": 0.1, "caucasian": 0.8, "african": 0.1}
    # detailed_helpers must stay True: the rig is fitted from the joint helper vertices
    return human.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True,
                              feet_on_ground=True, scale=0.1, macro_detail_dict=macros)


def add(svc, base, rel, kind="Clothes"):
    """Fit a clothes/hair/eyes asset (path relative to the library's MPFB data) onto the character."""
    rel = rel if rel.endswith(".mhclo") else rel + ".mhclo"
    return svc[0].add_mhclo_asset(path(rel), base, asset_type=kind)


def set_skin(svc, base, name):
    svc[0].set_character_skin(path("skins/%s/%s.mhmat" % (name, name)), base, skin_type="ENHANCED_SSS")


def tint_object(obj, hex_colour, strength=1.0):
    """Multiply an asset's base colour (e.g. darken blonde hair to brown). Returns False if no shader was found."""
    for slot in obj.material_slots:
        nt = slot.material.node_tree if slot.material else None
        if not nt:
            continue
        for node in nt.nodes:
            if node.type == "BSDF_PRINCIPLED":
                sock = node.inputs["Base Color"]
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                mix.blend_type = "MULTIPLY"
                mix.inputs["Factor"].default_value = strength
                mix.inputs["B"].default_value = lib.rgb(hex_colour)
                if sock.links:
                    nt.links.new(sock.links[0].from_socket, mix.inputs["A"])
                else:
                    mix.inputs["A"].default_value = sock.default_value
                nt.links.new(mix.outputs["Result"], sock)
                return True
    return False


def assets(base):
    """The fitted clothes, hair, eyes... of a character. MPFB parents them to the rig once one exists, so look
    them up by name ("<character>.<asset>") rather than by parent."""
    return [o for o in bpy.data.objects if o.name.startswith(base.name + ".")]


children = assets   # older name
