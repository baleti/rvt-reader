#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
for p in 2023/38_Arch_Link_Model.rvt 2020/19_Commercial_Sample_Project.rvt; do y=${p%%/*}; r=${p#*/}
  python ana_c5/rm2.py corpus/$p gt4/${y}_$r.tsv > ana_c5/rm2_${y}_$r.txt 2>&1
done
echo ALLDONE > ana_c5/rm2_done.txt
