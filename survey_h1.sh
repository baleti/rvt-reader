#!/bin/bash
cd /home/user1/rvt-research
~/rvt-env/bin/python ana_c3/survey.py survey1.json corpus/2020/18_rst_basic_sample_project.rvt corpus/2020/19_Commercial_Sample_Project.rvt corpus/2020/20_Residential_Sample_Project.rvt corpus/2020/22_rme_basic_sample_project.rvt corpus/2023/40_rme_basic_sample_project.rvt corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt corpus/2024/44_Snowdon_Towers_Sample_Electrical.rvt corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt > survey1.log 2>&1
