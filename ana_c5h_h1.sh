#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/pn2.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 575596 575853 576719 575459 > ana_c5/pn2.txt 2>&1
echo ALLDONE >> ana_c5/pn2.txt
