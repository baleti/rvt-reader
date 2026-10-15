#!/bin/sh
cd ~/rvt-research
for f in 18_rst_basic_sample_project 19_Commercial_Sample_Project 20_Residential_Sample_Project; do
  systemd-run --user --scope -q -p MemoryMax=4G -p MemorySwapMax=0 nice -n 10 timeout 5400 .venv3/bin/python gt_geom_cmp.py corpus/2020/$f.rvt gtg_r6/2020_${f%%_*}.jsonl
done
