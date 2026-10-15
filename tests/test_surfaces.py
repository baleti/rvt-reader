"""Regression tests for the surface/curve evaluators (formulas fitted exactly against Revit edges: cylinder, cone, ruled, revolution)."""
import sys, math
sys.path.insert(0, '/home/user1/rvt-research')
import numpy as np, rvt_mesh as M, rvt_curves as C

def close(a, b, tol=1e-9): return np.linalg.norm(np.asarray(a) - np.asarray(b)) < tol

def test_cylinder():
    k, ev = M.surface_eval({'m_center': [1, 2, 3], 'm_xVec': [1, 0, 0], 'm_yVec': [0, 1, 0], 'm_zVec': [0, 0, 1], 'm_radius': 2.0, 'm_orientFlag': 1})
    assert k == 'cylinder' and close(ev(0, 0), [3, 2, 3]) and close(ev(math.pi / 2, 5), [1, 4, 8])

def test_cone_apex_and_slant():
    al = math.radians(30)
    k, ev = M.surface_eval({'m_center': [0, 0, 0], 'm_xVec': [1, 0, 0], 'm_yVec': [0, 1, 0], 'm_zVec': [0, 0, 1], 'm_halfAngle': al})
    assert k == 'cone' and close(ev(1.23, 0), [0, 0, 0]) and close(ev(0, 2), [2 * math.sin(al), 0, 2 * math.cos(al)])

def test_ruled_between_two_ellipses_is_a_cylinder():
    e = lambda z: {'obj': {'m_endParams': [0.0, math.pi], 'm_center': [0, 0, z], 'm_xVec': [1, 0, 0], 'm_yVec': [0, 1, 0], 'm_xLen': 1.5, 'm_yLen': 1.5}}
    k, ev = M.surface_eval({'m_pProfileCurve1': e(0), 'm_pProfileCurve2': e(-6), 'm_Point1': [0, 0, 0], 'm_Point2': [0, 0, 0]})
    assert k == 'ruled' and close(ev(0, 0), [1.5, 0, 0]) and close(ev(0, 1), [1.5, 0, -6]) and close(ev(0.5, 0.5), [0, 1.5, -3])

def test_revolution_of_vertical_line_is_a_cylinder():
    line = {'obj': {'m_origin': [2, 0, 0], 'm_dirVec': [0, 0, 1], 'm_endParams': [0, 3]}}
    k, ev = M.surface_eval({'m_center': [0, 0, 0], 'm_xVec': [1, 0, 0], 'm_yVec': [0, 1, 0], 'm_zVec': [0, 0, 1], 'm_pProfileCurve': line})
    assert k == 'revolution' and close(ev(math.pi / 2, 1.5), [0, 2, 1.5])

def test_curves():
    assert close(C.curve_fn({'m_origin': [0, 0, 0], 'm_dirVec': [1, 0, 0], 'm_endParams': [0, 5]})[0](2), [2, 0, 0])
    f = C.curve_fn({'m_NodeArray': [{'m_iParametr': 0, 'm_iPoint': [0, 0, 0], 'm_iTangent': [1, 0, 0]}, {'m_iParametr': 1, 'm_iPoint': [1, 0, 0], 'm_iTangent': [1, 0, 0]}], 'm_endParams': [0, 1]})[0]
    assert close(f(0.5), [0.5, 0, 0])

def test_polymesh():
    t = M.polymesh_tris({'m_pFacetedTopology': {'obj': {'m_pointsArr': [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], 'm_facetsArr': [[0, 1, 2], [1, 3, 2]]}}})
    assert len(t) == 2

if __name__ == '__main__':
    n = 0
    for k, v in list(globals().items()):
        if k.startswith('test_'): v(); n += 1
    print(n, 'tests passed')
