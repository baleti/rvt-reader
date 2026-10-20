#!/bin/bash
cd /home/user1/rvt-research
for p in 2024/45_Snowdon_Towers_Sample_Plumbing 2020/22_rme_basic_sample_project 2022/33_Technical_school-current_m; do
  y=${p%%/*}; r=${p#*/}
  timeout 3000 python ana_c3/open_trust.py corpus/$p.rvt gt4/${y}_$r.rvt.tsv > otrust_$r.txt 2>&1
done
echo ALLDONE > otrust_done.txt
