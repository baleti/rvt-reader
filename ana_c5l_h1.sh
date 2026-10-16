#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/cut.py corpus/2020/18_rst_basic_sample_project.rvt gt4/2020_18_rst_basic_sample_project.rvt.tsv 60 > ana_c5/cut_rst.txt 2>&1
echo ALLDONE >> ana_c5/cut_rst.txt
