"""Composite character sprites onto a game background at the positions script.rpy uses, to judge them in context.

    python3 comp.py out.png bg_hall webb:out/tfo_daz/webb_calm_fast.png@815 nell:out/tfo_daz/nell_warm_fast.png@1110
"""
import sys

from PIL import Image

out, bg_name, *chars = sys.argv[1:]
bg = Image.open("../ten-forty-one/game/images/%s.webp" % bg_name).convert("RGB")
for spec in chars:
    _, rest = spec.split(":", 1)
    path, x = rest.split("@")
    im = Image.open(path).convert("RGBA")
    if im.size != (525, 700):
        im = im.resize((525, 700), Image.LANCZOS)
    bg.paste(im, (int(x) - 262, 30), im)
bg.save(out)
print("saved", out, bg.size)
