#!/bin/bash
cd /home/user1/rvt-research
python ana_c5/sec.py corpus/2024/45_Snowdon_Towers_Sample_Plumbing.rvt gt4/2024_45_Snowdon_Towers_Sample_Plumbing.rvt.tsv > ana_c5/sec_plumb.txt 2>&1
echo ALLDONE >> ana_c5/sec_plumb.txt
