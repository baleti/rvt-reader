#!/bin/bash
# c6 validation on host1: files whose classes changed (node rule, room perimeter, duct fitting area, level fallback) -> pout_c6/
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c6
for p in 2020/22_rme_basic_sample_project.rvt 2023/38_Arch_Link_Model.rvt 2020/20_Residential_Sample_Project.rvt 2020/19_Commercial_Sample_Project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c6 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c6.log 2>&1
done
echo ALLDONE >> params_c6.log
