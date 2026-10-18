#!/bin/bash
cd /home/user1/rvt-research
for y in 2026 2024; do for f in corpus/$y/*Snowdon*.rvt; do b=$(basename $f); echo "## $y $b"; ~/rvt-env/bin/python ana_c3/vdet.py $f gt4/${y}_$b.tsv 15 2>&1 | tail -30; done; done > vdet_all.out 2>&1
echo DONE >> vdet_all.out
