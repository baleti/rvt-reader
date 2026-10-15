"""Topography check vs oracle TOPO/MESH rows: our vertex set must equal the TOPO points and the triangle mesh area must match the oracle MESH area."""
import sys, os, numpy as np
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_elemmesh as EM
def area(P, T): return sum(np.linalg.norm(np.cross(P[b]-P[a], P[c]-P[a])) / 2 for a, b, c in T)
for nm in ('topography_base', 'topography_var'):
    tsv = 'gt_geom/2024_%s.tsv' % nm; pts = None; V = {}; T = {}
    for l in open(tsv):
        t = l.rstrip('\n').split('\t')
        if t[0] == 'TOPO': eid = int(t[1]); pts = np.array([[float(x) for x in p.split(',')] for p in t[2].split('=', 1)[1].split(';')])
        elif t[0] == 'V' and '.m' in t[1]: V = np.array([[float(x) for x in p.split(',')] for p in t[2].split()])
        elif t[0] == 'T' and '.m' in t[1]: T = [tuple(int(x) for x in p.split(',')) for p in t[2].split()]
    d = EM.Doc('rosetta/2024_%s.rte' % nm); m = EM.element_mesh(d, eid, detail=3)
    ours = np.unique(np.array([p for tr in m['tris'] for p in tr]).round(5), axis=0); ref = np.unique(pts.round(5), axis=0)
    a_o = sum(np.linalg.norm(np.cross(np.array(t[1]) - t[0], np.array(t[2]) - t[0])) / 2 for t in m['tris'])
    print(nm, 'vertices equal:', ours.shape == ref.shape and np.allclose(ours, ref, atol=1e-4), 'tris', len(m['tris']), 'vs', len(T), 'area %.4f vs %.4f' % (a_o, area(V, T)))
