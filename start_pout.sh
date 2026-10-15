#!/bin/sh
cd /home/user1/rvt-research
POOL_MEM=5G PYBIN=/home/user1/rvt-env/bin/python exec /home/user1/rvt-env/bin/python run_pool.py eval_params_all.py pout_log 1
