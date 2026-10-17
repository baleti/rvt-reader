#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c25
for p in 2020/22_rme_basic_sample_project.rvt 2024/45_Snowdon_Towers_Sample_Plumbing.rvt; do y=${p%%/*}; r=${p#*/}
  [ -f corpus/$p ] && RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c25 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c25.log 2>&1
done
echo ALLDONE >> params_c25.log
