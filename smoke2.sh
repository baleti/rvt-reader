#!/bin/bash
cd /home/user1/src/rvt-viewer
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run c7smoke --env occ --dir /home/user1/src/rvt-viewer -- bash -c "tools/h1_venv.sh; tools/demo_smoke.sh ~/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt 8952 > ~/rvt-research/smoke_c7b.txt 2>&1; echo ALLDONE >> ~/rvt-research/smoke_c7b.txt" 2>&1)
  echo "$(date +%T) $out" | tail -2 >> /home/user1/rvt-research/h1retry_smoke2.log
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
