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
    vol, closed, area, _ = M.volume_by_node(m['tris'], m.get('meta'), m['nid'], fid=m.get('fid'))
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
    if cat == CAT_MULLION:
        tr = _trf(f)
        if tr is not None:
            R, o = tr; L = (np.array(m['tris'], float).reshape(-1, 3) - o) @ R; ext = L.max(0) - L.min(0)
            out['Length'] = float(ext.max())
    return out
