#!/bin/sh
# second runner (reverse order) for fidfull4; one extra 5G job
cd /home/user1/rvt-research
ls gt4/*.tsv | sort -r | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull4/$b.jsonl ] && continue
  [ -e fidfull4/$b.lock ] && continue
  touch fidfull4/$b.lock
  avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); while [ "$avail" -lt 8 ]; do sleep 60; avail=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo); done
  systemd-run --user --scope -q -p MemoryMax=5G -p MemorySwapMax=0 nice -n 15 ionice -c3 .venv3/bin/python fidelity_full.py $f $g fidfull4/$b.jsonl 400 >> fidfull4/log.txt 2>> fidfull4/err.txt
done
echo ALLDONE-B >> fidfull4/log.txt
