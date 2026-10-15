#!/bin/bash
# parameter pipeline on host1 (capped slice): enum rules learned on the TRAIN split, then all gt4 files evaluated
#   pout_c4n/ current rules, no enum, no geometry;  pout_c4e/ + enum rules (train split);  pout_c4g/ + geometry-derived values  (test split = held-out precision)
cd /home/user1/rvt-research; export RVT_WORKERS=1
[ -s enum_rules_train.json ] || RVT_NOENUM=1 python learn_enum.py enum_rules_train.json train 60 > params_h1_learn.log 2>&1
for g in gt4/*.tsv; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] || continue
  [ -s pout_c4n/$rest.json ] || RVT_NOENUM=1 POUT_DIR=pout_c4n timeout 1500 python eval_params_all.py $f $g >> params_h1.log 2>&1
  [ -s pout_c4e/$rest.json ] || RVT_ENUM_FILE=enum_rules_train.json POUT_DIR=pout_c4e timeout 1500 python eval_params_all.py $f $g >> params_h1.log 2>&1
done
# + geometry-derived values (family instance / wall / floor / ceiling / roof Volume and Area from the decoded solids): slow, last
for g in gt4/*.tsv; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] || continue
  [ -s pout_c4g/$rest.json ] || RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train.json POUT_DIR=pout_c4g timeout 5400 python eval_params_all.py $f $g >> params_h1.log 2>&1
done
echo ALLDONE >> params_h1.log
