#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1 RVT_NOFAST=1
rm -rf pout_rv; mkdir -p pout_rv
for f in 2020/22_rme_basic_sample_project 2021/26_Arch_Link_Model 2024/42_Snowdon_Towers_Sample_HVAC 2020/18_rst_basic_sample_project; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_rv python3 eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_rv/DONE
