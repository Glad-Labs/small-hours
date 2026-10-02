#!/usr/bin/env python3
"""Extract downloaded MPFB asset packs into the folder the Blender add-on reads them from.

MPFB looks for clothes, hair, skins, targets and so on under its user data directory, which Blender keeps
on the system drive. This points that directory at the shared asset library (a symlink) and extracts every
complete pack zip into it. Safe to re-run: packs already installed are skipped, and zips that are still
downloading (or fail an integrity test) are left alone.
"""
import json
import os
import sys
import zipfile

LIB = os.environ.get("ASSET_LIBRARY", "/store/asset-library")
PACKS = os.path.join(LIB, "mpfb", "asset_packs")
DATA = os.path.join(LIB, "mpfb", "data")
BLENDER_MPFB = os.path.expanduser("~/.var/app/org.blender.Blender/config/blender/5.2/extensions/.user/user_default/mpfb")
STATE = os.path.join(LIB, "mpfb", "installed.json")


def link_data_dir():
    os.makedirs(DATA, exist_ok=True)
    target = os.path.join(BLENDER_MPFB, "data")
    if os.path.islink(target):
        return
    if os.path.isdir(target):
        if os.listdir(target):
            sys.exit("%s already has files; move them aside first" % target)
        os.rmdir(target)
    os.makedirs(BLENDER_MPFB, exist_ok=True)
    os.symlink(DATA, target)
    print("linked", target, "->", DATA)


def main():
    link_data_dir()
    done = json.load(open(STATE)) if os.path.exists(STATE) else {}
    added = 0
    for folder in ("functional", "cc0", "cc-by", "other"):
        d = os.path.join(PACKS, folder)
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not fn.endswith(".zip") or fn in done:
                continue
            path = os.path.join(d, fn)
            try:
                with zipfile.ZipFile(path) as z:
                    if z.testzip() is not None:
                        print("  corrupt, skipped:", fn)
                        continue
                    z.extractall(DATA)
            except zipfile.BadZipFile:
                print("  not a complete zip yet, skipped:", fn)
                continue
            done[fn] = folder
            added += 1
            print("  installed %-34s (%s)" % (fn, folder))
    json.dump(done, open(STATE, "w"), indent=1, sort_keys=True)
    print("%d new packs installed, %d in total" % (added, len(done)))


if __name__ == "__main__":
    main()
