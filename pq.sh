#!/bin/bash
# quick param probe on host1 (no geometry-derived params): pq.sh OUTDIR year/file ...   -> pout dir OUTDIR
cd /home/user1/rvt-research; out=$1; shift
for p in "$@"; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=${PQ_GEOM:-} RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=$out RVT_WORKERS=1 timeout 3000 ~/rvt-env/bin/python eval_params_all.py corpus/$p gt4/${y}_$r.tsv 2>&1 | tail -1
done
