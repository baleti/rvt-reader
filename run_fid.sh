#!/bin/sh
cd /home/user1/rvt-research; mkdir -p fid
for p in 2020/18_rst_basic_sample_project 2021/24_rst_basic_sample_project 2022/30_rst_basic_sample_project 2023/36_rst_basic_sample_project 2024/43_Snowdon_Towers_Sample_Structural 2025/49_Snowdon_Towers_Sample_Structural 2026/55_Snowdon_Towers_Sample_Structural; do
  y=${p%%/*}; b=${p#*/}
  systemd-run --user --scope -q -p MemoryMax=6G -p MemorySwapMax=0 nice -n 8 /home/user1/occ-env/bin/python fidelity_eval.py corpus/$p.rvt gt4/${y}_${b}.rvt.tsv fid/${y}_${b}.json 300 >> fid/log.txt 2>> fid/err.txt
done
echo ALLDONE >> fid/log.txt
