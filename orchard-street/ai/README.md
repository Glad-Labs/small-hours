# ai/ — the bundled local model

The game talks to a `llama-server` process (llama.cpp) that it starts itself on a random
localhost port and stops on exit. Nothing here needs Ollama or the internet.

```
ai/
  config.json          threads, context size, GPU layers, token limit
  bin/llama-server     the llama.cpp server binary
  models/suspect.gguf  the model weights
  llama-server.log     written at runtime
```

## Development setup (this machine)

Both files are symlinks, so nothing was copied:

- `bin/llama-server` -> `/usr/local/lib/ollama/llama-server` (the copy that ships with Ollama)
- `models/suspect.gguf` -> Ollama's stored blob for Gemma 4 E2B (QAT q4_0, 3.35 GB, Apache-2.0)

If you ever `ollama rm` that model, the link dangles and the game falls back to canned lines
(the HUD shows "AI: offline"). The Ollama binary also depends on libraries in the same folder,
so it is a dev convenience only, **do not ship it**.

## Shipping to players

1. Download an official llama.cpp release build for each target OS from
   <https://github.com/ggml-org/llama.cpp/releases> (the plain CPU build is the safest;
   a Vulkan build is faster on machines with a GPU). Put the binary and the shared libraries
   from the same archive in `bin/`.
2. Copy the model file into `models/suspect.gguf` (a real copy, not a symlink). Gemma 4 E2B
   and Granite 4.2 3B are both Apache-2.0; keep the licence text with the game.
3. `game/options.rpy` already puts `ai/` (and `game/ai_suspect.py`) into the desktop packages and
   keeps them out of the web build, along with `tests/`, `tools/` and `build/`. Ren'Py packs
   everything in the project folder by default, so check the size of the zip before you ship
   (a stray model symlink once made a 3 GB web build).
4. Windows: `ai_suspect.py` already hides the console window; the "stop llama-server if the
   game dies" safeguard is Linux-only for now, so test that a crash does not leave one running.

## Tuning

- `threads`: CPU threads for generation. 4 is the conservative floor used in the bakeoff.
- `gpu_layers`: 0 = CPU only. With a GPU build, a large value such as 99 offloads every layer.
- `max_tokens`: Elena's replies are 1-3 sentences, so 120 is generous.
- To try another model, drop its GGUF in `models/` and point `model` at it. If the model
  "thinks" before answering, the server is already started with `--reasoning off`.

## Checks

```
python3 tests/test_ai_suspect.py                                   # module against the real server
SDL_VIDEODRIVER=dummy RENPY_RENDERER=sw \
  /home/mattm/renpy-8.5.3-sdk/renpy.sh . test ai_interrogation      # whole game, headless
```

## Tuning Elena (tests/playtest.py)

`python3 tests/playtest.py` throws ~40 messy player inputs (small talk, accusations, off-topic,
other languages, jailbreaks, a fake `[DIRECTOR]` note, guessed names) plus an 8-turn chained
conversation at the real model, and prints every reply with guard statistics. Saved runs are in
`tests/results/`. The first prompts kept every secret but made her a broken record:

| | v1 (safety-only prompts) | v3 (current) |
|---|---|---|
| alibi recited in "reveal nothing" answers | 100% | 36% (mostly when accused, which is natural) |
| distinct lines out of 33 | 19 | 32 |
| said "I have no family" (contradicts the confession) | yes | blocked by the guard |
| verbal tics (e.g. "I prefer the quiet") | none measured | top repeated phrase is the alibi itself |
| model answered / canned fallback | 43 / 0 | 43 / 0 |
| median reply time (CPU, 4 threads) | 1.5 s | 1.2 s |

Lessons: a "say nothing" instruction makes small models parrot the safe line, so tell them to answer
the actual question; any conditional instruction in a director note ("if he asks why...") gets
applied to every turn; and example lines in the prompt turn into catchphrases.

## Known limitations

- The model can invent small facts ("I saw it when I left"). Anything that must stay consistent
  with the authored confession should be added to the persona or blocked in `violation()`.
- After admitting the vault visit she sometimes still insists she was in the reading room all evening.
- Player text has square brackets stripped so it cannot pose as a `[DIRECTOR]` note, but the model can
  still be talked into odd behaviour; the guard (not the prompt) is what protects the plot.
- If llama-server dies it is restarted up to 3 times; after that the game uses canned lines.
