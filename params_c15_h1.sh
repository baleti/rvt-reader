#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/lm.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv > ana_c5/lm_rst.txt 2>&1
echo ALLDONE >> ana_c5/lm_rst.txt
