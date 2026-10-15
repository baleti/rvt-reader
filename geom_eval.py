import sys, os, math, json, collections
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_geometry as GG, rvt_solids as So, eval_gt as G
from OCP.gp import gp_Pnt, gp_Vec
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

def occ_solid(s, ctx=None):
    """-> (volume, area_of_side/top, note) from the described solid using OCC"""
    k = s['kind']
    if k == 'extrusion':
        loops = []
        for l in s['profile']['loops']:
            loops.append([(tuple(x['p0']), tuple(x['p1']), tuple(x['mid']) if x['type'] == 'arc' else tuple((x['p0'][i] + x['p1'][i]) / 2 for i in range(3))) for x in l])
        areas = []
        for l in loops:
            f = So.planar_face([l]); areas.append((So.props_surface(f)[0], l))
        areas.sort(key=lambda a: -a[0]); face = So.planar_face([areas[0][1]] + [a[1] for a in areas[1:]])
        d = s['direction']; sh = So.extrude(face, [c * s['depth'] for c in d])
        v = So.props_volume(sh)[0]; a = So.props_surface(face)[0]
        return abs(v), a, 'occ'
    if k == 'wall_extrusion':
        c = s['location_curve']; W = s['thickness']; H = s['height']
        if c['type'] == 'line':
            p0, p1 = c['p0'], c['p1']; L = math.dist(p0, p1)
            return L * H * W, L * H, 'analytic'
        r = c['radius']; ang = abs(c['t1'] - c['t0']); L = r * ang
        return L * H * W, L * H, 'analytic'
    if k == 'box':
        lo, hi = s['min'], s['max']; return (hi[0]-lo[0])*(hi[1]-lo[1])*(hi[2]-lo[2]), None, 'box'
    return None, None, 'unsupported'

if __name__ == '__main__':
    rvt, tsv = sys.argv[1:3]
    ctx = GG.get_ctx(rvt); E, P = G.load_gt(tsv)
    res = collections.defaultdict(collections.Counter); ex = {}
    for eid, rec in ctx.recs.items():
        c = rec['class']
        if c not in GG.BUILDERS: continue
        g = GG.element_geometry(rvt, eid)
        gt = {nm: float(v) for b, nm, stg, v in P.get(eid, []) if stg == 'Double' and v != ''}
        if g['confidence'] == 'none': res[c]['unsupported/none'] += 1; continue
        if not g['solids']: res[c]['none'] += 1; continue
        try: vol, area, note = occ_solid(g['solids'][0])
        except Exception as e: res[c]['occ-error'] += 1; continue
        if g['confidence'] == 'box':
            res[c]['box-only'] += 1
            if vol is not None and 'Volume' in gt and gt['Volume'] > 0:
                res[c]['  box volume within x2 of Revit'] += (0.5 <= vol / gt['Volume'] <= 2) if True else 0
                res[c]['  box vs volume compared'] += 1
            continue
        key = None
        tests = []
        if 'Volume' in gt and vol is not None: tests.append(('Volume', vol, gt['Volume']))
        if 'Area' in gt and area is not None and g['solids'][0]['kind'] in ('wall_extrusion', 'extrusion'): tests.append(('Area', area, gt['Area']))
        if not tests: res[c]['no-gt'] += 1; continue
        for nm, mine, ref in tests:
            r = mine / ref if ref else None
            if r is None: continue
            st = 'exact' if abs(r - 1) <= 1e-6 else ('approx(<=5%)' if abs(r - 1) <= 0.05 else 'off(>5%)')
            res[c][nm + ':' + st] += 1
            if st == 'off(>5%)': ex.setdefault((c, nm), (eid, mine, ref, g['flags']))
    for c, cn in sorted(res.items()): print(c, dict(cn))
    for k, v in ex.items(): print('  e.g.', k, v)
