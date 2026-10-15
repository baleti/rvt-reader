#!/usr/bin/env python3
Files under /mnt/host1-backups are decoded on host1 (cached there, file read locally); anything else is decoded locally.
import sys, os, html, subprocess
here = os.path.dirname(os.path.abspath(__file__))
f = sys.argv[1]
txt = ''
try:
    if f.startswith('/mnt/host1-backups/'):
        hp = '/home/user1/backups/' + f[len('/mnt/host1-backups/'):]
        r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'host1', 'PATH=/home/user1/rvt-env/bin:$PATH python3 /home/user1/rvt-research/rvt_cache_get.py ' + "'" + hp.replace("'", "'\\''") + "'"], capture_output=True, timeout=1150)
        txt = r.stdout.decode('utf-8', 'replace')
    else:
        txt = subprocess.run([sys.executable, '-I', os.path.join(here, 'rvt2text.py'), f], capture_output=True, timeout=1100).stdout.decode('utf-8', 'replace')
except Exception:
    txt = ''
title = os.path.basename(f)
sys.stdout.write('<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><title>%s</title></head><body><pre>%s</pre></body></html>\n' % (html.escape(title), html.escape(txt)))
