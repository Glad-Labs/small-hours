#!/usr/bin/env python3
"""Checks for the case data, its rules and the voice guard. No model needed.

    python3 tests/test_case.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import case  # noqa: E402
import voice_ai  # noqa: E402
import voices  # noqa: E402

failures = []


def check(cond, what):
    print(("  ok    " if cond else "  FAIL  ") + what)
    if not cond:
        failures.append(what)


print("== clock and places")
check(case.clock_text(case.START) == "10:48 pm", "chapter 1 starts at 10:48 pm")
check(case.clock_text(case.hm(24, 15)) == "12:15 am", "the clock runs past midnight")
check(case.travel_cost("vault", "cellar") == 5, "vault to cellar goes through the hall (2 + 3)")
check(case.travel_cost("hall", "hall") == 0, "staying put is free")

print("== data is consistent")
script = open(os.path.join(ROOT, "game", "script.rpy")).read()
labels = set(re.findall(r"^label (\w+)", script, re.M))
for c, d in case.CLUES.items():
    check(d["place"] in case.PLACES, "clue %s is in a real place" % c)
    if d["action"]:
        check("clue_" + c in labels, "clue %s has a narration label" % c)
for aid, a in case.ASSUMPTIONS.items():
    check(all(c in case.CLUES for c in a["breaks"] + a["hints"]), "belief %s names real clues" % aid)
    check("broke_" + aid in labels, "belief %s has a 'struck out' label" % aid)
    for c in a["hints"]:
        check("hint_%s_%s" % (aid, c) in labels, "hint %s/%s has a label" % (aid, c))
for _, label in case.EVENTS:
    check(label in labels, "event %s has a label" % label)
for p, d in case.PEOPLE.items():
    for fact, conds in d["facts"]:
        check(fact in voice_ai.FACTS[p], "%s's fact %s has words in voice_ai" % (p, fact))
        for kind, what in conds:
            check(what in (case.ASSUMPTIONS if kind == "struck" else case.CLUES), "%s/%s unlock names something real" % (p, fact))

print("== fairness: every belief can be overturned in time")
for aid, a in case.ASSUMPTIONS.items():
    cheapest = min(case.travel_cost("vault", case.CLUES[c]["place"]) + case.CLUES[c]["cost"] for c in a["breaks"])
    check(case.START + cheapest < case.LIGHTS_OUT, "%s can be broken before the lights go (cheapest %d min)" % (aid, cheapest))
total = min(case.CLUES["chart"]["cost"], case.CLUES["phone"]["cost"]) + case.CLUES["duct"]["cost"]
check(case.START + total < case.LIGHTS_OUT, "all three beliefs can fall in one chapter (%d min of evidence)" % total)

print("== rules")
check(case.challenge("a_time", "chart") == "breaks", "the chart breaks 10:41")
check(case.challenge("a_time", "watch") == "hint", "the watch only hints")
check(case.challenge("a_sealed", "phone") == "no", "the phone says nothing about the door")
check(case.impossible(["a_harrow"]), "Harrow ruled out but 10:41 standing is the impossible crime")
check(not case.impossible(["a_harrow", "a_time"]), "...and stops being impossible once the time falls")
check(case.unlocked_facts("nell", [], []) == [], "Nell admits nothing at first")
check(case.unlocked_facts("nell", ["a_sealed"], []) == ["knows_duct"], "breaking the sealed vault unlocks Nell's duct")
check(case.unlocked_facts("nell", [], ["duct"]) == ["knows_duct"], "showing her the duct does too")
check(case.unlocked_facts("webb", [], ["chart"]) == ["time_broken"], "showing Webb the chart makes him concede the time")
check(case.due_events(case.hm(23, 6), []) == ["event_phones", "event_bridge"], "events fire in order once due")
check(case.due_events(case.hm(23, 6), ["event_phones", "event_bridge"]) == [], "and only once")
check(case.open_questions([], []), "there is always something still unknown at the start")

print("== voice requests and guard")
check(voices.valid_request("nell", ["knows_duct"]), "a known fact is a valid request")
check(not voices.valid_request("nell", ["time_broken"]), "another person's fact is not")
check(not voices.valid_request("harrow", []), "an unvoiced person is not")
v = voice_ai.violation
check(v("nell", [], {"line": "There's an old ventilation grille in there."}) is not None, "Nell can't mention the duct early")
check(v("nell", ["knows_duct"], {"line": "I've used the duct to move frames."}) is None, "...but can once it is unlocked")
check(v("nell", [], {"line": "I've got a ledger and a set of keys."}) is not None, "Nell can't hint she has the ledger")
check(v("nell", [], {"line": "I painted them myself."}) is not None, "Nell can't admit the forgeries")
check(v("webb", [], {"line": "I went down to the cellar for a smoke."}) is not None, "Webb can't put himself in the cellar")
check(v("webb", [], {"line": "I killed him, of course."}) is not None, "nobody admits harm")
check(v("webb", [], {"line": "Then let's spend it wisely. Going once on a better question, going twice..."}) is not None,
      "copying a persona example is rejected")
check(v("webb", [], {"line": "Ten forty-one. Write it down, my dear."}) is None, "an ordinary Webb line passes")
check("Webb" not in voice_ai.PERSONAS["nell"] or "kill" not in voice_ai.PERSONAS["nell"].lower(), "Nell's prompt does not say who did it")
check("killed crane" not in voice_ai.PERSONAS["webb"].lower(), "Webb's prompt does not contain the truth")

print("\n%s" % ("ALL CHECKS PASSED" if not failures else "%d FAILED" % len(failures)))
sys.exit(1 if failures else 0)
