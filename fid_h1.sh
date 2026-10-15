#!/bin/bash
# corpus evaluation on host1 (runs inside the capped rvt-offload slice; no systemd-run here)
cd /home/user1/rvt-research; mkdir -p fidfull6
ls gt4/*.tsv | while read g; do b=$(basename $g .tsv); y=${b%%_*}; rest=${b#*_}; f=$(ls corpus/$y/$rest 2>/dev/null | head -1); [ -n "$f" ] || continue
  [ -s fidfull6/$b.jsonl ] && continue
  python fidelity_full.py $f $g fidfull6/$b.jsonl 400 >> fidfull6/log.txt 2>> fidfull6/err.txt || RVT_NOFAST=1 python fidelity_full.py $f $g fidfull6/$b.jsonl 400 >> fidfull6/log.txt 2>> fidfull6/err.txt
done
echo ALLDONE >> fidfull6/log.txt
