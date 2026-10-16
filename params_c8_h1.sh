#!/bin/bash
# c8 validation on host1: RebarInSystem / Rebar / MEP changes on rebar-heavy files -> pout_c8/
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c8
for p in 2020/18_rst_basic_sample_project.rvt 2023/36_rst_basic_sample_project.rvt 2026/55_Snowdon_Towers_Sample_Structural.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c8 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c8.log 2>&1
done
echo ALLDONE >> params_c8.log
