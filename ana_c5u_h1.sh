#!/bin/bash
cd /home/user1/rvt-research
python -u ana_c5/mod.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv > ana_c5/mod_rme.txt 2>&1
echo ALLDONE >> ana_c5/mod_rme.txt
