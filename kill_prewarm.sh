#!/bin/sh
for p in $(pgrep -f "run_prewarm.sh"); do kill $p 2>/dev/null; done
for p in $(pgrep -f "xargs -0 -P"); do kill $p 2>/dev/null; done
