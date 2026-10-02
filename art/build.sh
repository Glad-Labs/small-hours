#!/bin/bash
# Re-render every game art asset with Blender (headless) and convert to WebP. Takes a few minutes.
#   art/build.sh          full quality
#   art/build.sh --fast   quick drafts (not copied to the game)
set -e
cd "$(dirname "$0")/.."
ART="$PWD/art"
# Set BLENDER_CMD to use a different Blender, e.g. BLENDER_CMD=/opt/blender/blender
BLENDER="${BLENDER_CMD:-flatpak run --command=blender org.blender.Blender} -b --factory-startup"
$BLENDER --python "$ART/office.py" -- "$@"
$BLENDER --python "$ART/elena.py" -- "$@"
[ "$1" = "--fast" ] || python3 "$ART/finalize.py"
