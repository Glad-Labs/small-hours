## Flat-colour interface for the slice. Sizes are chosen to stay readable on a phone in landscape.

style default:
    color "#e8e6df"
    size 27

## Dialogue box.
screen say(who, what):
    window:
        id "window"
        xfill True
        yalign 1.0
        ysize 210
        background Solid("#0d0d14ee")
        padding (60, 24, 60, 16)

        vbox:
            spacing 8
            if who is not None:
                text who id "who" size 30 bold True
            text what id "what" xmaximum 1140 line_spacing 4

## Free-text question box (used by renpy.input).
screen input(prompt):
    modal True
    window:
        xalign 0.5
        yalign 0.4
        xsize 960
        background Solid("#14141cf5")
        padding (40, 30)

        vbox:
            spacing 18
            text prompt color "#f2c48d"
            frame:
                xfill True
                background Solid("#00000099")
                padding (16, 12)
                input id "input" color "#ffffff"

## Menu choices.
screen choice(items):
    vbox:
        xpos 60
        yalign 0.42
        xsize 700
        spacing 12
        for i in items:
            textbutton i.caption:
                action i.action
                xfill True
                padding (24, 14)
                background Solid("#262636f2")
                hover_background Solid("#3b3b5cf2")
                text_color "#e8e6df"
                text_hover_color "#ffffff"

## Yes/no prompt, used by Quit(confirm=True) on desktop.
screen confirm(message, yes_action, no_action):
    modal True
    zorder 200
    add Solid("#000000a0")
    frame:
        xalign 0.5
        yalign 0.5
        padding (50, 36)
        background Solid("#1b1b26")
        vbox:
            spacing 28
            text message xalign 0.5
            hbox:
                xalign 0.5
                spacing 50
                textbutton "Yes" action yes_action
                textbutton "No" action no_action

## Always-on overlay: the time and place on the left, the model status on the right.
screen hud():
    zorder 50
    if not renpy.emscripten:
        key "game_menu" action Quit(confirm=True)

    if minute:
        frame:
            xpos 20
            ypos 20
            padding (18, 10)
            background Solid("#0d0d14cc")
            vbox:
                text case.clock_text(minute) size 30 color "#f2c48d" bold True
                text case.PLACES[place]["name"] size 20 color "#9fb3c8"

    frame:
        xalign 1.0
        xoffset -20
        ypos 20
        padding (18, 12)
        background Solid("#0d0d14cc")
        hbox:
            spacing 24
            text ai_status_text() size 20 color "#9fb3c8"
            if not renpy.emscripten:
                textbutton "Quit" action Quit(confirm=True) text_size 20

    ## Desktop only: refresh while the model loads so the status text updates (the test runner also
    ## relies on this tick). Never in the browser, where each refresh used to wipe the question box.
    if not renpy.emscripten:
        timer 1.0 repeat True action Function(renpy.restart_interaction)

## Shown while a suspect is composing a reply.
screen thinking(who):
    zorder 60
    frame:
        xalign 0.5
        yalign 0.62
        padding (30, 16)
        background Solid("#000000b8")
        text "[who] considers..." italic True

## The notebook: what everyone believes, what you have found, and what is still unknown.
## Returns ("challenge", assumption id) or "close".
screen notebook():
    modal True
    zorder 100
    add Solid("#0b0b12f4")

    text "NOTEBOOK   [case.clock_text(minute)]" xpos 50 ypos 30 size 30 color "#f2c48d" bold True

    hbox:
        xpos 50
        ypos 90
        spacing 40

        vbox:
            xsize 560
            spacing 10
            text "What everyone believes" size 24 color "#9fb3c8"
            for aid in case.ASSUMPTION_ORDER:
                if aid in assumptions:
                    $ a_text = case.ASSUMPTIONS[aid]["text"]
                    $ a_source = case.ASSUMPTIONS[aid]["source"]
                    if aid in struck:
                        text "{s}[a_text]{/s}" color "#6f7385"
                    else:
                        textbutton a_text:
                            action Return(("challenge", aid))
                            xfill True
                            padding (18, 10)
                            background Solid("#262636f2")
                            hover_background Solid("#3b3b5cf2")
                            text_color "#ffffff"
                        text "according to [a_source]. Tap to challenge it." size 19 color "#7d8095"
            null height 14
            text "Still unknown" size 24 color "#9fb3c8"
            for line in case.open_questions(found, struck):
                text "- [line]" size 22

        vbox:
            xsize 600
            spacing 10
            text "Evidence ([len(found)])" size 24 color "#9fb3c8"
            viewport:
                xsize 600
                ysize 470
                mousewheel True
                draggable True
                vbox:
                    xsize 580
                    spacing 12
                    for clue_id in [c for c in case.CLUE_ORDER if c in found]:
                        $ clue_title = case.CLUES[clue_id]["title"]
                        $ clue_note = case.CLUES[clue_id]["note"]
                        text clue_title size 23 bold True color "#f2c48d"
                        text clue_note size 21

    textbutton "Close":
        xalign 1.0
        yalign 1.0
        xoffset -40
        yoffset -30
        padding (30, 14)
        background Solid("#262636f2")
        hover_background Solid("#3b3b5cf2")
        action Return("close")

## End of the slice.
screen slice_end():
    modal True
    add Solid("#05050a")
    vbox:
        xalign 0.5
        yalign 0.42
        spacing 18
        xsize 900
        text "TEN FORTY-ONE" size 52 bold True color "#f2c48d" xalign 0.5
        text "Chapter 1 ends here. The story continues at 11:30 pm, in the dark." xalign 0.5 text_align 0.5
        null height 10
        text "Evidence found: [len(found)] of [len(case.CLUE_ORDER)]" xalign 0.5
        text "Beliefs you overturned: [len(struck)] of [len(case.ASSUMPTION_ORDER)]" xalign 0.5
        null height 10
        textbutton "Finish":
            xalign 0.5
            padding (30, 14)
            background Solid("#262636f2")
            hover_background Solid("#3b3b5cf2")
            action Return("finish")
