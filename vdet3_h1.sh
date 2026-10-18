#!/bin/bash
cd /home/user1/rvt-research
for p in "2022/32_Arch_Link_Model 2022_32_Arch_Link_Model" "2020/22_rme_basic_sample_project 2020_22_rme_basic_sample_project" "2024/45_Snowdon_Towers_Sample_Plumbing 2024_45_Snowdon_Towers_Sample_Plumbing"; do a=${p% *}; b=${p#* }; echo "## $a"; ~/rvt-env/bin/python ana_c3/vdet3.py corpus/$a.rvt gt4/$b.rvt.tsv 25; done > vdet3.out 2>&1
echo DONE >> vdet3.out
