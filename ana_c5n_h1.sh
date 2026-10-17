#!/bin/bash
cd /home/user1/rvt-research
python ana_c5/lf.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 431741 431839 432045 432067 > ana_c5/lf_rme.txt 2>&1
python ana_c5/door.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 576049 573586 573749 579166 > ana_c5/door_rme.txt 2>&1
echo ALLDONE >> ana_c5/lf_rme.txt
