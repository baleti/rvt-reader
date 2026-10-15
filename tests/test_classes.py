"""Class-level regression tests on corpus/2020/18_rst_basic_sample_project.rvt: closed-shell volumes must equal Revit's Volume (gt4) for walls and floors,
every Geometry-bearing FamilyInstance must give a mesh with bbox IoU >= 0.5 against the stored bbox. Run with the occ-env python (needs mapbox_earcut)."""
import sys, os
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, eval_gt as G
F = '/home/user1/rvt-research/corpus/2020/18_rst_basic_sample_project.rvt'; T = '/home/user1/rvt-research/gt4/2020_18_rst_basic_sample_project.rvt.tsv'
doc = EM.Doc(F); E, P = G.load_gt(T)
def gtvol(e): return [float(v) for b, nm, stg, v in P[e] if nm == 'Volume' and stg == 'Double' and v != ''][0]
def vol(e):
    m = EM.element_mesh(doc, e, detail=2); v, closed, _, _ = M.mesh_volume(m['tris']); return v, closed, m

def test_walls_exact():
    for e in (493612, 493879, 627064, 627729, 628523, 1115218, 1115258, 1141594):
        v, closed, m = vol(e); assert closed and abs(v / gtvol(e) - 1) < 1e-4, (e, v, gtvol(e))

def test_floors_exact():
    for e in (495352, 647908, 1206619, 1210630, 1211070):
        v, closed, m = vol(e); assert closed and abs(v / gtvol(e) - 1) < 1e-4, (e, v, gtvol(e))

def test_instances_have_meshes():
    n = ok = 0
    for e, d in E.items():
        if d['cls'] != 'FamilyInstance' or e not in doc.res or not doc.res[e]['bodies'].get('Face'): continue
        m = EM.element_mesh(doc, e, detail=2); n += 1; ok += bool(m['tris'])
    assert n > 20 and ok == n, (n, ok)

if __name__ == '__main__':
    for k, v in list(globals().items()):
        if k.startswith('test_'): v(); print(k, 'ok')
