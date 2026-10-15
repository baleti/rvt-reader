#!/bin/bash
# oracle regression on host1 (capped slice): rosetta + corpus .rte files -> gtg_ros2/, 2020 triple -> gtg_r10/ (fresh dirs)
cd /home/user1/rvt-research; mkdir -p gtg_ros2 gtg_r10; export RVT_WORKERS=1
for f in rosetta/*.rte corpus/2024/70_*.rte corpus/2024/71_*.rte corpus/2026/75_*.rte corpus/2026/77_*.rte; do
  b=$(basename $f .rte); [ -s gtg_ros2/$b.jsonl ] && continue
  timeout 1500 python gt_geom_cmp.py $f gtg_ros2/$b.jsonl >> gtg_ros2/log.txt 2>&1
done
for f in 18_rst_basic_sample_project 19_Commercial_Sample_Project 20_Residential_Sample_Project; do
  [ -s gtg_r10/2020_${f%%_*}.jsonl ] || timeout 5400 python gt_geom_cmp.py corpus/2020/$f.rvt gtg_r10/2020_${f%%_*}.jsonl >> gtg_r10/log.txt 2>&1
done
echo ALLDONE >> gtg_r10/log.txt
