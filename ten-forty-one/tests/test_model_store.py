#!/usr/bin/env python3
"""Checks for the first-run model download against a small local file (no internet, no 3 GB download).

    python3 tests/test_model_store.py
"""
import hashlib
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import model_store  # noqa: E402

BLOB = os.urandom(3 * 1024 * 1024 + 123)
SHA = hashlib.sha256(BLOB).hexdigest()
served = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        start = 0
        rng = self.headers.get("Range")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
        served.append(start)
        body = BLOB[start:]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


failures = []


def check(cond, what):
    print(("  ok    " if cond else "  FAIL  ") + what)
    if not cond:
        failures.append(what)


def wait(d):
    for _ in range(300):
        if d.state in ("done", "failed"):
            return
        time.sleep(0.05)


srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = "http://127.0.0.1:%d/model.gguf" % srv.server_address[1]

with tempfile.TemporaryDirectory() as tmp:
    dest = os.path.join(tmp, "model.gguf")
    d = model_store.Download(url=url, sha256=SHA, size=len(BLOB), dest=dest)
    d.start()
    wait(d)
    check(d.state == "done", "a fresh download completes (%s)" % (d.error or d.state))
    check(open(dest, "rb").read() == BLOB, "the file matches byte for byte")

    # Resume: leave half a file behind and check only the rest is fetched.
    os.remove(dest)
    with open(dest + ".part", "wb") as f:
        f.write(BLOB[:len(BLOB) // 2])
    served.clear()
    d = model_store.Download(url=url, sha256=SHA, size=len(BLOB), dest=dest)
    d.start()
    wait(d)
    check(d.state == "done" and served == [len(BLOB) // 2], "an interrupted download resumes where it stopped")
    check(open(dest, "rb").read() == BLOB, "and the resumed file is intact")

    # A wrong checksum must never be installed.
    os.remove(dest)
    d = model_store.Download(url=url, sha256="0" * 64, size=len(BLOB), dest=dest)
    d.start()
    wait(d)
    check(d.state == "failed" and not os.path.exists(dest), "a file with the wrong checksum is rejected")
    check(not os.path.exists(dest + ".part"), "and the bad partial file is removed")

print("== platform")
check(model_store.platform_key() in ("linux-x64", "linux-arm64", "windows-x64", "mac-arm64", "mac-x64"), "platform is recognised: " + model_store.platform_key())
check(os.path.isdir(model_store.data_dir()), "the per-user data folder exists: " + model_store.data_dir())

print("\n%s" % ("ALL CHECKS PASSED" if not failures else "%d FAILED" % len(failures)))
sys.exit(1 if failures else 0)
