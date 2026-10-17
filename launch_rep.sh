#!/bin/bash
cd /home/user1/rvt-research
for i in $(seq 1 120); do
  out=$(~/.local/share/offload/h1run run rep1 --env rvt --dir /home/user1/rvt-research -- python ana_c3/rep.py corpus/2020/19_Commercial_Sample_Project.rvt 2>&1)
  echo "$(date +%H:%M) $out" >> launch_rep.log
  echo "$out" | grep -q "^started" && exit 0
  sleep 240
done
