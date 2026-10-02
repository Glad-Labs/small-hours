#!/usr/bin/env python3
"""Download free 3D assets into a shared library that every project can use.

    python3 art/fetch_assets.py --models 2k --hdris 2k --textures 1k --mpfb all
    python3 art/fetch_assets.py --dry-run --models 2k            # only report what would be fetched

Sources (all free, see LICENSES.md written into the library):
  * Poly Haven (polyhaven.com): models, HDRIs and textures, all CC0. Uses their public API.
  * MakeHuman / MPFB asset packs (static.makehumancommunity.org): clothes, hair, skins, poses and face
    rigs for the MPFB Blender add-on. Each pack is CC0 or CC-BY; CC-BY packs are kept in their own folder
    because a game that ships them must credit the author.

The library defaults to /store/asset-library (override with ASSET_LIBRARY or --library). The script is
resumable: files that already exist with the right checksum are skipped. Poly Haven publishes an MD5 for
every file and it is checked; MPFB packs have no published checksums, so each zip is tested for integrity.
Downloads run four at a time to stay polite to the free services that host these.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile

UA = {"User-Agent": "asset-library fetch script (personal use; contact: mattg@gladlabs.io)"}
PH_API = "https://api.polyhaven.com"
MH_BASE = "https://static.makehumancommunity.org"
WORKERS = 4


def get_json(url, tries=4):
    for i in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40))
        except Exception:
            time.sleep(1 + i)
    return None


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest, md5=None, size=None):
    """Fetch url to dest unless it is already there and valid. Returns 'ok', 'skipped' or an error string."""
    if os.path.exists(dest):
        if md5 and md5_of(dest) == md5:
            return "skipped"
        if not md5 and size and os.path.getsize(dest) == size:
            return "skipped"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = "%s.part%d" % (dest, os.getpid())      # per-process name: two downloaders never share a temp file
    err = "unknown"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r, open(tmp, "wb") as out:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            if md5 and md5_of(tmp) != md5:
                err = "checksum mismatch"
                continue
            os.replace(tmp, dest)
            return "ok"
        except Exception as e:  # network hiccup: wait and retry
            err = "%s: %s" % (type(e).__name__, e)
            time.sleep(2 + attempt * 3)
    if os.path.exists(tmp):
        os.remove(tmp)
    return "FAILED " + err


def run_jobs(jobs, label):
    """jobs: list of (url, dest, md5, size). Runs them in parallel with a progress line."""
    done = ok = skipped = 0
    failed = []
    total_bytes = sum(j[3] or 0 for j in jobs)
    t0 = time.time()
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(download, *j): j for j in jobs}
        for fu in cf.as_completed(futs):
            res = fu.result()
            done += 1
            if res == "ok":
                ok += 1
            elif res == "skipped":
                skipped += 1
            else:
                failed.append((futs[fu][1], res))
            if done % 25 == 0 or done == len(jobs):
                print("  %s: %d/%d files (%d new, %d already there, %d failed) %.0fs" %
                      (label, done, len(jobs), ok, skipped, len(failed), time.time() - t0), flush=True)
    for dest, why in failed[:10]:
        print("  FAILED", dest, why, flush=True)
    return failed, total_bytes


# ---- Poly Haven ----------------------------------------------------------------------------
def polyhaven_jobs(lib, kind, res):
    assets = get_json("%s/assets?t=%s" % (PH_API, kind)) or {}
    print("Poly Haven %s: %d assets at %s" % (kind, len(assets), res), flush=True)
    index_path = os.path.join(lib, "polyhaven", "index.json")
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    jobs = []
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        files_all = dict(zip(assets, ex.map(lambda s: get_json("%s/files/%s" % (PH_API, s)), assets)))
    for slug, meta in assets.items():
        f = files_all.get(slug)
        if not f:
            print("  no file listing for", slug, flush=True)
            continue
        index[slug] = {"type": kind, "name": meta.get("name"), "categories": meta.get("categories", []),
                       "tags": meta.get("tags", []), "authors": list(meta.get("authors", {})),
                       "resolution": res, "license": "CC0"}
        if kind == "hdris":
            h = (f.get("hdri", {}).get(res) or {}).get("hdr")
            if h:
                jobs.append((h["url"], os.path.join(lib, "polyhaven", "hdris", "%s_%s.hdr" % (slug, res)), h.get("md5"), h.get("size")))
            continue
        b = (f.get("blend", {}).get(res) or {}).get("blend")        # models and textures: a .blend plus its images
        if not b:
            continue
        root = os.path.join(lib, "polyhaven", kind, slug)
        jobs.append((b["url"], os.path.join(root, "%s_%s.blend" % (slug, res)), b.get("md5"), b.get("size")))
        for rel, inc in b.get("include", {}).items():
            jobs.append((inc["url"], os.path.join(root, rel), inc.get("md5"), inc.get("size")))
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    json.dump(index, open(index_path, "w"), indent=1, sort_keys=True)
    return jobs


# ---- MakeHuman / MPFB asset packs ----------------------------------------------------------
def mpfb_jobs(lib, which, only=None):
    html = urllib.request.urlopen(urllib.request.Request(MH_BASE + "/assets/assetpacks.html", headers=UA), timeout=40).read().decode("utf8", "ignore")
    names = sorted(set(re.findall(r"/assets/assetpacks/([a-z0-9_]+)\.html", html)) - {"faq", "index", "release_20221122"})
    jobs, manifest = [], {}
    for n in names:
        if only and n not in only:
            continue
        page = urllib.request.urlopen(urllib.request.Request("%s/assets/assetpacks/%s.html" % (MH_BASE, n), headers=UA), timeout=40).read().decode("utf8", "ignore")
        zips = re.findall(r'href="([^"]+\.zip)"', page)
        if not zips:
            continue
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
        lic = sorted({m.upper() for m in re.findall(r"(CC0|CC-BY)", text, re.I)})
        folder = "functional" if "/functional/" in zips[0] else ("cc0" if lic == ["CC0"] else ("cc-by" if "CC-BY" in lic else "other"))
        if which == "cc0" and folder not in ("cc0", "functional"):
            continue
        size = None
        try:
            size = int(urllib.request.urlopen(urllib.request.Request(zips[0], method="HEAD", headers=UA), timeout=30).headers.get("Content-Length", 0)) or None
        except Exception:
            pass
        manifest[n] = {"license": lic or ["unspecified"], "url": zips[0], "folder": folder, "page": "%s/assets/assetpacks/%s.html" % (MH_BASE, n)}
        jobs.append((zips[0], os.path.join(lib, "mpfb", "asset_packs", folder, os.path.basename(zips[0])), None, size))
    os.makedirs(os.path.join(lib, "mpfb"), exist_ok=True)
    if not only:
        json.dump(manifest, open(os.path.join(lib, "mpfb", "asset_packs.json"), "w"), indent=1, sort_keys=True)
    print("MPFB asset packs: %d packs" % len(jobs), flush=True)
    return jobs


def verify_zips(lib):
    bad = []
    for dp, _, fs in os.walk(os.path.join(lib, "mpfb", "asset_packs")):
        for fn in fs:
            if fn.endswith(".zip"):
                try:
                    with zipfile.ZipFile(os.path.join(dp, fn)) as z:
                        if z.testzip() is not None:
                            bad.append(fn)
                except zipfile.BadZipFile:
                    bad.append(fn)
    print("MPFB zip integrity: %s" % ("all OK" if not bad else "BAD: %s" % bad), flush=True)
    return bad


LICENSES = """# Asset library licences

Everything here is free to use. Check the folder before shipping a game:

* `polyhaven/` is CC0 (https://polyhaven.com/license): any use, no attribution needed. Supporting them on
  Patreon is appreciated and worth doing if these assets help you earn money.
* `mpfb/asset_packs/cc0/` is CC0: any use, no attribution needed.
* `mpfb/asset_packs/cc-by/` is CC-BY: you may use it commercially, but a game that ships these assets must
  credit the author named on the pack's page (see `mpfb/asset_packs.json` for the page link of each pack).
* `mpfb/asset_packs/functional/` holds MPFB's face-rig and hair-editor helpers.
* `tools/` holds the MPFB Blender add-on (GPL-3.0-or-later). The characters it exports are not covered by the
  add-on's GPL; MakeHuman's own core assets are CC0.
* Characters made with MPFB from the CC0 assets are CC0 as well.

`polyhaven/index.json` lists every Poly Haven asset with its categories and tags, for searching.
Fetched by art/fetch_assets.py in the ai-interrogation repository.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default=os.environ.get("ASSET_LIBRARY", "/store/asset-library"))
    ap.add_argument("--models", metavar="RES", help="Poly Haven models at 1k/2k/4k")
    ap.add_argument("--hdris", metavar="RES", help="Poly Haven HDRIs at 1k/2k/4k")
    ap.add_argument("--textures", metavar="RES", help="Poly Haven textures at 1k/2k/4k")
    ap.add_argument("--mpfb", choices=["all", "cc0"], help="MPFB asset packs: all, or CC0 only")
    ap.add_argument("--packs", metavar="NAMES", help="only these MPFB packs (comma-separated); implies --mpfb all")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    lib = a.library
    os.makedirs(lib, exist_ok=True)
    open(os.path.join(lib, "LICENSES.md"), "w").write(LICENSES)

    plans = []
    for kind, res in (("models", a.models), ("hdris", a.hdris), ("textures", a.textures)):
        if res:
            plans.append(("polyhaven " + kind, polyhaven_jobs(lib, kind, res)))
    if a.packs:
        a.mpfb = a.mpfb or "all"
    if a.mpfb:
        plans.append(("mpfb packs", mpfb_jobs(lib, a.mpfb, set(a.packs.split(",")) if a.packs else None)))
    all_failed = []
    for label, jobs in plans:
        gb = sum(j[3] or 0 for j in jobs) / 1e9
        print("%s: %d files, %.1f GB" % (label, len(jobs), gb), flush=True)
        if a.dry_run:
            continue
        failed, _ = run_jobs(jobs, label)
        all_failed += failed
    if a.mpfb and not a.dry_run:
        verify_zips(lib)
    print("DONE. %d failed downloads (re-run the same command to retry them)." % len(all_failed) if not a.dry_run else "Dry run complete.", flush=True)
    return 1 if all_failed else 0


if __name__ == "__main__":
    sys.exit(main())
