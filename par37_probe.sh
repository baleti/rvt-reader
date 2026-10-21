#!/bin/bash
cd /home/user1/rvt-probe; export RVT_WORKERS=1; mkdir -p pout_c37
for g in $(ls gt4/*.tsv); do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] && echo "$(stat -c %s $f) $g"; done | sort -n | while read sz g; do
  b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest
  [ -s pout_c37/$rest.json ] && continue
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c37 timeout 7200 /home/user1/rvt-env/bin/python eval_params_all.py $f $g >> params_c37.log 2>&1
done
echo ALLDONE >> params_c37.log
