# Casework: a game engine on a game engine

Design notes, 2026-10-02. Status: proposal for review; nothing here beyond the Orchard Street prototype is built yet.

## The idea

Ren'Py is the engine. We add a second, game-agnostic layer on top of it that knows how detective stories work:
people with secrets, evidence that changes what they will admit, a clock that makes every choice cost something,
and a checker that proves the case is solvable and fair. A game is then a **content pack** for that layer (a cast, some
places, case files, an art list), not new code. The local model is the voice of that layer and never its author.

## Layers

| Layer | What it is | Status |
|---|---|---|
| 0. Ren'Py + llama.cpp | UI, saves, rollback, web export, local model | in use |
| 1. **Casework core** | Pure Python, no Ren'Py imports: case model, knowledge and secrets, reveal ladder, clock and events, director notes, reply guard, fair-play checker | prototype exists for one suspect (`orchard-street/game/ai_suspect.py`, `suspect_client.py`); to be generalised |
| 2. **Shell** | Generic Ren'Py screens and labels driven by a case: interview, evidence board, map and travel, notebook, clock HUD | one hard-coded scene exists |
| 3. **Series pack** | Content: cast bible, locations, case files, voice sheets, art manifest | one scene exists (Orchard Street) |
| 4. Art pipeline and library | Blender scripts, MPFB characters, Poly Haven props, `/store/asset-library` | built (`art/`) |
| 5. Audio | adaptive music, sound effects and ambience, with a licence manifest (see "Sound and music") | proposal only; nothing downloaded |

The rule that makes layers 1 and 3 separable is the one we already follow: **code decides what a person may admit; the model only voices it.**
Because layer 1 imports nothing from Ren'Py, it can be unit-tested headless, run on the PC server for phone play, and run in the browser build.

## Vocabulary and scale

- **Series**: a pack with a recurring cast, a home base and a slow hidden thread.
- **Episode**: one case, 30 to 60 minutes. The first one is the vertical slice; about 30 to 40 of them make roughly 30 hours.
- **Chapter**: a clocked segment of an episode, 8 to 15 minutes, that ends on a clock event or a cliffhanger.
- **Scene**: one interview, search or walk. Each costs minutes.

## The case file

One file per episode, authored in YAML and compiled to JSON by `tools/compile_case.py` for shipping (PyYAML exists on the dev machine but not inside Ren'Py).
The one rule: **the `truth` timeline is the single source of truth.** Clues, alibis and what each person knows are checked against it, so the story bible and the case file are the same artifact.

Illustrative only (names and values are not canon):

```yaml
case: ten-forty-one
clock: {start: "19:00", end: "06:00"}
places:
  vault:   {exits: {gallery: 2}}
  gallery: {exits: {vault: 2, hall: 1}}
truth:                                  # what really happened; nothing else may contradict it
  - {at: "21:50", who: vance, where: vault, did: kills_victim, seen_by: []}
  - {at: "22:05", who: vance, where: hall,  did: sets_clocks_to_2241}
clues:
  torn_pass:     {where: gallery, how: search, cost: 10, shows: [vance_in_vault_wing]}
  stopped_clock: {where: hall,    how: search, cost: 5,  shows: [clocks_were_set]}
people:
  vance:
    voice: voices/vance.md              # public persona only; secrets never go in the prompt
    knows: [kills_victim, sets_clocks_to_2241]
    cover: {claim: "in the gallery from 21:30", breaks_if: [torn_pass]}
    secrets:
      - {id: sets_clocks_to_2241, level: 2, unlocked_by: [stopped_clock]}
events:
  - {at: "23:30", do: lights_fail}
solution: {culprit: vance, proof: [torn_pass, stopped_clock]}
```

## The fair-play checker

Run at build time over every case file, and over every generated variant. A case fails the build if:

1. Any clue or statement contradicts the `truth` timeline.
2. With all clues found, more than one person still has means, motive and opportunity (or none does).
3. The `proof` set cannot be gathered inside the clock: shortest route through places and costs exceeds the budget, or a proof clue sits behind a person who is unreachable by then.
4. A secret is unreachable: no sequence of evidence ever unlocks it.
5. A clock event removes the only way to a proof clue before the player can get there.

This is how a plot hole such as "why was the storm convenient?" gets caught: the answer has to exist as a `truth` entry with a clue that exposes it.

## Interrogation, generalised

What `orchard-street` does for one suspect becomes a table lookup per person:
the reveal ladder (`none`, then `vault`, `vault_known`, `confess`) becomes per-secret levels unlocked by evidence; `director_level()` becomes `director_level(person, evidence)`;
`violation()` takes its banned words from the person's secrets; the canned fallbacks and reply cache stay as they are.
Big confessions stay authored dialogue, because small models will not deliver them on cue (see the bakeoff).

## The clock

Every action costs minutes. The player cannot do everything, so the order they investigate in changes what they learn and who is still around.
Clock events fire at fixed times or when a condition is met. This is the main source of replayability, and it costs no new content.

## Sound and music

Sound does a lot of the emotional work in a mystery, and it is cheap compared with art. Three ways to get it, mixed:

1. **Find it.** Only CC0 and CC-BY, never non-commercial licences. Candidate sources, as described by 2026 roundups (check each file's own licence before use): Kenney (CC0, UI clicks and impacts), Freesound (about half CC0, licence per clip),
   OpenGameArt (mixed, check each), the Sonniss GDC bundles (royalty-free, no attribution), and Kevin MacLeod's Incompetech (credit required).
   Roundups: [free sound effects and music](https://app.cinevva.com/guides/free-sound-effects-music), [free game assets](https://app.cinevva.com/guides/game-assets-guide), [free sound effects](https://assethoard.com/blog/free-sound-effects-2026).
2. **Make it with code.** Sound effects and ambience (rain, wind, thunder, clock ticks, candle crackle) can be synthesised from noise and filters in a few lines of Python, which makes them ours and licence-free.
   Music can be written as MIDI (motifs authored, arrangement generated by code) and rendered through FluidSynth with a CC0 SoundFont.
3. **Generate it.** Open-weights music models can run on the PC's GPU. As of mid-2026 roundups, ACE-Step 1.5 is Apache-2.0, Stable Audio 3.0 has open weights with a revenue threshold,
   and Meta's MusicGen weights are non-commercial, so MusicGen is out. Read each model card before relying on a roundup. Two caveats: AI-generated audio may not be copyrightable in the US (usable, but we could not claim it as exclusively ours), and quality needs curating by ear.
   Sources: [Best Open-Source AI Music Generators 2026](https://www.it-jim.com/blog/best-open-source-ai-music-generator/), [Boppy's roundup](https://boppy.me/blog/best-open-source-ai-music-models).

**The music engine** is adaptive, not a playlist. Each chapter has a bed made of three to five stems of the same tempo and length, one per Ren'Py audio channel,
and the case state sets their volumes: tension rises with the clock and falls in safe rooms; interviews add a pulse; presenting evidence that lands plays a sting; each suspect has a short **leitmotif** that rises softly when they are on screen and turns dissonant when they lie.
Clock events have sounds (a stopped-clock tick, a bolt, a generator dying). Ren'Py already has channels, fades and per-channel volume; whether several channels stay in sync in the browser build is untested.

**Housekeeping.** Audio lives in the shared library at `/store/asset-library/audio/` with a per-file licence manifest, and a script generates `CREDITS.md` from it, so CC-BY credits cannot be forgotten.
The browser build ships Opus or Ogg at a low bitrate; a budget of about 10 to 15 MB of audio per episode keeps phone loads reasonable (an estimate, not yet measured).
Nothing has been downloaded: a fetch script in the style of `art/fetch_assets.py` comes first, and downloading waits for your say-so.

## Making it different each time

Three dials, from cheapest to most expensive:

1. **Order and attention.** The clock already makes two runs of the same case play differently.
2. **Casting.** Cast slots (the nervous heir, the fixer, the loyal servant) are filled from a pool of names, faces (MPFB) and voice sheets; the timeline is the same shape with different people in it.
3. **Reassignment.** The culprit, method and motive are drawn from the authored menu of compatible combinations, the timeline is rebuilt from the skeleton, and the checker rejects any seed that is unfair. A seed makes a shareable or daily case.

What we deliberately do not do: let the model invent the mystery. Small models contradict themselves, and an unfair mystery is a bad one. Generation is code over authored parts; the model speaks inside it.
Honest limit: generated cases are shallower than hand-written twists, so each season mixes authored episodes with generated ones.

## Plot skeletons: borrowing from the old serial mysteries

The serial boys' mysteries of the late 1920s are close to a formula, which is what makes them a good source of skeletons: a hook, a false suspect, a hideout, a chase, a cliffhanger at the end of every chapter. Shapes from the early Hardy Boys volumes, and what each asks of the engine:

| Skeleton | Shape | Needs from the engine |
|---|---|---|
| The wrong man | valuables vanish, the obvious suspect is innocent, the real thief is someone who "helps" | alibi cracking, a suspect who cannot use their alibi without exposing a different secret |
| Rescue the investigator | a smuggling ring in a spooky house, and the person you are following is taken | countdown clock with a fail state |
| Two cases, one thread | a counterfeiting case and a second case turn out to share a hideout | multi-thread cases, shared clues |
| The hideout | friends vanish, there is a gang base on an island | location graph with discoverable edges |
| Treasure race | hidden gold or a family treasure, a rival gang searching too | a rival who acts on the clock |
| The missing heir | a vanished grandson and stolen medals | relationship and identity secrets |

Each skeleton is a case file with slots. A new episode is a skeleton plus a cast, a setting and a twist, which is how a long series stays affordable.
The flagship, Ten Forty-One, is a locked-circle thriller; a second series built from these skeletons (teen sleuths, daylight, a small town) is the real test that the engine is reusable.

### Rights

Notes, not legal advice.

- In the US, the first nine Hardy Boys volumes (1927 to 1930) are in the public domain: the first three since 2023, the 1930 volume since 1 January 2026. Sources: [OSU Libraries](https://library.osu.edu/site/copyright/2023/12/06/the-hardy-boys-public-domain-in-2023/), [Wikipedia on the 1930 volume](https://en.wikipedia.org/wiki/The_Great_Airport_Mystery).
- That covers the original texts only. The revised editions from 1959 on are separately copyrighted, so we must work from the originals, not from the books people read today.
- Outside the US it differs: the author's country, Canada, keeps the 1927 texts under copyright until 2048. A web game has a worldwide audience.
- I could not confirm trademark status of the series name; assume "Hardy Boys" and the character names are protected.
- Policy: take structure and premises, write fresh text, use original titles and characters. The early books also carry dated attitudes (part of why they were revised), so these are adaptations, not transcriptions.
- If a game is ever sold, have a lawyer look at it first.

## Roadmap

1. **Core.** Case schema, loader, compile step and fair-play checker, with tests. Port Orchard Street onto it; the existing `ai_interrogation` testcase must still pass unchanged.
2. **Shell.** Clock HUD, evidence board, travel screen and a generic interview label, all driven by the case.
3. **Ten Forty-One as a case file.** The story bible (`ten-forty-one.md`, checked against `FORMULA.md`) written as data and accepted by the checker; art manifest rendered from the library.
   Audio comes in alongside: fetch script and manifest, a first adaptive bed, and the cue hooks in the case file.
4. **Second pack.** A teen-sleuth series from the skeletons. Pass condition: no engine code changes.
5. **Generator.** Seeded casting and reassignment, validated by the checker.

## Risks

- **Content is the bottleneck, not code.** The engine makes an episode cheaper (a data file and a few renders), not free.
- **Art per location.** Each place needs a background; the shared library helps but a new setting still costs real time.
- **Model drift.** Guards, canned fallbacks and the reply cache exist because small models wander; every new persona needs a playtest run (`tests/playtest.py`).
- **Scope.** Thirty hours is a series, not a build. Ship episode one first.
