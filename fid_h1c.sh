#!/bin/bash
# corpus evaluation on host1 (runs inside the capped rvt-offload slice; no systemd-run here). Output fidfull9/ (code of 2026-10-15: ruled fan refined volume, 2017 rebar).
# The slice (9 GB) is shared with other agents: before each file wait (<= 40 min) until the slice uses < 5.5 GB (no timeout), smallest files first.
cd /home/user1/rvt-research; mkdir -p fidfull9; export RVT_WORKERS=${RVT_WORKERS:-1}
slice_mem() { systemctl --user show rvt-offload.slice -p MemoryCurrent --value 2>/dev/null || echo 0; }
for g in $(ls gt4/*.tsv); do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest; [ -f $f ] && echo "$(stat -c %s $f) $g"; done | sort -n | while read sz g; do
  b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=corpus/$y/$rest
  [ -s fidfull9/$b.jsonl ] && continue
  while :; do m=$(slice_mem); [ "$m" -lt 5500000000 ] 2>/dev/null && break; sleep 20; done
  python fidelity_full.py $f $g fidfull9/$b.jsonl 400 >> fidfull9/log.txt 2>> fidfull9/err.txt || RVT_NOFAST=1 python fidelity_full.py $f $g fidfull9/$b.jsonl 400 >> fidfull9/log.txt 2>> fidfull9/err.txt
done
echo ALLDONE >> fidfull9/log.txt
