#!/bin/sh
for p in $(pgrep -f "run_pool.py"); do kill $p 2>/dev/null; done
for p in $(pgrep -f "eval_params_all.py"); do kill $p 2>/dev/null; done
