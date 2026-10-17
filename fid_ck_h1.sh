#!/bin/bash
# regression check of mesh changes on host1: curved-face-heavy files -> fidck/ (compare with fidfull9)
cd /home/user1/rvt-research; mkdir -p fidck; export RVT_WORKERS=1
for b in 2024_46_Snowdon_Towers_Sample_Facades.rvt 2026_58_Snowdon_Towers_Sample_Facades.rvt 2020_20_Residential_Sample_Project.rvt 2024_47_Snowdon_Towers_Sample_Site.rvt; do
  y=${b%%_*}; rest=${b#*_}
  python fidelity_full.py corpus/$y/$rest gt4/$b.tsv fidck/$b.jsonl 400 >> fidck/log.txt 2>> fidck/err.txt
done
echo ALLDONE >> fidck/log.txt
