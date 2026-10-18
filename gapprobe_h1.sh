#!/bin/bash
cd /home/user1/rvt-research; P=~/rvt-env/bin/python
{ $P ana_c3/gap.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 573660 573664 576007
  $P ana_c3/gap.py corpus/2020/20_Residential_Sample_Project.rvt gt4/2020_20_Residential_Sample_Project.rvt.tsv 205606 205607 159906
  $P ana_c3/gap.py corpus/2021/26_Arch_Link_Model.rvt gt4/2021_26_Arch_Link_Model.rvt.tsv 287699 288219
  $P ana_c3/gap.py corpus/2020/19_Commercial_Sample_Project.rvt gt4/2020_19_Commercial_Sample_Project.rvt.tsv 224757
  $P ana_c3/gap.py corpus/2025/48_Snowdon_Towers_Sample_HVAC.rvt gt4/2025_48_Snowdon_Towers_Sample_HVAC.rvt.tsv 1421752
} > gapprobe.out 2>&1; echo DONE >> gapprobe.out
