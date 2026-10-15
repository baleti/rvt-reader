"""rvt_rebar centre-lines vs Revit's GetCenterlineCurves (gt_rebar/*.tsv): per bar position, per curve: endpoints / mid within 1e-4 ft"""
import sys, os, collections
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import numpy as np, rvt_rebar as RB
f = sys.argv[1]; y = f.split('/')[-2]; tsv = '/home/user1/rvt-research/gt_rebar/%s_%s.tsv' % (y, os.path.splitext(os.path.basename(f))[0])
gt = collections.defaultdict(lambda: collections.defaultdict(list)); cls = {}
P = lambda s: np.array([float(a) for a in s.split(',')])
for l in open(tsv):
    t = l.rstrip('\n').split('\t')
    if t[0] == 'RB': cls[int(t[1])] = t[2]
    if t[0] == 'RBC': gt[int(t[1])][int(t[2])].append((t[4], P(t[5]), P(t[6]), P(t[7]), float(t[8])))
st = collections.Counter(); bad = []
for eid, bars in gt.items():
    cl = RB.rebar_centerlines(f, eid); k = cls.get(eid, '?')
    if not cl: st[(k, 'missing')] += 1; continue
    ok = len(cl['bars']) >= len(bars); worst = 0.0
    if len(bars) > 1 and all(len(bars[i]) == len(bars[0]) and all(np.linalg.norm(a[1] - b[1]) < 1e-9 for a, b in zip(bars[i], bars[0])) for i in bars):
        bars = {0: bars[0]}                                              # the 2020 API overload returns the first bar for every index: only bar 0 is checkable
    for i, curves in bars.items():
        if i >= len(cl['bars']) or len(cl['bars'][i]) != len(curves): ok = False; break
        for g, m in zip(curves, cl['bars'][i]):
            worst = max(worst, np.linalg.norm(g[1] - m['p0']), np.linalg.norm(g[2] - m['p1']), np.linalg.norm(g[3] - m.get('mid', (m['p0'] + m['p1']) / 2)))
        if worst > 1e-3: ok = False
        if not ok: break
    st[(k, ('exact' if worst <= 1e-4 else 'within 1e-3 ft') if ok else 'wrong')] += 1
    if not ok and len(bad) < 5: bad.append((eid, k, len(bars), len(cl['bars'])))
print(os.path.basename(f), dict(st)); print(bad)
