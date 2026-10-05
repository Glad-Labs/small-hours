## Ten Forty-One, vertical slice: the prologue and chapter 1 (10:48 to 11:30 pm).
##
## The case (places, clues, beliefs, who may admit what, clock events) is data in case.py. This
## script narrates it and runs the loop: look around, walk, question people, and challenge in the
## notebook what everyone believes. Webb and Nell are voiced by the local model through voices.py
## (browser) or voice_ai.py (desktop); everyone else is written. See docs/ten-forty-one.md.

init -1 python:
    import case
    import voices

    REMOTE = voices.remote_url() is not None
    model_download = None           # a model_store.Download while the first-run download runs
    if not REMOTE:
        import voice_ai
        import model_store
        config.quit_callbacks.append(lambda: voice_ai.get().stop())
        config.quit_callbacks.append(lambda: model_download and model_download.cancel())

        def _start_model_when_downloaded():
            """Runs about 20 times a second: once the download is verified, load the model."""
            if model_download is not None and model_download.state == "done" and voice_ai.get().status == "no_model":
                voice_ai.get().start()
        config.periodic_callbacks.append(_start_model_when_downloaded)

    if renpy.emscripten:
        # Ren'Py's browser input calls startInput() whenever the screen is re-run, and that empties
        # the HTML text box and refocuses it, so a phone keyboard resizing the page could wipe a
        # half-typed question. Keep the text while the same prompt is already showing.
        # (Same fix as orchard-street/game/script.rpy.)
        import emscripten
        emscripten.run_script("""
            (function () {
                if (window.keepTyped) return;
                window.keepTyped = true;
                const start = window.startInput;
                window.startInput = function (prompt, value, allow, exclude, mask) {
                    const div = document.getElementById("inputDiv");
                    const shown = document.getElementById("inputPrompt");
                    if (div.classList.contains("visible") && shown.textContent === prompt) {
                        return;
                    }
                    return start(prompt, value, allow, exclude, mask);
                };
            })();
        """)

    def end_game():
        """Desktop closes the game; a browser tab cannot quit, so it restarts for another go."""
        if renpy.emscripten:
            renpy.full_restart()
        else:
            renpy.quit()

    def ai_status_text():
        if REMOTE:
            return voices.status_text()
        state = voice_ai.get().status
        if state == "no_model":
            d = model_download
            if d is None or d.state == "idle":
                return "AI: not installed (written lines)"
            if d.state == "running":
                return "AI: downloading %d%%" % int(d.fraction * 100)
            if d.state == "verifying":
                return "AI: checking download..."
            if d.state == "failed":
                return "AI: download failed (written lines)"
        return {"no_model": "AI: starting...", "idle": "AI: not started", "loading": "AI: loading model...",
                "ready": "AI: ready", "offline": "AI: offline (written lines)"}[state]

    def spend(minutes):
        global minute
        minute += minutes

    def say_safe(who, line):
        """Show a model line without letting it smuggle in Ren'Py text tags or interpolation."""
        renpy.say(who, line.replace("{", "{{").replace("[", "[["))

    def voice_reply(person, question):
        """Ask the model for a person's answer, keeping the window alive. Returns (line, source)."""
        facts = case.unlocked_facts(person, struck, shown[person])
        history = histories[person]
        renpy.show_screen("thinking", who=case.PEOPLE[person]["name"])
        if REMOTE:
            line, source, _secs = voices.ask(person, facts, question, history)
        else:
            reply = voice_ai.get().ask(person, facts, question, history)
            while not reply.done:
                renpy.pause(0.1, hard=True)
            line, source = reply.line, reply.source
        renpy.hide_screen("thinking")
        return line, source

    def show_place():
        renpy.scene()
        renpy.show("bg " + place)
        if place == "hall" and minute < case.LIGHTS_OUT:
            renpy.show(mood("webb"), at_list=[left_spot])
            renpy.show(mood("nell"), at_list=[right_spot])
        renpy.with_statement(Dissolve(0.25))

    # What the detective says when putting a clue in front of someone.
    def show_line(person, clue):
        lines = {
            "body": "Crane's notebook. The last page says: strokes left-handed, do not certify. What does that mean to you?",
            "watch": "Crane's watch says 10:41, but the crown is pulled out. Someone set it by hand.",
            "duct": "There's a grille in the vault wall, off its screws. A way in and out that isn't the door.",
            "chart": "The climate recorder in the vault says the warmth of a living person stopped at 9:31, not 10:41.",
            "phone": "Crane read a text from his wife at 9:26. Her next one, at 9:45, he never opened.",
            "thread": "This was caught on the grille at the cellar end of the duct. Silver-grey wool.",
            "timer": "Someone put a timer on the clock circuit in the cellar. Off at 10:41, on at 10:42.",
            "gavel": ("Your ivory gavel. It was wrapped in a rag in the cellar bin, cracked and stained." if person == "webb"
                      else "Mr Webb's ivory gavel. Wrapped in a rag in the cellar bin, cracked and stained."),
            "letter": "Half-burnt, in Harrow's hand: every Calder sold since 2019 through Aldous and Pryce is... Is what?",
            "shelf": "There's an empty shelf in your office labelled CALDER: SALES LEDGER.",
        }
        return lines[clue]

    def mood(person):
        """Which sprite to show: the code decides the expression from what has been proved, as with Elena."""
        facts = case.unlocked_facts(person, struck, shown[person])
        if person == "webb":
            return "webb pressed" if facts else "webb calm"
        return "nell rattled" if facts else "nell calm"

    def _dimmed(path, alpha):
        return Fixed(Transform(path, zoom=2.0 / 3.0), Solid("#000000%02x" % alpha))

## Art is rendered in Blender from CC0 assets (art/tfo_rooms.py, art/tfo_people.py) at 1920x1080 and
## 1050x1400, then shown at 2/3 and 1/2 so it stays sharp on big screens and phones.
image bg black = Solid("#000000")
image bg letter = _dimmed("images/bg_study.webp", 0xb0)
image bg bridge = Solid("#05070c")
image bg hall = Transform("images/bg_hall.webp", zoom=2.0 / 3.0)
image bg vault = Transform("images/bg_vault.webp", zoom=2.0 / 3.0)
image bg cellar = Transform("images/bg_cellar.webp", zoom=2.0 / 3.0)
image bg study = Transform("images/bg_study.webp", zoom=2.0 / 3.0)
image bg office = Transform("images/bg_office.webp", zoom=2.0 / 3.0)
image webb calm = Transform("images/webb_calm.webp", zoom=0.5)
image webb pressed = Transform("images/webb_pressed.webp", zoom=0.5)
image nell calm = Transform("images/nell_calm.webp", zoom=0.5)
image nell warm = Transform("images/nell_warm.webp", zoom=0.5)
image nell rattled = Transform("images/nell_rattled.webp", zoom=0.5)

## Both people stand right of centre, because menus take the left half of the screen.
transform left_spot:
    xpos 815 xanchor 0.5 ypos 30

transform right_spot:
    xpos 1110 xanchor 0.5 ypos 30

transform talk_spot:
    xpos 960 xanchor 0.5 ypos 30

define det = Character("You", who_color="#9fc5ff")
define think = Character(None, what_italic=True, what_color="#c9d4ff")
define webb_c = Character("Marcus Webb", who_color="#c8d3e6")
define nell_c = Character("Nell Ashby", who_color="#e7b9d0")
define pike = Character("Pike", who_color="#c9b48a")
define harrow = Character("Edmund Harrow", who_color="#d9a36a")
define crane = Character("Julian Crane", who_color="#a9c6a0")
define dom = Character("Dom Harrow-Bell", who_color="#a7c4e8")
define ibarra = Character("Dr Ibarra", who_color="#c7b7e6")
define SPEAKERS = {"webb": webb_c, "nell": nell_c}

## Game state. Everything the model may say is decided from this, never by the model.
default minute = 0                  # 0 until chapter 1 starts; then minutes since midnight of the auction day
default place = "vault"
default found = []                  # clues found, in order
default assumptions = []            # beliefs written in the notebook
default struck = []                 # beliefs the player has overturned
default shown = {"webb": [], "nell": []}            # clues put in front of each person
default histories = {"webb": [], "nell": []}        # (question, line) pairs sent back to the model
default fired = []                  # clock events that have happened
default harrow_denied = False       # prologue: Harrow said he wrote no letter
default saw_impossible = False
default talk_person = "webb"
default q = ""
default ai_turns = 0
default canned_turns = 0


label start:
    python:
        if not REMOTE:
            voice_ai.get().start()      # load the model while the player reads the prologue
    if not REMOTE and voice_ai.get().status == "no_model":
        $ choice = renpy.call_screen("first_run", size_gb=model_store.MODEL_SIZE / 1e9, credit=model_store.MODEL_CREDIT)
        if choice == "download":
            python:
                model_download = model_store.Download()
                model_download.start()
    show screen hud
    jump prologue


## The loop: fire any due clock events, then let the player choose what to spend time on.
label investigate:
    $ due = case.due_events(minute, fired)
    if due:
        $ fired.append(due[0])
        $ renpy.call(due[0])
        jump investigate

    $ show_place()

    if case.impossible(struck) and not saw_impossible:
        $ saw_impossible = True
        call impossible_crime

    python:
        options = []
        for c in case.searches_here(place, found):
            options.append(("%s (%d min)" % (case.CLUES[c]["action"], case.CLUES[c]["cost"]), ("search", c)))
        if place == "hall":
            options.append(("Talk to Marcus Webb", ("talk", "webb")))
            options.append(("Talk to Nell Ashby", ("talk", "nell")))
            options.append(("Talk to Dom or Dr Ibarra", ("others", None)))
        options.append(("Go somewhere else", ("go", None)))
        options.append(("Open your notebook", ("notebook", None)))
        action, arg = renpy.display_menu(options)

    if action == "search":
        $ spend(case.CLUES[arg]["cost"])
        $ found.append(arg)
        $ renpy.call("clue_" + arg)
    elif action == "talk":
        call talk(arg)
    elif action == "others":
        $ spend(2)
        call others
    elif action == "go":
        python:
            dests = [(("%s (%d min)" % (case.PLACES[p]["name"], case.travel_cost(place, p))), p)
                     for p in ("hall", "vault", "cellar", "study", "office") if p != place]
            dests.append(("Stay here", None))
            dest = renpy.display_menu(dests)
            if dest:
                spend(case.travel_cost(place, dest))
                place = dest
    else:
        call notebook_flow
    jump investigate


## ---------------------------------------------------------------------------------------------
## Questioning a voiced person.
label talk(person):
    $ talk_person = person
    $ first = case.PEOPLE[person]["name"].split()[0]
    scene expression ("bg " + place)
    $ renpy.show(mood(person), at_list=[talk_spot])
    with dissolve
    if person not in met:
        $ met.append(person)
        $ renpy.call("meet_" + person)
label talk_loop:
    python:
        options = [("Ask %s a question" % first, "ask")]
        if [c for c in found if c not in shown[talk_person]]:
            options.append(("Show %s something" % first, "show"))
        options.append(("Step away", "leave"))
        choice = renpy.display_menu(options)

    if choice == "leave":
        return

    if choice == "ask":
        $ q = renpy.input("What do you ask %s?" % first, length=160).strip()
        if not q:
            jump talk_loop
    else:
        python:
            items = [(case.CLUES[c]["title"], c) for c in case.CLUE_ORDER if c in found and c not in shown[talk_person]]
            items.append(("Never mind", None))
            clue = renpy.display_menu(items)
        if clue is None:
            jump talk_loop
        $ shown[talk_person].append(clue)
        $ q = show_line(talk_person, clue)

    $ spend(case.QUESTION_COST)
    det "[q!q]"
    $ line, source = voice_reply(talk_person, q)
    $ renpy.show(mood(talk_person), at_list=[talk_spot])
    $ say_safe(SPEAKERS[talk_person], line)
    python:
        histories[talk_person].append((q, line))
        del histories[talk_person][:-6]
        if source == "canned":
            canned_turns += 1
        else:
            ai_turns += 1

    if case.due_events(minute, fired):
        "Somewhere behind you, Pike's voice cuts across the hall."
        return
    jump talk_loop


## ---------------------------------------------------------------------------------------------
## The notebook: challenge a belief with a piece of evidence.
label notebook_flow:
    $ result = renpy.call_screen("notebook")
    if not isinstance(result, tuple):       # "close" (Ren'Py cannot Return None: it becomes True)
        return
    $ belief = result[1]
    python:
        items = [("Which evidence contradicts it?", None)]
        items += [(case.CLUES[c]["title"], c) for c in case.CLUE_ORDER if c in found]
        items.append(("Never mind", "never"))
        clue = renpy.display_menu(items)
    if clue in (None, "never"):
        jump notebook_flow
    $ outcome = case.challenge(belief, clue)
    if outcome == "breaks":
        $ struck.append(belief)
        $ renpy.call("broke_" + belief, clue)
    elif outcome == "hint":
        $ renpy.call("hint_%s_%s" % (belief, clue))
    else:
        think "That doesn't touch it."
    jump notebook_flow
