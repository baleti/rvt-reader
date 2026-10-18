#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c32
for p in 2024/47_Snowdon_Towers_Sample_Site.rvt 2024/44_Snowdon_Towers_Sample_Electrical.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c32 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c32.log 2>&1
done
echo ALLDONE >> params_c32.log
