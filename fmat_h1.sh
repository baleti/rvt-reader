#!/bin/bash
# face-material check (gtg_fmat.py) on the oracle files -> fmat_out.txt
cd /home/user1/rvt-research; : > fmat_out.txt
for f in 2020/20_Residential_Sample_Project 2020/19_Commercial_Sample_Project 2020/18_rst_basic_sample_project; do
  echo "== $f" >> fmat_out.txt; timeout 3000 python gtg_fmat.py corpus/$f.rvt >> fmat_out.txt 2>&1
done
echo ALLDONE >> fmat_out.txt
