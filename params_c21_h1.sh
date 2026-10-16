#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1; mkdir -p pout_c21
python ana_c5/rp.py corpus/2020/20_Residential_Sample_Project.rvt gt4/2020_20_Residential_Sample_Project.rvt.tsv RoomElem 10 'Occupancy Unit,Name,Area' > ana_c5/room_occ.txt 2>&1
for p in 2024/43_Snowdon_Towers_Sample_Structural.rvt; do y=${p%%/*}; r=${p#*/}
  RVT_PARAMS_GEOM=1 RVT_ENUM_FILE=enum_rules_train4.json POUT_DIR=pout_c21 timeout 7200 python eval_params_all.py corpus/$p gt4/${y}_$r.tsv >> params_c21.log 2>&1
done
echo ALLDONE >> params_c21.log
