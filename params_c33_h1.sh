#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c33
for p in 2020/18_rst_basic_sample_project.rvt 2020/21_rst_advanced_sample_project.rvt 2023/37_rst_advanced_sample_project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c33 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c33.log 2>&1
done
echo ALLDONE >> params_c33.log
