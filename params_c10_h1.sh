#!/bin/bash
# c10 delta validation on host1: structural Elevation at Top/Bottom (+ pipe fitting Fine volume, node rule categories) on rst_basic 2020, rst_advanced 2023, Snowdon Structural 2026, rme_basic 2020 -> pout_c10/; then the Cut Length analysis
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c10
for p in 2020/18_rst_basic_sample_project.rvt 2023/37_rst_advanced_sample_project.rvt 2026/55_Snowdon_Towers_Sample_Structural.rvt 2020/22_rme_basic_sample_project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c10 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c10.log 2>&1
done
./ana_c5l_h1.sh
python ana_c5/am.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv 40 > ana_c5/am_rst.txt 2>&1
echo ALLDONE >> params_c10.log
