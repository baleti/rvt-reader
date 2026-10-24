#!/bin/bash
# usage: gtg_run.sh OUTDIR  (run on host1 from ~/rvt-research)
cd /home/user1/rvt-research; mkdir -p $1
for f in corpus/2020/18_rst_basic_sample_project.rvt corpus/2020/19_Commercial_Sample_Project.rvt corpus/2020/20_Residential_Sample_Project.rvt corpus/2020/21_rst_advanced_sample_project.rvt corpus/2020/22_rme_basic_sample_project.rvt corpus/2020/23_rme_advanced_sample_project.rvt corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt; do
  [ -f "$f" ] || { echo "missing $f" >> $1/log.txt; continue; }
  python gt_geom_cmp.py $f $1/$(basename $f).jsonl >> $1/log.txt 2>&1
done; echo ALLDONE >> $1/log.txt
