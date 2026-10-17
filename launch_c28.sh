#!/bin/bash
cd /home/user1/rvt-research
for i in $(seq 1 120); do
  out=$(~/.local/share/offload/h1run run par28 --env rvt --dir /home/user1/rvt-research -- ./params_c28_h1.sh 2>&1)
  echo "$(date +%H:%M) $out" >> launch_c28.log
  echo "$out" | grep -q "^started" && exit 0
  sleep 240
done
