#!/bin/bash
# c5 analysis 2 on host1: geometry nodes of MEP devices (controlCommand), Revit Volume vs per-node volumes
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/cc.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 150 > ana_c5/cc2_rme.txt 2>&1
echo ALLDONE >> ana_c5/cc2_rme.txt
