#!/bin/bash
cd /home/user1/rvt-research
python vol_by_cat.py corpus/2026/57_Snowdon_Towers_Sample_Plumbing.rvt gt4/2026_57_Snowdon_Towers_Sample_Plumbing.rvt.tsv > volcat.out 2>&1
bash /home/user1/src/rvt-viewer/tools/demo_smoke.sh /home/user1/rvt-research/corpus/2020/20_Residential_Sample_Project.rvt 8897 > smk10.out 2>&1
bash vt_ab.sh
