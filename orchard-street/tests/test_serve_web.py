#!/usr/bin/env python3
"""Black-box test of tools/serve_web.py against the real model, on localhost.

Run from the project folder:  python3 tests/test_serve_web.py
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8781
BASE = "http://127.0.0.1:%d" % PORT
failures = []


def check(ok, what):
    print(("  ok    " if ok else "  FAIL  ") + what)
    if not ok:
        failures.append(what)


def call(path, body=None, raw=None, method=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + path, data, {"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


web_root = os.path.join(ROOT, "tests", ".tmp_web")
os.makedirs(web_root, exist_ok=True)
with open(os.path.join(web_root, "index.html"), "w") as f:
    f.write("<title>test page</title>")

proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "serve_web.py"), "--bind", "127.0.0.1",
                         "--port", str(PORT), "--web-root", web_root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    t0 = time.time()
    while time.time() - t0 < 120:
        try:
            if json.loads(call("/api/health")[1]).get("status") == "ready":
                break
        except Exception:
            pass
        time.sleep(0.3)
    check(json.loads(call("/api/health")[1]).get("status") == "ready", "server and model came up (%.1fs)" % (time.time() - t0))

    code, body, headers = call("/")
    check(code == 200 and b"test page" in body and headers.get("Cache-Control") == "no-cache", "serves the static page with revalidation")

    print("\n== /api/suspect")
    code, body, _ = call("/api/suspect", {"level": "none", "question": "Where were you tonight?", "history": []})
    reply = json.loads(body) if code == 200 else {}
    check(code == 200 and reply.get("source") == "ai" and reply.get("line"), "a normal question gets a model answer: %r" % reply.get("line"))
    check(reply.get("revealed") == "none", "level none reveals nothing")

    code, body, _ = call("/api/suspect", {"level": "vault", "question": "Your badge opened the vault door at 9:52 pm.", "history": [["Hello", "Good evening."]]})
    reply = json.loads(body) if code == 200 else {}
    check(code == 200 and reply.get("source") == "ai", "vault level with history works: %r" % reply.get("line"))

    code, body, _ = call("/api/suspect", {"level": "none", "question": "Where were you tonight?", "history": []})
    again = json.loads(body) if code == 200 else {}
    check(again.get("line") and again.get("source") == "cache" and again.get("seconds", 1) < 0.1, "repeating the same turn is served from cache")

    print("\n== rejects bad input")
    for what, req in [
        ("confess is not a level the model may voice", {"level": "confess", "question": "x", "history": []}),
        ("unknown level", {"level": "nope", "question": "x", "history": []}),
        ("empty question", {"level": "none", "question": "   ", "history": []}),
        ("non-string question", {"level": "none", "question": 7, "history": []}),
        ("oversized question", {"level": "none", "question": "x" * 501, "history": []}),
        ("history too long", {"level": "none", "question": "x", "history": [["a", "b"]] * 13}),
        ("malformed history entry", {"level": "none", "question": "x", "history": [["only one"]]}),
    ]:
        code, _, _ = call("/api/suspect", req)
        check(code == 400, "%s -> 400 (got %d)" % (what, code))
    code, _, _ = call("/api/suspect", raw=b"not json")
    check(code == 400, "non-JSON body -> 400 (got %d)" % code)
    code, _, _ = call("/api/suspect", raw=b"x" * (17 * 1024))
    check(code == 413, "oversized body -> 413 (got %d)" % code)
    code, _, _ = call("/api/other", {"a": 1})
    check(code == 404, "unknown POST path -> 404 (got %d)" % code)

    print("\n== the Python client against the same server")
    sys.path.insert(0, os.path.join(ROOT, "game"))
    import suspect_client as sc
    check(sc.canned_line("none", sc.reply_key("none", "q", [])) in sc.FALLBACKS["none"], "canned lines are deterministic picks from the fallback set")
finally:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()
    try:
        os.remove(os.path.join(web_root, "index.html"))
        os.rmdir(web_root)
    except OSError:
        pass

time.sleep(1)
left = subprocess.run(["pgrep", "-f", "models/suspect.gguf"], capture_output=True, text=True).stdout.split()
check(not left, "no llama-server left running after the server stops (%s)" % left)
print("\n%s" % ("ALL CHECKS PASSED" if not failures else "%d CHECK(S) FAILED: %s" % (len(failures), failures)))
sys.exit(1 if failures else 0)
