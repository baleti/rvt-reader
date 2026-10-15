#!/bin/bash
# vm.sh put LOCAL REMOTE | get REMOTE LOCAL | ps SCRIPT.ps1 | job PORT FILE.cs   (all via host2 -> vsock -> offline Windows VM)
case "$1" in
 ps) scp -q -i $K "$2" $H:/tmp/vm_run.ps1 && ssh -i $K $H '~/bin/winrun /tmp/vm_run.ps1';;
& C:\\Users\\User\\AppData\\Local\\Programs\\Python\\Python313\\python.exe C:\\ci\\runjob.py $2 C:\\ci\\exp_job.cs
EOP
 scp -q -i $K /tmp/vm_job.ps1 $H:/tmp/vm_run.ps1 && ssh -i $K $H '~/bin/winrun /tmp/vm_run.ps1';;
esac
