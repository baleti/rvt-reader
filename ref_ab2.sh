#!/bin/bash
# A/B of all c8 view/hub param rules, geometry off (rules are not geometry-derived)
cd /home/user1/rvt-research; export RVT_WORKERS=1
rm -rf pout_refA2 pout_refB2; mkdir -p pout_refA2 pout_refB2
for f in 2020/18_rst_basic_sample_project 2020/22_rme_basic_sample_project 2020/21_rst_advanced_sample_project 2022/34_rme_basic_sample_project 2023/36_rst_basic_sample_project 2023/37_rst_advanced_sample_project 2023/38_Arch_Link_Model 2023/40_rme_basic_sample_project 2024/43_Snowdon_Towers_Sample_Structural 2024/45_Snowdon_Towers_Sample_Plumbing; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
 RVT_NOVIEWREF=1 RVT_OLDVIEWRULES=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_refA2 python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_refB2 python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_refB2/DONE
