## End-to-end test: plays the slice against the real local model.
##
##   SDL_VIDEODRIVER=dummy RENPY_RENDERER=sw ./renpy.sh /path/to/ten-forty-one test slice
##
## It asserts the reply came from the model (ai_turns), so a broken llama-server setup cannot pass
## on written fallback lines.

testcase slice:
    description "Prologue, prove the time is wrong in the notebook, question Webb, reach lights out."
    run Jump("start")

    # Prologue: two people before the sale.
    advance until screen "choice" timeout 60
    click "Edmund Harrow, your host"
    advance until screen "choice" timeout 20
    click "Thank him for the invitation"
    advance until screen "choice" timeout 20
    click "The young man at the bar"
    advance until screen "choice" timeout 60
    assert eval (harrow_denied and minute == case.START and place == "vault")

    # Find the chart and use it to strike out 10:41.
    click "Read the climate recorder (10 min)"
    advance until screen "choice" timeout 30
    click "Open your notebook"
    click "Crane died at 10:41."
    click "The climate chart"
    advance until screen "notebook" timeout 30
    assert eval ("a_time" in struck and "chart" in found)
    click "Close"

    # Question Webb in the hall.
    advance until screen "choice" timeout 20
    click "Go somewhere else"
    click "Great Hall (2 min)"
    advance until screen "choice" timeout 20
    click "Talk to Marcus Webb"
    click "Ask Marcus a question"
    advance until screen "input" timeout 10
    type "Where were you at half past nine?"
    keysym "input_enter"
    advance until screen "choice" timeout 120
    assert eval (ai_turns == 1 and canned_turns == 0)
    click "Step away"

    # Spend the rest of the chapter in the cellar until the lights fail.
    advance until screen "choice" timeout 20
    click "Go somewhere else"
    click "Cellar (3 min)"
    advance until screen "choice" timeout 20
    click "Look at the cellar end of the duct (10 min)"
    advance until screen "choice" timeout 30
    click "Open the fuse cupboard (10 min)"
    advance until screen "choice" timeout 30
    click "Go through the bins (10 min)"
    advance until screen "slice_end" timeout 60
    assert eval ("event_lights_out" in fired and "event_bridge" in fired and len(found) == 5)
    exit
