#!/bin/sh
# runs rvt2text over every corpus/samples file; writes t2t/<path>.txt/.err and t2t/_status.log (exit code, seconds, file)
cd /home/user1/rvt-research
PATH=/home/user1/rvt-env/bin:$PATH
mkdir -p t2t; : > t2t/_status.log
for f in corpus/*/*.rvt corpus/*/*.rfa corpus/*/*.rte corpus/*/*.rft samples/*.rvt samples-rfa/*.rfa; do [ -f "$f" ] && echo "$f"; done | xargs -P 7 -I{} sh -c '. ./t2t_one.sh; one "{}"'
