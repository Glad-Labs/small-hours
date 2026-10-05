"""The parts of the voice layer that run everywhere, including Ren'Py's browser build.

A browser cannot run llama-server, so the web build POSTs each question to tools/serve_web.py on
the PC through renpy.exports.fetch. Desktop builds can take the same path by setting
TFO_REMOTE_URL, which is how the headless tests exercise it.

Pure Python: no threads, sockets or subprocesses. The personas, the guard and the model live in
voice_ai.py, on the PC only. A request names a person and the fact ids the game has unlocked for
them (see case.unlocked_facts); the words behind those ids never ship in the web build.
"""
import hashlib
import json
import os
import time

try:
    import renpy
except ImportError:  # standalone tests and the web server
    renpy = None

import case

# Shown when the model is unavailable or breaks a rule. "calm" before anything is unlocked,
# "pressed" after. Picked deterministically from the question so rollback shows the same line.
FALLBACKS = {
    "webb": {
        "calm": ["Ask me anything, my dear. I've nothing to hide but my commission.",
                 "Ten forty-one. I'd stake my reputation on it, and it's a good reputation.",
                 "I sell things for a living, Detective. Telling the truth is cheaper."],
        "pressed": ["You're very thorough. I admire that in a detective, up to a point.",
                    "I'm an auctioneer, not a cat burglar. Ask me something sensible.",
                    "Let's not get carried away, my dear. It's late and we're all frightened."],
    },
    "nell": {
        "calm": ["I've told you what I know. Ask me something useful.",
                 "I'm the registrar. I count things. Tonight I can't make anything add up.",
                 "Try me again when I've stopped shaking, Detective."],
        "pressed": ["I don't want to talk about that. Not here.",
                    "Please. Ask me something else.",
                    "You're good at this. I wish you weren't, tonight."],
    },
}


def stage(facts):
    return "pressed" if facts else "calm"


def reply_key(person, facts, question, history):
    """Stable fingerprint of one turn; keys the reply cache and picks the canned line."""
    blob = json.dumps([person, sorted(facts), question.strip().lower(), [list(h) for h in history]])
    return hashlib.sha1(blob.encode()).hexdigest()


def canned_line(person, facts, key):
    options = FALLBACKS[person][stage(facts)]
    return options[int(key[8:12], 16) % len(options)]


def valid_request(person, facts):
    return person in case.FACT_IDS and all(f in case.FACT_IDS[person] for f in facts)


# --- Remote model (browser build, or desktop with TFO_REMOTE_URL) ----------------------
def remote_url():
    env = os.environ.get("TFO_REMOTE_URL")
    if env:
        return env
    if renpy is not None and renpy.emscripten:
        try:
            import emscripten
            return emscripten.run_script_string("window.location.origin") + "/api/voice"
        except Exception:
            return "/api/voice"
    return None


_status = "idle"        # idle -> ready | offline
last_error = ""


def status_text():
    return {"idle": "AI: PC model", "ready": "AI: PC model ready",
            "offline": "AI: PC unreachable (canned lines)"}[_status]


def ask(person, facts, question, history):
    """Ask the PC for a person's answer. Returns (line, source, seconds) and never raises."""
    global _status, last_error
    t0 = time.time()
    try:
        # renpy.exports.fetch, not renpy.fetch: the shortcut only exists inside .rpy scripts.
        r = renpy.exports.fetch(remote_url(), json={"person": person, "facts": list(facts), "question": question,
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
        if os.environ.get("TFO_DEBUG"):
            print("voices.ask failed:", last_error)
        return canned_line(person, facts, reply_key(person, facts, question, history)), "canned", 0.0
