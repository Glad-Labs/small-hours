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
WEBB="--waistcoat --crop --browstyle 6 --brow 0.07,0.07,0.075 --age 1.0 --recede 0.02"
NELL="--sweater --combbob --haircolor 0.72,1.0 --hairlen 0.075 --waves 0.06 --shine 0.4 --makeup 1.0 --shape Kat=0.0,BaseFeminine=1.0,BaseFeminine_body_bs_Body=1.0,Amala=1.0 --browstyle 4 --browcut thin --lashes 2 --brow 0.07,0.03,0.018"
POSES=(
  "webb_calm    Matt charm   12  $WEBB"
  "webb_pressed Matt pressed 12  $WEBB"
  "nell_calm    Kat  calm   -12  $NELL"
  "nell_warm    Kat  warm   -12  $NELL"
  "nell_rattled Kat  rattled -12 $NELL"
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
