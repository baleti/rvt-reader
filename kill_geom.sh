#!/bin/sh
for p in $(pgrep -f "test_floor.py"); do kill $p 2>/dev/null; done
for p in $(pgrep -f "run_geomtest.sh"); do kill $p 2>/dev/null; done
