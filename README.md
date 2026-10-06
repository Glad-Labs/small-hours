# Small Hours

A series of mystery games in which every case happens in one night, between dark and dawn. You
question the suspects in your own words, and a small language model running on your own computer
voices them: no cloud API, no player-supplied key. A Glad Labs project.

| Folder | What it is |
|---|---|
| `ten-forty-one/` | **Small Hours: Ten Forty-One**, the first case. A storm, a bolted vault, a body in the wrong coat. Chapter 1 is playable on desktop (Windows, Linux, Mac packages) and on a phone. |
| `orchard-street/` | The original one-room prototype with Elena Voss, where the approach was proven. |
| `art/` | Blender scripts that build every background and character from free assets (Poly Haven, MakeHuman, Daz). |
| `docs/` | Design, the episode formula and the story bible. |

Status: Ten Forty-One's first chapter passes its automated tests headless and has been played on a phone.
The Linux desktop package is tested; Windows and Mac packages are built but not yet tried on real machines.
The art is realistic 3D rendered in Blender from free assets, all built by scripts in `art/`.

## The design in one paragraph

Game code decides what the suspect may admit; the model only voices it. Each turn carries a
`[DIRECTOR]` note chosen from the evidence on the table, the biggest secret never enters the
model's context at all, and the climactic confession is authored dialogue, not generated. Every
model reply passes a guard (no early admissions, no leaked names, no broken character, no
repeating herself) and falls back to canned lines rather than ever spoiling the plot. Replies are
cached so Ren'Py rollback replays are identical, and a crashed model server is restarted.

## Layout

| Path | What it is |
|---|---|
| `orchard-street/` | The Ren'Py project. `game/ai_suspect.py` is the model layer; `game/script.rpy` is the story. |
| `orchard-street/ai/` | Where the `llama-server` binary and GGUF model go. See `ai/README.md`. |
| `art/` | Blender scripts that build and render the background and the character, fetch the shared asset library and convert to WebP. See `art/README.md`. |
| `orchard-street/tools/serve_web.py` | Serves the browser build and the model to a phone over Tailscale. |
| `orchard-street/tests/` | Module tests, a messy-input play-test and saved play-test runs. |
| `bakeoff/` | The model comparison that picked the candidates (CPU only, 4 threads) and its raw results. |
| `docs/DESIGN.md` | Proposal for the reusable "casework" layer on top of Ren'Py: case files, fair-play checker, episodes and series, sound and music. |
| `docs/FORMULA.md` | The episode checklist: what well-loved mysteries share, including humor, romance and sound. |
| `docs/ten-forty-one.md` | Draft story bible for episode one: cast, true timeline, clue map, twists, endings. |

## Findings so far

- **Models (bakeoff):** Gemma 4 E2B (QAT q4_0, Apache-2.0) and Granite 4.2 3B (Apache-2.0) both
  kept secrets and produced valid JSON. LFM2.5 1.2B and Granite 4.0 350M were unusable for this.
- **Neither good model will deliver the dramatic confession on cue** (0/5 for Gemma even when told
  to), so that scene is scripted.
- **Safe prompts are not enough:** the first persona kept every secret but recited the same alibi in
  100% of answers. The play-test now measures that, and the current prompts cut it to 36%.
- Replies take about 1.2 s on 4 CPU threads of a fast desktop; expect slower on typical player
  hardware (not measured).

## Running it

Needs the [Ren'Py SDK](https://www.renpy.org/latest.html) (developed against 8.5.3), a
`llama-server` binary and a GGUF model in `orchard-street/ai/` (see `ai/README.md`).

```
/path/to/renpy-sdk/renpy.sh orchard-street                      # play
python3 orchard-street/tests/test_ai_suspect.py                 # model layer, needs the server
python3 orchard-street/tests/playtest.py                        # messy-input play-test
SDL_VIDEODRIVER=dummy RENPY_RENDERER=sw \
  /path/to/renpy-sdk/renpy.sh orchard-street test ai_interrogation   # whole game, headless
```

## Playing from a phone (Tailscale)

A browser cannot run threads, sockets or a model server, so the web build asks this PC for each
answer: the page POSTs to `/api/suspect` on the same server that served it, using `renpy.fetch`.
The persona prompt (`game/ai_suspect.py`) and the model stay on the PC and are not in the web build.

```
# once: build the browser version (needs the Ren'Py web package in the SDK's web/ folder)
/path/to/renpy-sdk/renpy.sh launcher web_build orchard-street --destination orchard-street/build/web

# whenever you want to play: needs the PC on, Tailscale on both devices
python3 orchard-street/tools/serve_web.py     # prints the address to open on the phone
```

The server binds to the Tailscale address only, never `0.0.0.0`, so only devices on your own
tailnet can reach it. There is no other login, so do not put it behind `tailscale funnel`. Hold the
phone in landscape; tapping the text field opens the phone's keyboard. Tests:
`python3 orchard-street/tests/test_serve_web.py`.

## Licensing

The code in this repository is licensed under the Apache License 2.0 (see `LICENSE`).

The models and the `llama-server` binary are not part of this repository and carry their own
licences. The ones tested here are Apache-2.0 (Gemma 4, Granite) and the LFM Open License (free
below US$10M annual revenue). Check them before shipping any model inside a game.
