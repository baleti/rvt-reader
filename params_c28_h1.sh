#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c28
for p in 2020/20_Residential_Sample_Project.rvt 2020/18_rst_basic_sample_project.rvt 2020/22_rme_basic_sample_project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c28 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c28.log 2>&1
done
echo ALLDONE >> params_c28.log
