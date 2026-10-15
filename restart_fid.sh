#!/bin/sh
cd /home/user1/rvt-research
for p in $(pgrep -f "run_fid_full"); do [ "$p" != "$$" ] && kill $p 2>/dev/null; done
for p in $(pgrep -f "fidelity_full"); do kill $p 2>/dev/null; done
sleep 2
rm -rf fidfull
nohup ./run_fid_full.sh > /dev/null 2>&1 &
echo restarted
