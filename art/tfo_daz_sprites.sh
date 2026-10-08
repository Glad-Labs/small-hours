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
WEBB="--waistcoat --tie #3a0f18 --crop --toplen 0.05 --frizz 0.3 --clump 0.55 --liftup 0.35 --haircolor2 0.13,0.13,0.14 --hairmix 0.55 --browstyle 7 --browcut thick --brow 0.035,0.035,0.037 --lashfade 0.35 --age 1.0 --stubble 1.0 --recede 0.02 --eyetex 12 --shape BaseMasculine=1.0,Ty=0.5,head_bs_AsymmetryFaceSquareLeft=1.0,head_bs_AsymmetryFaceSquareRight=1.0,head_bs_AsymmetryFaceRoundLeft=-0.8,head_bs_AsymmetryFaceRoundRight=-0.8"
NELL="--sweater --chunky --sweatercolor #5f6f55 --combbob --haircolor 0.72,1.0 --hairlen 0.075 --waves 0.06 --shine 0.4 --makeup 1.0 --eyetex 14 --eyewide 0.5 --shape Kat=0.0,BaseFeminine=1.0,BaseFeminine_body_bs_Body=1.0,Amala=1.0 --browstyle 4 --browcut thin --lashes 2 --brow 0.07,0.03,0.018"
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
