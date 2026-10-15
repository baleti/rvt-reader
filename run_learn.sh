#!/bin/sh
cd /home/user1/rvt-research
PATH=/home/user1/rvt-env/bin:$PATH NP=7 exec python3 learn_expr.py 0,1,2,3,5,7,8 expr_rules.json
