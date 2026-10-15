"""Rebuild B-rep faces from a decoded channel-103 Geometry node (planar faces first). Units feet."""
import math

def _v(x): return [float(a) for a in x]
def _ob(o): return o.get('obj', o) if isinstance(o, dict) else o

def plane_of(surf):
    s = _ob(surf)
    if not isinstance(s, dict) or not all(k in s for k in ('m_origin', 'm_xVec', 'm_yVec')) or 'm_radius' in s: return None
    o = _v(s['m_origin']); x = _v(s['m_xVec']); y = _v(s['m_yVec'])
    return o, x, y

def uv3d(pl, u, v):
    o, x, y = pl
    return [o[i] + u * x[i] + v * y[i] for i in range(3)]

def planar_faces(geo):
    """geo: dict with m_pFaces/m_pEdges. returns list of {'handle', 'plane', 'loops': [[3D points]], 'orient'}; faces with non-planar surfaces are returned with plane=None"""
    faces = geo.get('m_pFaces') or []; edges = geo.get('m_pEdges') or []
    eh = {}                                     # handle -> edge obj
    for e in edges:
        if isinstance(e, dict) and e.get('handle') not in (None, 0xffffffff) and isinstance(_ob(e), dict): eh[e['handle']] = _ob(e)
    fh = {}
    out = []
    for fc in faces:
        h = fc.get('handle'); f = _ob(fc)
        if not isinstance(f, dict): continue
        surf = f.get('m_pSurf'); pl = plane_of(surf) if surf else None
        rec = {'handle': h, 'plane': pl, 'loops': [], 'orient': (_ob(surf) or {}).get('m_orientFlag') if surf else None, 'surface_kind': 'plane' if pl else 'other'}
        if pl is None: out.append(rec); continue
        mine = {eid: e for eid, e in eh.items() if any(isinstance(r, dict) and r.get('ref') == h for r in (e.get('m_pFace') or []))}
        segs = []
        for eid, e in mine.items():
            side = [r.get('ref') if isinstance(r, dict) else None for r in e['m_pFace']].index(h)
            fl = e['m_firstAndLastEdgePnts']
            if len(fl) < 2: continue
            a = _ob(fl[0])['uv'][side]; b = _ob(fl[1])['uv'][side]
            inter = e.get('m_interiorEdgePnts') or []
            segs.append((a, b, inter, eid))
        rec['loops'] = _chain(segs, pl)
        out.append(rec)
    return out


def _close2(a, b, tol=1e-5): return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol

def _chain(segs, pl):
    used = [False] * len(segs); loops = []
    for i in range(len(segs)):
        if used[i]: continue
        used[i] = True; a, b, inter, _ = segs[i]; pts = [a]; cur = b; start = a; guard = 0
        while not _close2(cur, start) and guard < len(segs) + 2:
            guard += 1
            for j in range(len(segs)):
                if used[j]: continue
                a2, b2, i2, _ = segs[j]
                if _close2(a2, cur): used[j] = True; pts.append(a2); cur = b2; break
                if _close2(b2, cur): used[j] = True; pts.append(b2); cur = a2; break
            else: break
        if _close2(cur, start) and len(pts) >= 3: loops.append([uv3d(pl, p[0], p[1]) for p in pts])
    return loops
