#!/bin/bash
cd /home/user1/rvt-research
python ana_c5/sysrec.py corpus/2020/22_rme_basic_sample_project.rvt 543599 > ana_c5/sysrec_rme.txt 2>&1
echo ALLDONE >> ana_c5/sysrec_rme.txt
