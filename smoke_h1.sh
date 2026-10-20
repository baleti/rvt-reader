#!/bin/bash
cd /home/user1/src/rvt-viewer && mkdir -p .venv/bin && ln -sf $(command -v python) .venv/bin/python; tools/demo_smoke.sh /home/user1/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt 8951 > /home/user1/rvt-research/smoke_c7.txt 2>&1
echo ALLDONE >> /home/user1/rvt-research/smoke_c7.txt
