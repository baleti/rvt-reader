#!/bin/sh
for p in $(pgrep -f "run_fid2.sh"); do kill $p 2>/dev/null; done
for p in $(pgrep -f "fidelity_eval.py"); do kill $p 2>/dev/null; done
