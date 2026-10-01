## Orchard Street prototype settings.
##
## This project deliberately has no gui.rpy. The interface is a handful of flat-colour
## screens in screens.rpy, so the prototype carries no third-party art.

define config.name = "Orchard Street"
define config.window_title = "Orchard Street (prototype)"
define config.version = "0.1"
define config.save_directory = "orchard-street-prototype"

define config.screen_width = 1280
define config.screen_height = 720

define config.has_sound = False
define config.has_music = False
define config.has_voice = False

## Rollback works (replays reuse cached AI replies); saving is off in this prototype.
define config.has_autosave = False
define config.autosave_on_quit = False
define config.autosave_on_choice = False

## Skip the main menu and go straight to the game. The script ends with end_game().
label main_menu:
    return

## What goes into a distribution. Ren'Py packs everything in the project folder unless told
## otherwise, and the model files alone would add 3 GB, so be explicit. Rules are applied in order
## and the first match wins.
init python:
    build.classify("build/", None)                      # our own web build output
    build.classify("tests/", None)
    build.classify("tools/", None)
    build.classify("game/testcases.rpy", None)
    build.classify("game/testcases.rpyc", None)
    build.classify("**/__pycache__/", None)

    # The local model server (llama-server, the GGUF model, and the code that starts it) belongs in
    # desktop builds only. A browser build asks the PC's model through tools/serve_web.py instead.
    build.classify("ai/**", "linux windows mac")
    build.classify("game/ai_suspect.py", "linux windows mac")
    build.classify("game/ai_suspect.rpyc", "linux windows mac")
