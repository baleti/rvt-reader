#!/bin/bash
# 2017-2019 files have no Revit dump: compare them with the Revit 2020/2021 dump of the SAME model (element ids survive the upgrade). Output fidold/<year>_<file>.jsonl
cd /home/user1/rvt-research; mkdir -p fidold; export RVT_WORKERS=1
pair() { case "$1" in *rst_basic*) echo gt4/2020_18_rst_basic_sample_project.rvt.tsv;; *rst_advanced*) echo gt4/2020_21_rst_advanced_sample_project.rvt.tsv;;
  *Arch_Link*) echo gt4/2021_26_Arch_Link_Model.rvt.tsv;; *rme_basic*) echo gt4/2020_22_rme_basic_sample_project.rvt.tsv;; *rme_advanced*) echo gt4/2020_23_rme_advanced_sample_project.rvt.tsv;; *) echo;; esac; }
for y in 2017 2018 2019; do for f in corpus/$y/*.rvt; do g=$(pair $f); [ -n "$g" ] || continue; b=${y}_$(basename $f)
  [ -s fidold/$b.jsonl ] || timeout 5400 python fidelity_full.py $f $g fidold/$b.jsonl 400 >> fidold/log.txt 2>> fidold/err.txt
done; done
echo ALLDONE >> fidold/log.txt
