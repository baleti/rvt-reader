#!/bin/bash
cd /home/user1/rvt-research
for p in 2024/42_Snowdon_Towers_Sample_HVAC 2024/45_Snowdon_Towers_Sample_Plumbing 2020/22_rme_basic_sample_project; do
  y=${p%%/*}; r=${p#*/}
  timeout 3500 python ana_c3/brep_gain.py corpus/$p.rvt gt4/${y}_$r.rvt.tsv > bgain_$r.txt 2>&1
done
echo ALLDONE > bgain_done.txt
