#!/bin/bash
# retry until host1 has memory for the params job (h1run refuses below 11 GB MemAvailable)
cd /home/user1/rvt-research
for i in $(seq 1 40); do
  out=$(~/.local/share/offload/h1run run h1-par27 --env rvt --dir /home/user1/rvt-research -- ./params_c27_h1.sh 2>&1)
  echo "$(date +%H:%M) $out" >> launch_par27.log
  echo "$out" | grep -q "^started" && exit 0
  echo "$out" | grep -qi "already\|exists" && exit 0
  sleep 300
done
