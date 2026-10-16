#!/bin/bash
# c11 delta validation on host1: structural Elevation (z offset), AnalyticalMember releases -> pout_c11/; then the Snowdon framing elevation probe
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c11
python ana_c5/ri.py corpus/2017/05_rme_advanced_sample_project.rvt 600 > ana_c5/ri_2017.txt 2>&1
for p in 2020/18_rst_basic_sample_project.rvt 2023/37_rst_advanced_sample_project.rvt 2026/55_Snowdon_Towers_Sample_Structural.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c11 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c11.log 2>&1
done
./ana_c5m_h1.sh
python ana_c5/rp.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv ReferencePoint 14 'Moves With Grids,Location Mark,Associated Level,Associated Level Offset,Hosted U Parameter,Hosted V Parameter,Connection Status' > ana_c5/rp_ref.txt 2>&1
python ana_c5/rp.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv Hub 10 'Connection Status' > ana_c5/rp_hub.txt 2>&1
echo ALLDONE >> params_c11.log
