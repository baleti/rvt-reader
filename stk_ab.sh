#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
for f in 2020/18_rst_basic_sample_project 2020/19_Commercial_Sample_Project 2020/22_rme_basic_sample_project 2024/42_Snowdon_Towers_Sample_HVAC 2024/43_Snowdon_Towers_Sample_Structural; do
 b=$(basename $f)
 RVT_NOSTACKED=1 python gt_geom_cmp.py corpus/$f.rvt stk_ab/${b}_old.jsonl > stk_ab/${b}_old.log 2>&1
 python gt_geom_cmp.py corpus/$f.rvt stk_ab/${b}_new.jsonl > stk_ab/${b}_new.log 2>&1
done
echo DONE > stk_ab/DONE
