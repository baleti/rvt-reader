#!/bin/bash
# corpus evaluation on host1 (runs inside the capped rvt-offload slice; no systemd-run here)
cd /home/user1/rvt-research; mkdir -p fidfull7; export RVT_WORKERS=${RVT_WORKERS:-1}
ls gt4/*.tsv | tac | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull7/$b.jsonl ] && continue
  python fidelity_full.py $f $g fidfull7/$b.jsonl 400 >> fidfull7/log.txt 2>> fidfull7/err.txt || RVT_NOFAST=1 python fidelity_full.py $f $g fidfull7/$b.jsonl 400 >> fidfull7/log.txt 2>> fidfull7/err.txt
done
echo ALLDONE-R >> fidfull7/log.txt
