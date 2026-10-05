#!/usr/bin/env python3
"""Download the official llama.cpp server builds the game ships with, into ai/bin/<platform>/.

    python3 tools/fetch_llama.py            # all platforms
    python3 tools/fetch_llama.py linux-x64  # one platform

Pinned to one llama.cpp release so every package is built from the same server. Each archive is checked
against the SHA-256 digest GitHub publishes for it before anything is unpacked. llama.cpp is MIT-licensed;
its licence file is kept next to each binary. The binaries are not committed to git (see .gitignore).
"""
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
import urllib.request
import zipfile

RELEASE = "b11401"
ASSETS = {
    "windows-x64": "llama-%s-bin-win-vulkan-x64.zip" % RELEASE,
    "linux-x64": "llama-%s-bin-ubuntu-vulkan-x64.tar.gz" % RELEASE,
    "mac-arm64": "llama-%s-bin-macos-arm64.tar.gz" % RELEASE,
    "mac-x64": "llama-%s-bin-macos-x64.tar.gz" % RELEASE,
}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "TenFortyOne build script"}


def release_digests():
    url = "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/" + RELEASE
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
    return {a["name"]: (a["browser_download_url"], (a.get("digest") or "").replace("sha256:", "")) for a in data["assets"]}


def unpack(blob, name, dest):
    """Extract the archive flat into dest (the release archives keep everything in one folder)."""
    tmp = dest + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    if name.endswith(".zip"):
        zipfile.ZipFile(io.BytesIO(blob)).extractall(tmp)
    else:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
            t.extractall(tmp, filter="data")
    # Flatten a single top-level folder if there is one.
    entries = os.listdir(tmp)
    src = os.path.join(tmp, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])) else tmp
    shutil.rmtree(dest, ignore_errors=True)
    shutil.move(src, dest)
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    wanted = sys.argv[1:] or list(ASSETS)
    digests = release_digests()
    for plat in wanted:
        name = ASSETS[plat]
        url, digest = digests[name]
        print("%-12s %s" % (plat, name), flush=True)
        blob = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        got = hashlib.sha256(blob).hexdigest()
        if not digest:
            sys.exit("no published digest for %s; refusing to install it" % name)
        if got != digest:
            sys.exit("checksum mismatch for %s" % name)
        dest = os.path.join(ROOT, "ai", "bin", plat)
        unpack(blob, name, dest)
        exe = os.path.join(dest, "llama-server.exe" if plat.startswith("windows") else "llama-server")
        if not os.path.exists(exe):
            sys.exit("llama-server missing from %s" % name)
        if not plat.startswith("windows"):
            os.chmod(exe, 0o755)
        print("             %.1f MB, sha256 ok, -> %s" % (len(blob) / 1e6, os.path.relpath(dest, ROOT)), flush=True)


if __name__ == "__main__":
    main()
