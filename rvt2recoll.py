#!/usr/bin/env python3
Files under the remote-mirror prefix (RVT_MIRROR_PREFIX) are decoded on the remote host (cached there, file read locally); anything else is decoded locally.
import sys, os, html, subprocess
import json
except Exception: _cfg = {}
MIRROR = _cfg.get('mirror')   # local mount of the remote backups (None: everything is decoded locally)
REMOTE = _cfg.get('remote')   # same tree as seen on the remote host
here = os.path.dirname(os.path.abspath(__file__))
f = sys.argv[1]
txt = ''
try:
    if MIRROR and f.startswith(MIRROR):
        hp = REMOTE + f[len(MIRROR):]
        import fcntl, time
        fcntl.flock(lock, fcntl.LOCK_EX)                 # ONE decode on host1 at a time
        HALT, BASE = os.path.expanduser('~/.cache/indexes/revit/HALT'), 5
        def host1(cmd, t=30):
            return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'host1', cmd], capture_output=True, timeout=t).stdout.decode()
        ok = False
        for _ in range(60):                              # wait (up to ~15 min) for host1 to have room
            if os.path.exists(HALT): sys.exit(1)
            try:
                out = host1("grep MemAvailable /proc/meminfo; systemctl --user show qemu-ai1 -p NRestarts")
                mem = int(out.split('MemAvailable:')[1].split()[0]) // 1024
                nr = int(out.split('NRestarts=')[1].split()[0])
            except Exception:
                time.sleep(15); continue
            if nr > BASE:
                open(HALT, 'w').write('qemu-ai1 NRestarts %d\n' % nr); sys.exit(1)
            if mem > 11264: ok = True; break
            time.sleep(15)
        if not ok: sys.exit(1)                           # failure, not an empty document: it is retried later
        r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'host1', 'systemd-run --user --scope -q -p MemoryMax=4G -p MemorySwapMax=0 -p CPUQuota=200% nice -n 19 env PATH=/home/user1/rvt-env/bin:$PATH python3 /home/user1/rvt-research/rvt_cache_get.py ' + "'" + hp.replace("'", "'\\''") + "'"], capture_output=True, timeout=1150)
        txt = r.stdout.decode('utf-8', 'replace')
        try:
            if int(host1("systemctl --user show qemu-ai1 -p NRestarts").split('=')[1]) > BASE:
                open(HALT, 'w').write('qemu-ai1 restarted\n')
        except Exception: pass
    else:
        txt = subprocess.run([sys.executable, '-I', os.path.join(here, 'rvt2text.py'), f], capture_output=True, timeout=1100).stdout.decode('utf-8', 'replace')
except Exception:
    txt = ''
title = os.path.basename(f)
sys.stdout.write('<html><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"><title>%s</title></head><body><pre>%s</pre></body></html>\n' % (html.escape(title), html.escape(txt)))
