#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
for p in 2024/47_Snowdon_Towers_Sample_Site.rvt 2026/59_Snowdon_Towers_Sample_Site.rvt; do y=${p%%/*}; python ana_c5/prof.py topo corpus/$p 1264746 > ana_c5/prof_topo_$y.txt 2>&1; done
for p in 2017/05_rme_advanced_sample_project.rvt 2020/23_rme_advanced_sample_project.rvt; do y=${p%%/*}; python ana_c5/prof.py x corpus/$p > ana_c5/prof_x_$y.txt 2>&1; done
echo ALLDONE > ana_c5/prof_done.txt
