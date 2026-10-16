#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/sf.py corpus/2026/55_Snowdon_Towers_Sample_Structural.rvt gt4/2026_55_Snowdon_Towers_Sample_Structural.rvt.tsv 30 > ana_c5/sf_snow.txt 2>&1
echo ALLDONE >> ana_c5/sf_snow.txt
