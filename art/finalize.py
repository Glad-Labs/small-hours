#!/usr/bin/env python3
"""Turn the raw Blender renders in art/out/ into the web-friendly WebP files the game loads.

Renders are large PNGs (the background is 1920x1080); WebP is several times smaller, which matters
for the browser build that a phone has to download. Alpha is kept for the character sprites.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "out")
DST = os.path.join(os.path.dirname(HERE), "orchard-street", "game", "images")
os.makedirs(DST, exist_ok=True)

for name in sorted(os.listdir(SRC)):
    base, ext = os.path.splitext(name)
    if ext != ".png" or base.endswith("_fast"):
        continue
    img = Image.open(os.path.join(SRC, name))
    out = os.path.join(DST, base + ".webp")
    img.save(out, "WEBP", quality=90 if base.startswith("bg_") else 92, method=6)
    print("%-22s %7.0f KB -> %-24s %6.0f KB" % (name, os.path.getsize(os.path.join(SRC, name)) / 1024,
                                              os.path.basename(out), os.path.getsize(out) / 1024))
