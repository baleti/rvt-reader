#!/bin/sh
# run_idstat.sh FILE : writes idstat/<year>_<idx>_<name>.json (name without extension) and cov5/<..>.json
f="$1"; y=$(basename $(dirname "$f")); b=$(basename "$f"); idx=${b%%_*}; rest=${b#*_}; name=${rest%.*}
mkdir -p idstat cov5
COV_IDSTAT="idstat/${y}_${idx}_${name}.json" RVT_GEOM=1 timeout 3500 python3 cov_year.py "$f" > "cov5/${y}_${idx}_${name}.json" 2> "cov5/${y}_${idx}_${name}.err"
