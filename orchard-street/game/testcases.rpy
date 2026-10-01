## End-to-end test: plays the whole prototype against the real local model.
##
##   ./renpy.sh /path/to/orchard-street test ai_interrogation
##
## It asserts that the replies really came from the model (ai_turns), because canned
## fallback lines would otherwise let a broken llama-server setup pass unnoticed.

testcase ai_interrogation:
    description "Ask a question, gather both pieces of evidence, present them, reach the confession."
    run Jump("start")

    # Intro, then the first menu.
    advance until screen "choice" timeout 60

    # Free-text question answered by the model.
    click "Ask Elena a question"
    advance until screen "input" timeout 10
    type "Where were you tonight?"
    keysym "input_enter"
    advance until screen "choice" timeout 120
    assert eval (ai_turns == 1 and canned_turns == 0)

    # Gather evidence.
    click "Examine the vault badge log"
    advance until screen "choice" timeout 20
    click "Search the staff lockers"
    advance until screen "choice" timeout 20
    assert eval (found_badge_log and found_locker)

    # Presenting the badge log makes her admit the vault visit, and nothing more.
    click "Present evidence"
    click "Present the vault badge log"
    advance until screen "choice" timeout 120
    assert eval (admitted_vault and ai_turns == 2 and not confess_now)

    # With both pieces on the table, the scripted confession takes over (no model call).
    click "Present evidence"
    click "Present the ledger from her locker"
    advance until "typical wait" timeout 60
    assert eval (confess_now and ai_turns == 2)
    exit


## Renders key screens to PNG files so layout can be reviewed without playing.
##   ./renpy.sh /path/to/orchard-street test screenshots
testcase screenshots:
    description "Capture the intro, menu, input box, a model reply and the confession."
    run Jump("start")
    pause 1.0
    screenshot "shot_1_intro.png"
    advance until screen "choice" timeout 60
    screenshot "shot_2_menu.png"
    click "Ask Elena a question"
    advance until screen "input" timeout 10
    type "Where were you tonight?"
    screenshot "shot_3_input.png"
    keysym "input_enter"
    advance
    pause 5
    screenshot "shot_4_reply.png"
    advance until screen "choice" timeout 30
    click "Examine the vault badge log"
    advance until screen "choice" timeout 20
    click "Search the staff lockers"
    advance until screen "choice" timeout 20
    click "Present evidence"
    click "Present the vault badge log"
    advance
    pause 5
    screenshot "shot_5_vault.png"
    advance until screen "choice" timeout 30
    click "Present evidence"
    click "Present the ledger from her locker"
    advance until "ten years" timeout 60
    pause 0.5
    screenshot "shot_6_confession.png"
    exit
