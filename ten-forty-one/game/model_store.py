"""Where the voice model and the model server live on a player's machine, and fetching the model.

Desktop only (it uses threads and sockets); excluded from the browser build like voice_ai.py.

The game ships the small llama-server for each platform inside ai/bin/<platform>/, but not the 3.2 GB model.
On first run the player is asked whether to download it from Google's official release on Hugging Face
(Gemma 4 E2B QAT q4_0, Apache-2.0, public, no sign-in). The download resumes after interruptions and is
checked against Google's published SHA-256 before it is used. A model file placed by hand in ai/models/ or in
the data folder works too, so a "full" offline package can simply include it.
"""
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

MODEL_FILE = "gemma-4-E2B_q4_0-it.gguf"
MODEL_URL = "https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf/resolve/main/" + MODEL_FILE
MODEL_SHA256 = "fa401b55b07ee70a54c6dae3903c783a6e65064312529ea57175cb5f8dec6634"
MODEL_SIZE = 3349516256
MODEL_CREDIT = "Gemma 4 E2B (QAT q4_0) by Google, Apache License 2.0"

UA = {"User-Agent": "TenFortyOne-game/0.1 (first-run model download)"}


def data_dir():
    """A per-user folder the game can always write to (the install folder may be read-only, e.g. on macOS)."""
    if sys.platform.startswith("win"):
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    elif sys.platform == "darwin":
        root = os.path.expanduser("~/Library/Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(root, "TenFortyOne")
    os.makedirs(path, exist_ok=True)
    return path


def platform_key():
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if sys.platform.startswith("win"):
        return "windows-x64"
    if sys.platform == "darwin":
        return "mac-arm64" if arm else "mac-x64"
    return "linux-arm64" if arm else "linux-x64"


def server_binary(ai_dir):
    """The llama-server for this platform: ai/bin/<platform>/, then the dev link ai/bin/llama-server, then PATH."""
    exe = "llama-server.exe" if sys.platform.startswith("win") else "llama-server"
    for p in (os.path.join(ai_dir, "bin", platform_key(), exe), os.path.join(ai_dir, "bin", exe)):
        if os.path.exists(p):
            return p
    return shutil.which("llama-server")


# Names of graphics devices that share system memory or emulate a GPU in software: slower than the CPU path for
# this model, so they are never chosen even though they report lots of "free" memory.
_INTEGRATED = re.compile(r"llvmpipe|swiftshader|lavapipe|ryzen|radeon\(tm\) graphics|radeon graphics|vega \d+ graphics|"
                         r"intel\(r\) (uhd|hd|iris)|\bintel\b.*graphics|microsoft basic", re.I)
_DEVICE_LINE = re.compile(r"^\s*(\w+\d+):\s*(.*?)\s*\((\d+) MiB,\s*(\d+) MiB free\)")
NEEDS_MIB = 4200        # model weights plus room for the context


def pick_device(binary):
    """The one GPU to run on, as a llama.cpp device name (e.g. "Vulkan0", "MTL0"), or None for the CPU.

    llama.cpp otherwise spreads layers over every device it finds, and on a laptop that pairs built-in and
    dedicated graphics (or a PC with a busy second card) that is slower than using one good GPU."""
    try:
        out = subprocess.run([binary, "--list-devices"], capture_output=True, text=True, timeout=60,
                             **_no_window()).stdout
    except Exception:
        return None
    best = None
    for line in out.splitlines():
        m = _DEVICE_LINE.match(line)
        if not m:
            continue
        name, label, total, free = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        if name.upper().startswith("MTL") or name.upper().startswith("METAL"):
            return name                     # Apple Silicon: unified memory, always the right choice
        if _INTEGRATED.search(label) or free < NEEDS_MIB:
            continue
        if best is None or free > best[1]:
            best = (name, free)
    return best[0] if best else None


def _no_window():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def find_model(ai_dir):
    """Path of a usable model, or None. Shipped or hand-placed copies win over the download location."""
    for p in (os.path.join(ai_dir, "models", "suspect.gguf"),        # developer link
              os.path.join(ai_dir, "models", MODEL_FILE),           # a "full" package
              os.path.join(data_dir(), MODEL_FILE)):                 # the first-run download
        if os.path.exists(p) and os.path.getsize(p) == MODEL_SIZE:
            return p
    return None


class Download:
    """Fetch the model in the background. Poll .state: idle, running, verifying, done or failed."""

    def __init__(self, url=MODEL_URL, sha256=MODEL_SHA256, size=MODEL_SIZE, dest=None):
        self.url, self.sha256, self.size = url, sha256, size
        self.dest = dest or os.path.join(data_dir(), MODEL_FILE)
        self.part = self.dest + ".part"
        self.state = "idle"
        self.done_bytes = 0
        self.error = ""
        self._stop = False

    @property
    def fraction(self):
        return min(1.0, self.done_bytes / float(self.size)) if self.size else 0.0

    def start(self):
        if self.state in ("running", "verifying", "done"):
            return
        self.state, self.error, self._stop = "running", "", False
        threading.Thread(target=self._run, daemon=True, name="model-download").start()

    def cancel(self):
        self._stop = True

    def _run(self):
        try:
            for attempt in range(6):
                try:
                    self._fetch()
                    break
                except (OSError, ValueError) as e:      # dropped connection: resume from where we were
                    if self._stop or attempt == 5:
                        raise
                    self.error = "retrying: %s" % e
                    time.sleep(2 + attempt * 3)
            if self._stop:
                self.state = "idle"
                return
            self.state = "verifying"
            h = hashlib.sha256()
            with open(self.part, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 22), b""):
                    h.update(chunk)
            if h.hexdigest() != self.sha256:
                os.remove(self.part)
                raise ValueError("the downloaded file failed its checksum; please try again")
            os.replace(self.part, self.dest)
            self.state = "done"
        except Exception as e:
            self.error = "%s: %s" % (type(e).__name__, e)
            self.state = "failed"

    def _fetch(self):
        have = os.path.getsize(self.part) if os.path.exists(self.part) else 0
        if have > self.size:
            os.remove(self.part)
            have = 0
        self.done_bytes = have
        if have == self.size:
            return
        req = urllib.request.Request(self.url, headers=dict(UA, Range="bytes=%d-" % have))
        with urllib.request.urlopen(req, timeout=60) as r, open(self.part, "ab" if have else "wb") as out:
            if have and r.status != 206:            # server ignored the range: start over
                out.seek(0)
                out.truncate()
                self.done_bytes = 0
            while not self._stop:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                self.done_bytes += len(chunk)
        if not self._stop and self.done_bytes != self.size:
            raise ValueError("connection closed early (%d of %d bytes)" % (self.done_bytes, self.size))
