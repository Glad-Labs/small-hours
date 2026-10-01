"""The parts of the suspect layer that must run everywhere, including Ren'Py's browser build.

Browsers have no threads, sockets or subprocesses, so a web game cannot run llama-server itself.
Instead it POSTs each question to tools/serve_web.py on the PC (the same origin that served the
page) through renpy.fetch, which Ren'Py supports on every platform. Desktop builds can take the
same path by setting ORCHARD_REMOTE_URL, which is how the headless tests exercise it.

Keep this file pure Python: no threading, subprocess or socket imports, so it loads in the browser.
The persona prompt, the guard and the model live in ai_suspect.py, on the PC only.
"""
import hashlib
import json
import os
import time

try:
    import renpy
except ImportError:  # standalone tests and the web server
    renpy = None

# Shown when the model is unavailable or breaks a rule. Picked deterministically from the
# question, so a rollback replay shows the same line.
FALLBACKS = {
    "none": [
        "I've told you where I was, Detective. The east reading room, all evening.",
        "I'm sure you have questions. I have very few answers.",
        "Ask me something that isn't a trap and I'll answer it.",
    ],
    "vault": [
        "Yes. I went into the vault at 9:52 to check the humidity logs. That is all I did.",
        "The vault, at 9:52, for the humidity logs. Nothing more than that.",
    ],
    "vault_known": [
        "I've admitted the vault and the humidity logs. I won't be baited into more.",
        "I was checking the humidity logs, as I said. Ask me about something else.",
    ],
}

LEVELS = tuple(FALLBACKS)   # the levels the model may voice; "confess" is scripted


def director_level(evidence, admitted_vault):
    """What the game lets Elena admit, from the evidence the player has put on the table.

    "confess" is not voiced by the model at all; the script plays an authored scene.
    """
    ev = set(evidence)
    if {"badge_log", "ledger_in_locker"} <= ev:
        return "confess"
    if "badge_log" in ev:
        return "vault_known" if admitted_vault else "vault"
    return "none"


def reply_key(level, question, history):
    """Stable fingerprint of one turn; keys the reply cache and picks the canned line."""
    blob = json.dumps([level, question.strip().lower(), [list(h) for h in history]])
    return hashlib.sha1(blob.encode()).hexdigest()


def canned_line(level, key):
    options = FALLBACKS[level]
    return options[int(key[8:12], 16) % len(options)]


# --- Remote model (browser build, or desktop with ORCHARD_REMOTE_URL) -------------
def remote_url():
    """URL of the suspect API if this game should use the PC's model, else None."""
    env = os.environ.get("ORCHARD_REMOTE_URL")
    if env:
        return env
    if renpy is not None and renpy.emscripten:
        try:
            import emscripten
            return emscripten.run_script_string("window.location.origin") + "/api/suspect"
        except Exception:
            return "/api/suspect"
    return None


_status = "idle"        # idle -> ready | offline
last_error = ""         # why the most recent remote call fell back to a canned line, for debugging


def status_text():
    return {"idle": "AI: PC model (not asked yet)", "ready": "AI: PC model ready",
            "offline": "AI: PC unreachable (canned lines)"}[_status]


def ask(level, question, history):
    """Ask the PC for Elena's answer. Returns (line, source, seconds) and never raises.

    Called from the game thread. fetch keeps the window alive while it waits, so the
    "thinking" screen stays up; any failure falls back to a canned line.
    """
    global _status, last_error
    t0 = time.time()
    try:
        # renpy.exports.fetch, not renpy.fetch: the shortcut only exists inside .rpy scripts.
        r = renpy.exports.fetch(remote_url(), json={"level": level, "question": question,
                                            "history": [list(h) for h in history]},
                        result="json", timeout=90)
        line = r["line"]
        if not isinstance(line, str) or not line.strip():
            raise ValueError("empty line from server")
        _status = "ready"
        return line.strip(), str(r.get("source", "ai")), float(r.get("seconds", time.time() - t0))
    except Exception as e:
        _status = "offline"
        last_error = "%s: %s" % (type(e).__name__, e)
        if os.environ.get("ORCHARD_DEBUG"):
            print("suspect_client.ask failed:", last_error)
        return canned_line(level, reply_key(level, question, history)), "canned", 0.0
