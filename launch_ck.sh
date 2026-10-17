#!/bin/bash
cd /home/user1/rvt-research
for i in $(seq 1 120); do
  out=$(~/.local/share/offload/h1run run fidck --env rvt --dir /home/user1/rvt-research -- ./fid_ck_h1.sh 2>&1)
  echo "$(date +%H:%M) $out" >> launch_ck.log
  echo "$out" | grep -q "^started" && exit 0
  sleep 300
done
