#!/bin/bash
# Render the game's character sprites from Daz Genesis 9 characters into art/out/tfo_daz/.
#   art/tfo_daz_sprites.sh            full size (1050x1400), about 10 minutes per pose
#   FAST=1 art/tfo_daz_sprites.sh     drafts (525x700)
# Optional first argument: only this pose, e.g. nell_warm
cd "$(dirname "$0")" || exit 1
ART="$(pwd)"
OUT="$ART/out/tfo_daz"; mkdir -p "$OUT"
FASTFLAG=""; SUF=""
if [ -n "$FAST" ]; then FASTFLAG="--fast"; SUF="_fast"; fi

# name  character  expression  yaw  extra flags
POSES=(
  "webb_calm    Matt charm   12  --waistcoat --crop --brow 0.07,0.07,0.075"
  "webb_pressed Matt pressed 12  --waistcoat --crop --brow 0.07,0.07,0.075"
  "nell_calm    Kat  calm   -12  --sweater --combbob"
  "nell_warm    Kat  warm   -12  --sweater --combbob"
  "nell_rattled Kat  rattled -12 --sweater --combbob"
)
for line in "${POSES[@]}"; do
  set -- $line
  name=$1; char=$2; expr=$3; yaw=$4; shift 4
  [ -n "$ONLY" ] && [ "$ONLY" != "$name" ] && continue
  for try in 1 2 3; do
    o=$(flatpak run --command=blender --filesystem=/store org.blender.Blender -b --factory-startup \
        --python "$ART/tfo_daz.py" -- "$char" "$OUT/${name}${SUF}.png" $FASTFLAG --sprite --arms 14 --expr "$expr" --yaw "$yaw" "$@" 2>&1)
    echo "$o" | grep -q "merge-dirs" && { sleep 5; continue; }
    echo "$o" | grep -E "WROTE|Traceback|rror" | head -3
    break
  done
done
