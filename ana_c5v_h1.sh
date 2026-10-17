#!/bin/bash
cd /home/user1/rvt-research
python -u ana_c5/finder.py corpus/2020/18_rst_basic_sample_project.rvt gt4/2020_18_rst_basic_sample_project.rvt.tsv FamilyInstance 'Cut Length,End Join Cutback,Start Join Cutback,Elevation at Top Survey' 300 Structural > ana_c5/find_beam.txt 2>&1
python -u ana_c5/finder.py corpus/2023/37_rst_advanced_sample_project.rvt gt4/2023_37_rst_advanced_sample_project.rvt.tsv RoomElem 'Area per Person,Coefficient of Utilization,Calculated Cooling Load per area' 100 > ana_c5/find_room.txt 2>&1
echo ALLDONE >> ana_c5/find_room.txt
