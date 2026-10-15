#!/bin/bash
# c2-geometry parameter pipeline on host1 (capped slice): (1) rules learned on ALL gt4 files -> enum_rules_all.json (shipped as enum_rules.json after review);
# (2) every gt4 file evaluated with the TRAIN-split rules (enum_rules_train4.json) + geometry-derived values -> pout_c2g/ (test-split files = held-out numbers)
cd /home/user1/rvt-research; export RVT_WORKERS=1
[ -s enum_rules_all.json ] || RVT_NOENUM=1 python learn_enum.py enum_rules_all.json all 120 > params_c2_learn.log 2>&1
for g in gt4/*.tsv; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] || continue
  [ -s pout_c2g/$rest.json ] || RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c2g timeout 5400 python eval_params_all.py $f $g >> params_c2.log 2>&1
done
echo ALLDONE >> params_c2.log
