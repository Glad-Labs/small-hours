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
    build.name = "TenFortyOne"
    build.directory_name = "TenFortyOne-" + config.version
    build.executable_name = "TenFortyOne"

    build.classify("build/", None)
    build.classify("dist/", None)
    build.classify("tests/", None)
    build.classify("tools/", None)
    build.classify("game/testcases.rpy", None)
    build.classify("game/testcases.rpyc", None)
    build.classify("**/__pycache__/", None)

    # The model server ships per platform; the 3.2 GB model is downloaded on first run (model_store.py), so
    # neither the model nor the developer's links to it are ever packaged.
    # Ren'Py classifies a folder before looking inside it, so each folder needs its own rule ahead of the
    # catch-all at the end.
    build.classify("ai/models/", None)
    build.classify("ai/bin/llama-server", None)
    build.classify("ai/*.log", None)
    for plat, lists in (("windows-x64", "windows"), ("linux-x64", "linux"), ("mac-arm64", "mac"), ("mac-x64", "mac")):
        build.classify("ai/bin/%s/" % plat, lists)
        build.classify("ai/bin/%s/**" % plat, lists)
    build.classify("ai/bin/", "linux windows mac")
    build.classify("ai/", "linux windows mac")
    build.classify("ai/config.json", "linux windows mac")
    build.classify("ai/**", None)
    build.executable("ai/bin/linux-x64/llama-server")
    build.executable("ai/bin/mac-arm64/llama-server")
    build.executable("ai/bin/mac-x64/llama-server")

    # Code that holds the spoilers or starts processes: desktop builds only (the browser asks the PC).
    build.classify("game/voice_ai.py", "linux windows mac")
    build.classify("game/voice_ai.rpyc", "linux windows mac")
    build.classify("game/model_store.py", "linux windows mac")
    build.classify("game/model_store.rpyc", "linux windows mac")
