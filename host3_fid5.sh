#!/bin/sh
# geometry fidelity on host3: ONE job at a time, 5G cap, nice/ionice, waits for MemAvailable >= 10 GB
cd /home/user1/rvt-research; mkdir -p fidfull5
ls gt4/*.tsv | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull5/$b.jsonl ] && continue; [ -e fidfull5/$b.lock ] && continue; touch fidfull5/$b.lock
  :
  avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); while [ "$avail" -lt 3 ]; do sleep 60; avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); done
  systemd-run --user --scope -q -p MemoryMax=3500M -p MemorySwapMax=0 nice -n 15 ionice -c3 .venv3/bin/python fidelity_full.py $f $g fidfull5/$b.jsonl 400 >> fidfull5/log.txt 2>> fidfull5/err.txt || RVT_NOFAST=1 systemd-run --user --scope -q -p MemoryMax=3500M -p MemorySwapMax=0 nice -n 15 ionice -c3 .venv3/bin/python fidelity_full.py $f $g fidfull5/$b.jsonl 400 >> fidfull5/log.txt 2>> fidfull5/err.txt
done
echo ALLDONE >> fidfull5/log.txt
