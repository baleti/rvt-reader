"""Profile symbols (rosetta prof_* files): our outline (saved-graphics curves) vs Revit's per-type dimension parameters (TYPE rows: Height, Width, Thickness, Depth ...) and, for the family's current type, the PROFCURVE segments."""
import sys, os, re, collections, numpy as np
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_elemmesh as EM
DIMS = ('Height', 'Width', 'Thickness', 'Depth', 'Length', 'Flange Width', 'Overall Depth', 'Overall Width', 'Diameter')
def bbox(curves):
    P = []
    for c in curves:
        P += [c['p0'], c['p1']]
        if c['type'] == 'arc':
            for t in np.linspace(c['t0'], c['t1'], 33): P.append((np.array(c['center']) + c['radius'] * np.cos(t) * np.array(c['xvec']) + c['radius'] * np.sin(t) * np.array(c['yvec'])).tolist())
    P = np.array(P); return P.min(0), P.max(0)
tot = ok = 0; bad = []
for f in sys.argv[1:]:
    tsv = 'gt_geom/%s.tsv' % os.path.splitext(os.path.basename(f))[0]; types = {}
    for l in open(tsv):
        p = l.rstrip('\n').split('\t')
        if p[0] == 'TYPE' and len(p) > 4 and p[3] == 'Profiles':
            kv = {}
            for x in p[5:]:
                m = re.match(r'([^=]+)=([-0-9.eE+]+)', x)
                if m and m.group(1) in DIMS: kv[m.group(1)] = float(m.group(2))
            types[int(p[1])] = (p[4], kv)
    d = EM.Doc(f)
    for sid, (nm, kv) in types.items():
        cur = EM.element_curves(d, sid)
        if not cur or not kv: continue
        lo, hi = bbox(cur); ext = sorted([hi[0] - lo[0], hi[1] - lo[1]]); tot += 1
        vals = sorted(kv.values())
        good = all(any(abs(v - e) < 2e-4 for e in ext) for v in vals) if len(vals) <= 2 else all(any(abs(v - e) < 2e-4 for v in vals) for e in ext)
        ok += good
        if not good: bad.append((os.path.basename(f), sid, nm, [round(e, 4) for e in ext], {k: round(v, 4) for k, v in kv.items()}))
for b in bad[:20]: print('MISMATCH', b)
print('profile type outlines consistent with Revit type parameters: %d/%d' % (ok, tot))
