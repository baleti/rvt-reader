#!/bin/bash
cd /home/user1/rvt-research
for i in $(seq 1 400); do
  out=$(~/.local/share/offload/h1run run par33 --env rvt --dir /home/user1/rvt-research -- ./params_c33_h1.sh 2>&1)
  echo "$(date +%m-%d\ %H:%M) $out" >> launch_par33.log
  echo "$out" | grep -q "^started" && exit 0
  sleep 300
done
