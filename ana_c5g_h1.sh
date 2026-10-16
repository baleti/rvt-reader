#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/va3.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 100000 "" > ana_c5/va3_rme_all.txt 2>&1
echo ALLDONE >> ana_c5/va3_rme_all.txt
