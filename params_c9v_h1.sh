#!/bin/bash
# validation after restricting the node rule to electrical categories: Snowdon Structural 2026 (regressed -482) + rme_basic 2020 (gain must stay) -> pout_c9v/
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c9v
for p in 2026/55_Snowdon_Towers_Sample_Structural.rvt 2020/22_rme_basic_sample_project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c9v timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c9v.log 2>&1
done
echo ALLDONE >> params_c9v.log
