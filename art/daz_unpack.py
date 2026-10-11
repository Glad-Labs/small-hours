"""Unpack Daz content zips into the shared asset library and say what is in them.

    python3 art/daz_unpack.py ~/Downloads/*.zip            # unpack every Daz zip given (others are skipped)
    python3 art/daz_unpack.py --list ~/Downloads/*.zip     # only report, change nothing

Handles the layouts Daz content comes in: daz3d.com manual downloads (IM000…zip with a Content/ folder and a
Manifest.dsx), and community zips from Renderosity, ShareCG and the like, which put data/, People/, Runtime/ etc. at
the top or under a wrapper folder. Anything outside those library folders (readmes, promo images) is left out.

For each zip it lists the loadable items (.duf presets under People/, Props/, …) and which figure they are for,
read from the files themselves: Genesis 9 items fit the figures art/tfo_daz.py and art/tfo_toon.py use; Genesis 8
items need a Genesis 8 figure.
"""
import gzip
import os
import re
import sys
import zipfile

LIB = "/store/asset-library/daz"
ROOTS = ("data", "People", "Runtime", "Environments", "Props", "Light Presets", "Render Presets", "Scenes",
         "Shader Presets", "Figures", "Camera Presets", "Scripts", "Animals", "Vehicles")
FIGURES = [("Genesis 9", re.compile(r"Genesis ?9", re.I)), ("Genesis 8.1", re.compile(r"Genesis ?8[._]1", re.I)),
           ("Genesis 8", re.compile(r"Genesis ?8", re.I)), ("Genesis 3", re.compile(r"Genesis ?3", re.I)),
           ("Genesis 2", re.compile(r"Genesis ?2", re.I))]


def library_root(name):
    """The part of a zip path below its library root ('People/…'), or None if it is not library content."""
    parts = name.replace("\\", "/").split("/")
    for i, p in enumerate(parts):
        if p in ROOTS and i < len(parts) - 1:
            return "/".join(parts[i:])
    return None


def figure_of(zf, member, rel):
    """Which figure generation an item is for: from its path first, then from what its file references."""
    for label, pat in FIGURES:
        if pat.search(rel):
            return label
    try:
        raw = zf.read(member)[:400000]
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
        text = raw.decode("utf-8", "ignore")
    except Exception:
        return "?"
    hits = {label: len(pat.findall(text)) for label, pat in FIGURES}
    best = max(hits, key=hits.get)
    return best if hits[best] else "not figure-specific"


def handle(path, dry):
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        print("skip (not a zip): %s" % path)
        return
    members = [(m, library_root(m.filename)) for m in zf.infolist() if not m.is_dir()]
    content = [(m, rel) for m, rel in members if rel]
    if not content:
        print("skip (no Daz library folders inside): %s" % os.path.basename(path))
        return
    new = sum(1 for _, rel in content if not os.path.exists(os.path.join(LIB, rel)))
    print("\n== %s: %d library files (%d new), %.0f MB" % (os.path.basename(path), len(content), new,
                                                           sum(m.file_size for m, _ in content) / 1e6))
    items = sorted((rel, m) for m, rel in content if rel.endswith(".duf") and not rel.startswith(("data/", "Runtime/")))
    by_kind = {}
    for rel, m in items:
        kind = rel.split("/")[0] if not rel.startswith("People/") else "/".join(rel.split("/")[1:3])
        by_kind.setdefault(kind, []).append((rel, m))
    for kind, lst in sorted(by_kind.items()):
        print("  %s (%d)" % (kind, len(lst)))
        for rel, m in lst[:25]:
            print("    %-70s %s" % (os.path.basename(rel)[:-4][:70], figure_of(zf, m, rel)))
        if len(lst) > 25:
            print("    … and %d more" % (len(lst) - 25))
    if dry:
        return
    for m, rel in content:
        dest = os.path.join(LIB, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with zf.open(m) as src, open(dest, "wb") as out:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    print("  unpacked into %s" % LIB)


if __name__ == "__main__":
    dry = "--list" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        sys.exit(__doc__)
    for p in paths:
        handle(p, dry)
