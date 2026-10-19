#!/usr/bin/env python3
"""rvt_geometry: element geometry decoded from a Revit file (no Revit).
API:  element_geometry(file, element_id) -> dict   (see GEOMETRY_API.md)
      file_geometry_index(file) -> {element_id: class}   cheap listing
Units: Revit internal feet, radians. Transforms are 4x4 row-major local->world."""
import os, sys, math, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault('RVT_GEOM', '1')
import rvt_xcache, rvt_scan as S, rvt_geom as Gm, rvt_famparams as F
try: sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as _F
except Exception: _F = None

HERE = os.path.dirname(os.path.abspath(__file__))
PNAMES = json.load(open(os.path.join(HERE, 'param_names.json')))
_ctx = {}

def _sgn(v):
    v = int(v)
    return v - (1 << 64) if v >= 1 << 63 else (v - (1 << 32) if 1 << 31 <= v < 1 << 32 else v)

class Ctx:
    def __init__(s, path):
        s.path = path; x = rvt_xcache.get_x_ro(path); s.x = x; s.recs = {}
        for (eid, c), r in x['recs'].items(): s.recs.setdefault(eid, r)
        s.eh = x['eh']; s.own = S.owners(path); s.kids = collections.defaultdict(list)
        for e, o in s.own.items():
            if o is not None: s.kids[o].append(e)
        s.level = {}
        for eid, r in s.recs.items():
            if r['class'] == 'Level':
                o = _g(r['fields'], 'm_pSurface', 'm_origin')
                if o: s.level[eid] = o[2]
    def rec(s, eid): return s.recs.get(int(eid)) if eid is not None else None

def _g(f, *p): return F.S_(f, *p)

def get_ctx(path):
    c = _ctx.get(path)
    if c is None: c = _ctx[path] = Ctx(path)
    return c

def stored_params(rec):
    """{param name or pid: value} from the record's ParamValueSet{Double,Int,AString,ElementId}"""
    out = {}
    for k in ('m_pParamValueSetDouble', 'm_pParamValueSetInt', 'm_pParamValueSetAString', 'm_pParamValueSetElementId'):
        ps = _g(rec['fields'], k, 'm_paramSet') or []
        for e in ps:
            if not isinstance(e, dict): continue
            pid = _sgn(e.get('m_paramId', 0)); out[PNAMES.get(str(pid), pid)] = e.get('m_value')
    return out

# ---------- profile helpers ----------
def seg_dict(c):
    """a decoded line/arc record -> JSON-able curve"""
    p = c['m_endParams']
    if Gm.is_line(c):
        o = c['m_origin']; d = c['m_dirVec']
        pt = lambda t: [o[i] + d[i] * t for i in range(3)]
        return {'type': 'line', 'p0': pt(p[0]), 'p1': pt(p[1])}
    ce = c['m_center']; r = c['m_radius']; x = c['m_xVec']; y = c['m_yVec']
    pt = lambda t: [ce[i] + r * (math.cos(t) * x[i] + math.sin(t) * y[i]) for i in range(3)]
    return {'type': 'arc', 'center': list(ce), 'radius': r, 'xvec': list(x), 'yvec': list(y), 't0': p[0], 't1': p[1], 'p0': pt(p[0]), 'p1': pt(p[1]), 'mid': pt((p[0] + p[1]) / 2)}

def sketch_loops(ctx, eid):
    """closed curve loops of the sketch owned (up to depth 2) by element eid"""
    cur = []
    def desc(e, d=0):
        for k in ctx.kids.get(e, []):
            yield k
            if d < 2: yield from desc(k, d + 1)
    for k in desc(eid):
        r = ctx.rec(k)
        if r and r['class'] == 'CurveElem': cur += Gm.find_curves(r['fields'])
    if not cur: return None
    try:
        import rvt_solids as So
        loops = So.chain_loops(cur)
    except Exception:
        loops = None
    if not loops: return None
    out = []
    for l in loops:
        segs = []
        for (a, b, m) in l:
            straight = all(abs(m[i] - (a[i] + b[i]) / 2) < 1e-7 for i in range(3))
            segs.append({'type': 'line', 'p0': list(a), 'p1': list(b)} if straight else {'type': 'arc', 'p0': list(a), 'p1': list(b), 'mid': list(m)})
        out.append(segs)
    return out

def _compound(ctx, type_id):
    r = ctx.rec(type_id)
    if not r: return None
    cs = _g(r['fields'], 'm_pCompoundStructure') or {}
    cs = cs.get('obj', cs) if isinstance(cs, dict) else {}
    layers = cs.get('m_layers') or []
    out = []
    for l in layers:
        l = l.get('obj', l) if isinstance(l, dict) else {}
        if 'm_layerWidth' in l: out.append({'width': l['m_layerWidth'], 'material_id': int(l.get('m_materialId', -1)) if l.get('m_materialId') is not None else None, 'function': l.get('m_layerFunction')})
    return out or None

def _res(ctx, eid, rec, conf, solids, flags=(), transform=None, bbox=None, notes=''):
    return {'element_id': int(eid), 'class': rec['class'] if rec else None, 'confidence': conf, 'solids': solids, 'flags': list(flags),
            'transform': transform or [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], 'bbox': bbox, 'notes': notes}

# ---------- per-class builders ----------
def floor_like(ctx, eid, rec):
    f = rec['fields']; loops = sketch_loops(ctx, eid)
    tid = f.get('m_floorAttributesId') or f.get('m_ceilingAttributesId') or f.get('m_attributesId')
    layers = _compound(ctx, int(tid)) if tid is not None else None
    th = sum(l['width'] for l in layers) if layers else None
    if not loops or th is None: return None
    pts = [p for l in loops for s in l for p in (s['p0'], s['p1'])]
    z = sum(p[2] for p in pts) / len(pts)
    flags = []
    if any(s['type'] == 'arc' for l in loops for s in l): flags.append('has_arcs')
    flags.append('no_openings_or_slope')
    bb = [[min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]]
    bb[0][2] = z - th; bb[1][2] = z
    return _res(ctx, eid, rec, 'approx', [{'kind': 'extrusion', 'profile': {'plane': {'origin': [0, 0, z], 'xvec': [1, 0, 0], 'yvec': [0, 1, 0], 'normal': [0, 0, 1]}, 'loops': loops}, 'direction': [0, 0, -1], 'depth': th, 'layers': layers, 'voids': []}], flags, bbox=bb)

def wall(ctx, eid, rec):
    f = rec['fields']; cu = Gm.primary_curve(f)
    if cu is None: return None
    layers = _compound(ctx, int(f['m_WallAttributesId'])) if f.get('m_WallAttributesId') is not None else None
    w = sum(l['width'] for l in layers) if layers else None
    sp = stored_params(rec)
    base_lv = ctx.level.get(int(f['m_assocLevelId'])) if f.get('m_assocLevelId') is not None else None
    top_lv = ctx.level.get(int(f['m_upToLevelId'])) if f.get('m_upToLevelId') is not None else None
    bo = sp.get('Base Offset', 0.0); to = sp.get('Top Offset', 0.0)
    if base_lv is None or w is None: return None
    if top_lv is not None: H = (top_lv + to) - (base_lv + bo)
    else: H = sp.get('Unconnected Height')
    if H is None: return None
    seg = seg_dict(cu)
    z0 = base_lv + bo
    flags = ['no_joins', 'no_openings']
    if seg['type'] == 'arc': flags.append('curved')
    return _res(ctx, eid, rec, 'approx', [{'kind': 'wall_extrusion', 'location_curve': seg, 'thickness': w, 'height': H, 'base_z': z0, 'layers': layers, 'location_line': 'centre', 'voids': []}], flags, bbox=_wall_bbox(seg, w, z0, H))

def _wall_bbox(seg, w, z0, H):
    # world bbox of the analytic wall prism (centre line offset by half the thickness on both sides; arcs sampled through their 3 points, then widened by the half thickness)
    try:
        p0, p1 = seg['p0'], seg['p1']; xs = [p0[0], p1[0]]; ys = [p0[1], p1[1]]
        if seg['type'] == 'arc': xs.append(seg['mid'][0]); ys.append(seg['mid'][1])
        h = w / 2.0
        if seg['type'] == 'line':
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1.0; nx, ny = -dy / L * h, dx / L * h
            xs = [x + s * nx for x in xs for s in (-1, 1)]; ys = [y + s * ny for y in ys for s in (-1, 1)]
            return [[min(xs), min(ys), min(z0, z0 + H)], [max(xs), max(ys), max(z0, z0 + H)]]
        return [[min(xs) - h, min(ys) - h, min(z0, z0 + H)], [max(xs) + h, max(ys) + h, max(z0, z0 + H)]]
    except Exception:
        return None

def mep_curve(ctx, eid, rec):
    f = rec['fields']; cu = Gm.primary_curve(f)
    if cu is None: return None
    w = f.get('m_dWidthOrDiameter'); h = f.get('m_dHeight')
    if w is None: return None
    cls = rec['class']; round_ = cls in ('RbsPipeCurve', 'RbsConduitCurve')
    dpm = f.get('m_pDesignPropManager') or {}; dpm = dpm.get('obj', dpm) if isinstance(dpm, dict) else {}
    od = dpm.get('m_dOuterDiameter')
    sec = {'shape': 'round', 'diameter': (od or w)} if round_ else {'shape': 'rect', 'width': w, 'height': h or w}
    return _res(ctx, eid, rec, 'exact_geometry_approx_section', [{'kind': 'sweep', 'path': seg_dict(cu), 'section': sec, 'voids': []}], ['no_fittings_cuts'])

def instance_box(ctx, eid, rec):
    f = rec['fields']; inf = _g(f, 'm_pInstanceInfo') or {}
    inf = inf.get('obj', inf)
    trf = inf.get('m_Trf'); sid = inf.get('m_symbolId')
    sym = ctx.rec(sid)
    if not trf or not sym: return None
    m3 = trf['m_3x3']; o = trf['m_or']
    T = [[m3[0][0], m3[1][0], m3[2][0], o[0]], [m3[0][1], m3[1][1], m3[2][1], o[1]], [m3[0][2], m3[1][2], m3[2][2], o[2]], [0, 0, 0, 1]]
    ol = _g(sym['fields'], 'm_outline')
    mm = ol.get('m_minmax') if isinstance(ol, dict) else None
    if not mm or len(mm) < 2: return None
    lo, hi = mm[0], mm[1]
    return _res(ctx, eid, rec, 'box', [{'kind': 'box', 'min': list(lo), 'max': list(hi), 'symbol_id': int(sid)}], ['symbol_outline_only', 'family_solids_not_decoded'], transform=T)

BUILDERS = {'Floor': floor_like, 'Ceiling': floor_like, 'SWall': wall, 'RbsPipeCurve': mep_curve, 'RbsDuctCurve': mep_curve, 'RbsConduitCurve': mep_curve, 'CableTray': mep_curve, 'FamilyInstance': instance_box}

_docs = {}
def _mesh_geometry(file, element_id, rec):
    import rvt_elemmesh as EM
    d = _docs.get(file)
    if d is None: d = _docs[file] = (_F.Doc if _F and _F.on() else EM.Doc)(file)
    m = EM.element_mesh(d, int(element_id))
    if not m['tris']: return None
    import numpy as np
    P = np.array([p for t in m['tris'] for p in t])
    verts = P.round(6).tolist()
    prof = None
    try: prof = EM.end_cap_profile(m['tris'])
    except Exception: prof = None
    return _res(None, element_id, rec, 'mesh_approx', [{'kind': 'triangle_mesh', 'profile': prof, 'triangles': [[verts[3*i], verts[3*i+1], verts[3*i+2]] for i in range(len(verts)//3)], 'source': m['source']}],
                ['saved_graphics_tessellation'] + m['flags'], bbox=[P.min(0).tolist(), P.max(0).tolist()], notes='from channel-103 saved graphics; planar+cylindrical faces only')

def element_geometry(file, element_id):
    ctx = get_ctx(file); rec = ctx.rec(element_id)
    if rec is None: return _res(ctx, element_id, None, 'none', [], ['element_record_not_found'])
    b = BUILDERS.get(rec['class'])
    r = None
    if b:
        try: r = b(ctx, int(element_id), rec)
        except Exception as e: r = None
    merr = None
    if r is None or r['confidence'] == 'box':
        try:
            m = _mesh_geometry(file, element_id, rec)
            if m: return m
        except Exception as e:
            merr = 'mesh_error:%s:%s' % (type(e).__name__, str(e)[:80])     # e.g. missing mapbox_earcut outside the reader venv: never silent
    r = r or _res(ctx, element_id, rec, 'none', [], ['class_not_supported'])
    if merr: r['flags'] = list(r.get('flags', [])) + [merr]
    return r

def file_geometry_index(file):
    ctx = get_ctx(file); return {e: r['class'] for e, r in ctx.recs.items()}


def element_brep(file, element_id):
    """B-rep faces (surface dict + uv trim loops) of the element's saved graphics, in the vocabulary of the viewer's occsurf.py (see GEOMETRY_API.md)"""
    import rvt_elemmesh as EM
    d = _docs.get(file)
    if d is None: d = _docs[file] = (_F.Doc if _F and _F.on() else EM.Doc)(file)
    return EM.element_brep(d, int(element_id))


def curtain_grid(file, element_id):
    """curtain wall layout from the host record: {'u': [gridline ids], 'v': [...], 'panels': [...], 'mullions': [...]} (None when the element has no curtain grid).
    Panels/mullions/gridlines are separate elements: use element_geometry(id) for each."""
    ctx = get_ctx(file); r = ctx.rec(element_id)
    if r is None: return None
    out = {}
    drv = _g(r['fields'], 'm_hostObjMiscData', 'm_oCGDrivers') or []
    for d in drv:
        cg = _g(d, 'm_pCurtainGrid')
        if not isinstance(cg, dict): continue
        for k, nm in (('m_uLineIds', 'u'), ('m_vLineIds', 'v'), ('m_panelIds', 'panels'), ('m_mullionIds', 'mullions')):
            v = _g(cg, k)
            if isinstance(v, list): out.setdefault(nm, []).extend(int(x) for x in v)
    for d in drv:                                           # mullions are stored per edge/id in the driver's mullion table
        md = _g(d, 'm_mullionData', 'm_mullionsById')
        if isinstance(md, list):
            for e in md:
                mid = _g(e, 'm_mullionId')
                if mid is not None and int(mid) not in out.setdefault('mullions', []): out['mullions'].append(int(mid))
    return out or None
