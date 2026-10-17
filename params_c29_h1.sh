#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c29
for p in 2020/19_Commercial_Sample_Project.rvt 2020/20_Residential_Sample_Project.rvt 2023/38_Arch_Link_Model.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c29 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c29.log 2>&1
done
echo ALLDONE >> params_c29.log
