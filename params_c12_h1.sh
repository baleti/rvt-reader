#!/bin/bash
# c12 delta on host1: Snowdon-style framing elevation (no reference level), then reference point / hub probes with full scalar listing
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c12
for p in 2026/55_Snowdon_Towers_Sample_Structural.rvt 2023/37_rst_advanced_sample_project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c12 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c12.log 2>&1
done
python ana_c5/rp.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv ReferencePoint 8 'Moves With Grids,Location Mark,Associated Level,Associated Level Offset,Hosted U Parameter,Hosted V Parameter,Connection Status' > ana_c5/rp_ref2.txt 2>&1
python ana_c5/rp.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv Hub 10 'Connection Status' > ana_c5/rp_hub2.txt 2>&1
echo ALLDONE >> params_c12.log
