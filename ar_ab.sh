#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1 RVT_NOFAST=1
rm -rf pout_ar; mkdir -p pout_ar
for f in 2020/22_rme_basic_sample_project 2021/27_Technical_school-current_m 2024/42_Snowdon_Towers_Sample_HVAC 2020/19_Commercial_Sample_Project; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_ar python3 eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_ar/DONE
