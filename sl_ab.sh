#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1 RVT_NOFAST=1
rm -rf pout_sl; mkdir -p pout_sl
for f in 2023/37_rst_advanced_sample_project 2023/36_rst_basic_sample_project 2024/43_Snowdon_Towers_Sample_Structural; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_sl python3 eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_sl/DONE
