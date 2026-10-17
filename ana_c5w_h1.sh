#!/bin/bash
cd /home/user1/rvt-research
python -u ana_c5/finder.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv RoomElem 'Area per Person,Coefficient of Utilization,Calculated Cooling Load per area,Latent Heat Gain per person,Sensible Heat Gain per person,Room Cavity Ratio' 200 > ana_c5/find_room2.txt 2>&1
python -u ana_c5/finder.py corpus/2020/22_rme_basic_sample_project.rvt gt4/2020_22_rme_basic_sample_project.rvt.tsv FamilyInstance 'Pressure Drop,Loss Coefficient,Velocity Pressure,Coefficient of Utilization' 300 Fittings > ana_c5/find_fit.txt 2>&1
echo ALLDONE >> ana_c5/find_fit.txt
