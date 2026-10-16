#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c20
for p in 2023/68_Construction-DefaultMetric.rte 2020/18_rst_basic_sample_project.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c20 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c20.log 2>&1
done
python ana_c5/rp.py corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt gt4/2024_43_Snowdon_Towers_Sample_Structural.rvt.tsv IndependentTag 12 'Leader Line,Leader Line End Condition' > ana_c5/tag_leader.txt 2>&1
python ana_c5/rp.py corpus/2020/20_Residential_Sample_Project.rvt gt4/2020_20_Residential_Sample_Project.rvt.tsv Room 8 'Occupancy Unit,Name,Area' > ana_c5/room_occ.txt 2>&1
echo ALLDONE >> params_c20.log
