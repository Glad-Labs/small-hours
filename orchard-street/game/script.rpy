## Orchard Street: a one-room interrogation prototype.
##
## The model only voices Elena's open-ended answers. This script decides what she may
## admit (suspect_client.director_level) and plays the confession as authored dialogue.
##
## Two ways to reach the model:
##   * desktop: ai_suspect starts a bundled llama-server and talks to it directly;
##   * browser (or ORCHARD_REMOTE_URL set): the page asks tools/serve_web.py on the PC, because a
##     browser can run neither threads nor a model server. See suspect_client.py.

init python:
    import suspect_client

    REMOTE = suspect_client.remote_url() is not None
    if not REMOTE:
        import ai_suspect
        config.quit_callbacks.append(lambda: ai_suspect.get().stop())

    def end_game():
        """Desktop closes the game; a browser tab cannot quit, so it restarts for another go."""
        if renpy.emscripten:
            renpy.full_restart()
        else:
            renpy.quit()

    def pose(mood):
        """Show Elena in a pose, with a short dissolve so the change reads as an expression shift."""
        renpy.show("elena " + mood, at_list=[stage])
        renpy.with_statement(Dissolve(0.3))

    def ai_status_text():
        if REMOTE:
            return suspect_client.status_text()
        return {"idle": "AI: not started", "loading": "AI: loading model...",
                "ready": "AI: ready", "offline": "AI: offline (canned lines)"}[ai_suspect.get().status]

    def ask_elena(level, question):
        """Ask the model and wait without freezing the window. Returns (line, source, seconds)."""
        if REMOTE:
            renpy.show_screen("thinking")
            answer = suspect_client.ask(level, question, history)   # renpy.fetch keeps the window alive
            renpy.hide_screen("thinking")
            return answer
        reply = ai_suspect.get().ask(level, question, history)
        renpy.show_screen("thinking")
        while not reply.done:
            renpy.pause(0.1, hard=True)
        renpy.hide_screen("thinking")
        return reply.line, reply.source, reply.seconds

define det = Character("Detective", who_color="#9fc5ff")
define elena = Character("Elena Voss", who_color="#f2c48d")

## Art is rendered from 3D scenes in Blender (see art/README.md) larger than it is shown, so it stays
## sharp on big screens and phones; zoom brings it back to the 1280x720 layout. The background is
## 1920x1080 (zoom 2/3) and the sprites are 1050x1400 (zoom 1/2, shown at 525x700).
image bg office = Transform("images/bg_office.webp", zoom=2.0 / 3.0)
image elena guarded = Transform("images/elena_guarded.webp", zoom=0.5)
image elena tense = Transform("images/elena_tense.webp", zoom=0.5)
image elena broken = Transform("images/elena_broken.webp", zoom=0.5)

transform stage:
    xalign 0.75
    ypos 20

## Game state. Everything the model needs to know comes from here, never from the model.
default found_badge_log = False
default found_locker = False
default presented = []          # evidence on the table, in the order it was presented
default admitted_vault = False
default confess_now = False
default elena_mood = "guarded"
default history = []            # (question, line) pairs sent back to the model for continuity
default q = ""
default elena_line = ""
default ai_turns = 0
default canned_turns = 0
default ai_seconds = []


label start:
    python:
        if not REMOTE:
            ai_suspect.get().start()    # begin loading the model while the player reads the intro

    scene bg office
    show elena guarded at stage
    show screen hud

    "Orchard Street Gallery, 10:41 pm. The Harrow ledger was in the vault at nine. By ten it was gone."
    "The night archivist, Elena Voss, says she spent the whole evening in the east reading room. You have some questions."
    elena "Detective. I would offer you tea, but I suspect this is not that kind of visit."

    jump interrogate


label interrogate:
    if confess_now:
        jump confession

    menu:
        "What do you do?"

        "Ask Elena a question":
            call ask_question

        "Examine the vault badge log" if not found_badge_log:
            call examine_badge_log

        "Search the staff lockers" if not found_locker:
            call search_locker

        "Present evidence" if found_badge_log or found_locker:
            call present_evidence

        "Leave":
            jump leave

    jump interrogate


label ask_question:
    $ q = renpy.input("What do you ask Elena?", length=160).strip()
    if not q:
        return
    det "[q!q]"
    call elena_answers(q)
    return


label examine_badge_log:
    "You pull the vault door log up on the archive terminal."
    "9:52 pm: vault door opened, badge E. VOSS. 9:58 pm: door closed."
    $ found_badge_log = True
    return


label search_locker:
    "The staff lockers sit in the corridor outside. Elena's is third from the left."
    "Behind a stack of cleaning cloths: a leather-bound ledger stamped HARROW."
    $ found_locker = True
    return


label present_evidence:
    menu:
        "Present the vault badge log" if found_badge_log and "badge_log" not in presented:
            $ presented.append("badge_log")
            $ q = "Your badge opened the vault door at 9:52 pm. Explain that."

        "Present the ledger from her locker" if found_locker and "ledger_in_locker" not in presented:
            $ presented.append("ledger_in_locker")
            $ q = "We found the Harrow ledger in your locker, Ms. Voss. Why is it there?"

        "Never mind":
            return

    det "[q!q]"
    call elena_answers(q)
    return


## The heart of the design: code picks the level, the model (or a scripted scene) delivers it.
label elena_answers(question):
    $ level = suspect_client.director_level(presented, admitted_vault)

    if level == "confess":
        $ confess_now = True
        return

    $ elena_line, source, secs = ask_elena(level, question)

    if level == "vault":
        $ admitted_vault = True
        $ elena_mood = "tense"

    $ pose(elena_mood)
    elena "[elena_line!q]"

    $ history.append((question, elena_line))
    $ del history[:-6]
    if source == "ai":
        $ ai_turns += 1
        $ ai_seconds.append(round(secs, 1))
    elif source == "cache":
        $ ai_turns += 1             # a repeat or a rollback replay: still a model answer, just not a new wait
    else:
        $ canned_turns += 1
    return


## Authored, not generated: the climax is too important to leave to a small model.
label confession:
    $ pose("broken")

    elena "..."
    elena "Stop. Please. That is enough."
    elena "I went into the vault at 9:52 to check the humidity logs. The ledger was lying open on the table, at the page with my brother's name."
    elena "Tomas carried packages for a man who forged provenance papers. He never understood what was inside them. It is all in that book, in his own hand."
    elena "I meant to burn it. I got as far as my locker and found I could not. It is ten years of this gallery's history."
    elena "Arrest me if you must. But Tomas did not know what he was carrying, and I would like you to remember that when you read it."
    "Elena Voss pushes the ledger across the desk with both hands."
    "CASE CLOSED (prototype complete)."

    python:
        waits = sorted(ai_seconds)
        typical = waits[len(waits) // 2] if waits else 0
    "Elena's answers: [ai_turns] from the local model (typical wait [typical] s), [canned_turns] canned."

    $ end_game()
    return


label leave:
    "You leave the archive. The case stays open."
    $ end_game()
    return
