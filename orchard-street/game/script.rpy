## Orchard Street: a one-room interrogation prototype.
##
## The local model only voices Elena's open-ended answers. This script decides what she may
## admit (ai_suspect.director_level) and plays the confession as authored dialogue.

init python:
    import ai_suspect

    config.quit_callbacks.append(lambda: ai_suspect.get().stop())

    def placeholder(label, color):
        """Flat-colour stand-in for character art."""
        return Fixed(Solid(color, xysize=(300, 460)),
                     Text(label, size=26, xalign=0.5, yalign=0.5, text_align=0.5, color="#ffffff"),
                     xysize=(300, 460))

    def ai_status_text():
        return {"idle": "AI: not started", "loading": "AI: loading model...",
                "ready": "AI: ready", "offline": "AI: offline (canned lines)"}[ai_suspect.get().status]

    def ask_elena(level, question):
        """Ask the model and wait without freezing the window. Returns (line, source, seconds)."""
        reply = ai_suspect.get().ask(level, question, history)
        renpy.show_screen("thinking")
        while not reply.done:
            renpy.pause(0.1, hard=True)
        renpy.hide_screen("thinking")
        return reply.line, reply.source, reply.seconds

define det = Character("Detective", who_color="#9fc5ff")
define elena = Character("Elena Voss", who_color="#f2c48d")

image bg office = Fixed(Solid("#1d2230"),
                        Text("ARCHIVE OFFICE  -  Orchard Street Gallery", size=22, color="#4a5470",
                             xalign=0.5, ypos=30))
image elena guarded = placeholder("ELENA VOSS\n(guarded)", "#5b7fa3")
image elena tense = placeholder("ELENA VOSS\n(tense)", "#a38a5b")
image elena broken = placeholder("ELENA VOSS\n(broken)", "#a35b66")

transform stage:
    xalign 0.75
    ypos 50

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
    $ level = ai_suspect.director_level(presented, admitted_vault)

    if level == "confess":
        $ confess_now = True
        return

    $ elena_line, source, secs = ask_elena(level, question)

    if level == "vault":
        $ admitted_vault = True
        $ elena_mood = "tense"

    $ renpy.show("elena " + elena_mood, at_list=[stage])
    elena "[elena_line!q]"

    $ history.append((question, elena_line))
    $ del history[:-6]
    if source == "ai":
        $ ai_turns += 1
        $ ai_seconds.append(round(secs, 1))
    else:
        $ canned_turns += 1
    return


## Authored, not generated: the climax is too important to leave to a small model.
label confession:
    $ renpy.show("elena broken", at_list=[stage])

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

    $ renpy.quit()
    return


label leave:
    "You leave the archive. The case stays open."
    $ renpy.quit()
    return
