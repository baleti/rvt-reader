#!/bin/sh
# pre-decode all bm3 Revit files on host1 into t2c/ (small first, big ones serially with a larger memory cap)
cd /home/user1/rvt-research
PATH=/home/user1/rvt-env/bin:$PATH
sort -n /tmp/bm3_revit.txt > /tmp/bm3_sorted_sz.txt
awk '$1<=300000000 {sub(/^[0-9]+ /,""); print}' /tmp/bm3_sorted_sz.txt > prewarm_small.txt
awk '$1>300000000 {sub(/^[0-9]+ /,""); print}' /tmp/bm3_sorted_sz.txt > prewarm_big.txt
echo "$(date +%T) small $(wc -l < prewarm_small.txt) big $(wc -l < prewarm_big.txt)" > prewarm.log
tr '\n' '\0' < prewarm_small.txt | RVT_AS_GB=5 xargs -0 -P 2 -n 1 systemd-run --user --scope -q -p MemoryMax=6G -p MemorySwapMax=0 nice -n 12 python3 rvt_cache_get.py --compute-only 2>/dev/null
echo "$(date +%T) small done" >> prewarm.log
tr '\n' '\0' < prewarm_big.txt | RVT_AS_GB=10 xargs -0 -P 1 -n 1 systemd-run --user --scope -q -p MemoryMax=11G -p MemorySwapMax=0 nice -n 12 python3 rvt_cache_get.py --compute-only 2>/dev/null
echo "$(date +%T) ALLDONE" >> prewarm.log
