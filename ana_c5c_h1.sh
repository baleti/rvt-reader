#!/bin/bash
# c5 analysis 3 on host1: room Area/Perimeter from the room solid vs Revit (which files / rooms are wrong)
cd /home/user1/rvt-research; export RVT_WORKERS=1
for p in 2020/20_Residential_Sample_Project.rvt 2023/38_Arch_Link_Model.rvt 2024/47_Snowdon_Towers_Sample_Site.rvt; do y=${p%%/*}; r=${p#*/}
  [ -f corpus/$p ] && python ana_c5/rm.py corpus/$p gt4/${y}_$r.tsv > ana_c5/rm_${y}_$r.txt 2>&1
done
echo ALLDONE > ana_c5/rm_done.txt
