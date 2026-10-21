#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
rm -rf pout_nfA pout_nfB; mkdir -p pout_nfA pout_nfB
for f in 2024/45_Snowdon_Towers_Sample_Plumbing 2024/42_Snowdon_Towers_Sample_HVAC 2024/44_Snowdon_Towers_Sample_Electrical; do
 y=${f%%/*}; b=$(basename $f); g=gt4/${y}_${b}.rvt.tsv; [ -f $g ] || continue
 RVT_OLDVIEWRULES=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_nfA python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
 RVT_NOFAST=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_nfB python eval_params_all.py corpus/$f.rvt $g > /dev/null 2>&1
done
echo DONE > pout_nfB/DONE
