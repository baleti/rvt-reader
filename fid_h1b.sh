#!/bin/bash
# corpus evaluation on host1 (runs inside the capped rvt-offload slice; no systemd-run here). Output fidfull8/ (code of 2026-10-12 23:00).
# The slice (9 GB) is shared with other agents: before each file wait (<= 40 min) until the slice uses < 2.5 GB, smallest files first.
cd /home/user1/rvt-research; mkdir -p fidfull8; export RVT_WORKERS=${RVT_WORKERS:-1}
slice_mem() { systemctl --user show rvt-offload.slice -p MemoryCurrent --value 2>/dev/null || echo 0; }
for g in $(ls gt4/*.tsv); do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] && echo "$(stat -c %s $f) $g"; done | sort -n | while read sz g; do
  b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest
  [ -s fidfull8/$b.jsonl ] && continue
  for i in $(seq 1 240); do m=$(slice_mem); [ "$m" -lt 2600000000 ] 2>/dev/null && break; sleep 10; done
  python fidelity_full.py $f $g fidfull8/$b.jsonl 400 >> fidfull8/log.txt 2>> fidfull8/err.txt || RVT_NOFAST=1 python fidelity_full.py $f $g fidfull8/$b.jsonl 400 >> fidfull8/log.txt 2>> fidfull8/err.txt
done
echo ALLDONE >> fidfull8/log.txt
