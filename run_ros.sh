#!/bin/sh
cd ~/rvt-research
for f in rosetta/*.rte corpus/2024/70_*.rte corpus/2024/71_*.rte corpus/2026/75_*.rte corpus/2026/77_*.rte; do
  b=$(basename $f .rte); [ -s gtg_ros/$b.jsonl ] && continue
  systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 nice -n 10 timeout 1500 .venv3/bin/python gt_geom_cmp.py $f gtg_ros/$b.jsonl 2>&1 | tail -1
done
