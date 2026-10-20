#!/bin/bash
cd /home/user1/rvt-research
timeout 3500 python ana_c3/vol_diag2.py corpus/2024/45_Snowdon_Towers_Sample_Plumbing.rvt gt4/2024_45_Snowdon_Towers_Sample_Plumbing.rvt.tsv > vd_plumb2.txt 2>&1
echo ALLDONE >> vd_plumb2.txt
