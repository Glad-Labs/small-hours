#!/bin/bash
# Build the downloadable packages: Windows, Linux and Mac, each with its own model server and no model
# (the game downloads the model on first run). Output goes to DEST (default /store/tfo-dist).
#   tools/build_release.sh
set -e
cd "$(dirname "$0")/.."
PROJECT="$PWD"
SDK="${RENPY_SDK:-$HOME/renpy-8.5.3-sdk}"
DEST="${DEST:-/store/tfo-dist}"
for plat in windows-x64 linux-x64 mac-arm64 mac-x64; do
  [ -x "ai/bin/$plat/llama-server" ] || [ -f "ai/bin/$plat/llama-server.exe" ] || python3 tools/fetch_llama.py "$plat"
done
python3 tests/test_case.py > /dev/null && python3 tests/test_model_store.py > /dev/null
mkdir -p "$DEST"
cd "$SDK"
for pkg in win linux mac; do
  ./renpy.sh launcher distribute "$PROJECT" --destination "$DEST" --package "$pkg" --no-update > "$DEST/build_$pkg.log" 2>&1
done
ls -la "$DEST"/TenFortyOne-*
