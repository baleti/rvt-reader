#!/bin/sh
# geometry fidelity on host3: ONE job at a time, 5G cap, nice/ionice, waits for MemAvailable >= 10 GB
cd /home/user1/rvt-research; mkdir -p fidfull3
ls gt4/*.tsv | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull3/$b.jsonl ] && continue
  while pgrep -f "fidelity_full.py" > /dev/null; do sleep 30; done
  avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); while [ "$avail" -lt 10 ]; do sleep 60; avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); done
  systemd-run --user --scope -q -p MemoryMax=5G -p MemorySwapMax=0 nice -n 15 ionice -c3 .venv3/bin/python fidelity_full.py $f $g fidfull3/$b.jsonl 3000 >> fidfull3/log.txt 2>> fidfull3/err.txt
done
echo ALLDONE >> fidfull3/log.txt
