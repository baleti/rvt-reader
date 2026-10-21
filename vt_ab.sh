#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1 RVT_NOFAST=1
rm -rf pout_vtD; mkdir -p pout_vtD
for f in 2020/21_rst_advanced_sample_project 2020/18_rst_basic_sample_project 2026/56_Snowdon_Towers_Sample_Electrical 2026/55_Snowdon_Towers_Sample_Structural 2024/43_Snowdon_Towers_Sample_Structural; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_vtD python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_vtD/DONE
