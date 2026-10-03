# Casework: a game engine on a game engine

Design notes, revised 2026-10-02 after a critique of the first draft. Status: proposal; nothing here beyond the Orchard Street prototype is built yet.

## The idea

Ren'Py is the engine. Over time we add a second, game-agnostic layer that knows how detective stories work:
people with secrets, evidence that changes what they will admit, a clock that makes every choice cost something,
and a checker that proves the case is solvable and fair. A game becomes a **content pack** for that layer, not new code. The local model is the voice of the layer and never its author.

**But the order matters: game first, engine second.** Building an engine before a game usually produces the wrong engine. So episode one is built as a game, with its data in files wherever that is natural,
and the reusable layer is extracted from what that game actually needed. The one piece worth building early is the fair-play checker, because it protects the thing that makes a mystery good.

## What similar games teach us

From the reception of existing games, as reported by 2026 roundups and Steam pages (figures drift):

- **The player should make the deduction.** *Return of the Obra Dinn* (96% positive over about 32K reviews), *The Case of the Golden Idol* (97%) and *Her Story* (89%) all work by letting the player do the clicking.
  We copy this with a notebook and a fill-in **deduction sheet**.
- **Give the AI a narrow job with a clear goal.** *Uncover the Smoking Gun* (95% positive) has you extract specific things from a suspect. *Vaudeville* (48%) and *Suck Up!* (63%) are criticised for aimless, unguided, inconsistent conversation.
  Our rule that code decides what a suspect may admit and the model only voices it follows the first pattern.
- **Never leave a blank text box.** Always show what you still need to know, keep a notebook of statements, and offer suggested questions the model does not control.
- **A distinctive look beats fidelity.** Obra Dinn and Golden Idol are known for a style. Realistic 3D at phone size risks the uncanny, so test it on real people and consider a toon or painterly pass.
- **Budget for the AI stigma.** One analyst found AI-labelled games on Steam get about 53% fewer reviews and more negative ones, and Steam requires disclosing AI that ships in the game. Be upfront about it.
- **Short sessions, a demo, a one-sentence hook.** Detective games sell through demos and Steam's festival pages.

Sources: [Vaudeville](https://store.steampowered.com/app/2240920/Vaudeville/), [Uncover the Smoking Gun](https://store.steampowered.com/app/2492290/Uncover_the_Smoking_Gun/), [Suck Up!](https://store.steampowered.com/app/2726370/Suck_Up/),
[PC Gamer on AI stigma](https://www.pcgamer.com/software/ai/data-analyst-finds-ai-stigma-on-steam-can-reduce-the-number-of-reviews-a-game-gets-by-around-53-percent-and-the-reviews-it-does-get-are-more-negative/),
[Steam's January 2026 AI disclosure update](https://gaminghq.eu/2026/01/17/steam-updates-ai-disclosure-rules-generative-tools-debate/),
[Steam Detective Fest and mystery games](https://mysterygamedev.substack.com/p/steam-detective-fest-and-the-golden-age-of-mystery-games).

## Scope: episode one first

| Build now | Not now |
|---|---|
| the notebook, working assumptions and the deduction sheet | generated and procedurally varied cases |
| four model-voiced suspects, the rest scripted | the Hardy Boys skeleton library and a second series |
| one romance, one trust meter | a sidekick and delegation, a second romance |
| the clock and its events | adaptive music stems and AI-generated music |
| about six found music tracks and 30 sound effects | a general engine; extract it after episode one plays |
| the case-file format and the fair-play checker for this one case | |

## Layers

| Layer | What it is | Status |
|---|---|---|
| 0. Ren'Py + llama.cpp | UI, saves, rollback, web export, local model | in use |
| 1. Casework core | Pure Python, no Ren'Py imports: case model, knowledge and secrets, reveal ladder, clock, director notes, reply guard, fair-play checker | prototype for one suspect (`orchard-street/game/ai_suspect.py`, `suspect_client.py`) |
| 2. Shell | Ren'Py screens driven by a case: interview, notebook, deduction sheet, map, clock HUD | one hard-coded scene exists |
| 3. Series pack | cast, places, case files, voice sheets, art list | one scene exists (Orchard Street) |
| 4. Art pipeline and library | Blender scripts, MPFB characters, Poly Haven props, `/store/asset-library` | built (`art/`) |
| 5. Audio | found tracks and effects with a licence manifest | proposal only; nothing downloaded |

Layer 1 imports nothing from Ren'Py, so it can be unit-tested headless, run on the PC server for phone play, and run in the browser build.

## Vocabulary

- **Series**: a pack with a recurring cast, a home base and a slow hidden thread.
- **Episode**: one case, 30 to 60 minutes. About 30 to 40 episodes would make roughly 30 hours, which is a long-term hope, not a plan.
- **Chapter**: a clocked segment of 8 to 15 minutes that ends on a clock event or a cliffhanger.
- **Scene**: one interview, search or walk. Each costs minutes.

## The notebook and the deduction sheet

The notebook logs every statement with its source and time, lists **working assumptions** the game has filled in (such as a time of death) with their sources, records who leaves the hall, and always shows what is still unknown.
You challenge an assumption by presenting evidence, and a correct challenge strikes it through. This makes the main twist a thing the player does, not a thing they are told.

The **deduction sheet** ends the game: a few sentences with blanks, each filled from a list and backed by evidence the player holds. A wrong blank says only that the sentence does not hold.
Every sentence has at least two evidence routes. Because the sheet is data, the checker can prove it is solvable.

## The case file

One file per episode, authored in YAML and compiled to JSON by `tools/compile_case.py` for shipping (PyYAML exists on the dev machine but not inside Ren'Py).
The rule: **the `truth` timeline is the single source of truth**; clues, alibis and what each person knows are checked against it, so the story bible and the case file are the same artifact.

Illustrative only:

```yaml
case: ten-forty-one
clock: {start: "22:48", end: "06:00"}
people:
  webb:
    ai: true                              # voiced by the model; false means scripted
    build: lean
    voice: voices/webb.md                 # public persona only; secrets never go in the prompt
    cover: {claim: "in the green room 21:08 to 21:40", breaks_if: [chart]}
    ladder:
      - {level: 1, unlocked_by: [chart]}
      - {level: 2, unlocked_by: [timer, thread]}
truth:
  - {at: "21:31", who: webb, where: vault, did: kills_crane}
clues:
  chart: {where: vault, cost: 10, shows: [crane_died_2131]}
  phone: {where: vault, cost: 5,  shows: [crane_died_2131]}
sheet:
  - {claim: crane_died_2131, routes: [[chart], [phone]]}     # any one route proves it
```

## The fair-play checker

Run at build time. A case fails the build if:

1. Any clue or statement contradicts the `truth` timeline.
2. With all clues found, more than one person still has means, build, motive and opportunity, or none does.
3. Any sheet claim has fewer than two evidence routes, or a route cannot be gathered inside the clock (shortest path through places and costs, with clock events applied).
4. A secret is unreachable: no sequence of evidence ever unlocks it.
5. A clock event removes the only way to a needed clue before the player can reach it.

## Interrogation, generalised

What `orchard-street` does for one suspect becomes a table lookup per person: the reveal ladder becomes per-secret levels unlocked by evidence or trust; `director_level()` becomes `director_level(person, evidence)`;
`violation()` takes its banned words from the person's secrets; canned fallbacks and the reply cache stay. Big confessions stay authored dialogue, because small models will not deliver them on cue (see the bakeoff).
Only people for whom free text matters are model-voiced; everyone else is scripted. Each voiced person needs a playtest run (`tests/playtest.py`) before it ships.

## The clock

Every action costs minutes, so the player cannot do everything, and the order they investigate in changes what they learn and who is still around.
Clock events fire at set times or on conditions. This is the main source of replayability, and it costs no new content.

## Sound and music (start small)

Sound does a lot of the emotional work and is cheap compared with art. For episode one: about six music tracks, one per mood, and about 30 sound effects, all found, all CC0 or CC-BY, none non-commercial.
Candidate sources, as described by 2026 roundups (check each file's own licence before use): Kenney (CC0), Freesound (about half CC0, licence per clip), OpenGameArt (mixed, check each), the Sonniss GDC bundles (royalty-free, no attribution) and Kevin MacLeod's Incompetech (credit required).
Roundups: [free sound effects and music](https://app.cinevva.com/guides/free-sound-effects-music), [free game assets](https://app.cinevva.com/guides/game-assets-guide), [free sound effects](https://assethoard.com/blog/free-sound-effects-2026).

Audio lives in the shared library at `/store/asset-library/audio/` with a per-file licence manifest, and a script generates `CREDITS.md` from it so CC-BY credits are never forgotten.
The browser build ships Opus or Ogg at a low bitrate; about 10 to 15 MB per episode is an estimate, not yet measured. A fetch script in the style of `art/fetch_assets.py` comes first, and nothing is downloaded without your say-so.

**Later, if episode one earns it:** adaptive music (stems on parallel channels, volumes driven by tension, a leitmotif per suspect), sound synthesised in code, and open-weights music models.
As of 2026 roundups, ACE-Step 1.5 is Apache-2.0 and Stable Audio 3.0 has open weights with a revenue threshold, while Meta's MusicGen weights are non-commercial. Read each model card, and note that AI-generated audio may not be copyrightable in the US.
[Best Open-Source AI Music Generators 2026](https://www.it-jim.com/blog/best-open-source-ai-music-generator/), [Boppy's roundup](https://boppy.me/blog/best-open-source-ai-music-models).
Whether several audio channels stay in sync in the Ren'Py browser build is untested.

## Later: variation and borrowed skeletons

Not for episode one. When there is a game worth extending:

- **Variation**, cheapest first: the clock already makes runs differ; cast slots can be refilled from a pool of names, faces and voice sheets; the culprit, method and motive can be reassigned from an authored menu and the checker rejects unfair seeds.
  The model never invents the mystery. Generated cases will be shallower than authored ones, so a season would mix both.
- **Skeletons from the old serial mysteries** (the wrong man, rescue the investigator, two cases one thread, the hideout, the treasure race, the missing heir), each a case file with slots.
  A second series built from them is the real test that the engine is reusable.

### Rights

Notes, not legal advice.

- In the US, the first nine Hardy Boys volumes (1927 to 1930) are in the public domain: the first three since 2023, the 1930 volume since 1 January 2026. Sources: [OSU Libraries](https://library.osu.edu/site/copyright/2023/12/06/the-hardy-boys-public-domain-in-2023/), [Wikipedia on the 1930 volume](https://en.wikipedia.org/wiki/The_Great_Airport_Mystery).
- That covers the original texts only. The revised editions from 1959 on are separately copyrighted.
- Outside the US it differs: the author's country, Canada, keeps the 1927 texts under copyright until 2048. A web game has a worldwide audience.
- I could not confirm trademark status of the series name; assume "Hardy Boys" and the character names are protected.
- Policy: take structure and premises, write fresh text, use original titles and characters. The early books carry dated attitudes, so these would be adaptations, not transcriptions.
- If a game is ever sold, have a lawyer look at it first.

## Roadmap

0. **Play what exists.** Play Orchard Street on the phone and in a desktop window and fix what feels wrong. Nobody but the developer has played it.
1. **A vertical slice.** The prologue and chapter 1 of *Ten Forty-One*, with two voiced suspects (Webb and Nell), the notebook with its pre-filled assumption, and the clock. The question it answers: is the loop fun?
2. **The case file and checker** for episode one, with tests, and the story bible compiled into it.
3. **The rest of episode one**: four voiced suspects, the deduction sheet, six places, the endings, found music and effects.
4. **Playtest** with about five people, on a phone and a desktop. Fix pacing, the model's personas and the art.
5. **Only then:** extract the reusable layer, decide how the game ships, and consider episode two.

## Risks

- **The core is unproven.** Free-text questioning with a small local model has to stay fun and consistent for 45 minutes across four personas. The slice exists to find out early.
- **Content is the bottleneck, not code.** An engine makes an episode cheaper, not free.
- **Art may land badly.** Realistic 3D at phone size can look uncanny; the stylised pass is a cheap test.
- **How it ships.** A 3.35 GB model download and slower replies on typical CPUs than the 2 seconds on the dev machine (not measured elsewhere). The phone version only works through the dev PC. Decide whether to ship desktop with a bundled model, host a model, or fall back to scripted lines.
- **AI stigma** on Steam; disclosure is required for AI that ships in the game.
- **Scope.** Thirty hours is a series, not a build. Ship episode one first.
