#!/usr/bin/env python3
"""rvt_cache_get.py HOSTPATH [--compute-only]: prints rvt2text output for a Revit file, from the cache t2c/<sha1(path|size|mtime)>.txt (computes and stores it on a miss; at most 3 computations at once per host, each address-space capped)."""
import sys, os, hashlib, subprocess, fcntl, time
here = os.path.dirname(os.path.abspath(__file__)); cd = os.path.join(here, 't2c'); os.makedirs(cd, exist_ok=True)
p = [a for a in sys.argv[1:] if not a.startswith("--")][0]; st = os.stat(p)
key = hashlib.sha1(('%s|%d|%d' % (p, st.st_size, int(st.st_mtime))).encode()).hexdigest()
f = os.path.join(cd, key + '.txt'); bad = os.path.join(cd, key + '.fail')

def _slot(n=3):
    while True:
        for i in range(n):
            fh = open('/tmp/rvtcg.slot%d' % i, 'w')
            try: fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB); return fh
            except OSError: fh.close()
        time.sleep(2)

def compute():
    gb = float(os.environ.get('RVT_AS_GB', '6'))
    def lim():
        import resource; resource.setrlimit(resource.RLIMIT_AS, (int(gb * (1 << 30)),) * 2)
    try:
        r = subprocess.run([sys.executable, os.path.join(here, 'rvt2text.py'), p], capture_output=True, timeout=1100, preexec_fn=lim)
        if r.returncode == 0 and r.stdout: open(f + '.tmp', 'wb').write(r.stdout); os.replace(f + '.tmp', f)
        else: open(bad, 'w').write('rc=%d %s' % (r.returncode, r.stderr[-300:].decode('utf-8', 'replace')))
    except Exception as e:
        open(bad, 'w').write(repr(e))

if not os.path.exists(f) and not os.path.exists(bad):
    fh = _slot()
    if not os.path.exists(f) and not os.path.exists(bad): compute()
if '--compute-only' in sys.argv: sys.exit(0)
if os.path.exists(f): sys.stdout.buffer.write(open(f, 'rb').read())
