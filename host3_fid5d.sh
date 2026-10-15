#!/bin/sh
# second runner (reverse order) for fidfull5; one extra 5G job
cd /home/user1/rvt-research
ls gt4/*.tsv | awk "NR>45" | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull5/$b.jsonl ] && continue
  [ -e fidfull5/$b.lock ] && continue
  touch fidfull5/$b.lock
  avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); while [ "$avail" -lt 8 ]; do sleep 60; avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); done
  systemd-run --user --scope -q -p MemoryMax=5G -p MemorySwapMax=0 nice -n 15 ionice -c3 .venv3/bin/python fidelity_full.py $f $g fidfull5/$b.jsonl 400 >> fidfull5/log.txt 2>> fidfull5/err.txt
done
echo ALLDONE-D >> fidfull5/log.txt
