#!/bin/bash
# c22 final params evaluation (all validated fixes 2026-10-16 evening) on host1 (capped slice): every gt4 file, smallest first, current code (thermal/material type/omniclass/rebar/symbol/beam changes of 2026-10-15), TRAIN-split enum rules, geometry-derived values on -> pout_c30/
cd /home/user1/rvt-research; export RVT_WORKERS=1
for g in $(ls gt4/*.tsv); do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] && echo "$(stat -c %s $f) $g"; done | sort -n | while read sz g; do
  b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest
  [ -s pout_c30/$rest.json ] && continue
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c30 timeout 7200 python eval_params_all.py $f $g >> params_c30.log 2>&1
done
echo ALLDONE >> params_c30.log
