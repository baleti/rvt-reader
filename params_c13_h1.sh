#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c13
python ana_c5/hub2.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv > ana_c5/hub2_rst.txt 2>&1
RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c13 timeout 7200 python eval_params_all.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv >> params_c13.log 2>&1
echo ALLDONE >> params_c13.log
