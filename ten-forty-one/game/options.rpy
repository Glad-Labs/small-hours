## Ten Forty-One settings. Like Orchard Street, there is no gui.rpy: the interface is a handful of
## flat-colour screens in screens.rpy.

define config.name = "Ten Forty-One"
define config.window_title = "Ten Forty-One (slice)"
define config.version = "0.1"
define config.save_directory = "ten-forty-one-slice"

define config.screen_width = 1280
define config.screen_height = 720

define config.has_sound = False
define config.has_music = False
define config.has_voice = False

## Rollback works (replays reuse cached replies); saving is off in the slice.
define config.has_autosave = False
define config.autosave_on_quit = False
define config.autosave_on_choice = False

## Skip the main menu. The script ends with end_game().
label main_menu:
    return

## What goes into a distribution; first match wins. The model and the code holding the spoilers
## (voice_ai.py: personas, secrets) ship in desktop builds only; the browser asks the PC instead.
init python:
    build.classify("build/", None)
    build.classify("tests/", None)
    build.classify("tools/", None)
    build.classify("game/testcases.rpy", None)
    build.classify("game/testcases.rpyc", None)
    build.classify("**/__pycache__/", None)
    build.classify("ai/**", "linux windows mac")
    build.classify("game/voice_ai.py", "linux windows mac")
    build.classify("game/voice_ai.rpyc", "linux windows mac")
