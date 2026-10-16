#!/bin/bash
cd /home/user1/rvt-research; export RVT_WORKERS=1
for p in 2024/47_Snowdon_Towers_Sample_Site.rvt 2026/59_Snowdon_Towers_Sample_Site.rvt; do y=${p%%/*}; r=${p#*/}
  python ana_c5/topo.py corpus/$p 1264746 > ana_c5/topo_$y.txt 2>&1
done
echo ALLDONE > ana_c5/topo_done.txt
