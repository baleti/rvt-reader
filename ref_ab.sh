#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
mkdir -p pout_refA pout_refB
for f in 2020/18_rst_basic_sample_project 2020/19_Commercial_Sample_Project 2020/20_Residential_Sample_Project 2020/22_rme_basic_sample_project 2023/38_Arch_Link_Model 2024/45_Snowdon_Towers_Sample_Plumbing 2024/49_Snowdon_Towers_Sample_Structural; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
 RVT_NOVIEWREF=1 RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_refA python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
 RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_refB python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_refB/DONE
