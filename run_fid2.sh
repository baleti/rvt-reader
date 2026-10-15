#!/bin/sh
cd /home/user1/rvt-research; mkdir -p fid4; export XDG_RUNTIME_DIR=/run/user/1000
for p in 2022/35_rme_advanced_sample_project 2023/39_Technical_school-current_m 2024/47_Snowdon_Towers_Sample_Site 2024/46_Snowdon_Towers_Sample_Facades; do
  y=${p%%/*}; b=${p#*/}
  systemd-run --user --scope -q -p MemoryMax=5G -p MemorySwapMax=0 nice -n 8 /home/user1/occ-env/bin/python fidelity_eval.py corpus/$p.rvt gt4/${y}_${b}.rvt.tsv fid4/${y}_${b}.json 300 >> fid4/log.txt 2>> fid4/err.txt
done
echo ALLDONE >> fid4/log.txt
