#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1 RVT_NOFAST=1
rm -rf pout_vtE; mkdir -p pout_vtE
for f in 2020/22_rme_basic_sample_project 2024/42_Snowdon_Towers_Sample_HVAC 2021/26_Arch_Link_Model 2026/56_Snowdon_Towers_Sample_Electrical 2020/21_rst_advanced_sample_project 2024/43_Snowdon_Towers_Sample_Structural; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_vtE python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_vtE/DONE
