"""Geometry-derived parameters (bucket b of OBJECTIVES.md #2), computed from the decoded saved-graphics solids (rvt_elemmesh.element_mesh).
Own analysis, validated against Revit's parameter dumps (gt4/*.tsv):
* Volume       = closed-solid volume of the element at the detail level Revit computes it with: MEDIUM for files of Revit 2020-2025, FINE for Revit 2026
  (same Snowdon model dumped by Revit 2024/2025/2026: 608201 13.6098/13.6098/13.7427 = our Medium/Medium/Fine; 2020 Commercial columns Medium).
  Elements without a solid (annotation, title blocks, generic annotations) report 0.
* Area (FamilyInstance, not curtain panels) = HALF of the total surface area of the element's solids (Revit's HOST_AREA_COMPUTED for families;
  doors 68.75 -> 34.375, windows 41.934 -> 20.967, mullions 3.533 -> 1.7665 in 2020 Commercial).
* Curtain panels: Area = area of the largest planar face (the panel face), Width/Height = its extents in the panel's own frame
  (local x / local y of the instance transform) when the face is a rectangle, else 0 (Revit reports 0 for non-rectangular panels).
* Mullions: Length = extent of the solid along the instance's local axis that is longest.
usage: geom_params(doc, eid, fields, category_id) -> {name: value}; doc = rvt_elemmesh.Doc(file)."""
import collections
import numpy as np
import rvt_elemmesh as EM, rvt_mesh as M

CAT_PANEL, CAT_MULLION = -2000170, -2000171

def _trf(f):
    import rvt_famparams as F
    t = F.S_(f, 'm_pInstanceInfo', 'm_Trf')
    if not t or 'm_3x3' not in t: return None
    return np.array(t['m_3x3'], float), np.array(t['m_or'], float)

def _mesh(doc, eid, detail):
    m = EM.element_mesh(doc, eid, detail=detail)
    if not m['tris'] or not m.get('nid') or len(m['nid']) != len(m['tris']): return None
    return m

_FORM_NODE_CATS = {-2001060, -2008087, -2001120, -2001040}      # electrical fixtures, lighting devices, lighting fixtures, electrical equipment: the categories the node rule was validated on (rme_basic 2020: 926/926); structural families regressed (2026 Snowdon Structural -482 volumes)

def _drop_form_nodes(doc, eid, m, detail):
    """Revit's Volume/Area ignore a symbol geometry node whose GInfo.m_controlCommand has bit 26 (0x4000000) without bit 15 (0x8000) when another node remains
    (rme_basic 2020: electrical fixtures cc [0, 0x4000000] -> only the first solid, Passive Infrared devices [0x8000, 0x4008000] -> both; 3/3 and 2/2 samples). Single-instance symbols only."""
    try:
        gg, ii = EM._geos_f(doc.rec(eid)['fields'], detail)
        if gg or len(ii) != 1: return m
        sid = int(EM._ob(ii[0]['m_instanceInfo']).get('m_symbolId')); sg, si = EM._geos_f(doc.rec(sid)['fields'], detail)
        ccs = [int((g.get('m_GInfo') or {}).get('m_controlCommand') or 0) for g in sg]
        fl = [int((g.get('m_GInfo') or {}).get('m_flags') or 0) for g in sg]
        drop = {100000 + i for i, c in enumerate(ccs) if (c & 0x4000000) and not (c & 0x8000) and not (fl[i] & 0xE0)}      # nodes with flag bits 0xE0 (pipe fittings at Medium: cc [0x4008000, 0x4000000, 0x4000000], Revit counts all three) are not touched
        if not drop or len(drop) >= len(ccs): return m
        keep = [i for i, n in enumerate(m['nid']) if n not in drop]
        return {k: ([v[i] for i in keep] if isinstance(v, list) and len(v) == len(m['nid']) else v) for k, v in m.items()}
    except Exception: return m

def apply_form_node_rule(doc, eid, m, cat, detail):
    """public helper for renderers: drop the symbol solids Revit does not count (see _drop_form_nodes) from an element_mesh result `m` when the element's category (signed id) is one the rule was validated on (electrical / lighting categories); returns m unchanged otherwise"""
    if m is not None and m.get('source') == 'symbol_instance' and cat in _FORM_NODE_CATS: return _drop_form_nodes(doc, eid, m, detail)
    return m

def volume_detail(doc):
    """detail level of Revit's computed Volume/Area for this file (2 = Medium up to Revit 2025, 3 = Fine from 2026)"""
    if getattr(doc, '_vdetail', None) is None:
        try:
            import olefile, export_schemas as ES
            doc._vdetail = 3 if int(ES.build_info(olefile.OleFileIO(doc.f)).get('revit') or 0) >= 2026 else 2
        except Exception: doc._vdetail = 2
    return doc._vdetail

def wall_volume(doc, eid):
    """Revit's wall Volume parameter: the wall's own body; integrated sweeps / banding drawn as instances with the wall (nid >= 2e7) are part of its
    geometry but not of the parameter (2026 Facades: 593337 own 102.51 vs Revit 102.498, with sweeps 112.28)"""
    m = _mesh(doc, eid, 2)
    if m is None: return None
    ix = [i for i, n in enumerate(m['nid']) if n < 2 * 10**7]
    if not ix: return None
    v, closed, _, _ = M.volume_by_node([m['tris'][i] for i in ix], [m['meta'][i] for i in ix] if m.get('meta') else None, [m['nid'][i] for i in ix], fid=[m['fid'][i] for i in ix] if m.get('fid') else None)
    return float(v) if v > 0 else None

HOSTS = {'Floor': ('Volume', 'Area'), 'Ceiling': ('Volume', 'Area'), 'FootPrintRoof': ('Volume',), 'ExtrusionRoof': ('Volume',), 'RoofBase': ('Volume',)}

def host_params(doc, eid, cls):
    """floors / ceilings: Volume = solid, Area = largest face (2020 Commercial exact); roofs: Volume only (Revit's roof Area sums the slopes);
    rooms are left out (Revit's room Area/Perimeter follow its computation-height rules, not the room solid's faces)"""
    m = _mesh(doc, eid, 2)
    if m is None: return {}
    out = {}
    v, closed, _, _ = M.volume_by_node(m['tris'], m.get('meta'), m['nid'], fid=m.get('fid'))
    if closed and v > 0: out['Volume'] = float(v)
    if 'Area' in HOSTS[cls]:
        T = np.array(m['tris'], float); a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); fa = collections.Counter()
        for i, fi in enumerate(m['fid']): fa[fi] += a[i]
        if fa: out['Area'] = float(max(fa.values()))
    return out

def geom_params(doc, eid, f, cat, cls='FamilyInstance'):
    out = {}
    if cls in HOSTS: return host_params(doc, eid, cls)
    if cls == 'SWall':
        v = wall_volume(doc, eid); out = {'Volume': v} if v is not None else {}
        m = _mesh(doc, eid, 2)
        if m is not None:                                              # Revit's wall Area = the largest face of the wall's own body (one side, openings cut): 90/91 exact in 2020 Commercial
            T = np.array(m['tris'], float); a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); fa = collections.Counter()
            for i, (fi, ni) in enumerate(zip(m['fid'], m['nid'])):
                if ni < 2 * 10**7: fa[fi] += a[i]
            if fa: out['Area'] = float(max(fa.values()))
        return out
    m = _mesh(doc, eid, volume_detail(doc))
    if m is None: return {'Volume': 0.0, 'Area': 0.0} if cls == 'FamilyInstance' and cat not in (CAT_PANEL,) else out
    if cls == 'FamilyInstance' and m.get('source') == 'symbol_instance' and cat in _FORM_NODE_CATS: m = _drop_form_nodes(doc, eid, m, volume_detail(doc))
    vol, closed, area, _ = M.volume_by_node(m['tris'], m.get('meta'), m['nid'], fid=m.get('fid'))
    if cat == -2008049 and cls == 'FamilyInstance' and volume_detail(doc) == 2:       # pipe fittings: Revit's Volume is the Fine solid even in files whose other families follow Medium (rme_basic 2020, 40 samples: every fitting whose Medium and Fine bodies differ matches Fine); Area stays Medium (exact)
        m3 = _mesh(doc, eid, 3)
        if m3 is not None:
            v3, c3, _a3, _ = M.volume_by_node(m3['tris'], m3.get('meta'), m3['nid'], fid=m3.get('fid'))
            if c3 and v3 > 0: vol, closed = v3, c3
    if closed and vol > 0: out['Volume'] = float(vol)
    if cls != 'FamilyInstance': return out
    if cat == CAT_PANEL:
        T = np.array(m['tris'], float); a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        fa = collections.Counter()
        for i, fi in enumerate(m.get('fid') or range(len(T))): fa[fi] += a[i]
        if not fa: return out
        fbig, abig = fa.most_common(1)[0]; out['Area'] = float(abig)
        tr = _trf(f)
        if tr is not None:
            R, o = tr; idx = [i for i, fi in enumerate(m['fid']) if fi == fbig]
            L = (T[idx].reshape(-1, 3) - o) @ R; ext = L.max(0) - L.min(0)
            w, h = float(ext[0]), float(ext[1])
            if abs(w * h - abig) <= 1e-6 * max(1.0, abig): out['Width'], out['Height'] = w, h
            else: out['Width'] = out['Height'] = 0.0
        return out
    out['Area'] = float(area) / 2
    if cat == -2008010: out.pop('Area', None)          # duct fittings: Revit's Area is not half the surface (0 of 311 right in rme_basic 2020; pipe fittings 119 of 119); better absent than wrong
    if cat == CAT_MULLION:
        tr = _trf(f)
        if tr is not None:
            R, o = tr; L = (np.array(m['tris'], float).reshape(-1, 3) - o) @ R; ext = L.max(0) - L.min(0)
            out['Length'] = float(ext.max())
    return out


def room_params(doc, eid):
    """Room Area / Perimeter from the room solid: area and boundary length of its bottom (lowest horizontal) face loop (rme/Commercial 2020: Area 8/8, Perimeter 7/8 within 0.2%)"""
    m = EM.element_mesh(doc, eid, detail=3)
    if not m['tris']: return {}
    T = np.array(m['tris'], float); n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-12
    if not ok.any(): return {}
    zmin = T[:, :, 2].min()
    bot = ok & (np.abs(n[:, 2] / np.where(ok, ln, 1)) > 0.999) & (np.abs(T[:, :, 2].max(1) - zmin) < 1e-6)
    if not bot.any(): return {}
    ed = collections.Counter()
    for tri in T[bot]:
        for i in range(3):
            p, q = tuple(np.round(tri[i], 6)), tuple(np.round(tri[(i + 1) % 3], 6)); ed[(min(p, q), max(p, q))] += 1
    bnd = [(p, q) for (p, q), k in ed.items() if k == 1]
    adj = collections.defaultdict(list)
    for i, (p, q) in enumerate(bnd): adj[p].append(i); adj[q].append(i)
    seen = set(); loops = []
    for i0 in range(len(bnd)):
        if i0 in seen: continue
        stack = [i0]; seen.add(i0); L = 0.0
        while stack:                                                  # connected boundary component (outer loop or an island such as a column)
            i = stack.pop(); p, q = bnd[i]; L += float(np.linalg.norm(np.array(p) - np.array(q)))
            for v in (p, q):
                for j in adj[v]:
                    if j not in seen: seen.add(j); stack.append(j)
        loops.append(L)
    per = max(loops) if loops else 0.0                                # Revit's Perimeter is the outer boundary only (islands / columns excluded: Arch_Link 2023, 223193: 55.54 vs 58.68 with a 3.14 column)
    return {'Area': float(ln[bot].sum() / 2), 'Perimeter': per}
