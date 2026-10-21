#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
rm -rf pout_flA pout_flB; mkdir -p pout_flA pout_flB
for f in 2020/18_rst_basic_sample_project 2020/19_Commercial_Sample_Project 2020/22_rme_basic_sample_project 2024/43_Snowdon_Towers_Sample_Structural; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
 RVT_NOELEV=1 RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_flA python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
 RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_flB python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_flB/DONE
