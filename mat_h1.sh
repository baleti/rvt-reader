#!/bin/bash
# per-triangle material evaluation vs the oracle's fmatall dumps (host1, capped slice)
cd /home/user1/rvt-research; mkdir -p matall
export RVT_WORKERS=1
for f in corpus/2020/19_Commercial_Sample_Project.rvt corpus/2020/20_Residential_Sample_Project.rvt corpus/2024/45_Snowdon_Towers_Sample_Plumbing.rvt corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt corpus/2026/54_Snowdon_Towers_Sample_HVAC.rvt corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt; do
  b=$(basename $f .rvt); y=$(basename $(dirname $f))
  python mat_tri_eval.py $f > matall/${y}_$b.txt 2>&1
done
echo ALLDONE > matall/done.txt
