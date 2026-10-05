"""Ten Forty-One, episode one: the case as data, and the small rules that read it.

Pure Python with no Ren'Py imports, so it runs in the browser build and in plain unit tests
(tests/test_case.py). Game state lives in the Ren'Py store as plain lists and dicts, and these
functions take it as arguments, so rollback and saving never see anything unusual.

Spoilers stay out of this file: it says WHEN a person may admit something (by fact id), never
WHAT they admit. The words the model is given live in voice_ai.py, which only runs on the PC.
See docs/ten-forty-one.md for the whole story.
"""


def hm(h, m):
    """Minutes since midnight of the auction day; after midnight keep counting past 24:00."""
    return h * 60 + m


START = hm(22, 48)          # chapter 1 opens as the detective reaches the vault
LIGHTS_OUT = hm(23, 30)     # end of the slice

QUESTION_COST = 2           # minutes per question or piece of evidence shown


def clock_text(minute):
    h, m = divmod(minute % (24 * 60), 60)
    return "%d:%02d %s" % (h % 12 or 12, m, "am" if h < 12 else "pm")


# --- Places -------------------------------------------------------------------------
PLACES = {
    "hall":   {"name": "Great Hall"},
    "vault":  {"name": "Vault"},
    "cellar": {"name": "Cellar"},
    "study":  {"name": "Harrow's study"},
    "office": {"name": "Registrar's office"},
}

# Walking minutes from the Great Hall; everywhere else is reached through it.
FROM_HALL = {"vault": 2, "cellar": 3, "study": 1, "office": 1}


def travel_cost(a, b):
    if a == b:
        return 0
    return FROM_HALL.get(a, 0) + FROM_HALL.get(b, 0)


# --- Clues --------------------------------------------------------------------------
# "label" is the Ren'Py label that narrates finding it; "note" is the notebook line.
CLUES = {
    "body":   {"place": "vault",  "cost": 0,  "action": None,
               "title": "Crane's body", "note": "Julian Crane, not Harrow, in Harrow's coat. A flat round blow to the back of the head. In the coat: his notebook: \"strokes left-handed. Do not certify.\""},
    "watch":  {"place": "vault",  "cost": 5,  "action": "Examine Crane's wristwatch",
               "title": "Crane's watch", "note": "Stopped at 10:41, crystal smashed, but the crown is pulled out. Someone set it by hand."},
    "duct":   {"place": "vault",  "cost": 5,  "action": "Search the walls and the door",
               "title": "The duct grille", "note": "Door bolted from inside. Low on the back wall, a ventilation grille off its screws, leaning against the wall. A slim person could crawl through."},
    "chart":  {"place": "vault",  "cost": 10, "action": "Read the climate recorder",
               "title": "The climate chart", "note": "Spring-driven paper chart, not on the mains. The warmth and damp of a living person in the sealed vault stop at 9:31."},
    "phone":  {"place": "vault",  "cost": 5,  "action": "Check Crane's phone",
               "title": "Crane's phone", "note": "His wife's text read at 9:26. Her next, at 9:45, never opened."},
    "thread": {"place": "cellar", "cost": 10, "action": "Look at the cellar end of the duct",
               "title": "Silver-grey thread", "note": "Fresh scuffs at the cellar-side grille, and a silver-grey wool thread caught on its edge."},
    "timer":  {"place": "cellar", "cost": 10, "action": "Open the fuse cupboard",
               "title": "The timer", "note": "A plug-in timer on the clock circuit: off at 10:41, on at 10:42. That is why every clock stopped."},
    "gavel":  {"place": "cellar", "cost": 10, "action": "Go through the bins",
               "title": "The ivory gavel", "note": "Webb's grandfather's ivory gavel, wrapped in a rag. The head is cracked and stained dark."},
    "letter": {"place": "study",  "cost": 10, "action": "Search Harrow's desk",
               "title": "Burnt letter", "note": "Half-burnt, in Harrow's hand: \"...every Calder sold since 2019 through Aldous & Pryce is...\""},
    "shelf":  {"place": "office", "cost": 5,  "action": "Look over Nell's office",
               "title": "Empty shelf", "note": "A labelled gap on the shelf: CALDER: SALES LEDGER."},
}

CLUE_ORDER = ["body", "watch", "duct", "chart", "phone", "thread", "timer", "gavel", "letter", "shelf"]


def searches_here(place, found):
    """Clues the player can still look for in this place, in a stable order."""
    return [c for c in CLUE_ORDER if CLUES[c]["place"] == place and CLUES[c]["action"] and c not in found]


# --- Working assumptions ------------------------------------------------------------
# What everyone believes at 10:48, filled into the notebook for the player. Each can be
# challenged with evidence: "breaks" strikes it through, "hints" is a step in the right direction.
ASSUMPTIONS = {
    "a_time":   {"text": "Crane died at 10:41.",
                 "source": "every clock in the house, Crane's watch, Pike, Webb",
                 "breaks": ["chart", "phone"], "hints": ["watch", "timer"]},
    "a_sealed": {"text": "The vault was sealed. Nobody could get in or out.",
                 "source": "Nell",
                 "breaks": ["duct"], "hints": []},
    "a_harrow": {"text": "Harrow killed him and ran.",
                 "source": "Webb",
                 "breaks": ["duct"], "hints": ["letter"]},
}

ASSUMPTION_ORDER = ["a_time", "a_sealed", "a_harrow"]


def challenge(assumption, clue):
    """Result of presenting `clue` against `assumption`: "breaks", "hint" or "no"."""
    a = ASSUMPTIONS[assumption]
    if clue in a["breaks"]:
        return "breaks"
    if clue in a["hints"]:
        return "hint"
    return "no"


def open_questions(found, struck):
    """What the notebook says is still unknown, so the player always has a next step."""
    out = []
    if "a_time" not in struck:
        out.append("Did he really die at 10:41?")
    if "a_sealed" not in struck:
        out.append("How did the killer get out of a vault bolted from inside?")
    elif "thread" not in found:
        out.append("Where does the duct come out?")
    if "a_harrow" not in struck:
        out.append("Where is Harrow, and could he have done it?")
    if "a_time" in struck and "a_harrow" in struck:
        out.append("Who in this house was out of sight around 9:30?")
    return out


def impossible(struck):
    """The moment the crime becomes impossible: Harrow is ruled out but 10:41 still stands."""
    return "a_harrow" in struck and "a_time" not in struck


# --- People ---------------------------------------------------------------------------
# Who can be questioned in chapter 1, and the facts each may admit. A fact unlocks when ANY of
# its conditions is met: ("struck", assumption) or ("shown", clue shown to this person).
PEOPLE = {
    "webb": {"name": "Marcus Webb", "where": "hall", "voiced": True,
             "facts": [
                 ("time_broken", [("struck", "a_time"), ("shown", "chart"), ("shown", "phone")]),
                 ("gavel",       [("shown", "gavel")]),
                 ("thread",      [("shown", "thread")]),
             ]},
    "nell": {"name": "Nell Ashby", "where": "hall", "voiced": True,
             "facts": [
                 ("knows_duct", [("struck", "a_sealed"), ("shown", "duct")]),
                 ("the_note",   [("shown", "body")]),
                 ("the_ledger", [("shown", "shelf")]),
             ]},
}

FACT_IDS = {p: [f for f, _ in d["facts"]] for p, d in PEOPLE.items()}


def unlocked_facts(person, struck, shown):
    """Fact ids this person may admit now. `shown` is the list of clues shown to them."""
    out = []
    for fact, conditions in PEOPLE[person]["facts"]:
        for kind, what in conditions:
            if (kind == "struck" and what in struck) or (kind == "shown" and what in shown):
                out.append(fact)
                break
    return out


# --- Clock events ---------------------------------------------------------------------
EVENTS = [
    (hm(22, 58), "event_phones"),
    (hm(23, 5), "event_bridge"),
    (LIGHTS_OUT, "event_lights_out"),
]


def due_events(minute, fired):
    """Event labels whose time has come and that have not fired yet, earliest first."""
    return [label for at, label in EVENTS if at <= minute and label not in fired]
