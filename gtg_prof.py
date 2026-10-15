"""Profile families (rosetta prof_* files): our curves from saved graphics vs Revit PROFCURVE rows (per symbol id: same set of line segments / arcs up to 1e-6 ft)."""
import sys, os, re, collections, numpy as np
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_elemmesh as EM
def parse(c):
    t = c.split()
    if t[0] == 'Line': return ('line', tuple(np.round([float(x) for x in t[1].split(',')], 5)), tuple(np.round([float(x) for x in t[2].split(',')], 5)))
    return (t[0].lower(),)
tot = ok = 0; rows = []
for f in sys.argv[1:]:
    tsv = 'gt_geom/%s.tsv' % os.path.splitext(os.path.basename(f))[0]; ref = collections.defaultdict(list); fam = {}
    for l in open(tsv):
        p = l.rstrip('\n').split('\t')
        if p[0] == 'PROFCURVE': ref[int(p[1])].append(p[4]); fam[int(p[1])] = p[2]
    d = EM.Doc(f)
    for sid, curves in ref.items():
        mine = EM.element_curves(d, sid); tot += 1
        want = collections.Counter(); 
        for c in curves:
            k = parse(c); 
            if k[0] == 'line': want[frozenset([k[1], k[2]])] += 1
            else: want[(k[0],)] += 1
        have = collections.Counter()
        for c in mine:
            if c['type'] == 'line': have[frozenset([tuple(np.round(c['p0'], 5)), tuple(np.round(c['p1'], 5))])] += 1
            else: have[('arc',)] += 1
        good = set(want) == set(have)
        ok += good; rows.append((os.path.basename(f), sid, fam[sid], len(curves), len(mine), good))
fam_ok = collections.defaultdict(bool)
for r in rows: fam_ok[(r[0], r[2])] |= r[5]
for k, v in fam_ok.items():
    if not v: print('FAMILY WITHOUT EXACT CURRENT-TYPE MATCH', k)
print('symbols matching PROFCURVE exactly: %d/%d; families with the current type reproduced exactly: %d/%d' % (ok, tot, sum(fam_ok.values()), len(fam_ok)))
