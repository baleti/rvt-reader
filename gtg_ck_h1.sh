#!/bin/bash
cd /home/user1/rvt-research; mkdir -p gtgck
for f in corpus/2020/20_Residential_Sample_Project.rvt corpus/2020/19_Commercial_Sample_Project.rvt; do python gt_geom_cmp.py $f gtgck/$(basename $f).jsonl >> gtgck/log.txt 2>&1; done; echo ALLDONE >> gtgck/log.txt
