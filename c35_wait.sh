#!/bin/bash
cd /home/user1/rvt-research
until ssh host1 'grep -q ALLDONE rvt-research/params_c34.log'; do sleep 300; done
./h1retry.sh par35 ./params_c35_h1.sh
