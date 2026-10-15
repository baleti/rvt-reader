#!/bin/sh
cd /home/user1/rvt-research
while pgrep -f "run_pool.py eval_params_all.py pout_log 1" > /dev/null; do sleep 20; done
./start_pout2.sh
