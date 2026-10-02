#!/bin/bash
# Re-render every game art asset with Blender (headless) and convert to WebP. Takes a few minutes.
#   art/build.sh                full quality, realistic art (Poly Haven + MPFB; needs the asset library)
#   art/build.sh --fast         quick low-resolution drafts (not copied to the game)
#   art/build.sh --stylised     the older low-poly art instead (no library needed)
set -e
cd "$(dirname "$0")/.."
ART="$PWD/art"
# Set BLENDER_CMD to use a different Blender, e.g. BLENDER_CMD=/opt/blender/blender
BLENDER="${BLENDER_CMD:-flatpak run --command=blender org.blender.Blender} -b --factory-startup"
if [ "$1" = "--stylised" ]; then
  $BLENDER --python "$ART/office.py" --
  $BLENDER --python "$ART/elena.py" --
else
  $BLENDER --python "$ART/office_real.py" -- "$@"
  $BLENDER --python "$ART/elena_real.py" -- "$@"
fi
[ "$1" = "--fast" ] || python3 "$ART/finalize.py"
