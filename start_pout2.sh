#!/bin/sh
cd /home/user1/rvt-research
export XDG_RUNTIME_DIR=/run/user/1000
# A: re-run the files that only have old-rule results in pout_before (first 16) with the current rules
for j in pout_before/*.json; do b=$(basename $j .json); rm -f pout/$b.json; for y in 2020 2021 2022 2023 2024 2025 2026; do rm -f pout_log/${y}_*_$b.out 2>/dev/null; done; done
PYBIN=/home/user1/rvt-env/bin/python POOL_MEM=5G /home/user1/rvt-env/bin/python run_pool.py eval_params_all.py pout_log 1
# B: 'before' (no universal lookups) for all other files
mkdir -p pout_logB
SKIP_EXISTING=1 POUT_DIR=pout_before RVT_NOUNIV=1 PYBIN=/home/user1/rvt-env/bin/python POOL_MEM=5G /home/user1/rvt-env/bin/python run_pool.py eval_params_all.py pout_logB 1
