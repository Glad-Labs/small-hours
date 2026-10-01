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

## Skip the main menu and go straight to the game. The script ends with renpy.quit().
label main_menu:
    return

## Packaging note: the ai/ folder (llama-server binary + GGUF model) lives beside game/,
## not inside it, so it has to be added to builds explicitly. See ai/README.md.
