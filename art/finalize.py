#!/usr/bin/env python3
"""Turn the raw Blender renders in art/out/ into the web-friendly WebP files the game loads.

Renders are large PNGs (the background is 1920x1080); WebP is several times smaller, which matters
for the browser build that a phone has to download. Alpha is kept for the character sprites.
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# (render folder, game images folder): Orchard Street's renders sit in out/, Ten Forty-One's in out/tfo/.
JOBS = [(os.path.join(HERE, "out"), os.path.join(REPO, "orchard-street", "game", "images")),
        (os.path.join(HERE, "out", "tfo"), os.path.join(REPO, "ten-forty-one", "game", "images"))]

for src, dst in JOBS:
    if not os.path.isdir(src):
        continue
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        base, ext = os.path.splitext(name)
        if ext != ".png" or base.endswith("_fast") or "stylised" in base:
            continue
        img = Image.open(os.path.join(src, name))
        out = os.path.join(dst, base + ".webp")
        img.save(out, "WEBP", quality=90 if base.startswith("bg_") else 92, method=6)
        print("%-22s %7.0f KB -> %-40s %6.0f KB" % (name, os.path.getsize(os.path.join(src, name)) / 1024,
                                                  os.path.relpath(out, REPO), os.path.getsize(out) / 1024))
