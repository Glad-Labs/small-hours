## Flat-colour interface for the prototype. No image assets are used.

style default:
    color "#e8e6df"
    size 26

## Dialogue box. The `who` and `what` ids are how the engine styles names and text.
screen say(who, what):
    window:
        id "window"
        xfill True
        yalign 1.0
        ysize 200
        background Solid("#0d0d14ee")
        padding (60, 26, 60, 18)

        vbox:
            spacing 8
            if who is not None:
                text who id "who" size 30 bold True
            text what id "what" xmaximum 1100 line_spacing 4

## Free-text question box (used by renpy.input).
screen input(prompt):
    modal True
    window:
        xalign 0.5
        yalign 0.45
        xsize 900
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
        xpos 70
        yalign 0.38
        xsize 640
        spacing 14
        for i in items:
            textbutton i.caption:
                action i.action
                xfill True
                padding (24, 14)
                background Solid("#262636f2")
                hover_background Solid("#3b3b5cf2")
                text_color "#e8e6df"
                text_hover_color "#ffffff"

## Yes/no prompt, used by Quit(confirm=True).
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

## Always-on overlay: evidence board, model status and a quit button.
screen hud():
    zorder 50
    if not renpy.emscripten:
        key "game_menu" action Quit(confirm=True)

    frame:
        xpos 20
        ypos 20
        padding (18, 12)
        background Solid("#0d0d14cc")
        vbox:
            spacing 4
            text "EVIDENCE" size 18 color "#f2c48d"
            if not found_badge_log and not found_locker:
                text "nothing yet" size 20 color "#7d8095"
            if found_badge_log:
                text ("[[x] Vault badge log" if "badge_log" in presented else "[[ ] Vault badge log") size 20
            if found_locker:
                text ("[[x] Ledger from locker" if "ledger_in_locker" in presented else "[[ ] Ledger from locker") size 20

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

    ## The model loads in the background; refresh so the status text updates.
    timer 1.0 repeat True action Function(renpy.restart_interaction)

## Shown while the model is composing a reply.
screen thinking():
    zorder 60
    frame:
        xalign 0.5
        yalign 0.6
        padding (30, 16)
        background Solid("#000000b8")
        text "Elena considers her words..." italic True
