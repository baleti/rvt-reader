#!/bin/bash
cd /home/user1/rvt-research
python ana_c5/gridrec.py corpus/2023/37_rst_advanced_sample_project.rvt 118715 118725 > ana_c5/gridrec.txt 2>&1
echo ALLDONE >> ana_c5/gridrec.txt
