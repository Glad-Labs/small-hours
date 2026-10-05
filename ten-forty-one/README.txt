TEN FORTY-ONE (beta, chapter 1)

A storm, a locked vault, and a body that isn't who everyone thinks. You question the suspects in your
own words; they are voiced by a small AI model that runs entirely on your computer.

STARTING
  Windows: run TenFortyOne.exe.   Linux: run TenFortyOne.sh.
  Mac: right-click TenFortyOne.app and choose Open (the game is not yet signed by Apple).

FIRST RUN
  The game asks to download its voice model once: 3.3 GB from Google's official release (Gemma 4, Apache 2.0).
  You can start playing while it downloads. Until it finishes, suspects answer with written lines.
  It is saved here, so you only download it once:
    Windows: %LOCALAPPDATA%\TenFortyOne     Mac: ~/Library/Application Support/TenFortyOne
    Linux: ~/.local/share/TenFortyOne
  To install it by hand instead, put gemma-4-E2B_q4_0-it.gguf in that folder.

PRIVACY
  Everything you type stays on your computer. The only time the game goes online is that one download.

SPEED
  With a graphics card that has 4 GB or more of free memory, answers are near instant.
  Without one, the game uses the processor and answers take a few seconds.
  If something goes wrong, the model server's log is llama-server.log in the folder above.

See CREDITS.txt for licences.
