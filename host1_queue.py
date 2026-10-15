#!/usr/bin/env python3
"""Single sequential job queue for host1 (shares the box with the user's 17 GB ai1 VM): one job at a time, all inside rvt-work.slice (MemoryMax 3.5G, no swap),
each job waits until MemAvailable > 10 GB + its cap, nice/ionice. Tasks are (name, command) in the order of the user's priorities."""
import os, sys, glob, time, subprocess
HOME = '/home/user1/rvt-research'; os.chdir(HOME)
os.environ['XDG_RUNTIME_DIR'] = '/run/user/%d' % os.getuid()
CAP_G = 3.5
def avail_gb():
    for ln in open('/proc/meminfo'):
        if ln.startswith('MemAvailable'): return int(ln.split()[1]) / 1048576
def restarts():
    r = subprocess.run(['systemctl', '--user', 'show', 'qemu-ai1', '-p', 'NRestarts'], capture_output=True, text=True).stdout.strip()
    return r
BASE = restarts()
def run(name, cmd, env=None):
    while avail_gb() < 10 + CAP_G:
        time.sleep(30)
    if restarts() != BASE:
        print('qemu-ai1 restart counter changed (%s -> %s): stopping queue' % (BASE, restarts()), flush=True); sys.exit(3)
    e = dict(os.environ); e.update(env or {})
    full = ['systemd-run', '--user', '--scope', '-q', '--slice=rvt-work.slice', '-p', 'MemoryMax=%dM' % int(CAP_G * 1024), '-p', 'MemorySwapMax=0', 'nice', '-n', '12', 'ionice', '-c3'] + cmd
    t = time.time(); r = subprocess.run(full, env=e, capture_output=True, text=True, timeout=7200)
    print('%s rc=%d %.0fs avail=%.1fG %s' % (name, r.returncode, time.time() - t, avail_gb(), (r.stdout.strip() or r.stderr.strip())[-120:]), flush=True)

def pairs():
    out = []
    for g in sorted(glob.glob('gt4/*.tsv')):
        b = os.path.basename(g)[:-4]; y, rest = b.split('_', 1)
        f = glob.glob('corpus/%s/%s' % (y, rest))
        if f: out.append((f[0], g, b))
    return out
OCC = '/home/user1/occ-env/bin/python'; ENVP = '/home/user1/rvt-env/bin/python'
if __name__ == '__main__':
    which = sys.argv[1:] or ['fid', 'pout']
    P = pairs()
    if 'fid' in which:
        os.makedirs('fidfull', exist_ok=True)
        for f, g, b in P:
            if os.path.exists('fidfull/%s.jsonl' % b) and os.path.getsize('fidfull/%s.jsonl' % b) > 0: continue
            run('fid ' + b, [OCC, 'fidelity_full.py', f, g, 'fidfull/%s.jsonl' % b, '3000'])
    if 'pout' in which:
        os.makedirs('pout', exist_ok=True)
        for f, g, b in P:
            if not os.path.exists('pout_after_ok/%s' % b):
                run('pout-after ' + b, [ENVP, 'eval_params_all.py', f, g], {'POUT_DIR': 'pout_after'})
                os.makedirs('pout_after_ok', exist_ok=True); open('pout_after_ok/%s' % b, 'w').write('1')
        for f, g, b in P:
            if not os.path.exists('pout_before_ok/%s' % b):
                run('pout-before ' + b, [ENVP, 'eval_params_all.py', f, g], {'POUT_DIR': 'pout_before2', 'RVT_NOUNIV': '1'})
                os.makedirs('pout_before_ok', exist_ok=True); open('pout_before_ok/%s' % b, 'w').write('1')
