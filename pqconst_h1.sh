#!/bin/bash
cd /home/user1/rvt-research
rm -rf pout_d28; ./pq.sh pout_d28 2020/22_rme_basic_sample_project.rvt 2024/43_Snowdon_Towers_Sample_Structural.rvt 2024/42_Snowdon_Towers_Sample_HVAC.rvt 2024/44_Snowdon_Towers_Sample_Electrical.rvt > pqconst.log 2>&1
echo DONE >> pqconst.log
