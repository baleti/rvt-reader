#!/bin/bash
# c5 analysis batch on host1: (1) FamilyInstance Volume/Area ratios for MEP fixtures/fittings/curtain panels, (2) Elevation from Level misses; rme_basic 2020 + Snowdon Plumbing 2024
cd /home/user1/rvt-research; export RVT_WORKERS=1
python ana_c5/va3.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv 100000 "Electrical Fixtures,Duct Fittings,Pipe Fittings,Curtain Panels,Lighting,Plumbing" > ana_c5/va3_rme.txt 2>&1
python ana_c5/el.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv > ana_c5/el_rme.txt 2>&1
echo ALLDONE >> ana_c5/el_rme.txt
