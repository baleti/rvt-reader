#!/bin/sh
cd /home/user1/rvt-research; mkdir -p fidfull; export XDG_RUNTIME_DIR=/run/user/1000
ls gt4/*.tsv | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull/$b.jsonl ] && continue
  systemd-run --user --scope -q -p MemoryMax=5G -p MemorySwapMax=0 nice -n 10 /home/user1/occ-env/bin/python fidelity_full.py $f $g fidfull/$b.jsonl 3000 >> fidfull/log.txt 2>> fidfull/err.txt
done
echo ALLDONE >> fidfull/log.txt
