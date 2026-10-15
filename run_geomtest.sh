#!/bin/sh
# usage: run_geomtest.sh SCRIPT OUTDIR   -> runs SCRIPT corpus-file gt-file for every gt4 tsv with a matching corpus file
cd /home/user1/rvt-research; mkdir -p "$2"
for g in gt4/*.tsv; do b=$(basename "$g" .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] && echo "$f $g"; done | xargs -P 4 -L 1 sh -c 'n=$(basename "$1"); /home/user1/occ-env/bin/python '"$1"' "$1" "$2" > '"$2"'/${n}.out 2> '"$2"'/${n}.err' sh
