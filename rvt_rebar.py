"""Rebar centre-lines from the file alone (own analysis; validated against Revit's Rebar.GetCenterlineCurves, gt_rebar/).
A Rebar record caches the centre-line curves of its FIRST bar in world coordinates (m_oInstance.m_oCacheData.m_noSelfIntersectingCenterlineCurves[0].m_centerlineCurves:
lines {m_origin, m_dirVec, m_endParams} and arcs {m_center, m_xVec, m_yVec, m_radius, m_endParams}); the other bar positions are rigid transforms of the first bar
(m_oInstance.m_barPositionsRelativeToFirstBarArr[i] = {m_3x3, m_or}, world = m_3x3 @ p + m_or) composed with m_individualBarsTrf[i]; m_includedBars masks hidden ends.
Bar diameter: the RebarBarType (m_barTypeId) -> 'Bar Diameter'.
API: rebar_centerlines(file, eid) -> {'bars': [[curve, ...] per bar position], 'diameter': ft or None}; curve = {'type': 'line', 'p0', 'p1'} | {'type': 'arc', 'p0', 'p1', 'mid', 'center', 'radius'}
     rebar_mesh(file, eid, sides=8) -> triangle list (swept circle of the bar diameter along each centre-line) for the viewer."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault('RVT_GEOM', '1')
import numpy as np
import rvt_famparams as F

def _ob(o): return o.get('obj', o) if isinstance(o, dict) and 'obj' in o else o

def _curve(c):
    c = _ob(c)
    if not isinstance(c, dict) or 'm_endParams' not in c: return None
    t0, t1 = c['m_endParams']
    if 'm_dirVec' in c:
        o = np.array(c['m_origin'], float); d = np.array(c['m_dirVec'], float)
        return {'type': 'line', 'p0': o + t0 * d, 'p1': o + t1 * d}
    if 'm_radius' in c:
        C = np.array(c['m_center'], float); X = np.array(c['m_xVec'], float); Y = np.array(c['m_yVec'], float); r = float(c['m_radius'])
        ev = lambda t: C + r * (math.cos(t) * X + math.sin(t) * Y)
        return {'type': 'arc', 'p0': ev(t0), 'p1': ev(t1), 'mid': ev((t0 + t1) / 2), 'center': C, 'radius': r, 'xvec': X, 'yvec': Y, 't0': t0, 't1': t1}
    return None

def _xf(cv, R, o):
    out = dict(cv)
    for k in ('p0', 'p1', 'mid', 'center'):
        if k in cv: out[k] = R @ cv[k] + o
    for k in ('xvec', 'yvec'):
        if k in cv: out[k] = R @ cv[k]
    return out

_X = {}
def _recs(path):
    if path not in _X:
        import rvt_xcache; x = rvt_xcache.get_x_ro(path); recs = {}
        for (eid, c), r in x['recs'].items(): recs.setdefault(eid, r)
        _X[path] = recs
    return _X[path]

def rebar_centerlines(path, eid):
    recs = _recs(path); r = recs.get(int(eid))
    if r is None: return None
    if r['class'] == 'RebarInSystem':
        sid = r['fields'].get('m_systemId')
        if sid is None: return None
        ar = area_reinforcement_bars(path, int(sid))
        return (ar or {}).get(int(eid))
    oi = F.S_(r['fields'], 'm_oInstance')
    if not isinstance(oi, dict): oi = F.S_(r['fields'], 'm_instance')            # Revit 2017 field name (same content)
    if not isinstance(oi, dict): return None
    cd = F.S_(oi, 'm_oCacheData') or {}
    if os.environ.get('RVT_REBAR_SHAPE') or not (cd.get('m_noSelfIntersectingCenterlineCurves') or cd.get('m_selfIntersectingCenterlineCurves')):
        sc = shape_centerline(recs, oi)
        if not sc: return None
        first, dia = sc; t = oi.get('m_shapeInstTrf') or {}; R = np.array(t.get('m_3x3', np.eye(3)), float); o = np.array(t.get('m_or', [0, 0, 0]), float)
        nb = int(oi.get('m_numberOfBarPositions') or 1); sp = float(oi.get('m_endPar') or 0.0) / (nb - 1) if nb > 1 else 0.0
        bars = []; inc = []
        for i in range(nb):
            inc.append(not ((i == 0 and oi.get('m_includeFirstBar') == 0) or (i == nb - 1 and oi.get('m_includeLastBar') == 0)))
            off = np.array([0.0, 0.0, i * sp])
            bars.append([_xf({k_: (v_ + off if k_ in ('p0', 'p1', 'mid', 'center') else v_) for k_, v_ in c.items()}, R, o) for c in first])
        return {'bars': bars, 'included': inc, 'diameter': dia, 'source': 'shape'}
    adjusted = os.environ.get('RVT_REBAR_ADJUSTED')                 # default: the plain centre-lines (GetCenterlineCurves(adjustForSelfIntersection=false)); the other cache is Revit's tilted variant that avoids hook overlap
    sets = (cd.get('m_noSelfIntersectingCenterlineCurves') if adjusted else cd.get('m_selfIntersectingCenterlineCurves')) or cd.get('m_noSelfIntersectingCenterlineCurves') or cd.get('m_selfIntersectingCenterlineCurves') or []
    if not sets: return None
    first = [c for c in (_curve(x) for x in (_ob(sets[0]).get('m_centerlineCurves') or [])) if c is not None]
    pos = oi.get('m_barPositionsRelativeToFirstBarArr') or [{'m_3x3': np.eye(3).tolist(), 'm_or': [0, 0, 0]}]
    ind = oi.get('m_individualBarsTrf') or []
    bars = []
    for i, t in enumerate(pos):
        R = np.array(t['m_3x3'], float); o = np.array(t['m_or'], float)
        if i < len(ind):
            R2 = np.array(ind[i]['m_3x3'], float); o2 = np.array(ind[i]['m_or'], float); R, o = R2 @ R, R2 @ o + o2
        bars.append([_xf(c, R, o) for c in first])
    ib = oi.get('m_includedBars'); inc = [True] * len(bars)
    if isinstance(ib, (bytes, bytearray)) and len(ib) == len(bars): inc = [bool(b_) for b_ in ib]
    elif isinstance(ib, str) and ib.startswith("b'"):
        try:
            import ast; bb = ast.literal_eval(ib)
            if len(bb) == len(bars): inc = [bool(b_) for b_ in bb]
        except Exception: pass
    dia = None
    bt = oi.get('m_barTypeId')
    if bt is not None and int(bt) in recs:
        bf = recs[int(bt)]['fields']
        for k in ('m_barModelDiameter', 'm_barDiameter', 'm_barNominalDiameter'):
            v = F.S_(bf, k) if isinstance(bf, dict) else None
            if isinstance(v, float): dia = v; break
    return {'bars': bars, 'included': inc, 'diameter': dia, 'source': 'cache'}

def _shape_params(oi):
    mp = F.S_(oi, 'm_params') or {}
    ent = (mp.get('m_map') or {}).get('m_map') or []; dv = ((mp.get('m_values') or {}).get('m_doubles')) or []
    out = {}
    for e in ent:
        sec = e.get('second') or {}
        if sec.get('m_ste') == 2 and 0 <= sec.get('m_index', -1) < len(dv): out[int(e['first'])] = float(dv[sec['m_index']])
    return out

def _arc(C, X, Y, r, t0, t1):
    ev = lambda t: C + r * (math.cos(t) * X + math.sin(t) * Y)
    return {'type': 'arc', 'p0': ev(t0), 'p1': ev(t1), 'mid': ev((t0 + t1) / 2), 'center': C, 'radius': r, 'xvec': X, 'yvec': Y, 't0': t0, 't1': t1}

def shape_centerline(recs, oi):
    """first-bar centre-line from the RebarShape definition (shapes defined by segments; files without the centre-line cache, Revit 2020-2022), in the shape frame:
    out-to-out polyline from (0,0) along the segments' fixed directions with the instance's length parameters, centre-line inset by d/2 toward the turning side,
    bends filleted with r = bend diameter / 2 + d / 2 (stirrup/tie bend diameter for stirrup-style shapes), hooks bend toward the inside at the end corners"""
    sid = oi.get('m_shapeId'); sh = recs.get(int(sid)) if sid is not None else None
    if sh is None: return None
    shf = sh['fields']; d_ = F.S_(shf, 'm_oDefinition')
    if not isinstance(d_, dict) or not d_.get('m_edges'): return None
    vals = _shape_params(oi); bt = recs.get(int(oi.get('m_barTypeId') or -1)); btf = bt['fields'] if bt else {}
    dia = float(btf.get('m_barDiameter') or btf.get('m_barModelDiameter') or 0.0)
    stirrup = shf.get('m_style') == 1
    bend_d = float(btf.get('m_stirrupTieBendDiam') if stirrup else btf.get('m_standardBendDiam') or 0.0)
    hook_d = float(btf.get('m_stirrupTieBendDiam') if stirrup else btf.get('m_standardHookBendDiam') or bend_d)
    segs = []
    for e in d_['m_edges']:
        e = _ob(e); dr = None; L = None
        for c in e.get('m_constraints') or []:
            c = _ob(c)
            if 'm_dir' in c: dr = np.array(c['m_dir']['m_xyz'][:2], float)
            if 'm_paramId' in c and c['m_paramId'] is not None and int(c['m_paramId']) in vals: L = vals[int(c['m_paramId'])]
        if dr is None or L is None or e.get('m_type', 0) != 0: return None          # only straight segments with a fixed direction and a length parameter (yet)
        segs.append((dr / np.linalg.norm(dr), L))
    n = len(segs); P = [np.zeros(2)]
    for dr, L in segs: P.append(P[-1] + dr * L)
    cr = lambda a, b: a[0] * b[1] - a[1] * b[0]
    turns = [np.sign(cr(segs[k][0], segs[k + 1][0])) for k in range(n - 1)]
    side = []
    for k in range(n):
        t = turns[k] if k < n - 1 else (turns[k - 1] if k > 0 else 1.0)
        if t == 0: t = turns[k - 1] if k > 0 else 1.0
        side.append(t)
    inset = dia / 2
    if n == 1:                                                         # a straight bar: centre-line on the shape's own axis; hooks bend to the side given by the instance (m_hookOrient 1 = left, 0 = right)
        inset = 0.0; side = [1.0]
    lft = lambda v: np.array([-v[1], v[0]])
    rc = bend_d / 2 + dia / 2; rh = hook_d / 2 + dia / 2
    cl = [(P[k] + lft(segs[k][0]) * side[k] * inset, P[k + 1] + lft(segs[k][0]) * side[k] * inset) for k in range(n)]     # inset centre-line segments
    for k in range(n - 1):                                             # inset corner = intersection of the two inset lines
        nu = lft(segs[k][0]) * side[k]; nv = lft(segs[k + 1][0]) * side[k + 1]
        A_ = np.array([nu, nv]); bb = np.array([np.dot(P[k + 1], nu) + dia / 2, np.dot(P[k + 1], nv) + dia / 2])
        try: q = np.linalg.solve(A_, bb)
        except np.linalg.LinAlgError: continue
        cl[k] = (cl[k][0], q); cl[k + 1] = (q, cl[k + 1][1])
    # corner fillets: trim each pair of consecutive centre-line segments at the tangent points
    starts = [c[0].copy() for c in cl]; ends = [c[1].copy() for c in cl]; arcs = []
    for k in range(n - 1):
        u, v = segs[k][0], segs[k + 1][0]; th = math.acos(max(-1.0, min(1.0, float(np.dot(u, v)))))
        if th < 1e-9: arcs.append(None); continue
        a_ = rc * math.tan(th / 2); corner = ends[k]                       # inset segments meet at the inset corner
        ends[k] = corner - u * a_; starts[k + 1] = corner + v * a_
        C = ends[k] + lft(u) * side[k] * rc
        arcs.append((C, ends[k], starts[k + 1], side[k]))
    out = []
    hooks = shf.get('m_hook') or [0, 0]
    def arc2(C, pa, pb, sd):
        X = np.array([1.0, 0.0]); a0 = math.atan2(*(pa - C)[::-1]); a1 = math.atan2(*(pb - C)[::-1])
        if sd > 0:
            while a1 < a0: a1 += 2 * math.pi
        else:
            while a1 > a0: a1 -= 2 * math.pi
        return (C, abs(pa - C).max() and float(np.linalg.norm(pa - C)), a0, a1)
    def hook(at_start):
        ang = math.radians(float(hooks[0 if at_start else 1] or 0))
        if ang <= 0: return []
        k = 0 if at_start else n - 1; u = segs[k][0]
        ho = (shf.get('m_hookOri') or [1, 3])[0 if at_start else 1]
        sd = (1.0 if ho == 1 else -1.0) if at_start else (1.0 if ho == 3 else -1.0)     # RebarShape.m_hookOri: start 1 = left of the bar direction, 3 = right; end 3 = left, 1 = right (stirrups [1, 3]: both inward)
        if at_start:
            T = P[0] + lft(u) * sd * inset + u * (rh + dia / 2)              # tangent point where segment 0 straight begins (out-to-out from the hook outer face)
            starts[0] = T; C = T + lft(u) * sd * rh
            a1 = math.atan2(*(T - C)[::-1]); a0 = a1 - sd * ang           # the hook arc ends at T
            e0 = C + rh * np.array([math.cos(a0), math.sin(a0)])
            tg = np.array([-math.sin(a0), math.cos(a0)]) * sd               # arc direction at its start
            ext = _hook_ext(btf, oi, dia, 0, ang, rh, recs)
            return [('line', e0 - tg * ext, e0), ('arc', C, rh, a0, a1)]
        T = P[n] + lft(u) * sd * inset - u * (rh + dia / 2)
        ends[n - 1] = T; C = T + lft(u) * sd * rh
        a0 = math.atan2(*(T - C)[::-1]); a1 = a0 + sd * ang
        e1 = C + rh * np.array([math.cos(a1), math.sin(a1)]); tg = np.array([-math.sin(a1), math.cos(a1)]) * sd
        return [('arc', C, rh, a0, a1), ('line', e1, e1 + tg * _hook_ext(btf, oi, dia, 1, ang, rh, recs))]
    hs = hook(True); he = hook(False)
    seq = list(hs)
    for k in range(n):
        seq.append(('line', starts[k], ends[k]))
        if k < n - 1 and arcs[k] is not None:
            C, pa, pb, sd = arcs[k]; _, r_, a0, a1 = arc2(C, pa, pb, sd); seq.append(('arc', C, r_, a0, a1))
    seq += he
    res = []
    X3 = np.array([1.0, 0.0, 0.0]); Y3 = np.array([0.0, 1.0, 0.0]); z3 = lambda q: np.array([q[0], q[1], 0.0])
    for it in seq:
        if it[0] == 'line':
            if np.linalg.norm(it[2] - it[1]) > 1e-9: res.append({'type': 'line', 'p0': z3(it[1]), 'p1': z3(it[2])})
        else:
            _, C, r_, a0, a1 = it; res.append(_arc(z3(C), X3, Y3, r_, a0, a1))
    return res, dia

def _hook_ext(btf, oi, dia, end, ang=None, rh=None, recs=None):
    """straight extension of a hook: the bar type's hook-length setting for this hook type (m_HLSettingsMap[hook type].m_offsetLength; 0.2 mm shorter than Revit's
    curve in 2020_21), else 6 x diameter (Revit's default extension multiplier)"""
    ht = oi.get('m_hookTypeId%d' % end)
    for e in btf.get('m_HLSettingsMap') or []:
        if ht is not None and int(e.get('first', -1)) == int(ht):
            ol = float((e.get('second') or {}).get('m_offsetLength') or -1); hl = float((e.get('second') or {}).get('m_hookLength') or -1)
            if ol > 0: return ol
            if hl > 0 and rh is not None and ang is not None and abs(ang - math.pi / 2) < 1e-6: return hl - rh - dia / 2      # 90-degree hook: out-to-out hook length (2020_21 157117 exact)
    mult = 6.0
    if recs is not None and ht is not None and int(ht) in recs:
        mult = float(recs[int(ht)]['fields'].get('m_straightLineMultiplier') or 6.0)
    return mult * dia

def _polyline(cv, seg_angle=math.pi / 12):
    if cv['type'] == 'line': return [cv['p0'], cv['p1']]
    n = max(2, int(math.ceil(abs(cv['t1'] - cv['t0']) / seg_angle)))
    C, X, Y, r = cv['center'], cv['xvec'], cv['yvec'], cv['radius']
    return [C + r * (math.cos(t) * X + math.sin(t) * Y) for t in np.linspace(cv['t0'], cv['t1'], n + 1)]

def rebar_mesh(path, eid, sides=8, default_dia=0.04):
    """triangles (numpy (n, 3, 3) array, feet) of the included bars swept as open tubes along the centre-lines"""
    cl = rebar_centerlines(path, eid)
    if not cl: return np.zeros((0, 3, 3))
    rad = (cl['diameter'] or default_dia) / 2; out = []
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False); cs, sn = np.cos(ang), np.sin(ang)
    inc = cl.get('included') or [True] * len(cl['bars'])
    for bi, bar in enumerate(cl['bars']):
        if not inc[bi]: continue
        pts = []
        for cv in bar:
            p = _polyline(cv)
            pts += p if not pts else p[1:]
        A = np.array(pts[:-1], float); B = np.array(pts[1:], float); D = B - A; L = np.linalg.norm(D, axis=1)
        ok = L > 1e-9
        if not ok.any(): continue
        A, B, D = A[ok], B[ok], D[ok] / L[ok][:, None]
        ref = np.where(np.abs(D[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
        U = np.cross(D, ref); U /= np.linalg.norm(U, axis=1)[:, None]; V = np.cross(D, U)
        R = rad * (U[:, None, :] * cs[None, :, None] + V[:, None, :] * sn[None, :, None])      # (segments, sides, 3)
        R1 = np.roll(R, -1, axis=1)
        a0, b0, b1, a1 = A[:, None, :] + R, B[:, None, :] + R, B[:, None, :] + R1, A[:, None, :] + R1
        out.append(np.stack([a0, b0, b1], axis=2).reshape(-1, 3, 3)); out.append(np.stack([a0, b1, a1], axis=2).reshape(-1, 3, 3))
    return np.concatenate(out) if out else np.zeros((0, 3, 3))

# ---------------- area reinforcement (RebarSystem + RebarInSystem), own analysis vs Revit's GetCenterlineCurves (gt_rebar) ----------------
_COV = {}
def _cover(recs, host_id):
    """cover distance: the document's first CoverType (Revit's default 'Rebar Cover 1'; hosts in the samples name no cover type of their own)"""
    k = id(recs)
    if k not in _COV:
        cts = sorted(i for i, r in recs.items() if r['class'] == 'CoverType')
        _COV[k] = float(recs[cts[0]]['fields'].get('m_length') or 0.0) if cts else 0.0
    return _COV[k]

_AR = {}
def area_reinforcement_bars(path, system_id):
    k = (path, int(system_id))
    if k not in _AR: _AR[k] = _area_reinforcement_bars(path, system_id)
    return _AR[k]

def _area_reinforcement_bars(path, system_id):
    """{rebar_in_system_id: {'bars': [[line]], 'diameter'}} for an AreaReinforcement (RebarSystem record): boundary = the outline Revit draws for the system
    on the exterior face (saved graphics, three copies: exterior face, centre, interior face), major direction = the sketch's direction curve; per layer
    (m_face 0 exterior / 1 interior, m_direction 0 major / 1 minor): depth = cover + d/2 (major, outermost) or cover + d + d/2 (minor), bars run along their
    direction between the boundary +- cover, n = m_numberOfLines bars spread evenly between boundary + cover + d/2 and boundary - cover - d/2"""
    import rvt_elemmesh as EM
    recs = _recs(path); sy = recs.get(int(system_id))
    if sy is None or sy['class'] != 'RebarSystem': return None
    f = sy['fields']; doc = _DOCS.get(path) or _DOCS.setdefault(path, EM.Doc(path))
    curves = [c for c in EM.element_curves(doc, int(system_id)) if c.get('type') == 'line']
    if len(curves) < 3: return None
    sk = recs.get(int(f.get('m_sketchId') or -1)); mj = None
    if sk is not None:
        for p in F.S_(sk['fields'], 'm_elemIdsPairSet', 'm_data') or []:
            r = recs.get(int(p.get('m_elementId', -1)))
            if r is not None and r['class'] == 'CurveElem':
                import rvt_geom as Gm
                cu = Gm.primary_curve(r['fields'])
                if cu is not None and 'm_dirVec' in cu: mj = (np.array(cu['m_origin'], float), np.array(cu['m_dirVec'], float)); break
    if mj is None: return None
    u = mj[1] / np.linalg.norm(mj[1])
    P = np.array([[c['p0'], c['p1']] for c in curves], float)
    # the outline copies lie in parallel planes; their normal is perpendicular to u and to the outline's other direction
    dirs = [d / np.linalg.norm(d) for d in (P[:, 1] - P[:, 0]) if np.linalg.norm(d) > 1e-9]
    w = next((d for d in dirs if abs(np.dot(d, u)) < 0.5), None)
    if w is None: return None
    n = np.cross(u, w); n /= np.linalg.norm(n)
    offs = np.round(P.reshape(-1, 3) @ n, 6); levels = sorted(set(offs.tolist()))
    ext = float(np.dot(mj[0], n)); intr = min(levels, key=lambda x: -abs(x - ext))       # sketch (major direction curve) is on the exterior face; interior = farthest copy
    if ext < intr: n = -n; ext, intr = -ext, -intr; offs = -offs
    face_pts = P.reshape(-1, 3)[np.abs(offs - ext) < 1e-4]
    v = np.cross(u, n)                                                 # bar order and minor-bar direction as Revit's (2020 rst_basic oracle)
    U = face_pts @ u; V = face_pts @ v
    umin, umax, vmin, vmax = U.min(), U.max(), V.min(), V.max()
    cover = _cover(recs, f.get('m_hostId'))
    out = {}
    # boundary polygon edges on the exterior face, in (u, v)
    segs2 = []
    for c, o_ in zip(P, offs.reshape(-1, 2)):
        if abs(o_[0] - ext) < 1e-4 and abs(o_[1] - ext) < 1e-4: segs2.append(((float(c[0] @ u), float(c[0] @ v)), (float(c[1] @ u), float(c[1] @ v))))
    def clip(t, along_u):
        """intervals of the line (v = t if along_u else u = t) inside the boundary (even-odd over the drawn outline)"""
        xs = []
        for (pa, pb) in segs2:
            ca, cb = (pa[1], pb[1]) if along_u else (pa[0], pb[0]); da, db = (pa[0], pb[0]) if along_u else (pa[1], pb[1])
            if (ca - t) * (cb - t) < 0 or (abs(ca - cb) > 1e-12 and min(ca, cb) < t <= max(ca, cb) and (ca == t or cb == t)):
                xs.append(da + (db - da) * (t - ca) / (cb - ca))
        xs.sort(); return [(xs[k], xs[k + 1]) for k in range(0, len(xs) - 1, 2)]
    # boundary loop (chained outline edges) offset inward by the cover: Revit measures the cover perpendicular to each boundary edge (slanted edges too)
    def _loop(sg):
        if not sg: return None
        key = lambda p_: (round(p_[0], 5), round(p_[1], 5)); nxt = {}
        for a_, b_ in sg: nxt.setdefault(key(a_), []).append(b_); nxt.setdefault(key(b_), []).append(a_)
        loop = [sg[0][0], sg[0][1]]; prev = key(sg[0][0])
        for _ in range(len(sg) + 2):
            cand = [q for q in nxt.get(key(loop[-1]), []) if key(q) != prev]
            if not cand: return None
            prev = key(loop[-1]); q = cand[0]
            if key(q) == key(loop[0]): return loop
            loop.append(q)
        return None
    def _inset(loop, c):
        Lp = [np.array(q, float) for q in loop]
        k = 0
        while len(Lp) > 3 and k < len(Lp):                             # drop collinear split points (the outline is drawn in pieces)
            a_, b_, c_ = Lp[k - 1], Lp[k], Lp[(k + 1) % len(Lp)]
            if abs((b_[0] - a_[0]) * (c_[1] - b_[1]) - (b_[1] - a_[1]) * (c_[0] - b_[0])) < 1e-9 * max(1.0, np.linalg.norm(c_ - a_)) ** 2: Lp.pop(k)
            else: k += 1
        m_ = len(Lp)
        area = sum(Lp[k][0] * Lp[(k + 1) % m_][1] - Lp[(k + 1) % m_][0] * Lp[k][1] for k in range(m_)) / 2
        inward = 1.0 if area > 0 else -1.0                                 # CCW loop: inside is to the left of each edge
        lines = []
        for k in range(m_):
            a_, b_ = Lp[k], Lp[(k + 1) % m_]; dd = (b_ - a_) / np.linalg.norm(b_ - a_); nn = np.array([-dd[1], dd[0]]) * inward
            lines.append((a_ + nn * c, dd))
        out_ = []
        for k in range(m_):
            (p1_, d1), (p2_, d2) = lines[k - 1], lines[k]
            A_ = np.array([d1, -d2]).T
            try: tt = np.linalg.solve(A_, p2_ - p1_); out_.append(p1_ + d1 * tt[0])
            except np.linalg.LinAlgError: out_.append(p2_)
        return [(tuple(out_[k]), tuple(out_[(k + 1) % m_])) for k in range(m_)]
    _lp = _loop(segs2)
    inset_segs = _inset(_lp, cover) if _lp else None
    def clip_inset(t, along_u, c):
        """intervals of the bar line inside the boundary inset by the cover"""
        if inset_segs is None:
            return [(a0 + c, a1 - c) for a0, a1 in clip(t, along_u) if a1 - a0 > 2 * c]
        keep = segs2[:]; segs2[:] = inset_segs
        try: return clip(t, along_u)
        finally: segs2[:] = keep
    members = {}
    for i, r in recs.items():
        if r['class'] == 'RebarInSystem' and int(r['fields'].get('m_systemId') or -1) == int(system_id):
            key = F.S_(r['fields'], 'm_key') or {}
            members.setdefault(int(key.get('m_layer') or 0), []).append((int(key.get('m_index') or 0), i))
    for li, L in enumerate(f.get('m_layers') or []):
        if not L.get('m_active', 1) or li not in members: continue
        bt = recs.get(int(L.get('m_barType') or -1)); d = float((bt['fields'].get('m_barDiameter') or bt['fields'].get('m_barModelDiameter') or 0.0) if bt else 0.0)
        minor = bool(L.get('m_direction')); interior = bool(L.get('m_face'))
        depth = cover + d / 2 + (d if minor else 0.0)
        plane = (intr + depth) if interior else (ext - depth)
        along, across = (v, u) if minor else (u, v)
        b0, b1 = (umin, umax) if minor else (vmin, vmax)
        nb = int(L.get('m_numberOfLines') or 0); lo, hi = b0 + cover + d / 2, b1 - cover - d / 2
        groups = []                                                    # consecutive bars with the same clipped extents form one RebarInSystem piece (m_key.m_index order)
        for k in range(nb):
            t = lo + (hi - lo) * k / (nb - 1) if nb > 1 else (lo + hi) / 2
            for (a0, a1) in clip_inset(t, not minor, cover):
                p0 = n * plane + across * t + along * a0; p1 = n * plane + across * t + along * a1
                key = (round(a0, 5), round(a1, 5))
                if not groups or groups[-1][0] != key: groups.append([key, []])
                groups[-1][1].append([{'type': 'line', 'p0': p0, 'p1': p1, 'mid': (p0 + p1) / 2}])
        for (idx, eid_), g in zip(sorted(members[li]), groups):
            out[eid_] = {'bars': g[1], 'included': [True] * len(g[1]), 'diameter': d, 'source': 'area_reinforcement'}
    return out
_DOCS = {}
