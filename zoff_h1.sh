#!/bin/bash
cd /home/user1/rvt-research
~/rvt-env/bin/python ana_c3/finder.py corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt gt4/2024_43_Snowdon_Towers_Sample_Structural.rvt.tsv FamilyInstance 'z Offset Value' 3000 'Framing' > zoff.out 2>&1
echo DONE >> zoff.out
