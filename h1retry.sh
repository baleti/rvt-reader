#!/bin/bash
# h1retry.sh NAME SCRIPT : retry h1run every 5 min until host1 has memory (run as a systemd --user unit)
cd /home/user1/rvt-research
for i in $(seq 1 600); do
  out=$(~/.local/share/offload/h1run run $1 --env rvt --dir /home/user1/rvt-research -- $2 2>&1)
  echo "$(date +%m-%d\ %H:%M) $out" >> h1retry_$1.log
  echo "$out" | grep -q "^started" && exit 0
  sleep 300
done
