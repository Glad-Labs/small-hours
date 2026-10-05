#!/usr/bin/env python3
"""Serve the Ten Forty-One web build and its suspects' voices to a phone over Tailscale.

Adapted from orchard-street/tools/serve_web.py. The browser build cannot run a model, so the page
POSTs each question to /api/voice on this server, which runs the same personas, guard and
llama-server as the desktop game. The personas and the model stay on this PC.

    python3 tools/serve_web.py                 # binds to this machine's Tailscale address
    python3 tools/serve_web.py --bind 127.0.0.1 --port 8791   # local testing

It binds to the Tailscale address only, never 0.0.0.0, so the game is reachable from your own
tailnet and not from the LAN or the internet. There is no other authentication: anyone on your
tailnet who can reach the port can play. Do not put it behind `tailscale funnel`.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import voice_ai  # noqa: E402
import voices  # noqa: E402

DEFAULT_PORT = 8781        # Orchard Street keeps 8780
DEFAULT_WEB_ROOT = os.path.join(ROOT, "build", "web")
MAX_BODY = 16 * 1024        # bytes of request body we will read
MAX_TEXT = 500              # characters per question or history line
MAX_HISTORY = 12            # history entries accepted (the model layer keeps the last few)
WAIT_SECONDS = 120          # how long one request may wait for the model


def tailscale_info():
    """(ipv4, dns_name) of this machine on the tailnet, or (None, None)."""
    try:
        out = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=8).stdout
        me = json.loads(out)["Self"]
        ips = [ip for ip in me.get("TailscaleIPs", []) if "." in ip]
        return (ips[0] if ips else None), (me.get("DNSName") or "").rstrip(".") or None
    except Exception:
        return None, None


def parse_request(raw):
    """Validate a POST body. Returns (person, facts, question, history) or raises ValueError(why)."""
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("body is not JSON")
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    person, facts, question = data.get("person"), data.get("facts", []), data.get("question")
    if not isinstance(facts, list) or not voices.valid_request(person, facts):
        raise ValueError("unknown person or fact")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if len(question) > MAX_TEXT:
        raise ValueError("question too long")
    history = data.get("history", [])
    if not isinstance(history, list) or len(history) > MAX_HISTORY:
        raise ValueError("bad history")
    clean = []
    for entry in history:
        if (not isinstance(entry, (list, tuple)) or len(entry) != 2
                or not all(isinstance(x, str) and len(x) <= MAX_TEXT for x in entry)):
            raise ValueError("bad history entry")
        clean.append((entry[0], entry[1]))
    return person, facts, question, clean


class Handler(SimpleHTTPRequestHandler):
    ai = None   # the shared VoiceAI, set in main()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Revalidate every load so a rebuilt game is picked up, without re-downloading unchanged files.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/health":
            return self._json(200, {"status": self.ai.status, "error": self.ai.error})
        super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/voice":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return self._json(400, {"error": "empty body"})
        if length > MAX_BODY:
            return self._json(413, {"error": "body too large"})
        try:
            person, facts, question, history = parse_request(self.rfile.read(length))
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        reply = self.ai.ask(person, facts, question, history)
        deadline = time.time() + WAIT_SECONDS
        while not reply.done and time.time() < deadline:
            time.sleep(0.05)
        if not reply.done:
            return self._json(504, {"error": "model timed out"})
        self._json(200, {"line": reply.line, "source": reply.source,
                         "seconds": round(reply.seconds, 2), "note": reply.note})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bind", help="address to listen on (default: this machine's Tailscale address)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--web-root", default=DEFAULT_WEB_ROOT, help="folder holding the Ren'Py web build")
    args = ap.parse_args()

    ts_ip, dns_name = tailscale_info()
    bind = args.bind or ts_ip
    if not bind:
        sys.exit("Could not find a Tailscale address. Is Tailscale running? "
                 "(Pass --bind 127.0.0.1 to serve this machine only.)")
    if bind in ("0.0.0.0", "::"):
        print("warning: binding to every interface exposes the game to your whole LAN", file=sys.stderr)
    if not os.path.isdir(args.web_root):
        print("note: %s does not exist yet, so only /api/* will work until the web build is there"
              % args.web_root, file=sys.stderr)

    ai = voice_ai.VoiceAI(os.path.join(ROOT, "ai"))
    ai.start()
    Handler.ai = ai
    server = ThreadingHTTPServer((bind, args.port), partial(Handler, directory=args.web_root))
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))

    print("Serving %s" % args.web_root, flush=True)
    print("Open on your phone (Tailscale on):  http://%s:%d/" % (bind, args.port), flush=True)
    if dns_name and bind == ts_ip:
        print("                       or:  http://%s:%d/" % (dns_name, args.port), flush=True)
    print("Model: loading in the background; GET /api/health shows its state. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        ai.stop()


if __name__ == "__main__":
    main()
