#!/bin/sh
cd /home/user1/rvt-research
for p in $(pgrep -f "host3_fid"); do [ "$p" != "$$" ] && kill $p 2>/dev/null; done
for p in $(pgrep -f "fidelity_full"); do kill $p 2>/dev/null; done
sleep 3
mkdir -p fidfull3_old; mv fidfull3/*.jsonl fidfull3_old/ 2>/dev/null
nohup ./host3_fid.sh > /dev/null 2>&1 &
echo restarted
