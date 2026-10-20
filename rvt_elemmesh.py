"""element_mesh(file, id): triangle mesh of an element from its saved graphics (channel 103). Units feet, world frame."""
import os, sys, pickle, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault('RVT_GEOM', '1')
import numpy as np, g103_get as GG, rvt_mesh as M

def _ob(x): return x.get('obj', x) if isinstance(x, dict) else x

class Doc:
    def __init__(s, f, index_pkl=None):
        s.f = f; s.res = pickle.load(open(index_pkl, 'rb')) if index_pkl else GG.cached_index(f); s.o, s.dec = GG.load_dec(f)
    def _census(s):
        """element class per id + WallSweep types, from a light extraction (class census, cached next to the xcache); never loads the full-field cache"""
        if getattr(s, '_cen', None) is not None: return s._cen
        import hashlib, pickle, rvt_entities as RE
        here = os.path.dirname(os.path.abspath(__file__)); st = os.stat(s.f)
        k = hashlib.sha1(('%s|%d|%d|%d|%d' % (s.f, st.st_size, int(st.st_mtime), int(os.path.getmtime(os.path.join(here, 'rvt_decode.py'))), 2)).encode()).hexdigest()
        fn = os.path.join(here, 'xcache', k + '.census.pkl')
        if os.path.exists(fn):
            s._cen = pickle.load(open(fn, 'rb')); return s._cen
        x = RE.extract(s.f, want_all=True, slim=lambda c: c == 'WallSweep')
        cen = {'cls': {}, 'ws': {}}
        for (eid, c), r in x['recs'].items():
            cen['cls'].setdefault(eid, c)
            if c == 'WallSweep':
                try:
                    import rvt_entities as _E
                    cen['ws'][eid] = int(_E.S_(r['fields'], 'm_wallSweepInfo', 'm_wallSweepType'))
                except Exception: pass
        os.makedirs(os.path.dirname(fn), exist_ok=True); pickle.dump(cen, open(fn + '.tmp', 'wb')); os.replace(fn + '.tmp', fn)
        s._cen = cen; return cen
    def cls(s, eid):
        """element class name of an id (light class census), None if unknown"""
        try: return s._census()['cls'].get(int(eid))
        except Exception: return None
    def is_reveal(s, eid):
        """WallSweepInfo.m_wallSweepType 1 = reveal (cuts the wall, adds no solid), 0 = sweep"""
        try: return s._census()['ws'].get(int(eid)) == 1
        except Exception: return False
    def rec(s, eid):
        i = s.res.get(eid)
        return GG.get_record(s.f, i, s.o, s.dec) if i else None

def _polymeshes(fields):
    out = []; st = [fields]
    while st:
        z = st.pop()
        if isinstance(z, dict):
            if 'm_pFacetedTopology' in z: out.append(z)
            for b in z.values():
                if b is not None: st.append(b)
        elif isinstance(z, list): st.extend(z)
    return out

def _cond_ok(c, detail):
    c = _ob(c)
    if not isinstance(c, dict): return True
    comp = c.get('m_comp')
    if comp == 3 and c.get('m_param') == 3: return c.get('m_value') == detail            # detail-level condition: 1 coarse, 2 medium, 3 fine
    if comp == 0 and c.get('m_param') == 3: return c.get('m_value') != detail              # empirical: a representation tagged (0,3,v) is drawn for the other detail levels, not at v (203022 vs 1458122)
    if comp in (6, 7): return bool(c.get('m_negateDirCondition'))                         # cut-plane variants (above/below a view cut): the uncut 3D body is the negated one
    return True

def _geos_f(fields, detail=2):
    """Geometry nodes / GInstance nodes of a scene-graph record that apply to the 3D model at the given detail level (1 coarse, 2 medium = Revit API default, 3 fine)"""
    out = []; inst = []
    def walk(n, ok):
        n = _ob(n)
        if not isinstance(n, dict): return
        if ok and n.get('m_oConditions'):
            ok = all(_cond_ok(c, detail) for c in n['m_oConditions'])
        if not ok: return
        if n.get('m_pFaces'): out.append(n)
        if 'm_instanceInfo' in n: inst.append(n)
        for k in (n.get('m_subNodes') or []): walk(k, ok)
    walk(fields, True)
    if any(((g.get('m_GInfo') or {}).get('m_flags') or 0) & 0xE0 for g in out) and any(not (((g.get('m_GInfo') or {}).get('m_flags') or 0) & 0xE0) for g in out): out = [g for g in out if not (((g.get('m_GInfo') or {}).get('m_flags') or 0) & 0xE0)]      # nodes with GInfo flag bits 0xE0 set are not part of the displayed solid (hidden/auxiliary bodies)
    if False and any((g.get('m_flags') or 0) & 1 for g in out): out = [g for g in out if (g.get('m_flags') or 0) & 1]       # Geometry.m_flags bit 0 clear = not a displayed solid (e.g. void bodies)
    return out, inst

def _geos(fields):
    out = []; inst = []
    st = [fields]
    while st:
        z = st.pop()
        if isinstance(z, dict):
            if z.get('m_pFaces'): out.append(z)
            if 'm_instanceInfo' in z: inst.append(z)
            for b in z.values():
                if b is not None: st.append(b)
        elif isinstance(z, list): st.extend(z)
    return out, inst

def _xf(tris, R, o):
    return [tuple(R @ np.asarray(p) + o for p in t) for t in tris]

def _xfm(meta, R, o):
    out = []
    for kind, ev, uvs in meta:
        out.append((kind, (lambda u, v, ev=ev: R @ np.asarray(ev(u, v)) + o), uvs))
    return out

def _material_of(doc, rs, node_style):
    """material id of a face (as rvt_materials.material_for_face): face render style when it is a MaterialElem, else that style's graphics-style material,
    else the material of the Geometry node's graphics style (GInfo.m_categoryId); -1 when unassigned"""
    c = doc.__dict__.setdefault('_matc', {}); k = (rs, node_style)
    if k in c: return c[k]
    import rvt_materials as RM
    out = -1; rs_ = RM._eid(rs); ns_ = RM._eid(node_style)
    try:
        sg = (rs_ - (1 << 64)) if rs_ is not None and rs_ >= 1 << 63 else ((rs_ - (1 << 32)) if rs_ is not None and 1 << 31 <= rs_ < 1 << 32 else rs_)
        if sg is not None and sg < -1: out = sg                                    # built-in material id (rooms: -4000011), as Revit's Face.MaterialElementId reports it
        elif rs_ is not None:
            rr = RM._ctx(doc.f).rec(rs_)
            if rr is not None and rr['class'] == 'MaterialElem': out = rs_
            else:
                m = RM.gstyle_material(doc.f, rs_)
                if m is not None: out = m
        if out == -1 and ns_ is not None:
            m = RM.gstyle_material(doc.f, ns_)
            if m is not None: out = m
    except Exception: out = -1
    c[k] = out; return out

def _sty(g):
    """graphics style key for duplicate-body merging: built-in styles with a small id (< 1000: 'Cutting geometry' in 2024 Structural, id 231) behave like no style; subcategory styles created by the family (Insulation / Lining of duct fittings, ids in the tens of thousands) keep a body of their own (Revit sums those)"""
    try:
        v = int((g.get('m_GInfo') or {}).get('m_categoryId'))
        return -1 if (v < 1000 or v >= 1 << 63 or v == 0xFFFFFFFF) else v
    except Exception: return -1

def _node_style(g):
    try: return (g.get('m_GInfo') or {}).get('m_categoryId')
    except Exception: return None

def _tri_mats(doc, t, g):
    """per-triangle material ids of a tessellate_geometry/element_faces_in_bbox result of Geometry node g"""
    ns = _node_style(g); frs = t.get('frs') or [None] * len(t['tris'])
    return [_material_of(doc, r, ns) for r in frs]

def _inst_parts(doc, inst, bb, symbol_depth, detail, flags):
    """meshes of the symbol instances of an element (symbol graphics transformed by the instance transform) -> (tris, metas, nids, fids)"""
    tris = []; metas = []; nids = []; fids = []; ninst = 0; mats = []
    # an instance flagged with a forbidden-target mask is drawn through its own element (e.g. a railing's top rail): not part of this element's solid
    inst = [z for z in inst if not (isinstance(z.get('m_forbiddenTarget'), dict) and z['m_forbiddenTarget'].get('m_targets'))] or inst
    inst = [z for z in inst if doc.cls(_ob(z['m_instanceInfo']).get('m_symbolId')) != 'FamilyInstance']       # nested hosted FamilyInstances are separate elements (Revit's own geometry of the host does not repeat them)
    for z in inst:
        ii = _ob(z['m_instanceInfo']); t = ii.get('m_Trf'); sid = ii.get('m_symbolId')
        if not t or sid is None: continue
        sub = element_mesh(doc, int(sid), symbol_depth - 1, detail)
        if not sub['tris']: flags.append('symbol_no_graphics'); continue
        m3 = np.array(t['m_3x3'], float); o = np.array(t['m_or'], float)
        # m_3x3 stored row-major as basis vectors? choose the variant whose bbox fits the element bbox
        best = None
        for R in (m3,):                                                  # verified against Revit's FINST/GeometryInstance transforms: the columns of m_3x3 are the basis vectors (world = m_3x3 @ local + m_or)
            tt = _xf(sub['tris'], R, o)
            if bb:
                P = np.array([p for tr in tt for p in tr]); lo, hi = P.min(0), P.max(0)
                l = np.maximum(lo, bb[0]); h = np.minimum(hi, bb[1]); inter = np.prod(np.clip(h - l, 0, None))
                iou = inter / (np.prod(hi - lo) + np.prod(np.array(bb[1]) - np.array(bb[0])) - inter + 1e-12)
            else: iou = 0
            if best is None or iou > best[0]: best = (iou, tt, R)
        ninst += 1; fids += [ninst * 10**6 + f_ for f_ in (sub.get('fid') or list(range(len(sub['tris']))))]; nids += [ninst * 100000 + (n_ if n_ is not None else 0) for n_ in (sub.get('nid') or [0] * len(sub['tris']))]; tris += best[1]; mats += (sub.get('mat') if len(sub.get('mat') or []) == len(sub['tris']) else [-1] * len(sub['tris'])); metas += _xfm(sub.get('meta', []), best[2], o) if sub.get('meta') and len(sub['meta']) == len(sub['tris']) else [('plane', None, None)] * len(sub['tris'])
    _inst_parts.last_mat = mats
    return tris, metas, nids, fids

def element_mesh(doc, eid, symbol_depth=2, detail=3):
    m = _element_mesh0(doc, eid, symbol_depth, detail)
    try:                                                                   # topography carries its material only as the instance parameter 'Material' (-1002107), no per-face render style
        if m.get('tris') and doc.cls(eid) in ('SiteSurface', 'Toposolid') and all(x == -1 for x in (m.get('mat') or [-1])):
            import rvt_params as RP
            import rvt_materials as RM2
            mid = RP.stored_params(RM2._ctx(doc.f).rec(eid)['fields']).get(-1002107)
            if isinstance(mid, int) and mid > 0: m['mat'] = [mid] * len(m['tris'])
    except Exception: pass
    return m

def _element_mesh0(doc, eid, symbol_depth=2, detail=3):
    rec = doc.rec(eid)
    if rec is None: return {'tris': [], 'source': 'none', 'flags': ['no_saved_graphics']}
    fl = rec['fields']; bb = fl.get('m_bBox'); geos, inst = _geos_f(fl, detail)
    if not geos and not inst: geos, inst = _geos(fl)
    flags = []
    pm = []
    for z in _polymeshes(fl): pm += M.polymesh_tris(z)
    own = []; ownm = []; ownf = []; ownn = []; un = []; nface = 0; ownp = {}; fmat = {}
    def _cat_ok(g):
        try: return int(g['m_GInfo']['m_categoryId']) not in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
        except Exception: return False
    geos_all = geos
    if any(_cat_ok(g) for g in geos) and doc.cls(eid) in ('ModelText', 'Text3dElem'): geos = [g for g in geos if _cat_ok(g)]      # ModelText keeps an uncategorised bounding box node next to the letters          # auxiliary nodes (reference boxes, layer interfaces) carry no category
    if bb:
        for gi_, g in enumerate(geos):
            t = M.element_faces_in_bbox(g, bb, eps=0.02); fmat.update({nface + f_: m_ for f_, m_ in zip(t['fidx'], _tri_mats(doc, t, g))}); own += t['tris']; ownm += t['meta']; ownf += [nface + f for f in t['fidx']]; ownn += [gi_] * len(t['tris']); ownp.update({nface + k_: v_ for k_, v_ in t.get('fprio', {}).items()}); nface += t['faces'] + 1; un += t['unsupported']
    if own or pm:
        if pm: flags = flags + ['polymesh']
        if own and len(ownf) == len(own):
            # nodes that close on their own are the element's bodies; single reference faces / other elements' faces in the same joined geometry do not
            per = []
            if len(set(ownn)) > 1:
                for g_ in sorted(set(ownn)):
                    ix = [i for i, n_ in enumerate(ownn) if n_ == g_]
                    st1, sm1, ok1 = M.select_closed_shell([own[i] for i in ix], [ownm[i] for i in ix], [ownf[i] for i in ix], prio=ownp)
                    if ok1 and len(st1) < 0.5 * len(ix) and M.nearly_closed([own[i] for i in ix]):
                        # a small closed sub-shell of a large nearly-closed body (trimmed curved faces that do not weld): the body is the solid (2026 Site 'Block 69': 156 of 5,660 triangles kept, volume 0.7% of Revit's)
                        fl1 = list(M.select_closed_shell.last_fidx)
                        vw = M.volume_by_node([own[i] for i in ix], [ownm[i] for i in ix], [0] * len(ix), fid=[ownf[i] for i in ix])[0]
                        vs = M.volume_by_node(st1, sm1, [0] * len(st1), fid=fl1)[0]
                        if vw > 1.5 * vs and os.environ.get("RVT_WHOLEBODY_LOG"): print("WHOLEBODY", eid, round(vs, 4), round(vw, 4), file=sys.stderr)
                        if vw > 1.5 * vs: per.append(([own[i] for i in ix], [ownm[i] for i in ix], [ownf[i] for i in ix], g_)); continue
                        M.select_closed_shell.last_fidx = fl1
                    if ok1: per.append((st1, sm1, list(M.select_closed_shell.last_fidx), g_))
                    elif M.nearly_closed([own[i] for i in ix]): per.append(([own[i] for i in ix], [ownm[i] for i in ix], [ownf[i] for i in ix], g_))      # trimmed curved faces whose boundary samples do not weld exactly
            if per:                                                       # exact duplicate bodies (same corners) are one solid in Revit's geometry
                def _sig(p):                                              # same corners AND same graphics style: a duct fitting's zero-thickness insulation/lining bodies coincide with the duct but Revit sums them (2020_22: Volume = 3x the body)
                    P = np.array([q for t in p[0] for q in t]); return (len(p[0]), tuple(np.round(P.min(0), 3)), tuple(np.round(P.max(0), 3)), round(float(np.abs(P).sum()), 2), str(_sty(geos[p[3]])))
                seen_sig = set(); uniq = []
                for p in per:
                    sg = _sig(p)
                    if sg in seen_sig: continue
                    seen_sig.add(sg); uniq.append(p)
                per = uniq
                own = [t for p in per for t in p[0]]; ownm = [m for p in per for m in p[1]]; ownf = [f for p in per for f in p[2]]; ownn = [p[3] for p in per for _ in p[0]]; flags = flags + ['closed_shell', 'per_node']
            else:
                st, sm, ok = M.select_closed_shell(own, ownm, ownf, prio=ownp)
                if ok: own, ownm = st, sm; ownn = [0] * len(own); ownf = list(M.select_closed_shell.last_fidx); flags = flags + ['closed_shell']
        xt = []; xm = []; xn = []; xf = []; xmat = []
        if inst and symbol_depth > 0:                                  # the element also instantiates other symbols (e.g. a stair railing's balusters next to its rods)
            inst_sym = [z for z in inst if z.get('m_oEmbeddedSymbolGRep') is None and ((doc.cls(_ob(z['m_instanceInfo']).get('m_symbolId')) or '').endswith('Symbol') or (doc.cls(_ob(z['m_instanceInfo']).get('m_symbolId')) in ('WallSweep',) and not doc.is_reveal(_ob(z['m_instanceInfo']).get('m_symbolId'))))]       # instances of another element (e.g. a nested hosted FamilyInstance) are separate elements
            xt, xm, xn, xf = _inst_parts(doc, inst_sym, bb, symbol_depth, detail, flags) if inst_sym else ([], [], [], [])
            xmat = list(_inst_parts.last_mat) if xt else []
            if xt:
                # an instance whose triangles repeat the element's own faces is the same solid seen through its symbol: keep only genuinely additional instances
                sig = lambda tr: tuple(sorted(tuple(np.round(np.asarray(p) * 1e3).astype(np.int64)) for p in tr))
                have = {sig(tr) for tr in own + pm}; grp = {}
                for i, n_ in enumerate(xn): grp.setdefault(n_ // 100000, []).append(i)
                keep_i = []
                for g_, idx in grp.items():
                    if sum(sig(xt[i]) in have for i in idx) < 0.5 * len(idx): keep_i += idx
                xmat = [xmat[i] for i in keep_i]; xt = [xt[i] for i in keep_i]; xm = [xm[i] for i in keep_i]; xn = [xn[i] for i in keep_i]; xf = [xf[i] for i in keep_i]
            if xt: flags = flags + ['plus_instances']
        omat = [fmat.get(f_, -1) for f_ in ownf] if len(ownf) == len(own) else [-1] * len(own)
        if len(xmat) != len(xt): xmat = [-1] * len(xt)
        return {'mat': omat + [-1] * len(pm) + xmat, 'tris': own + pm + xt, 'fid': (ownf if len(ownf) == len(own) else list(range(len(own)))) + [10**7] * len(pm) + [2 * 10**7 + f_ for f_ in xf], 'nid': (ownn if len(ownn) == len(own) else [0] * len(own)) + [10**9] * len(pm) + [2 * 10**7 + n_ for n_ in xn], 'meta': ownm + [('plane', None, None)] * len(pm) + xm, 'source': 'own_geometry_in_bbox', 'flags': flags + (['unsupported_faces'] if un else []), 'bbox': bb}
        return {'mat': omat + [-1] * len(pm), 'tris': own + pm, 'fid': (ownf if len(ownf) == len(own) else list(range(len(own)))) + [10**7] * len(pm), 'nid': (ownn if len(ownn) == len(own) else [0] * len(own)) + [10**9] * len(pm), 'meta': ownm + [('plane', None, None)] * len(pm), 'source': 'own_geometry_in_bbox', 'flags': flags + (['unsupported_faces'] if un else []), 'bbox': bb}
    # instance of a symbol: symbol graphics transformed by the instance transform
    if inst and symbol_depth > 0:
        tris, metas, nids, fids = _inst_parts(doc, inst, bb, symbol_depth, detail, flags)
        if tris: return {'mat': list(_inst_parts.last_mat), 'tris': tris, 'fid': fids, 'nid': nids, 'meta': metas, 'source': 'symbol_instance', 'flags': flags, 'bbox': bb}
    # symbol itself / element without in-bbox faces: all faces of own geometry
    allt = []; allm = []; alln = []; allf = []; allmat = []
    for gi_, g in enumerate(geos):
        t = M.tessellate_geometry(g); allmat += _tri_mats(doc, t, g); allt += t['tris']; allm += t['meta']; alln += [gi_] * len(t['tris']); allf += [gi_ * 100000 + f_ for f_ in t['fidx']]; un += t['unsupported']
    return {'mat': allmat, 'tris': allt, 'fid': allf, 'nid': alln, 'meta': allm, 'source': 'all_geometry', 'flags': flags + (['unsupported_faces'] if un else []), 'bbox': bb}

def brep_topology_closed(doc, eid, detail=2, depth=2):
    """topological closure of an element's saved B-rep: True when it has Geometry nodes (own or through its symbol instances) and in every node each edge is used by exactly two faces.
    Independent of how the faces were sampled: a mesh that does not weld (planar end faces and cylinders sampling a shared arc differently) is still the closed solid Revit measures
    (Snowdon HVAC grilles: 404 open meshes, refined volume 0.08716 vs Revit 0.08718)"""
    rec = doc.rec(eid)
    if rec is None: return False
    geos, inst = _geos_f(rec['fields'], detail)
    if not geos and not inst: geos, inst = _geos(rec['fields'])
    nodes = 0
    for g in geos:
        ed = M._edge_map(g)
        if not ed or not g.get('m_pFaces'): return False
        for e in ed.values():
            rf = [r.get('ref') if isinstance(r, dict) else r for r in (e.get('m_pFace') or [])]
            if len([x for x in rf if x is not None]) != 2: return False
        nodes += 1
    if depth > 0:
        for z in inst:
            sid = _ob(z['m_instanceInfo']).get('m_symbolId')
            if sid is None: continue
            if doc.cls(int(sid)) == 'FamilyInstance': continue
            r = brep_topology_closed(doc, int(sid), detail, depth - 1)
            if not r: return False
            nodes += 1
    return nodes > 0

def end_cap_profile(tris, tol=1e-5):
    """Cross-section of a prismatic element from its mesh: the two largest planar groups whose normal is parallel to the element's main axis.
    returns {'axis':[..], 'caps':[{'origin','xvec','yvec','loops':[[[x,y],...]], 'area'}]} (loops in the cap plane coordinates) or None"""
    import collections
    if not tris: return None
    P = np.array([p for t in tris for p in t]); lo, hi = P.min(0), P.max(0); axis_i = int(np.argmax(hi - lo)); 
    groups = collections.defaultdict(list)
    for t in tris:
        a, b, c = [np.asarray(p, float) for p in t]; n = np.cross(b - a, c - a); L = np.linalg.norm(n)
        if L < 1e-12: continue
        n = n / L
        if abs(n[axis_i]) < 0.9999: continue
        d = float(np.dot(n, a)); groups[(round(d / tol), 1 if n[axis_i] > 0 else -1)].append((a, b, c, L / 2))
    caps = []
    for (dk, sgn), ts in groups.items():
        area = sum(t[3] for t in ts)
        em = collections.Counter(); pts = {}
        key = lambda p: tuple(np.round(p / tol).astype(np.int64))
        for a, b, c, _ in ts:
            ks = [key(p) for p in (a, b, c)]
            for p, k in zip((a, b, c), ks): pts[k] = p
            for u, v in ((0, 1), (1, 2), (2, 0)): em[frozenset((ks[u], ks[v]))] += 1
        bnd = [tuple(e) for e, n_ in em.items() if n_ == 1 and len(e) == 2]
        nxt = collections.defaultdict(list)
        for u, v in bnd: nxt[u].append(v); nxt[v].append(u)
        seen = set(); loops = []
        for u, v in bnd:
            if (u, v) in seen or (v, u) in seen: continue
            loop = [u]; cur = v; prev = u; seen.add((u, v))
            while cur != loop[0] and len(loop) < 100000:
                loop.append(cur); cand = [w for w in nxt[cur] if w != prev and (cur, w) not in seen and (w, cur) not in seen]
                if not cand: break
                nx = cand[0]; seen.add((cur, nx)); prev, cur = cur, nx
            if len(loop) >= 3: loops.append([pts[k] for k in loop])
        if not loops: continue
        # simplify collinear points
        o = ts[0][0]; n = np.cross(ts[0][1] - ts[0][0], ts[0][2] - ts[0][0]); n = n / np.linalg.norm(n)
        e1 = np.cross(n, [1, 0, 0]);
        if np.linalg.norm(e1) < 1e-6: e1 = np.cross(n, [0, 1, 0])
        e1 = e1 / np.linalg.norm(e1); e2 = np.cross(n, e1)
        outl = []
        for L_ in loops:
            xy = [[float(np.dot(p - o, e1)), float(np.dot(p - o, e2))] for p in L_]
            s = [xy[0]]
            for i in range(1, len(xy) - 1):
                a, b, c = np.array(s[-1]), np.array(xy[i]), np.array(xy[i + 1]); 
                if abs((b - a)[0] * (c - b)[1] - (b - a)[1] * (c - b)[0]) > 1e-9: s.append(xy[i])
            s.append(xy[-1]); outl.append(s)
        caps.append({'origin': o.tolist(), 'xvec': e1.tolist(), 'yvec': e2.tolist(), 'normal': (n * sgn).tolist(), 'loops': outl, 'area': float(area)})
    if not caps: return None
    caps.sort(key=lambda c: -c['area'])
    ax = [0.0, 0.0, 0.0]; ax[axis_i] = 1.0
    return {'axis': ax, 'caps': caps[:2]}

# ---------------- B-rep export in the viewer's surface-dict vocabulary (NEEDS-FROM-READER.md section 1/2) ----------------
def _curve_dict(c):
    import rvt_curves as C
    k = C.kind(c); c = _ob(c); fn = C.curve_fn(c)
    if fn is None: return None
    f, t0, t1 = fn
    if k == 'line': return {'type': 'line', 'p0': f(t0).tolist(), 'p1': f(t1).tolist()}
    if k == 'arc': return {'type': 'arc', 'p0': f(t0).tolist(), 'mid': f((t0 + t1) / 2).tolist(), 'p1': f(t1).tolist()}
    pts = [f(t0 + (t1 - t0) * i / 32).tolist() for i in range(33)]
    return {'type': 'bspline', 'degree': 1, 'poles': pts, 'knots': [0.0] * 1 + [i / 32 for i in range(33)] + [1.0], 'note': 'sampled ' + str(k)}

def surface_dict(surf):
    """decoded Revit surface -> plain dict (types: plane, cylinder, cone, revolution, ruled, hermite); coordinates as stored (document feet)"""
    s = _ob(surf)
    if not isinstance(s, dict): return None
    L = lambda k: [float(a) for a in s[k]]
    if 'm_pProfileCurve1' in s: return {'type': 'ruled', 'curve1': _curve_dict(s['m_pProfileCurve1']), 'curve2': _curve_dict(s['m_pProfileCurve2'])}
    if 'm_pProfileCurve' in s:
        import rvt_curves as C
        fn = C.curve_fn(s['m_pProfileCurve']); c = np.array(L('m_center')); X = np.array(L('m_xVec')); Y = np.array(L('m_yVec')); Z = np.array(L('m_zVec'))
        f, t0, t1 = fn
        def w(t): p = f(t); return (c + p[0] * X + p[1] * Y + p[2] * Z)          # profile in the surface's local frame -> world at u = 0
        k = C.kind(s['m_pProfileCurve'])
        if k == 'line': prof = {'type': 'line', 'p0': w(t0).tolist(), 'p1': w(t1).tolist()}
        elif k == 'arc': prof = {'type': 'arc', 'p0': w(t0).tolist(), 'mid': w((t0 + t1) / 2).tolist(), 'p1': w(t1).tolist()}
        else: prof = {'type': 'bspline', 'degree': 1, 'poles': [w(t0 + (t1 - t0) * i / 32).tolist() for i in range(33)], 'note': 'sampled ' + str(k)}
        return {'type': 'revolution', 'profile': prof, 'axis_origin': c.tolist(), 'axis_dir': Z.tolist(), 'xdir': X.tolist(), 'ydir': Y.tolist(), 'u': 'angle about axis from xdir', 'v': 'profile curve parameter'}
    if 'm_halfAngle' in s: return {'type': 'cone', 'origin': L('m_center'), 'xdir': L('m_xVec'), 'ydir': L('m_yVec'), 'zdir': L('m_zVec'), 'ref_radius': 0.0, 'semi_angle': float(s['m_halfAngle']), 'note': 'apex at origin; v = slant distance from the apex'}
    if 'm_radius' in s and 'm_center' in s: return {'type': 'cylinder', 'origin': L('m_center'), 'xdir': L('m_xVec'), 'ydir': L('m_yVec'), 'zdir': L('m_zVec'), 'radius': float(s['m_radius'])}
    if 'm_NodeArray' in s: return {'type': 'hermite', 'uparams': [float(a) for a in s['m_uParams']], 'vparams': [float(a) for a in s['m_vParams']],
                                    'nodes': [{'p': _ob(n)['m_iPoint'], 'tu': _ob(n)['m_iTangent'][0], 'tv': _ob(n)['m_iTangent'][1], 'twist': _ob(n)['m_iMixedDer']} for n in s['m_NodeArray']], 'order': 'u fastest'}
    if all(k in s for k in ('m_origin', 'm_xVec', 'm_yVec')): return {'type': 'plane', 'origin': L('m_origin'), 'xdir': L('m_xVec'), 'ydir': L('m_yVec')}
    return None

def element_brep(doc, eid, depth=2, detail=3):
    """faces of the element's own Geometry nodes at the given detail level (no shell selection): [{'handle','surface','loops_uv','orient','render_style'}];
    `instances` = the GInstance nodes, each with the recursively resolved faces of its symbol (`faces`, `instances`; coordinates in the symbol frame, world = m_3x3 @ local + m_or)"""
    rec = doc.rec(eid)
    if rec is None: return {'faces': []}
    geos, inst = _geos_f(rec['fields'], detail)
    if not geos and not inst: geos, inst = _geos(rec['fields'])
    out = []
    for gi, g in enumerate(geos):
        edges = M._edge_map(g)
        for fc in g['m_pFaces']:
            f = _ob(fc)
            if not isinstance(f, dict): continue
            sd = surface_dict(f.get('m_pSurf'))
            loops = M.face_loops_uv(fc.get('handle'), edges)
            rs = f.get('m_renderStyleId')
            out.append({'geometry': gi, 'handle': fc.get('handle'), 'surface': sd, 'loops_uv': [[list(map(float, p)) for p in l] for l in loops],
                        'orient': (_ob(f.get('m_pSurf')) or {}).get('m_orientFlag'), 'render_style': int(rs) if rs is not None else None})
    insts = []
    for z in inst:
        ii = _ob(z['m_instanceInfo']); sid = int(ii.get('m_symbolId'))
        d_ = {'symbol_id': sid, 'transform': ii.get('m_Trf')}
        if depth > 0:
            sub = element_brep(doc, sid, depth - 1, detail); d_['faces'] = sub['faces']; d_['instances'] = sub.get('instances', [])
        insts.append(d_)
    return {'faces': out, 'instances': insts}


def element_curves(doc, eid):
    """curve segments of the element's saved graphics (profile families: detail lines/arcs/splines), duplicates across detail levels removed.
    returns [{'type':'line','p0','p1'} | {'type':'arc','center','radius','xvec','yvec','t0','t1','p0','p1'}]"""
    rec = doc.rec(eid)
    if rec is None: return []
    out = []; seen = set()
    def add(c):
        k = (c['type'],) + tuple(np.round(np.array(c['p0']), 6)) + tuple(np.round(np.array(c['p1']), 6))
        k2 = (c['type'],) + tuple(np.round(np.array(c['p1']), 6)) + tuple(np.round(np.array(c['p0']), 6))
        if k in seen or k2 in seen: return
        seen.add(k); out.append(c)
    def walk(n):
        n = _ob(n)
        if not isinstance(n, dict): return
        if 'm_endParams' in n and 'm_dirVec' in n and 'm_origin' in n:
            o = np.array(n['m_origin'], float); d = np.array(n['m_dirVec'], float); t0, t1 = n['m_endParams']
            add({'type': 'line', 'p0': (o + d * t0).tolist(), 'p1': (o + d * t1).tolist()})
        elif 'm_endParams' in n and 'm_radius' in n and 'm_center' in n:
            c = np.array(n['m_center'], float); x = np.array(n['m_xVec'], float); y = np.array(n['m_yVec'], float); r = float(n['m_radius']); t0, t1 = n['m_endParams']
            P = lambda t: (c + r * np.cos(t) * x + r * np.sin(t) * y).tolist()
            add({'type': 'arc', 'center': c.tolist(), 'radius': r, 'xvec': x.tolist(), 'yvec': y.tolist(), 't0': t0, 't1': t1, 'p0': P(t0), 'p1': P(t1)})
        for k in (n.get('m_subNodes') or []): walk(k)
    walk(rec['fields'])
    out = [c for c in out if np.linalg.norm(np.array(c['p1']) - np.array(c['p0'])) > 1e-9 or c['type'] == 'arc']           # zero-length placeholder lines
    # a line whose both ends lie strictly inside other curves' spans is a divider/reference line, not part of the profile outline
    def interior(p, c):
        if c['type'] != 'line': return False
        a = np.array(c['p0']); b = np.array(c['p1']); d = b - a; L2 = float(d @ d)
        if L2 < 1e-18: return False
        t = float((np.array(p) - a) @ d / L2); return 1e-6 < t < 1 - 1e-6 and np.linalg.norm(a + t * d - np.array(p)) < 1e-6
    keep = []
    for i, c in enumerate(out):
        if c['type'] == 'line' and all(any(interior(c[k], o) for j, o in enumerate(out) if j != i) for k in ('p0', 'p1')): continue
        keep.append(c)
    return keep

def element_has_solids(doc, eid, depth=3):
    """False when neither the element's saved graphics nor any symbol it instantiates carries a face at ANY detail level or view condition:
    such elements have no 3D solid in Revit either (void/opening families, reference columns, quantity markers: Revit Volume 0). None = no saved graphics."""
    rec = doc.rec(eid)
    if rec is None: return None
    geos, inst = _geos(rec['fields'])
    if any(g.get('m_pFaces') for g in geos): return True
    if depth <= 0: return False
    for z in inst:
        sid = _ob(z.get('m_instanceInfo') or {}).get('m_symbolId')
        if sid is not None and element_has_solids(doc, int(sid), depth - 1): return True
    return False
