#!/bin/bash
# usage: probe_run.sh OUTDIR year/file ...   (in ~/rvt-probe)
cd /home/user1/rvt-probe; out=$1; shift; rm -rf $out; mkdir -p $out
for p in "$@"; do y=${p%%/*}; r=${p#*/}
  RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=$out RVT_WORKERS=1 /home/user1/rvt-env/bin/python eval_params_all.py corpus/$p.rvt gt4/${y}_$r.rvt.tsv
done
