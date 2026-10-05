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
    if not REMOTE:
        import voice_ai
        config.quit_callbacks.append(lambda: voice_ai.get().stop())

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
        return {"idle": "AI: not started", "loading": "AI: loading model...",
                "ready": "AI: ready", "offline": "AI: offline (written lines)"}[voice_ai.get().status]

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
            renpy.show("webb", at_list=[left_spot])
            renpy.show("nell", at_list=[right_spot])
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

    # Placeholder art until the Blender pass: a tinted room name and a labelled card per person.
    def _bg(title, colour):
        return Fixed(Solid(colour), Text(title, size=84, color="#ffffff16", bold=True, xalign=0.5, yalign=0.38))

    def _person(name, colour):
        return Fixed(Solid(colour), Text(name, size=28, color="#ffffffb0", bold=True, xalign=0.5, ypos=40),
                     xysize=(330, 470))

image bg black = Solid("#000000")
image bg letter = _bg("THREE DAYS EARLIER", "#14121a")
image bg bridge = _bg("THE BRIDGE", "#18202b")
image bg hall = _bg("GREAT HALL", "#2b2433")
image bg vault = _bg("VAULT", "#1f2a2a")
image bg cellar = _bg("CELLAR", "#1c1a17")
image bg study = _bg("HARROW'S STUDY", "#2d2219")
image bg office = _bg("REGISTRAR'S OFFICE", "#202430")
image webb = _person("MARCUS WEBB", "#3a404d")
image nell = _person("NELL ASHBY", "#3d3348")

transform left_spot:
    xpos 330 yalign 0.62 xanchor 0.5

transform right_spot:
    xpos 950 yalign 0.62 xanchor 0.5

transform talk_spot:
    xpos 950 yalign 0.62 xanchor 0.5

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
    show screen hud
    jump prologue


## ---------------------------------------------------------------------------------------------
## Prologue (authored). Everything the player needs later is planted here.
label prologue:
    scene bg letter with fade
    "Three days ago a letter reached you on Harrow Gallery paper."
    "{i}Irregularities in the Calder provenance. Discretion essential. Come to Thursday's sale as my guest.{/i} Signed, Edmund Harrow."
    "The sale had been set for Saturday. Someone moved it to Thursday. The forecast for Thursday said storm."

    scene bg bridge with dissolve
    "6:00 pm. The lift bridge rattles under your tyres. Behind you the channel is already white."

    scene bg hall with dissolve
    "The Harrow Gallery was a customs house once. It still looks as if it expects to tax you."
    show nell at right_spot with dissolve
    nell_c "You must be the detective. Nell Ashby, registrar. Programme."
    "She hands it over with her left hand. There is ink on her fingers, blue to the second knuckle."
    nell_c "Lot nine is the one everyone is pretending not to want. The bar is on the left. Please don't touch Untitled (Chair). It's a chair, but don't."
    hide nell with dissolve

    show webb at left_spot with dissolve
    "At the rostrum, a lean man in a silver-grey waistcoat is polishing a gavel with an ivory handle."
    webb_c "Marcus Webb, Aldous & Pryce. And this is my grandfather's gavel. It has sold three Constables and a ghost."
    webb_c "I like things exact. The hammer falls at a time, not around one. You'll see."
    hide webb with dissolve

    "Across the room a stout man in a velvet jacket is holding court: Edmund Harrow, judging by how the others give him space."
    "Beside him a thin, nervous man in a cardigan rubs his hands together. Julian Crane, the authenticator, says your programme."
    harrow "Julian, you're blue. The vault's an icebox. Take my coat, I insist."
    "Harrow drapes a camel coat over Crane's shoulders. It swamps him."
    "A grey-haired caretaker shoulders past with a crate of wine."
    pike "Cellar door propped open all night for the wine. Whoever's idea that was."

    "There is time for a word with two people before the sale."
    $ talked = []
label prologue_mingle:
    menu:
        "Edmund Harrow, your host" if "harrow" not in talked:
            $ talked.append("harrow")
            harrow "Detective! Delighted, delighted. You must try the... is something the matter?"
            menu:
                "Thank him for the invitation":
                    harrow "Invitation?"
                    "His smile stays where it is. His eyes don't."
                    harrow "I wrote you no letter. I don't... Who sent you?"
                    $ harrow_denied = True
                    "Before you can answer, Webb calls him to the rostrum, and he goes like a man glad of the excuse."
                "Ask about the Calder works":
                    harrow "Magnificent. Late, unfinished, raw. They will make history tonight."
                    "He doesn't meet your eyes once."

        "The young man at the bar" if "dom" not in talked:
            $ talked.append("dom")
            dom "Dom Harrow-Bell. Nephew, heir, family embarrassment. Funny, they moved the date. It was meant to be Saturday."
            dom "Uncle Eddie says the buyers fly out on Friday. Uncle Eddie says a lot of things."

        "The man by the terrace doors" if "ibarra" not in talked:
            $ talked.append("ibarra")
            ibarra "Tomás Ibarra. Physician, collector, insomniac. Forgive me, I have to take this."
            "He steps out onto the terrace with his phone already at his ear, and the colour goes out of his face."

    if len(talked) < 2:
        jump prologue_mingle

    "8:30 pm. The sale begins. Webb is very good: he makes a room of rich people feel poor."
    "9:00 pm. The interval. The room scatters to the bar, the terrace and the corridors. Crane goes down to the vault for a last look at the lots."
    "9:40 pm. The sale resumes. Webb raps the block with a plain boxwood gavel. You don't remember when the ivory one went."
    "10:35 pm. Harrow slips out of the hall. Pike goes for the vault keys, to bring out lot nine."
    "Out of habit you count the room. Webb at the rostrum. Nell at the catalogue desk. Dom at the bar. Ibarra by the window. Everyone but Harrow and Pike."
    scene bg black
    "10:41 pm. The lights die."
    "One second. Two. They stutter back on. Every clock in the hall has stopped."
    "10:44 pm. A shout from the vault corridor."
    pike "Mr Harrow! Mr Harrow's dead!"
    jump chapter_one


## ---------------------------------------------------------------------------------------------
## Chapter 1: The Wrong Body.
label chapter_one:
    $ place = "vault"
    scene bg vault with fade
    "10:48 pm. The vault door hangs open on its override. Pike stands in the doorway, white."
    "A man lies face down on the floor in a camel coat."
    "You kneel and turn him over."
    $ found.append("body")
    "It isn't Harrow. It's Julian Crane, swamped in Harrow's coat, a flat round dent in the back of his skull."
    "In the coat pocket, a notebook. The last page, in a tight hand: {i}strokes left-handed. Do not certify.{/i}"
    "His watch is smashed. It reads 10:41."
    show webb at left_spot
    show nell at right_spot
    with dissolve
    webb_c "Ten forty-one. Every clock in the house says it, and so does his watch. Write that down, my dear. It will matter."
    nell_c "The door was bolted from inside. Pike had to use the override. There's no other way in."
    pike "Mr Harrow's not in his study. Not anywhere."
    webb_c "His coat. His vault. And now he's gone. I hate to say it."
    $ assumptions[:] = list(case.ASSUMPTION_ORDER)
    "You open your notebook. Three things everyone already believes go in first:"
    "{b}Crane died at 10:41.{/b} {b}The vault was sealed.{/b} {b}Harrow killed him and ran.{/b}"
    think "Nobody can cross the bridge before dawn, and I don't trust the lights in this place."
    "Every search, walk and question moves the clock. Open your notebook to challenge what everyone believes."
    $ minute = case.START
    jump investigate


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
        $ spend(1)
        dom "Later, Detective. I'm drinking for two: me and Uncle Eddie, wherever he is."
        ibarra "I've told the caretaker everything I know, which is nothing. I'd like to keep it that way."
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
    show expression person at talk_spot
    with dissolve
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


label broke_a_time(clue):
    if clue == "chart":
        think "The chart doesn't care about the clocks. At 9:31 the warmth of a living man went out of that room."
    else:
        think "9:26, read. 9:45, never opened. Julian Crane was dead before ten."
    think "So 10:41 is a lie, and somebody went to the trouble of telling it."
    think "Every alibi for 10:41 is worthless now. Including the one I watched with my own eyes: Webb, on the rostrum."
    "{b}Struck out:{/b} Crane died at 10:41."
    return

label broke_a_sealed(clue):
    think "Bolted from the inside, and a way out the size of a grille. The vault was never sealed."
    think "And Nell told me there was no other way in."
    "{b}Struck out:{/b} The vault was sealed."
    return

label broke_a_harrow(clue):
    think "Whoever killed Crane left through that duct. Harrow is a big man; he'd stick at the shoulders."
    think "Whoever crawled out of there was slim."
    "{b}Struck out:{/b} Harrow killed him and ran."
    return

label hint_a_time_watch:
    think "The crown is pulled out. Someone set this watch to 10:41 by hand."
    think "That proves the time was faked. It doesn't tell me when he really died."
    return

label hint_a_time_timer:
    think "The clocks stopped because a timer told them to, at a time somebody chose."
    think "So when did he really die?"
    return

label hint_a_harrow_letter:
    think "Harrow was frightened of something. Frightened men run. They don't always kill."
    return

label impossible_crime:
    think "Wait."
    think "If Crane died at 10:41, nobody could have killed him."
    think "Every slim person in this house was in front of me in the hall at 10:41. The only two who weren't, Harrow and Pike, could never fit through that duct."
    think "So he didn't die at 10:41. Prove it."
    return


## ---------------------------------------------------------------------------------------------
## Finding things. Each label narrates one clue from case.py.
label clue_watch:
    "Crane's watch: a plain steel thing, crystal smashed, hands at 10:41."
    "The crown is pulled all the way out. A watch stops like that when someone is setting it."
    return

label clue_duct:
    "The door bolt is thrown from the inside, its keeper sheared by Pike's override."
    "Low on the back wall, behind a rack of frames, an old ventilation grille sits off its screws, leaning against the wall."
    "Behind it, a duct runs off into the dark. A slim person could crawl through it. A big one would stick."
    return

label clue_chart:
    "On a shelf by the door, a climate recorder: a drum of paper turned by a clockwork spring, a pen tracing the vault's warmth and damp."
    "Not on the mains. It didn't stop at 10:41."
    "The trace climbs from 9:14, when someone shut themselves in. At 9:31 it turns and falls away. The warmth of a living person, going out."
    return

label clue_phone:
    "Crane's phone is in his trouser pocket. No lock screen. He trusted people."
    "A text from his wife at 9:26: {i}don't let them bully you x{/i}. Read."
    "Another at 9:45: {i}ring me when you're done?{/i} Never opened."
    return

label clue_thread:
    "The duct comes out low in the cellar wall, behind the wine racks. The grille here is back on its screws, but only just."
    "Fresh scuffs in the dust. Caught on the grille's edge, a single thread of silver-grey wool."
    return

label clue_timer:
    "The fuse cupboard. Among the old ceramic fuses, something new: a plug-in timer on the circuit marked CLOCKS."
    "Set to cut the power at 10:41 and restore it at 10:42."
    think "Every clock in the house stopped because somebody told it to."
    return

label clue_gavel:
    "Behind the wine racks, a bin of packing straw and broken bottles."
    "Wrapped in a rag at the bottom: an ivory-handled gavel. The head is cracked, and stained dark."
    return

label clue_letter:
    "Harrow's desk. The grate behind it is still warm."
    "A half-burnt page in his big looping hand: {i}...every Calder sold since 2019 through Aldous & Pryce is...{/i} The rest is ash."
    return

label clue_shelf:
    "Nell's office is the tidiest room in the building. Every shelf is labelled."
    "One label sits over a gap: {i}CALDER: SALES LEDGER.{/i}"
    return


## ---------------------------------------------------------------------------------------------
## Clock events.
label event_phones:
    scene bg hall
    "10:58 pm. Pike comes in from the storm, soaked to the waist."
    pike "Phones are dead. Landline too. I went out to the box on the wall. The line's cut. Clean."
    pike "That's not the wind."
    return

label event_bridge:
    scene bg hall
    "11:05 pm. Pike again, out of breath."
    pike "Bridge won't come down. The pump's dead. The fuse is gone from the box. Somebody took it."
    think "The storm didn't trap us here. Somebody did."
    return

label event_lights_out:
    scene bg black with Dissolve(1.0)
    "11:30 pm. Somewhere below you the generator coughs, twice, and dies."
    "Every light in the Harrow Gallery goes out at once."
    nell_c "Detective? Are you still there?"
    webb_c "Nobody move. My dear, nobody move at all."
    $ renpy.call_screen("slice_end")
    $ end_game()
    return
