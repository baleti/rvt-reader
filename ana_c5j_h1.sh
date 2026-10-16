#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/vfei.py corpus/2020/19_Commercial_Sample_Project.rvt 120 > ana_c5/vfei_comm.txt 2>&1
python ana_c5/vfei.py corpus/2024/47_Snowdon_Towers_Sample_Site.rvt 6 1264746 > ana_c5/vfei_site24.txt 2>&1
python ana_c5/vfei.py corpus/2024/49_Snowdon_Towers_Sample_Structural.rvt 60 > ana_c5/vfei_struct24.txt 2>&1
python ana_c5/e1.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 40 > ana_c5/e1_rme.txt 2>&1
echo ALLDONE > ana_c5/vfei_done.txt
