"""Tessellate decoded channel-103 Geometry (B-rep) nodes: planar + cylindrical faces (others reported). Units feet."""
import math, collections, os
import numpy as np
import mapbox_earcut as earcut

def _v(x): return [float(a) for a in x]
def _ob(o): return o.get('obj', o) if isinstance(o, dict) else o

def surface_eval(s):
    """returns (kind, f(u,v)->xyz) or (None,None)"""
    s = _ob(s)
    if not isinstance(s, dict): return None, None
    if 'm_radius' in s and 'm_center' in s and 'm_zVec' in s:
        c = np.array(_v(s['m_center'])); x = np.array(_v(s['m_xVec'])); y = np.array(_v(s['m_yVec'])); z = np.array(_v(s['m_zVec'])); R = float(s['m_radius'])
        return 'cylinder', (lambda u, v: c + R * math.cos(u) * x + R * math.sin(u) * y + v * z)
    if 'm_NodeArray' in s and 'm_uParams' in s:
        # bicubic Hermite patch grid: nodes u-fastest, m_iTangent = (d/du, d/dv), m_iMixedDer = twist (corner values verified; interior pending validation)
        U = np.array(s['m_uParams'], float); V = np.array(s['m_vParams'], float); nu, nv = len(U), len(V); nodes = [_ob(n) for n in s['m_NodeArray']]
        if len(nodes) != nu * nv or nu < 2 or nv < 2: return None, None
        Pp = np.zeros((nu, nv, 3)); Tu = np.zeros((nu, nv, 3)); Tv = np.zeros((nu, nv, 3)); W = np.zeros((nu, nv, 3))
        for k, n in enumerate(nodes):
            i, j = k % nu, k // nu; Pp[i, j] = n['m_iPoint']; t = n['m_iTangent']; Tu[i, j] = t[0]; Tv[i, j] = t[1]; W[i, j] = n['m_iMixedDer']
        def hb(t): return (2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2)
        def ev(u, v):
            i = int(np.clip(np.searchsorted(U, u, side='right') - 1, 0, nu - 2)); j = int(np.clip(np.searchsorted(V, v, side='right') - 1, 0, nv - 2))
            hu = U[i+1] - U[i]; hv = V[j+1] - V[j]; bu = hb((u - U[i]) / hu); bv = hb((v - V[j]) / hv); out = np.zeros(3)
            for a, ia in ((0, i), (1, i + 1)):
                for b, jb in ((0, j), (1, j + 1)):
                    fu = (bu[0], bu[1]) if a == 0 else (bu[2], bu[3]); fv = (bv[0], bv[1]) if b == 0 else (bv[2], bv[3])
                    out += fu[0]*fv[0]*Pp[ia, jb] + fu[1]*hu*fv[0]*Tu[ia, jb] + fu[0]*fv[1]*hv*Tv[ia, jb] + fu[1]*hu*fv[1]*hv*W[ia, jb]
            return out
        return 'hermite', ev
    if 'm_halfAngle' in s and 'm_center' in s:
        c = np.array(_v(s['m_center'])); x = np.array(_v(s['m_xVec'])); y = np.array(_v(s['m_yVec'])); z = np.array(_v(s['m_zVec'])); al = float(s['m_halfAngle'])
        sa, ca = math.sin(al), math.cos(al)
        return 'cone', (lambda u, v: c + v * sa * (math.cos(u) * x + math.sin(u) * y) + v * ca * z)       # apex at m_center, v = slant distance
    if 'm_pProfileCurve' in s and 'm_center' in s:
        import rvt_curves as C
        cf = C.curve_fn(s['m_pProfileCurve'])
        if cf:
            fn = cf[0]; c = np.array(_v(s['m_center'])); x = np.array(_v(s['m_xVec'])); y = np.array(_v(s['m_yVec'])); z = np.array(_v(s['m_zVec']))
            def ev(u, v):
                L = fn(v); cu, su = math.cos(u), math.sin(u)
                return c + (L[0] * cu - L[1] * su) * x + (L[0] * su + L[1] * cu) * y + L[2] * z
            return 'revolution', ev
        return None, None
    if 'm_pProfileCurve1' in s and 'm_pProfileCurve2' in s:
        import rvt_curves as C
        a = C.curve_fn(s['m_pProfileCurve1']) if s.get('m_pProfileCurve1') else None; b = C.curve_fn(s['m_pProfileCurve2']) if s.get('m_pProfileCurve2') else None
        if a and b:
            fa, a0, a1 = a; fb, b0, b1 = b
            return 'ruled', (lambda u, v: (1 - v) * fa(a0 + (a1 - a0) * u) + v * fb(b0 + (b1 - b0) * u))
        if (a or s.get('m_pProfileCurve1') is None) and (b or s.get('m_pProfileCurve2') is None) and 'm_Point1' in s and 'm_Point2' in s and (a or b):
            # ruled surface between a curve and a point (fan from an apex): the missing profile curve 1 is the constant Point1, a missing curve 2 the constant Point2 (verified against Revit's face grids)
            P1 = np.array(_v(s['m_Point1'])); P2 = np.array(_v(s['m_Point2']))
            fa, a0, a1 = a if a else ((lambda t: P1), 0.0, 1.0); fb, b0, b1 = b if b else ((lambda t: P2), 0.0, 1.0)
            return 'ruled', (lambda u, v: (1 - v) * fa(a0 + (a1 - a0) * u) + v * fb(b0 + (b1 - b0) * u))
        return None, None
    if all(k in s for k in ('m_origin', 'm_xVec', 'm_yVec')):
        o = np.array(_v(s['m_origin'])); x = np.array(_v(s['m_xVec'])); y = np.array(_v(s['m_yVec']))
        return 'plane', (lambda u, v: o + u * x + v * y)
    return None, None


def _edge_map(geo):
    """handle -> Edge object for every edge defined anywhere inside the Geometry node (first appearance may be a loop/edge pointer, not m_pEdges)"""
    if 'm_edgeMap' in geo: return geo['m_edgeMap']
    out = {}; st = [geo]
    while st:
        z = st.pop()
        if isinstance(z, dict):
            if 'handle' in z and 'obj' in z and isinstance(z['obj'], dict) and 'm_firstAndLastEdgePnts' in z['obj'] and z['handle'] not in (None, 0xffffffff):
                out[z['handle']] = z['obj']
            for b in z.values():
                if b is not None: st.append(b)
        elif isinstance(z, list): st.extend(z)
    return out

def _cycles_from_polylines(polys, tol=1e-6):
    """polys: list of uv polylines (each >= 2 points). Builds the planar graph (splitting segments at T-vertices, removing duplicates and dangling
    edges) and returns the closed boundary cycles as lists of uv points."""
    import math
    vid = {}; V = []
    def vkey(p): return (round(p[0] / tol), round(p[1] / tol))
    def vertex(p):
        k = vkey(p)
        if k not in vid: vid[k] = len(V); V.append((float(p[0]), float(p[1])))
        return vid[k]
    segs = set()
    for pl in polys:
        for a, b in zip(pl, pl[1:]):
            ia, ib = vertex(a), vertex(b)
            if ia != ib: segs.add((min(ia, ib), max(ia, ib)))
    # split segments at vertices lying on them
    changed = True; guard = 0
    while changed and guard < 20:
        changed = False; guard += 1; new = set()
        for a, b in sorted(segs):
            pa, pb = V[a], V[b]; dx, dy = pb[0] - pa[0], pb[1] - pa[1]; L2 = dx * dx + dy * dy
            cut = None
            for c in range(len(V)):
                if c == a or c == b: continue
                pc = V[c]; t = ((pc[0] - pa[0]) * dx + (pc[1] - pa[1]) * dy) / L2 if L2 else -1
                if 1e-9 < t < 1 - 1e-9:
                    ex, ey = pa[0] + t * dx - pc[0], pa[1] + t * dy - pc[1]
                    if ex * ex + ey * ey < (10 * tol) ** 2: cut = c; break
            if cut is None: new.add((a, b))
            else: new.add((min(a, cut), max(a, cut))); new.add((min(cut, b), max(cut, b))); changed = True
        segs = new
    adj = collections.defaultdict(set)
    for a, b in sorted(segs): adj[a].add(b); adj[b].add(a)
    # prune dangling vertices
    stack = [v for v in adj if len(adj[v]) < 2]
    while stack:
        v = stack.pop()
        for w in list(adj.get(v, ())):
            adj[w].discard(v)
            if len(adj[w]) < 2: stack.append(w)
        adj.pop(v, None)
    used = set(); cycles = []
    def angle(u, v, w):      # clockwise turn from direction v->u to v->w in [0, 2pi)
        a1 = math.atan2(V[u][1] - V[v][1], V[u][0] - V[v][0]); a2 = math.atan2(V[w][1] - V[v][1], V[w][0] - V[v][0])
        d = (a1 - a2) % (2 * math.pi)
        return d if d > 1e-12 else 2 * math.pi
    for a in sorted(adj):
        for b in sorted(adj[a]):
            if (a, b) in used: continue
            cyc = [a]; u, v = a, b; used.add((a, b)); guard = 0
            while v != a and guard < 100000:
                guard += 1; cyc.append(v)
                cands = [w for w in sorted(adj[v]) if w != u] or [u]
                w = min(cands, key=lambda w: angle(u, v, w))
                if (v, w) in used: break
                used.add((v, w)); u, v = v, w
            if v == a and len(cyc) >= 3: cycles.append([V[i] for i in cyc])
    return cycles

def _c2(a, b, tol=1e-5): return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol

def _snap_to_plane(oev, psd, u, v):
    """move (u, v) along v on the curved surface oev so that the point lies on the plane psd (intersection curve of cylinder/cone/revolution with a plane); falls back to (u, v)"""
    try:
        o = np.array(_v(psd['m_origin'])); xv = np.array(_v(psd['m_xVec'])); yv = np.array(_v(psd['m_yVec'])); n = np.cross(xv, yv); n = n / (np.linalg.norm(n) or 1.0)
        f = lambda vv: float(n @ (np.asarray(oev(u, vv)) - o))
        v0 = v; f0 = f(v0)
        if abs(f0) < 1e-12: return u, v0
        h = 1e-4; v1 = v0 + h; f1 = f(v1)
        for _ in range(8):
            if abs(f1 - f0) < 1e-18: return u, v
            v2 = v1 - f1 * (v1 - v0) / (f1 - f0); v0, f0 = v1, f1; v1 = v2; f1 = f(v1)
            if abs(f1) < 1e-11: break
        if abs(f1) < 1e-9 and abs(v1 - v) < 2.0: return u, v1
    except Exception: pass
    return u, v

def face_loops_uv(h, edges, surfs=None, allow_gaps=False, out_mine=None):
    """closed loops of face h in its uv space. Edge pointers (m_next[side]) give the loop order; geometric cycle extraction is the fallback.
    surfs = {handle: (kind, ev, surface_dict)}: when this face is planar and the neighbour across an edge is curved, the stored edge samples are densified through the
    neighbour's surface so that caps of cylinders/cones are true circles instead of 22-gons."""
    mine = {}
    me = surfs.get(h) if surfs else None
    plane_inv = None
    if me and me[0] == 'plane':
        sd = _ob(me[2]); o = np.array(_v(sd['m_origin'])); xv = np.array(_v(sd['m_xVec'])); yv = np.array(_v(sd['m_yVec']))
        plane_inv = lambda P: ((P - o) @ xv, (P - o) @ yv)
    for eid, e in edges.items():
        refs = [r.get('ref') if isinstance(r, dict) else None for r in (e.get('m_pFace') or [])]
        if h in refs:
            side = refs.index(h); fl = e['m_firstAndLastEdgePnts']
            if len(fl) < 2: continue
            a = _ob(fl[0])['uv'][side]; b = _ob(fl[1])['uv'][side]
            inter = [_ob(p)['uv'][side] for p in (e.get('m_interiorEdgePnts') or []) if isinstance(_ob(p), dict)]
            if plane_inv and len(refs) == 2 and refs[1 - side] in surfs and surfs[refs[1 - side]][0] in ('cylinder', 'cone', 'revolution', 'ruled'):
                ok_, oev = surfs[refs[1 - side]][0], surfs[refs[1 - side]][1]
                other = [_ob(fl[0])['uv'][1 - side]] + [_ob(p)['uv'][1 - side] for p in (e.get('m_interiorEdgePnts') or []) if isinstance(_ob(p), dict)] + [_ob(fl[1])['uv'][1 - side]]
                dense = []
                for (u0, v0), (u1, v1) in zip(other, other[1:]):
                    kdiv = int(min(64, max(1, math.ceil(max(abs(u1 - u0) if ok_ != "ruled" else 0, 0) / 0.1))))
                    for i in range(1, kdiv):
                        t = i / kdiv; uu, vv = _snap_to_plane(oev, _ob(me[2]), u0 + (u1 - u0) * t, v0 + (v1 - v0) * t); dense.append(plane_inv(np.asarray(oev(uu, vv))))
                    dense.append(None)           # placeholder marking original sample positions
                if any(d is not None for d in dense):
                    pts_new = []; k0 = 0
                    # rebuild: original interior points (projected/kept) interleaved with the dense extras
                    seq = []; orig = [a] + inter + [b]; oi = 1
                    for d in dense:
                        if d is None: seq.append(orig[oi]); oi += 1
                        else: seq.append((float(d[0]), float(d[1])))
                    inter = seq[:-1]            # last original sample is b
            if me and me[0] in ('cylinder', 'cone', 'revolution') and len(refs) == 2 and refs[1 - side] in surfs and surfs[refs[1 - side]][0] == 'plane':
                orig = [a] + inter + [b]; seq = []
                for (u0, v0), (u1, v1) in zip(orig, orig[1:]):
                    kdiv = int(min(64, max(1, math.ceil(abs(u1 - u0) / 0.1))))
                    seq.append((u0, v0))
                    for i in range(1, kdiv): t = i / kdiv; seq.append(_snap_to_plane(me[1], _ob(surfs[refs[1 - side]][2]), u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
                inter = seq[1:]
            nx = e.get('m_next') or []; pv = e.get('m_prev') or []
            nref = nx[side].get('ref') if side < len(nx) and isinstance(nx[side], dict) else None
            pref = pv[side].get('ref') if side < len(pv) and isinstance(pv[side], dict) else None
            mine[eid] = (a, b, inter, nref, pref)
    if out_mine is not None: out_mine.update(mine)
    seen = set(); loops = []
    def seq_from(start):
        # walk back to the beginning of the chain (or around a cycle), then forward
        cur = start; guard = 0
        while mine[cur][4] in mine and mine[cur][4] != start and guard < 100000 and mine[cur][4] not in seen:
            cur = mine[cur][4]; guard += 1
        first = cur; seq = [cur]; guard = 0
        while mine[cur][3] in mine and mine[cur][3] != first and mine[cur][3] not in seq and guard < 100000:
            cur = mine[cur][3]; seq.append(cur); guard += 1
        return seq
    for e0 in sorted(mine):
        if e0 in seen: continue
        seq = seq_from(e0); seen.update(seq)
        # orient by continuity
        segs = [mine[k] for k in seq]
        if len(segs) == 1:
            a, b, inter, _, _ = segs[0]; pts = [a] + list(inter)
            if _c2(a, b) and len(pts) >= 3: loops.append(pts)
            continue
        a0, b0, i0 = segs[0][0], segs[0][1], segs[0][2]
        a1, b1 = segs[1][0], segs[1][1]
        if _c2(a0, a1) or _c2(a0, b1): a0, b0, i0 = b0, a0, list(reversed(i0))        # first edge runs b->a
        pts = [a0] + list(i0); cur = b0; gaps = []
        for a, b, inter, _, _ in segs[1:]:
            if _c2(a, cur): pts += [a] + list(inter); cur = b
            elif _c2(b, cur): pts += [b] + list(reversed(inter)); cur = a
            else: gaps.append((cur, a)); pts += [a] + list(inter); cur = b         # discontinuity: keep going, the loop test below decides
        if not _c2(cur, a0): gaps.append((cur, a0))
        # allow_gaps: a gap along an iso-line (pole / apex: the degenerate edge is missing from the edge list) closes the loop implicitly
        axis_gap = all(abs(p[0] - q[0]) < 1e-9 or abs(p[1] - q[1]) < 1e-9 for p, q in gaps)
        if len(pts) >= 3 and (_c2(cur, a0) or (allow_gaps and gaps and len(gaps) <= 2 and axis_gap)): loops.append(pts)
        else: loops.append(None)                               # unclosed chain -> use the geometric fallback below
    if loops and all(l is not None and abs(_area2(l)) > 1e-12 for l in loops): return [x for l in loops for x in _cancel_slits(l)]
    polys = [[v[0]] + list(v[2]) + [v[1]] for v in mine.values()]
    cyc = _cycles_from_polylines(polys)
    if cyc:
        seen_k = set(); out = []
        for c in cyc:
            k = frozenset((round(p[0] / 1e-5), round(p[1] / 1e-5)) for p in c)
            if k in seen_k: continue
            seen_k.add(k); out.append(c)
        return out
    ch = _face_loops_chain(mine)
    if ch or os.environ.get('RVT_NOSNAP'): return ch
    # last resort: edge endpoints that miss each other by < 2e-3 (uv) are snapped together (2024 Facades column symbol 1280281: 0.0007 gaps)
    ends = []
    def snap(p):
        for q in ends:
            if abs(p[0] - q[0]) < 2e-3 and abs(p[1] - q[1]) < 2e-3: return q
        ends.append((float(p[0]), float(p[1]))); return ends[-1]
    polys2 = []
    for v in mine.values():
        pl = [v[0]] + list(v[2]) + [v[1]]; pl[0] = snap(pl[0]); pl[-1] = snap(pl[-1]); polys2.append(pl)
    return _cycles_from_polylines(polys2) or []

def _face_loops_chain(mine):
    segs = [(v[0], v[1], v[2]) for v in mine.values()]
    used = [False] * len(segs); loops = []
    for i in range(len(segs)):
        if used[i]: continue
        used[i] = True; a, b, inter = segs[i]; pts = [a] + list(inter); cur = b; start = a; guard = 0
        while not _c2(cur, start) and guard < len(segs) + 2:
            guard += 1
            for j in range(len(segs)):
                if used[j]: continue
                a2, b2, i2 = segs[j]
                if _c2(a2, cur): used[j] = True; pts += [a2] + list(i2); cur = b2; break
                if _c2(b2, cur): used[j] = True; pts += [b2] + list(reversed(i2)); cur = a2; break
            else: break
        if _c2(cur, start) and len(pts) >= 3: loops.append(pts)
    return loops

def _area2(p):
    a = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]; x1, y1 = p[(i + 1) % len(p)]; a += x0 * y1 - x1 * y0
    return a / 2

def _pip(pt, poly):
    x, y = pt; inside = False; n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-300) + x0: inside = not inside
    return inside

def _loop_in_loop(inner, outer):
    """most of the inner loop's edge midpoints lie inside the outer loop or on its boundary (a hole may touch the outline)"""
    n = len(inner); tot = 0; ok = 0
    ox = np.asarray(outer, float)
    for i in range(n):
        p = ((inner[i][0] + inner[(i + 1) % n][0]) / 2, (inner[i][1] + inner[(i + 1) % n][1]) / 2); tot += 1
        if _pip(p, outer): ok += 1; continue
        a = ox; b = np.roll(ox, -1, axis=0); d = b - a; L2 = np.maximum((d * d).sum(1), 1e-18)
        t = np.clip(((np.asarray(p) - a) * d).sum(1) / L2, 0, 1); dist = np.linalg.norm(a + t[:, None] * d - np.asarray(p), axis=1)
        if dist.min() < 1e-6: ok += 1
    return tot > 0 and ok >= 0.6 * tot

def _group_loops(loops):
    """loops -> [(outer, [holes])] by containment depth (even depth = outer, odd = hole of its parent)"""
    order = sorted(range(len(loops)), key=lambda i: -abs(_area2(loops[i])))
    parent = {}
    for pos, i in enumerate(order):
        par = None
        for j in reversed(order[:pos]):
            if _loop_in_loop(loops[i], loops[j]): par = j; break
        parent[i] = par
    def depth(i):
        d = 0
        while parent[i] is not None: i = parent[i]; d += 1
        return d
    groups = {}
    for i in order:
        if depth(i) % 2 == 0: groups[i] = (loops[i], [])
    for i in order:
        if depth(i) % 2 == 1 and parent[i] in groups: groups[parent[i]][1].append(loops[i])
    return list(groups.values())

def _cancel_slits(ring, tol=1e-6):
    """remove zero-width slits from a closed walk: split every edge at the other vertices lying on it, drop each sub-edge that is traversed in both directions, re-trace the remaining directed edges into loops.
    returns a list of loops (a single loop when the ring was already clean)"""
    n = len(ring)
    if n < 4: return [ring]
    P = np.asarray(ring, float); key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    uniq = {}; 
    for p in P: uniq.setdefault(key(p), p)
    U = np.array(list(uniq.values())); ukeys = list(uniq.keys())
    edges = []
    for i in range(n):
        a = P[i]; b = P[(i + 1) % n]; d = b - a; L2 = float(d @ d)
        if L2 < 1e-18: continue
        t = (U - a) @ d / L2; dist = np.linalg.norm(U - (a + np.outer(t, d)), axis=1)
        sel = [j for j in np.nonzero((dist < 10 * tol) & (t > 1e-9) & (t < 1 - 1e-9))[0]]
        chain = [key(a)] + [ukeys[j] for j in sorted(sel, key=lambda j: t[j])] + [key(b)]
        for u_, v_ in zip(chain, chain[1:]): edges.append((u_, v_))
    cnt = collections.Counter(edges)
    keep = []
    for (u_, v_), c in cnt.items():
        r = c - cnt.get((v_, u_), 0)
        if r > 0: keep += [(u_, v_)] * r
    if len(keep) == len(edges): return [ring]
    coords = {key(p): tuple(p) for p in P}
    for k_, p in uniq.items(): coords[k_] = tuple(p)
    nxt = collections.defaultdict(list)
    for u_, v_ in keep: nxt[u_].append(v_)
    loops = []
    while nxt:
        start = next(iter(nxt)); cur = start; lp = []
        guard = 0
        while guard < 100000:
            guard += 1; lp.append(coords[cur]); outs = nxt[cur]
            if not outs: break
            nx_ = outs.pop(); 
            if not outs: del nxt[cur]
            cur = nx_
            if cur == start: break
        if len(lp) >= 3 and cur == start: loops.append(lp)
        nxt = {k: v for k, v in nxt.items() if v}
        nxt = collections.defaultdict(list, nxt)
    return loops or [ring]

def _loop_via_poles(mine, ev, tol=1e-6):
    """chain the uv polylines of a face's edges end to end; where the chain breaks, jump along a pole (both ends map to one 3D point) to the next unused edge.
    returns a closed loop (list of uv) when every edge is used exactly once, else None"""
    segs = [([tuple(a)] + [tuple(q) for q in inter] + [tuple(b)]) for (a, b, inter, _n, _p) in mine.values()]
    if not segs: return None
    close = lambda p, q: abs(p[0] - q[0]) < tol and abs(p[1] - q[1]) < tol
    used = [False] * len(segs); used[0] = True; pts = list(segs[0]); poles = 0
    for _ in range(len(segs)):
        cur = pts[-1]; nxt = None
        for j, sg in enumerate(segs):
            if used[j]: continue
            if close(sg[0], cur): nxt = (j, sg); break
            if close(sg[-1], cur): nxt = (j, sg[::-1]); break
        if nxt is None:
            for j, sg in enumerate(segs):                       # pole jump
                if used[j]: continue
                for cand in (sg, sg[::-1]):
                    if np.linalg.norm(np.asarray(ev(*cand[0])) - np.asarray(ev(*cur))) < 1e-7 and (abs(cand[0][0] - cur[0]) > tol or abs(cand[0][1] - cur[1]) > tol): nxt = (j, cand); poles += 1; break
                if nxt: break
        if nxt is None: break
        used[nxt[0]] = True; pts += list(nxt[1])
    if not all(used): return None
    if not close(pts[-1], pts[0]):
        if np.linalg.norm(np.asarray(ev(*pts[-1])) - np.asarray(ev(*pts[0]))) < 1e-7: poles += 1
        else: return None
    return pts if poles >= 0 and len(pts) >= 3 else None

def _nudge_repeats(ring, eps=1e-7):
    """a weakly simple ring (a vertex visited twice where two sub-loops touch) breaks ear clipping: move later visits a hair toward the mean of their neighbours"""
    seen = {}; out = [list(p) for p in ring]; n = len(out)
    for i, p in enumerate(ring):
        k = (round(p[0] * 1e6), round(p[1] * 1e6))
        if k in seen:
            a = np.asarray(ring[(i - 1) % n], float); b = np.asarray(ring[(i + 1) % n], float); d = (a + b) / 2 - np.asarray(p, float); L = np.linalg.norm(d)
            if L > 0: out[i] = [p[0] + eps * d[0] / L * (1 + seen[k]), p[1] + eps * d[1] / L * (1 + seen[k])]
            seen[k] += 1
        else: seen[k] = 0
    return out

def tessellate_geometry(geo):
    """-> dict(tris=[(p0,p1,p2),...], unsupported=[kinds], faces=n)"""
    faces = geo.get('m_pFaces') or []; edges = _edge_map(geo)
    tris = []; meta = []; unsup = []; nf = 0; fidx = []; fprio = {}
    surfs = {}
    for fc in faces:
        f_ = _ob(fc)
        if isinstance(f_, dict) and f_.get('m_pSurf'):
            k_, e_ = surface_eval(f_.get('m_pSurf'))
            if e_ is not None: surfs[fc.get('handle')] = (k_, e_, f_.get('m_pSurf'))
    frs = []; _rs = None                                                 # per triangle: the source face's m_renderStyleId (material / graphics style; viewer per-triangle materials)
    for fc in faces:
        frs.extend([_rs] * (len(tris) - len(frs)))
        f = _ob(fc)
        if not isinstance(f, dict): continue
        _rs = f.get('m_renderStyleId')
        kind, ev = surface_eval(f.get('m_pSurf'))
        if ev is None: unsup.append('surface'); continue
        _pr = bool(((f.get('m_GInfo') or {}).get('m_flags') or 0) & 0x80000)          # faces of the displayed solid carry this flag; reference/auxiliary faces usually do not
        loops = face_loops_uv(fc.get('handle'), edges, surfs)
        if not loops:
            mine0 = {}; face_loops_uv(fc.get('handle'), edges, surfs, out_mine=mine0)
            lp = _loop_via_poles(mine0, ev) if mine0 else None
            try: e0, e1 = _ob(_ob(f['m_pFirstLoop'])['m_Envelope'])['m_corners']; rect_a = (e1[0] - e0[0]) * (e1[1] - e0[1])
            except Exception: rect_a = 0
            off_border = False
            if rect_a > 0:                                           # only a TRIMMED face (some edge leaves the uv rectangle's border) needs this; untrimmed edgeless/seam-only faces use the rectangle grid
                for (ea, eb, einter, _n, _p) in mine0.values():
                    for q in [ea] + list(einter) + [eb]:
                        if not (abs(q[0] - e0[0]) < 1e-4 or abs(q[0] - e1[0]) < 1e-4 or abs(q[1] - e0[1]) < 1e-4 or abs(q[1] - e1[1]) < 1e-4): off_border = True
            if lp is not None and off_border and abs(_area2(lp)) > 1e-3 * rect_a: loops = [lp]
        if not loops:
            lg = face_loops_uv(fc.get('handle'), edges, surfs, allow_gaps=True)
            try: cc0, cc1 = _ob(_ob(f['m_pFirstLoop'])['m_Envelope'])['m_corners'] if 'm_Envelope' in _ob(f['m_pFirstLoop']) else _ob(f['m_pFirstLoop'])['m_Envelope']['m_corners']
            except Exception: cc0 = cc1 = None
            if lg and cc0 is not None and sum(abs(_area2(l)) for l in lg) > 0 and abs(sum(abs(_area2(l)) for l in lg) / ((cc1[0] - cc0[0]) * (cc1[1] - cc0[1])) - 1) < 0.03: loops = lg
            elif lg and len(lg) == 1:
                # a trimmed face of a revolution/cone whose pole edge is missing: the implicit closing segment must run along a pole (both ends map to one 3D point)
                try:
                    Lp = lg[0]; npole = 0; nn = len(Lp)
                    for i_ in range(nn):
                        p_, q_ = Lp[i_], Lp[(i_ + 1) % nn]
                        if abs(p_[0] - q_[0]) + abs(p_[1] - q_[1]) > 1e-3 and np.linalg.norm(np.asarray(ev(*p_)) - np.asarray(ev(*q_))) < 1e-7: npole += 1
                    if npole >= 1: loops = lg
                except Exception: pass
        if not loops:
            # edgeless face (full sphere/torus patches): the loop envelope is the uv rectangle
            try: c0, c1 = _ob(_ob(f['m_pFirstLoop'])['m_Envelope'])['m_corners'] if 'm_Envelope' in _ob(f['m_pFirstLoop']) else _ob(f['m_pFirstLoop'])['m_Envelope']['m_corners']
            except Exception: c0 = c1 = None
            if c0 is not None and c1[0] > c0[0] and c1[1] > c0[1]:
                hh = fc.get('handle'); on_rect = True                      # the envelope rectangle is the face only if every edge of the face runs along its border
                for e_ in edges.values():
                    rf = [r.get('ref') if isinstance(r, dict) else None for r in (e_.get('m_pFace') or [])]
                    if hh not in rf: continue
                    sd = rf.index(hh); fl_ = e_.get('m_firstAndLastEdgePnts') or []
                    for p_ in list(fl_) + list(e_.get('m_interiorEdgePnts') or []):
                        po = _ob(p_)
                        if not isinstance(po, dict) or 'uv' not in po: continue
                        u_, v_ = po['uv'][sd]
                        if not (abs(u_ - c0[0]) < 1e-4 or abs(u_ - c1[0]) < 1e-4 or abs(v_ - c0[1]) < 1e-4 or abs(v_ - c1[1]) < 1e-4): on_rect = False
                if not on_rect: c0 = None
            if c0 is not None and c1[0] > c0[0] and c1[1] > c0[1]:
                mine_ = {}; face_loops_uv(fc.get('handle'), edges, surfs, out_mine=mine_)
                bd = {'v0': [], 'v1': [], 'u0': [], 'u1': []}
                for (ea, eb, einter, _n, _p) in mine_.values():
                    ep = [ea] + list(einter) + [eb]
                    for key_, test in (('v0', lambda q: abs(q[1] - c0[1]) < 1e-6), ('v1', lambda q: abs(q[1] - c1[1]) < 1e-6), ('u0', lambda q: abs(q[0] - c0[0]) < 1e-6), ('u1', lambda q: abs(q[0] - c1[0]) < 1e-6)):
                        if all(test(q) for q in ep): bd[key_] += [tuple(q) for q in ep]
                for key_, corners in (('v0', [(c0[0], c0[1]), (c1[0], c0[1])]), ('v1', [(c0[0], c1[1]), (c1[0], c1[1])]), ('u0', [(c0[0], c0[1]), (c0[0], c1[1])]), ('u1', [(c1[0], c0[1]), (c1[0], c1[1])])): bd[key_] += corners
                has_real = any(len(set(bd[k_])) > 2 for k_ in bd)
                try:                                                      # a pole border (the whole row maps to one point) needs interior samples: use the regular grid
                    for vv_ in (c0[1], c1[1]):
                        if np.linalg.norm(np.asarray(ev(c0[0], vv_)) - np.asarray(ev((c0[0] + c1[0]) / 2, vv_))) < 1e-9: has_real = False
                except Exception: pass
                if not has_real:                                          # edgeless face (sphere/torus halves): regular uv grid
                    nu = int(min(64, max(2, math.ceil((c1[0] - c0[0]) / 0.1)))); nv = int(min(64, max(2, math.ceil((c1[1] - c0[1]) / 0.2))))
                    try:
                        pa = np.asarray(ev(c0[0], c0[1])); pb = np.asarray(ev(c0[0], c1[1])); pm = np.asarray(ev(c0[0], (c0[1] + c1[1]) / 2))
                        if np.linalg.norm(pm - (pa + pb) / 2) < 1e-9 * max(1.0, np.linalg.norm(pb - pa)): nv = 1
                    except Exception: pass
                    Us = [c0[0] + (c1[0] - c0[0]) * i / nu for i in range(nu + 1)]; Vs = [c0[1] + (c1[1] - c0[1]) * j / nv for j in range(nv + 1)]
                    ue = sorted({round(q[0], 9) for k_ in ('v0', 'v1') if len(set(bd[k_])) > 2 for q in bd[k_]})            # grid lines through the edge samples of the borders that have edges
                    ve = sorted({round(q[1], 9) for k_ in ('u0', 'u1') if len(set(bd[k_])) > 2 for q in bd[k_]})
                    if len(ue) > 2: Us = ue
                    if len(ve) > 2: Vs = ve
                    nu = len(Us) - 1; nv = len(Vs) - 1
                    G = [[(Us[i], Vs[j]) for j in range(nv + 1)] for i in range(nu + 1)]
                    nf += 1; fprio[nf] = _pr
                    for i in range(nu):
                        for j in range(nv):
                            a_, b_, c_, d_ = G[i][j], G[i + 1][j], G[i + 1][j + 1], G[i][j + 1]
                            for tri in ((a_, b_, c_), (a_, c_, d_)):
                                P = [np.array(ev(u, v)) for u, v in tri]
                                if min(np.linalg.norm(P[0] - P[1]), np.linalg.norm(P[1] - P[2]), np.linalg.norm(P[0] - P[2])) < 1e-9: continue
                                tris.append(tuple(P)); meta.append((kind, ev, tuple(tri))); fidx.append(nf)
                    continue
                for key_ in ('v0', 'v1'):                                    # a border without any edge (degenerate pole, or an edgeless face) is sampled uniformly
                    if len(set(bd[key_])) <= 2:
                        vv = c0[1] if key_ == 'v0' else c1[1]; n_ = int(min(64, max(2, math.ceil((c1[0] - c0[0]) / 0.1))))
                        bd[key_] += [(c0[0] + (c1[0] - c0[0]) * i / n_, vv) for i in range(n_ + 1)]
                for key_ in ('u0', 'u1'):
                    if len(set(bd[key_])) <= 2:
                        uu = c0[0] if key_ == 'u0' else c1[0]; ev_ = ev
                        n_ = 1
                        try:
                            pa = np.asarray(ev(uu, c0[1])); pb = np.asarray(ev(uu, c1[1])); pm = np.asarray(ev(uu, (c0[1] + c1[1]) / 2))
                            if np.linalg.norm(pm - (pa + pb) / 2) > 1e-9 * max(1.0, np.linalg.norm(pb - pa)): n_ = int(min(64, max(2, math.ceil((c1[1] - c0[1]) / 0.2))))
                        except Exception: pass
                        bd[key_] += [(uu, c0[1] + (c1[1] - c0[1]) * i / n_) for i in range(n_ + 1)]
                def _srt(lst, ax, rev=False):
                    out_ = []; 
                    for q in sorted(set((round(x, 9), round(y, 9)) for x, y in lst), key=lambda q: q[ax], reverse=rev):
                        if not out_ or abs(q[0] - out_[-1][0]) + abs(q[1] - out_[-1][1]) > 1e-9: out_.append(q)
                    return out_
                ring = _srt(bd['v0'], 0)[:-1] + _srt(bd['u1'], 1)[:-1] + _srt(bd['v1'], 0, True)[:-1] + _srt(bd['u0'], 1, True)[:-1]
                nf += 1; fprio[nf] = _pr
                arr = np.array(ring, dtype=np.float64)
                try: idx = earcut.triangulate_float64(arr, np.array([len(arr)], dtype=np.uint32))
                except Exception: unsup.append('earcut'); continue
                P = [np.array(ev(u, v)) for u, v in ring]
                for k in range(0, len(idx), 3):
                    tri = (ring[idx[k]], ring[idx[k + 1]], ring[idx[k + 2]]); Pt = [P[idx[k]], P[idx[k + 1]], P[idx[k + 2]]]
                    if min(np.linalg.norm(Pt[0] - Pt[1]), np.linalg.norm(Pt[1] - Pt[2]), np.linalg.norm(Pt[0] - Pt[2])) < 1e-9: continue
                    tris.append(tuple(Pt)); meta.append((kind, ev, tri)); fidx.append(nf)
                continue
        if not loops: unsup.append('noloops'); continue
        nf += 1; fprio[nf] = _pr
        for outer, holes in _group_loops(loops):
            verts = _nudge_repeats(list(outer)); ring_ends = [len(verts)]
            for hl in holes: verts += hl; ring_ends.append(len(verts))
            arr = np.array(verts, dtype=np.float64)
            try: idx = earcut.triangulate_float64(arr, np.array(ring_ends, dtype=np.uint32))
            except Exception: unsup.append('earcut'); continue
            if kind != 'plane' and not os.environ.get('RVT_NOREFINE'):        # curved face: the emitted triangles must follow the surface (viewer request 10)
                g_ = _rect_grid(verts, ev) if len(ring_ends) == 1 else None
                if g_ is None and os.environ.get('RVT_STRIP'): g_ = _strip_tri(verts, ring_ends, ev)      # experimental: adds points on loop edges (breaks shell welding)
                if g_ is not None: verts, tl = g_
                elif len(ring_ends) == 1: verts, tl = refine_curved(verts, idx, ev)
                else: tl = [tuple(idx[k:k + 3]) for k in range(0, len(idx), 3)]
                idx = [q for t_ in tl for q in t_]
            P = [np.array(ev(u, v)) for u, v in verts]
            for k in range(0, len(idx), 3):
                tris.append((P[idx[k]], P[idx[k + 1]], P[idx[k + 2]])); meta.append((kind, ev, (verts[idx[k]], verts[idx[k + 1]], verts[idx[k + 2]]))); fidx.append(nf)
    frs.extend([_rs] * (len(tris) - len(frs)))
    return {'tris': tris, 'unsupported': unsup, 'faces': nf, 'meta': meta, 'fidx': fidx, 'fprio': fprio, 'frs': frs}

def _rect_grid(verts, ev, max_n=48):
    """a curved face whose uv loop is its uv rectangle (every sample on the border, loop area = rectangle area): structured grid through the loop's own
    border samples (u from the v-borders, v from the u-borders), so it welds to the neighbours and every triangle lies on the surface. None otherwise."""
    U = np.array(verts, float); u0, v0 = U.min(0); u1, v1 = U.max(0)
    if u1 - u0 < 1e-9 or v1 - v0 < 1e-9: return None
    tb = 1e-6 * max(1.0, abs(u1 - u0), abs(v1 - v0))
    onb = (np.abs(U[:, 0] - u0) < tb) | (np.abs(U[:, 0] - u1) < tb) | (np.abs(U[:, 1] - v0) < tb) | (np.abs(U[:, 1] - v1) < tb)
    if not onb.all() or abs(abs(_area2([tuple(q) for q in verts])) - (u1 - u0) * (v1 - v0)) > 1e-6 * (u1 - u0) * (v1 - v0) + 1e-12: return None
    ub0 = {round(q[0], 8) for q in U if abs(q[1] - v0) < tb} | {round(u0, 8), round(u1, 8)}; ub1 = {round(q[0], 8) for q in U if abs(q[1] - v1) < tb} | {round(u0, 8), round(u1, 8)}
    vb0 = {round(q[1], 8) for q in U if abs(q[0] - u0) < tb} | {round(v0, 8), round(v1, 8)}; vb1 = {round(q[1], 8) for q in U if abs(q[0] - u1) < tb} | {round(v0, 8), round(v1, 8)}
    if vb0 != vb1: return None                                         # the two u-borders must share their v samples (rows); the v-borders may differ (zipper rows)
    Vs = sorted(vb0)
    def thin(L):
        out = [L[0]]
        for x in L[1:]:
            if x - out[-1] > 1e-9: out.append(x)
        return out
    A0, A1, Vs = thin(sorted(ub0)), thin(sorted(ub1)), thin(Vs)
    nv = len(Vs) - 1
    if nv < 1 or nv > max_n or len(A0) - 1 > 4 * max_n or len(A1) - 1 > 4 * max_n: return None
    sgn = 1 if _area2([tuple(q) for q in verts]) > 0 else -1           # keep the loop's winding
    V = []; rows = []
    for jj, vv in enumerate(Vs):                                      # bottom half of the rows carries the v0-border samples, top half the v1-border samples
        A = A0 if jj * 2 < nv or jj == 0 else A1
        if jj == nv: A = A1
        rows.append([len(V) + k for k in range(len(A))]); V += [(u, vv) for u in A]
    T = []
    for jj in range(nv):
        r0, r1 = rows[jj], rows[jj + 1]; i0 = i1 = 0
        while i0 < len(r0) - 1 or i1 < len(r1) - 1:
            adv0 = i1 >= len(r1) - 1 or (i0 < len(r0) - 1 and V[r0[i0 + 1]][0] <= V[r1[i1 + 1]][0])
            if adv0: t = (r0[i0], r0[i0 + 1], r1[i1]); i0 += 1
            else: t = (r0[i0], r1[i1 + 1], r1[i1]); i1 += 1
            T.append(t if sgn > 0 else (t[0], t[2], t[1]))
    P = [np.asarray(ev(*q), float) for q in V]
    T = [t for t in T if min(np.linalg.norm(P[t[0]] - P[t[1]]), np.linalg.norm(P[t[1]] - P[t[2]]), np.linalg.norm(P[t[0]] - P[t[2]])) > 1e-9]
    return V, T

def _strip_tri(verts, ring_ends, ev, rel_tol=5e-3, abs_tol=0.0033, max_tris=6000):
    """triangulation of a CURVED face's uv region (outer loop + holes, even-odd) by strips between consecutive distinct u values of the loop samples:
    in each strip the region is a set of trapezoids between edge crossings; a trapezoid is split along v only where the surface bends in v more than tol
    (cylinders/cones/extrusions: never). Every loop sample is a strip boundary, so the face keeps its own samples (crossings add points ON the loop's uv
    segments: T-junctions on the edge, no cracks). Returns (verts, triangles) or None."""
    V = [tuple(map(float, q)) for q in verts]; n = len(V)
    if n < 3: return None
    rings = []; st = 0
    for e in ring_ends: rings.append(list(range(st, e))); st = e
    edges = [(r[i], r[(i + 1) % len(r)]) for r in rings for i in range(len(r))]
    us = sorted({round(q[0], 9) for q in V})
    if len(us) < 2 or len(us) > 600: return None
    P0 = np.array([ev(*q) for q in V], float); tol = max(abs_tol, rel_tol * float(np.linalg.norm(P0.max(0) - P0.min(0))))
    sgn = 1 if sum(_area2([V[i] for i in r]) for r in rings[:1]) > 0 else -1
    out = []; idx = {}
    def vid(u, v):
        k = (round(u, 9), round(v, 9))
        if k not in idx: idx[k] = len(out); out.append((u, v))
        return idx[k]
    def vat(e, u):
        (ua, va), (ub, vb) = V[e[0]], V[e[1]]
        if abs(ub - ua) < 1e-12: return va
        return va + (vb - va) * (u - ua) / (ub - ua)
    T = []
    def bend(u, v0, v1):
        a = np.asarray(ev(u, v0), float); b = np.asarray(ev(u, v1), float); m = np.asarray(ev(u, (v0 + v1) / 2), float)
        return float(np.linalg.norm(m - (a + b) / 2))
    for ua, ub in zip(us[:-1], us[1:]):
        if ub - ua < 1e-12: continue
        um = (ua + ub) / 2
        cr = [e for e in edges if min(V[e[0]][0], V[e[1]][0]) <= ua + 1e-12 and max(V[e[0]][0], V[e[1]][0]) >= ub - 1e-12 and abs(V[e[0]][0] - V[e[1]][0]) > 1e-12]
        cr.sort(key=lambda e: vat(e, um))
        for k in range(0, len(cr) - 1, 2):
            lo, hi = cr[k], cr[k + 1]
            a0, a1, b0, b1 = vat(lo, ua), vat(hi, ua), vat(lo, ub), vat(hi, ub)
            ns = 1                                                    # splits along v where the surface bends in v
            while ns < 32 and max(bend(ua, a0 + (a1 - a0) * j / ns, a0 + (a1 - a0) * (j + 1) / ns) for j in range(ns)) > tol: ns *= 2
            for j in range(ns):
                p00 = vid(ua, a0 + (a1 - a0) * j / ns); p01 = vid(ua, a0 + (a1 - a0) * (j + 1) / ns)
                p10 = vid(ub, b0 + (b1 - b0) * j / ns); p11 = vid(ub, b0 + (b1 - b0) * (j + 1) / ns)
                for t in ((p00, p10, p11), (p00, p11, p01)):
                    if len({t[0], t[1], t[2]}) == 3: T.append(t if sgn > 0 else (t[0], t[2], t[1]))
            if len(T) > max_tris: return None
    if not T: return None
    P = [np.asarray(ev(*q), float) for q in out]
    T = [t for t in T if min(np.linalg.norm(P[t[0]] - P[t[1]]), np.linalg.norm(P[t[1]] - P[t[2]]), np.linalg.norm(P[t[0]] - P[t[2]])) > 1e-9]
    return out, T

def refine_curved(verts, idx, ev, rel_tol=float(os.environ.get("RVT_REFINE_REL", 5e-3)), abs_tol=0.0033, max_tris=2000):
    """conforming refinement of an earcut triangulation of a CURVED face in (u,v): earcut only connects loop samples, so on a doubly curved patch its
    triangles are chords through the solid (torus face area 16.8 vs 10.0). Interior edges whose uv midpoint lies farther than tol from the chord are bisected
    (both adjacent triangles split, winding kept); triangles made only of loop edges get their uv centroid inserted. The loop itself is never changed, so the
    face still welds to its neighbours. tol = max(abs_tol, rel_tol * face diagonal) feet. Returns (verts, triangles as index triples)."""
    V = [tuple(map(float, q)) for q in verts]; T = [tuple(int(idx[k + j]) for j in range(3)) for k in range(0, len(idx), 3)]
    if not T: return V, T
    P = [np.asarray(ev(*q), float) for q in V]
    A = np.array(P); tol = max(abs_tol, rel_tol * float(np.linalg.norm(A.max(0) - A.min(0))))
    nloop = len(V); bnd = set()
    bdev = 0.0                                                         # the loop's own chord error: refining the interior beyond it adds triangles, not fidelity (viewer note 15)
    for i in range(nloop):
        j = (i + 1) % nloop; m = ((V[i][0] + V[j][0]) / 2, (V[i][1] + V[j][1]) / 2)
        try: bdev = max(bdev, float(np.linalg.norm(np.asarray(ev(*m), float) - (P[i] + P[j]) / 2)))
        except Exception: pass
    tol = max(tol, bdev)
    for i in range(nloop): bnd.add(frozenset((i, (i + 1) % nloop)))
    def dev(i, j):
        m = ((V[i][0] + V[j][0]) / 2, (V[i][1] + V[j][1]) / 2); pm = np.asarray(ev(*m), float)
        return float(np.linalg.norm(pm - (P[i] + P[j]) / 2)), m, pm
    def add(m, pm): V.append(m); P.append(pm); return len(V) - 1
    # 1) edge flips (no new vertices): an interior diagonal is replaced by the other diagonal of its (uv-convex) quad when that one deviates less from the
    #    surface; earcut's long chords across a cylinder/cone patch become the natural strip, so far fewer splits are needed (viewer note 15)
    def _cross(o, a_, b_): return (V[a_][0] - V[o][0]) * (V[b_][1] - V[o][1]) - (V[a_][1] - V[o][1]) * (V[b_][0] - V[o][0])
    for _fp in range(8):
        em = {}
        for ti, t in enumerate(T):
            for k in range(3): em.setdefault(frozenset((t[k], t[(k + 1) % 3])), []).append(ti)
        flipped = 0; used = set()
        for e, ts in em.items():
            if e in bnd or len(ts) != 2 or ts[0] in used or ts[1] in used: continue
            i, j = tuple(e); t1, t2 = T[ts[0]], T[ts[1]]
            c = [q for q in t1 if q not in e]; d_ = [q for q in t2 if q not in e]
            if len(c) != 1 or len(d_) != 1: continue
            c, d_ = c[0], d_[0]
            if frozenset((c, d_)) in em: continue
            # convex quad in uv: c and d on opposite sides of (i, j), i and j on opposite sides of (c, d)
            if _cross(i, j, c) * _cross(i, j, d_) >= 0 or _cross(c, d_, i) * _cross(c, d_, j) >= 0: continue
            if dev(c, d_)[0] + 1e-12 >= dev(i, j)[0]: continue
            a_, b_, c_ = t1
            for _ in range(3):
                if {a_, b_} == {i, j}: break
                a_, b_, c_ = b_, c_, a_
            T[ts[0]] = (a_, d_, c_); T[ts[1]] = (d_, b_, c_)          # keeps t1's winding: (a, b, c) -> (a, d, c) + (d, b, c)
            used.update(ts); flipped += 1
        if not flipped: break
    for _pass in range(12):
        if len(T) >= max_tris: break
        em = {}
        for ti, t in enumerate(T):
            for k in range(3):
                e = frozenset((t[k], t[(k + 1) % 3])); em.setdefault(e, []).append(ti)
        changed = False; used = set(); newT = list(T); drop = set()
        cand = []
        for e, ts in em.items():
            if e in bnd or len(ts) != 2: continue
            i, j = tuple(e); d, m, pm = dev(i, j)
            if d > tol: cand.append((d, i, j, m, pm, ts))
        cand.sort(key=lambda c: -c[0])
        for d, i, j, m, pm, ts in cand:
            if len(newT) - len(drop) >= max_tris: break
            if any(t_ in used for t_ in ts): continue
            mi = add(m, pm)
            for t_ in ts:
                a_, b_, c_ = T[t_]
                for _ in range(3):                                      # rotate so that the split edge is (a_, b_)
                    if {a_, b_} == {i, j}: break
                    a_, b_, c_ = b_, c_, a_
                newT.append((a_, mi, c_)); newT.append((mi, b_, c_)); drop.add(t_); used.add(t_)
            changed = True
        for ti, t in enumerate(T):                                       # triangles bounded only by loop edges: insert the centroid when it is off the plane
            if ti in drop or len(newT) - len(drop) >= max_tris: continue
            if all(frozenset((t[k], t[(k + 1) % 3])) in bnd for k in range(3)):
                c = (sum(V[q][0] for q in t) / 3, sum(V[q][1] for q in t) / 3); pc = np.asarray(ev(*c), float)
                if np.linalg.norm(pc - (P[t[0]] + P[t[1]] + P[t[2]]) / 3) > tol:
                    ci = add(c, pc); a_, b_, c_ = t
                    newT += [(a_, b_, ci), (b_, c_, ci), (c_, a_, ci)]; drop.add(ti); changed = True
        T = [t for ti, t in enumerate(newT) if ti not in drop]
        if not changed: break
    return V, T

def mesh_volume(tris, tol=5e-5):
    """orient triangles consistently through shared edges; returns (volume, closed, n_open_edges, area)"""
    if not tris: return 0.0, False, 0, 0.0
    key = lambda p: (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    vid = {}; T = []
    for t in tris:
        ids = []
        for p in t:
            k = key(p); ids.append(vid.setdefault(k, len(vid)))
        if len(set(ids)) == 3: T.append(ids)
    V = np.zeros((len(vid), 3))
    for t in tris:
        for p in t: V[vid[key(p)]] = p
    # edge -> triangles
    em = collections.defaultdict(list)
    for ti, t in enumerate(T):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): em[(min(a, b), max(a, b))].append((ti, a, b))
    # input winding already consistent (every directed edge cancelled by its reverse, non-manifold edges allowed): trust it
    de = collections.Counter()
    for t in T:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): de[(a, b)] += 1
    if T and all(de[(b, a)] == c for (a, b), c in de.items()):
        Tn = np.array(T); A = V[Tn[:, 0]]; B = V[Tn[:, 1]]; C = V[Tn[:, 2]]
        vol = float(np.einsum('ij,ij->i', A, np.cross(B, C)).sum() / 6)
        if vol > 0: return vol, True, 0, float(np.linalg.norm(np.cross(B - A, C - A), axis=1).sum() / 2)
    flip = [None] * len(T)
    for s in range(len(T)):
        if flip[s] is not None: continue
        flip[s] = False; stack = [s]
        while stack:
            ti = stack.pop(); t = T[ti]
            if flip[ti]: t = [t[0], t[2], t[1]]
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                if len(em[(min(a, b), max(a, b))]) != 2: continue            # non-manifold edge (e.g. a chord shared by two faces' triangulations): do not propagate orientation across it
                for (tj, a2, b2) in em[(min(a, b), max(a, b))]:
                    if tj == ti or flip[tj] is not None: continue
                    # neighbour must traverse b->a
                    same = (a2 == a and b2 == b)
                    flip[tj] = same; stack.append(tj)
    vol = 0.0; area = 0.0
    for ti, t in enumerate(T):
        p0, p1, p2 = V[t[0]], V[t[1]], V[t[2]]
        if flip[ti]: p1, p2 = p2, p1
        vol += np.dot(p0, np.cross(p1, p2)) / 6.0; area += np.linalg.norm(np.cross(p1 - p0, p2 - p0)) / 2
    open_edges = sum(1 for k, v in em.items() if len(v) != 2)
    return abs(vol), open_edges == 0, open_edges, area

def components(geo):
    """split a Geometry node into shells (face sets connected through shared edges). returns list of dicts"""
    faces = geo.get('m_pFaces') or []; edges = _edge_map(geo)
    fh = [fc.get('handle') for fc in faces if isinstance(fc, dict) and isinstance(_ob(fc), dict)]
    parent = {h: h for h in fh}
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in edges.values():
        refs = [r.get('ref') for r in (e.get('m_pFace') or []) if isinstance(r, dict)]
        refs = [r for r in refs if r in parent]
        for a, b in zip(refs, refs[1:]): parent[find(a)] = find(b)
    groups = collections.defaultdict(list)
    for h in fh: groups[find(h)].append(h)
    out = []
    for root, hs in groups.items():
        sub = {'m_pFaces': [fc for fc in faces if isinstance(fc, dict) and fc.get('handle') in hs], 'm_pEdges': geo.get('m_pEdges'), 'm_edgeMap': edges}
        t = tessellate_geometry(sub)
        comp = {'faces': hs, 'n_faces': len(hs), 'unsupported': t['unsupported'], 'tris': t['tris']}
        if t['tris']:
            P = np.array([p for tr in t['tris'] for p in tr]); comp['bbox'] = (P.min(0), P.max(0))
            vol, closed, nopen, area = mesh_volume(t['tris']); comp.update(volume=vol, closed=closed, open_edges=nopen, area=area)
        out.append(comp)
    return out

def element_faces_in_bbox(geo, bb, eps=2e-3):
    """tessellate only faces fully inside the element bbox (the element's own shell inside a larger joined/cut geometry)"""
    faces = geo.get('m_pFaces') or []; edges = _edge_map(geo)
    lo = np.array(bb[0]) - eps; hi = np.array(bb[1]) + eps
    keep = []
    for fc in faces:
        f = _ob(fc)
        if not isinstance(f, dict): continue
        kind, ev = surface_eval(f.get('m_pSurf'))
        if ev is None: continue
        loops = face_loops_uv(fc.get('handle'), edges)
        if not loops:
            # no ordinary loop (edgeless / pole / trimmed faces): judge the face by its own tessellation
            tt = tessellate_geometry({'m_pFaces': [fc], 'm_pEdges': geo.get('m_pEdges'), 'm_edgeMap': edges})
            if not tt['tris']: continue
            P = np.array([p for tr in tt['tris'] for p in tr])
            if (P.min(0) >= lo).all() and (P.max(0) <= hi).all(): keep.append(fc)
            continue
        P = np.array([ev(u, v) for u, v in max(loops, key=lambda l: abs(_area2(l)))])
        if (P.min(0) >= lo).all() and (P.max(0) <= hi).all(): keep.append(fc)
    sub = {'m_pFaces': keep, 'm_pEdges': geo.get('m_pEdges'), 'm_edgeMap': edges}
    t = tessellate_geometry(sub)
    return t

def heal_open(tris, tol=5e-5):
    """Cap open boundaries: boundary edges are chained into loops; each planar loop is triangulated and added (a face shared with a joined neighbour is stored in the neighbour's geometry).
    returns (tris, n_caps, healed_all)"""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    em = collections.defaultdict(list); pts = {}
    for t in tris:
        ks = [key(p) for p in t]
        for p, k in zip(t, ks): pts[k] = np.asarray(p)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if ks[a] != ks[b]: em[frozenset((ks[a], ks[b]))].append((ks[a], ks[b]))
    bnd = [v[0] for e, v in em.items() if len(v) == 1]
    if not bnd: return tris, 0, True
    nxt = collections.defaultdict(list)
    for a, b in bnd: nxt[a].append(b)
    used = set(); loops = []
    for a, b in bnd:
        if (a, b) in used: continue
        loop = [a]; cur = b; used.add((a, b)); guard = 0
        while cur != a and guard < 10000:
            guard += 1; cand = [c for c in nxt[cur] if (cur, c) not in used]
            if not cand: break
            used.add((cur, cand[0])); loop.append(cur); cur = cand[0]
        if cur == a and len(loop) >= 3: loops.append(loop)
        else: return tris, 0, False
    out = list(tris); caps = 0
    for loop in loops:
        P = np.array([pts[k] for k in loop]); c = P.mean(0)
        u, s, vt = np.linalg.svd(P - c)
        if s[2] > 1e-4 * max(s[0], 1e-9) + 1e-6: return tris, 0, False        # not planar
        e1, e2 = vt[0], vt[1]; uv = np.stack([(P - c) @ e1, (P - c) @ e2], 1)
        try: idx = earcut.triangulate_float64(uv, np.array([len(uv)], dtype=np.uint32))
        except Exception: return tris, 0, False
        for k in range(0, len(idx), 3): out.append((P[idx[k]], P[idx[k + 1]], P[idx[k + 2]]))
        caps += 1
    return out, caps, True


def tjunction_closed(tris, tol=5e-5):
    """geometric watertightness (orientation-free): boundary edges are split at boundary vertices that lie on them (T-junctions between faces sampled differently); closed when every piece then occurs an even number of times"""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    pts = {}; ec = collections.Counter()
    for t in tris:
        ks = [key(p) for p in t]
        for p, k in zip(t, ks): pts[k] = np.asarray(p, float)
        if len(set(ks)) < 3: continue
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]; ec[(min(a, b), max(a, b))] += 1
    bd = [e for e, c in ec.items() if c % 2]
    if not bd: return True
    vs = sorted({k for e in bd for k in e}); P = np.array([pts[k] for k in vs]); idx = {k: i for i, k in enumerate(vs)}
    out = collections.Counter()
    for a, b in bd:
        A = P[idx[a]]; B = P[idx[b]]; d = B - A; L2 = float(d @ d)
        if L2 < 1e-18: continue
        t_ = (P - A) @ d / L2; Q = A + np.outer(t_, d); dist = np.linalg.norm(P - Q, axis=1)
        sel = list(np.nonzero((dist < max(tol * 4, 1e-6)) & (t_ > 1e-6) & (t_ < 1 - 1e-6))[0])
        chain = [idx[a]] + sorted(sel, key=lambda i: t_[i]) + [idx[b]]
        for u_, v_ in zip(chain, chain[1:]): out[(min(u_, v_), max(u_, v_))] += 1
    if all(c % 2 == 0 for c in out.values()): return True
    # curved boundary sampled differently on the two sides: chord/arc deviation only - every unmatched piece must lie within `near` of the other unmatched pieces
    near = 4e-3; segs = [(P[a], P[b]) for (a, b), c in out.items() if c % 2]
    if len(segs) > 2000: return False
    A = np.array([x[0] for x in segs]); B = np.array([x[1] for x in segs]); D = B - A; L2 = np.maximum((D * D).sum(1), 1e-18)
    for i, (p, q) in enumerate(segs):
        for pt in (p, q, (p + q) / 2):
            t_ = np.clip(((pt - A) * D).sum(1) / L2, 0, 1); dist = np.linalg.norm(A + t_[:, None] * D - pt, axis=1); dist[i] = 1e9
            if dist.min() > near: return False
    return True


def nearly_closed(tris, frac=0.12, min_tris=40):
    """True when only a few boundary edges are unmatched (sampling mismatch on trimmed curved faces, not a missing face): <= frac of all edges, both after T-junction welding"""
    if len(tris) < min_tris: return False
    try:
        if tjunction_closed(tris): return True
        no_ = mesh_volume(tris)[2]
        return no_ <= frac * 1.5 * len(tris)
    except Exception: return False

def _fan_uv(kind, ev, uv, n):
    """uv sub-triangles of a coarse triangle with ONE degenerate vertex (ruled surface between a curve and a point: ev(u, v_apex) is the same point for every u).
    The coarse triangle (apex, b, c) covers the patch u in [u_b, u_c] along straight generators; subdividing its uv triangle would follow curves
    u = u_apex + ... instead and cover only part of the patch (2024 Snowdon rect-to-round duct transitions: -10% volume). Returns (m, 3, 2) uv triangles
    with the winding of the input (n x n grid of P(s, t) = (u_b + s (u_c - u_b), v_apex + t (v_b + s (v_c - v_b) - v_apex))), or None."""
    try:
        pole = [float(np.linalg.norm(np.asarray(ev(float(a_), float(b_))) - np.asarray(ev(float(a_) + 0.3, float(b_))))) < 1e-9 for a_, b_ in uv]
    except Exception: return None
    if sum(pole) != 1: return None
    i = pole.index(True); j, k = (i + 1) % 3, (i + 2) % 3
    ub, vb = uv[j]; uc, vc = uv[k]; vp = uv[i][1]
    s = np.linspace(0.0, 1.0, n + 1); out = []
    P = lambda a, b: (ub + s[a] * (uc - ub), vp + s[b] * (vb + s[a] * (vc - vb) - vp))
    for a in range(n):
        for b in range(n):
            q00, q10, q11, q01 = P(a, b), P(a + 1, b), P(a + 1, b + 1), P(a, b + 1)
            # (apex, b, c) = (t=0, s=0..1 at t=1): in (s, t) the input winding is (s=*, t=0) -> (0, 1) -> (1, 1), i.e. clockwise; keep it
            out.append([q00, q01, q11]); out.append([q00, q11, q10])
    T = np.array(out, float)
    return T

def refined_volume(tris, meta, levels=3, tol=5e-5, centroid=False, fid=None):
    """volume of a closed shell with curved faces: orientation from the coarse closed mesh (shared boundary vertices), then every curved
    coarse triangle is subdivided in (u,v) and mapped through its surface; sub-triangles keep the orientation of their coarse parent.
    returns (volume, closed_coarse, area)"""
    if not tris: return 0.0, False, 0.0
    off = np.mean(np.array(tris[0], float), axis=0) * 0 + np.mean(np.array([np.asarray(p, float) for t in tris for p in t]), axis=0)      # work relative to the mesh centre: closure errors are not amplified by a far-away origin
    key = lambda p: (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    vid = {}; T = []; keep = []
    for ti, t in enumerate(tris):
        ids = [vid.setdefault(key(p), len(vid)) for p in t]
        if len(set(ids)) == 3: T.append(ids); keep.append(ti)
    em = collections.defaultdict(list)
    for k, t in enumerate(T):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): em[(min(a, b), max(a, b))].append((k, a, b))
    de = collections.Counter()
    for t in T:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): de[(a, b)] += 1
    balanced = bool(T) and all(de[(b, a)] == c for (a, b), c in de.items())      # winding already consistent (non-manifold touching edges allowed)
    flip = [False] * len(T) if balanced else [None] * len(T)
    comp = [0] * len(T)
    if fid is not None and not balanced:
        # face-level orientation: triangles of one face already agree, so propagate across inter-face edges that exactly two triangles share (non-manifold chords are ignored)
        fk = [fid[ti] for ti in keep]; fadj = collections.defaultdict(list)
        for e, lst in em.items():
            if len(lst) != 2: continue
            (k1, a1, b1), (k2, a2, b2) = lst
            if fk[k1] == fk[k2]: continue
            fadj[fk[k1]].append((fk[k2], a1 == a2)); fadj[fk[k2]].append((fk[k1], a1 == a2))       # same traversal direction -> relative flip
        ff = {}; fc = {}
        for f0 in dict.fromkeys(fk):
            if f0 in ff: continue
            ff[f0] = False; fc[f0] = f0; st = [f0]
            while st:
                f = st.pop()
                for g, rel in fadj[f]:
                    if g not in ff: ff[g] = ff[f] ^ rel; fc[g] = f0; st.append(g)
        # absolute sign of every BFS component from the surfaces' own normals: with orientFlag 1 the parametric normal su x sv points out of the solid, so the winding of a face either agrees with it or not
        ag = {}
        for k_, ti_ in enumerate(keep):
            f_ = fk[k_]
            if f_ in ag and len(ag[f_]) >= 3: continue
            kind_, ev_, uvs_ = meta[ti_]
            if ev_ is None: continue
            try:
                t_ = [np.asarray(x, float) for x in tris[ti_]]; nt = np.cross(t_[1] - t_[0], t_[2] - t_[0])
                if np.linalg.norm(nt) < 1e-14: continue
                u_, v_ = np.mean(np.array(uvs_, float), 0); h_ = 1e-5
                ns_ = np.cross((np.asarray(ev_(u_ + h_, v_)) - np.asarray(ev_(u_ - h_, v_))), (np.asarray(ev_(u_, v_ + h_)) - np.asarray(ev_(u_, v_ - h_))))
                if np.linalg.norm(ns_) < 1e-14: continue
                ag.setdefault(f_, []).append(1 if float(nt @ ns_) > 0 else -1)
            except Exception: continue
        votes = collections.defaultdict(int)
        for f_, lst in ag.items():
            sg = 1 if sum(lst) >= 0 else -1; votes[fc[f_]] += (sg if not ff[f_] else -sg)
        for f_ in list(ff):
            if votes.get(fc[f_], 0) < 0: ff[f_] = not ff[f_]
        flip = [ff[f] for f in fk]; comp = [fc[f] for f in fk]
    for s0 in range(len(T)):
        if flip[s0] is not None: continue
        flip[s0] = False; comp[s0] = s0; stack = [s0]
        while stack:
            k = stack.pop(); t = T[k]
            if flip[k]: t = [t[0], t[2], t[1]]
            for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                if len(em[(min(a, b), max(a, b))]) != 2: continue
                for (k2, a2, b2) in em[(min(a, b), max(a, b))]:
                    if k2 == k or flip[k2] is not None: continue
                    flip[k2] = (a2 == a and b2 == b); comp[k2] = s0; stack.append(k2)
    closed = balanced or all(len(v) == 2 for v in em.values())
    if not closed:
        try: closed = tjunction_closed(tris, tol)
        except Exception: pass
    vol = 0.0; area = 0.0; csum = np.zeros(3); cv = collections.defaultdict(lambda: [0.0, np.zeros(3), None, None])
    def _acc(k, dv, c3, P3):
        e = cv[comp[k]]; e[0] += dv; e[1] = e[1] + c3
        lo, hi = np.min(P3, 0), np.max(P3, 0); e[2] = lo if e[2] is None else np.minimum(e[2], lo); e[3] = hi if e[3] is None else np.maximum(e[3], hi)
    for k, ti in enumerate(keep):
        kind, ev, uvs = meta[ti]
        if kind == 'plane' or levels <= 0 or ev is None:
            p = [np.asarray(x, float) - off for x in tris[ti]]
            if flip[k]: p = [p[0], p[2], p[1]]
            dv = float(np.dot(p[0], np.cross(p[1], p[2]))) / 6.0; _acc(k, dv, dv * (p[0] + p[1] + p[2]) / 4, np.array(p)); area += float(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0]))) / 2
            continue
        uv = np.array(uvs, float)                                     # (3, 2)
        if kind in ('cone', 'revolution'):                            # a pole vertex (apex, sphere pole) has no meaningful u: take the mean of the other two
            pole = [bool(np.linalg.norm(np.asarray(ev(float(a_), float(b_ + 0.0))) - np.asarray(ev(float(a_ + 0.3), float(b_)))) < 1e-9) for a_, b_ in uv]
            if sum(pole) >= 1:
                p = [np.asarray(x, float) - off for x in tris[ti]]
                if flip[k]: p = [p[0], p[2], p[1]]
                dv = float(np.dot(p[0], np.cross(p[1], p[2]))) / 6.0; _acc(k, dv, dv * (p[0] + p[1] + p[2]) / 4, np.array(p)); area += float(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0]))) / 2
                continue
        if kind in ('cylinder', 'cone', 'revolution'):
            du = max(abs(uv[0][0] - uv[1][0]), abs(uv[1][0] - uv[2][0]), abs(uv[0][0] - uv[2][0]))
            if kind == 'revolution':                                  # a curved profile (torus tube, sphere) needs the same resolution along v
                dv = max(abs(uv[0][1] - uv[1][1]), abs(uv[1][1] - uv[2][1]), abs(uv[0][1] - uv[2][1]))
                if dv > 0.1:
                    try:
                        u_ = float(uv[0][0]); va = float(uv[:, 1].min()); vb = float(uv[:, 1].max()); pa = np.asarray(ev(u_, va)); pb = np.asarray(ev(u_, vb)); pm = np.asarray(ev(u_, (va + vb) / 2))
                        if np.linalg.norm(pm - (pa + pb) / 2) > 1e-6 * max(1.0, np.linalg.norm(pb - pa)): du = max(du, dv)
                    except Exception: pass
            lv = int(min(5, max(1, math.ceil(math.log2(max(du, 1e-9) / 0.1)))))
        else: lv = levels + 1
        T = uv[None, :, :]
        fan = _fan_uv(kind, ev, uv, 2 ** lv) if kind == 'ruled' else None
        if fan is not None: T = fan                                  # ruled fan from a point: the apex has no single u (see _fan_uv)
        else:
          for _ in range(lv):                                        # all four children keep the winding of (a, b, c)
            a_, b_, c_ = T[:, 0], T[:, 1], T[:, 2]; ab, bc, ca = (a_ + b_) / 2, (b_ + c_) / 2, (c_ + a_) / 2
            T = np.concatenate([np.stack([a_, ab, ca], 1), np.stack([ab, b_, bc], 1), np.stack([ca, bc, c_], 1), np.stack([ab, bc, ca], 1)], 0)
        flat = T.reshape(-1, 2); cache = {}; pts = np.empty((len(flat), 3))
        for i, (u, v) in enumerate(flat):
            key = (round(float(u), 10), round(float(v), 10)); pt = cache.get(key)
            if pt is None: pt = cache[key] = ev(float(u), float(v))
            pts[i] = pt
        Q = pts.reshape(-1, 3, 3) - off
        if flip[k]: Q = Q[:, [0, 2, 1], :]
        cr = np.cross(Q[:, 1], Q[:, 2]); dvs = np.einsum('ij,ij->i', Q[:, 0], cr) / 6.0
        _acc(k, float(dvs.sum()), (dvs[:, None] * (Q[:, 0] + Q[:, 1] + Q[:, 2]) / 4).sum(0), Q.reshape(-1, 3))
        area += float(np.linalg.norm(np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]), axis=1).sum()) / 2
    # independent shells (rods, separate bodies in one node) have an arbitrary BFS orientation: each counts positive, unless it sits inside a bigger shell (cavity)
    comps = list(cv.values())
    if __import__("os").environ.get("RV_DEBUG"): print("comps", [(round(c[0], 4), np.round(c[2], 2).tolist(), np.round(c[3], 2).tolist()) for c in comps], balanced)
    for i, (v_i, c_i, lo_i, hi_i) in enumerate(comps):
        sgn = 1.0 if v_i >= 0 else -1.0; inner = False
        if not balanced:
            for j, (v_j, _, lo_j, hi_j) in enumerate(comps):
                if j != i and abs(v_j) > abs(v_i) and (lo_i > lo_j + 1e-6).all() and (hi_i < hi_j - 1e-6).all(): inner = True; break
        w = -1.0 if inner else 1.0
        vol += w * abs(v_i); csum += w * sgn * c_i
    if balanced and len(comps) == 1: vol = comps[0][0]; csum = comps[0][1]
    if centroid: return abs(vol), closed, area, ((csum / vol + off) if vol else off)
    return abs(vol), closed, area


def polymesh_tris(node):
    """GPolyMesh node -> list of triangles (tuples of 3 xyz arrays); quads are split"""
    ft = node.get('m_pFacetedTopology'); ft = _ob(ft) if ft else None
    if not isinstance(ft, dict): return []
    P = ft.get('m_pointsArr'); F = ft.get('m_facetsArr')
    if not P or not F: return []
    P = np.array(P, dtype=float); out = []
    for f in F:
        if len(f) == 3: out.append((P[f[0]], P[f[1]], P[f[2]]))
        elif len(f) == 4: out += [(P[f[0]], P[f[1]], P[f[2]]), (P[f[0]], P[f[2]], P[f[3]])]
        elif len(f) > 4:
            for k in range(1, len(f) - 1): out.append((P[f[0]], P[f[k]], P[f[k + 1]]))
    return out


def select_closed_shell(tris, meta, fidx, tol=5e-5, prio=None):
    """Several Geometry nodes (solid + single-face reference nodes, duplicated faces, zero-area slivers) can lie inside an element bbox.
    Drop degenerate and duplicate faces, then peel faces that own an edge used by only one face until every remaining edge is shared by exactly two.
    returns (tris, meta, closed) - the original input when peeling does not give a closed shell"""
    if not tris: return tris, meta, False
    key = lambda p: (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
    faces = collections.OrderedDict()
    for t, m, f in zip(tris, meta, fidx): faces.setdefault(f, []).append((t, m))
    keep = {}
    seen = set()
    for f, lst in faces.items():
        area = sum(np.linalg.norm(np.cross(np.asarray(t[1]) - np.asarray(t[0]), np.asarray(t[2]) - np.asarray(t[0]))) / 2 for t, _ in lst)
        if area < 1e-9: continue
        sig = (round(area, 6), tuple(sorted({key(p) for t, _ in lst for p in t}))[:6])
        if sig in seen: continue
        seen.add(sig); keep[f] = lst
    def edges_of(lst):
        out = collections.Counter()
        for t, _ in lst:
            ks = [key(p) for p in t]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                if ks[a] != ks[b]: out[frozenset((ks[a], ks[b]))] += 1
        return out
    # a face's own boundary = edges that occur once inside the face's triangulation
    fedges = {f: {e for e, n in edges_of(lst).items() if n == 1} for f, lst in keep.items()}
    # T-junctions: split every face-boundary edge at the vertices (of any face) that lie strictly inside it, so differently sampled neighbours still pair up
    allv = sorted({k for es in fedges.values() for e in es for k in e})
    if allv and sum(len(es) for es in fedges.values()) * len(allv) <= 3_000_000:
        PV = np.array(allv, float) * tol; vi = {k: i for i, k in enumerate(allv)}
        for f, es in list(fedges.items()):
            new = set()
            for e in es:
                a, b = tuple(e); A = PV[vi[a]]; B = PV[vi[b]]; D = B - A; L2 = float(D @ D)
                if L2 < 1e-18: new.add(e); continue
                t_ = (PV - A) @ D / L2; dist = np.linalg.norm(PV - (A + np.outer(t_, D)), axis=1)
                sel = np.nonzero((dist < 4 * tol) & (t_ > 1e-6) & (t_ < 1 - 1e-6))[0]
                chain = [vi[a]] + [int(i) for i in sel[np.argsort(t_[sel])]] + [vi[b]]
                for u_, v_ in zip(chain, chain[1:]): new.add(frozenset((allv[u_], allv[v_])))
            fedges[f] = new
    def peel(kp):
        kp = dict(kp); ch = True
        while ch and kp:
            ch = False; cnt = collections.Counter(e for f in kp for e in fedges[f])
            for f in list(kp):
                if any(cnt[e] == 1 for e in fedges[f]): del kp[f]; ch = True
        return kp
    def n_open(kp):
        cnt = collections.Counter(e for f in kp for e in fedges[f]); return sum(1 for n in cnt.values() if n == 1)
    kp0 = None
    if prio:
        # the displayed solid's faces carry a flag bit: try them alone, then add the fewest unflagged faces that close the remaining gaps
        pk = {f: l for f, l in keep.items() if prio.get(f)}
        if pk and tjunction_closed([t for l in pk.values() for t, _ in l], tol): kp0 = pk
        elif pk:
            cur = dict(pk); best = n_open(cur)
            while best > 0:
                cnt = collections.Counter(e for f in cur for e in fedges[f]); opn = {e for e, n in cnt.items() if n == 1}
                cands = [f for f in keep if f not in cur and fedges[f] & opn]
                if not cands: break
                scored = sorted(((n_open({**cur, f: keep[f]}), f) for f in cands))
                if scored[0][0] >= best: break
                best = scored[0][0]; cur[scored[0][1]] = keep[scored[0][1]]
            if best == 0 and cur: kp0 = cur
    n_all = len(keep); open_all = n_open(keep); n_edges_all = len({e for f in keep for e in fedges[f]})
    if kp0 is not None: keep = kp0
    else: keep = peel(keep)
    if not keep: return tris, meta, False
    # a nearly closed surface (terrain, large sites) loses most of its faces to peeling and leaves a tiny closed fragment: keep the whole thing instead
    if kp0 is None and len(keep) < 0.5 * n_all and open_all <= 0.05 * max(n_edges_all, 1): return tris, meta, False
    cnt = collections.Counter(e for f in keep for e in fedges[f])
    closed = all(n == 2 for n in cnt.values()) or kp0 is not None
    if not closed: return tris, meta, False
    out_t = [t for lst in keep.values() for t, _ in lst]; out_m = [m for lst in keep.values() for _, m in lst]; out_f = [f for f, lst in keep.items() for _ in lst]
    select_closed_shell.last_fidx = out_f
    return out_t, out_m, True


def volume_by_node(tris, meta, nid, levels=3, centroid=False, fid=None):
    """volume of an assembly: every Geometry node (body) is oriented and measured on its own (touching bodies make shared edges non-manifold in a joint mesh).
    returns (volume, closed_all, area, n_nodes)"""
    groups = collections.OrderedDict()
    for i, n in enumerate(nid): groups.setdefault(n, []).append(i)
    vol = area = 0.0; closed_all = True; csum = np.zeros(3); closed_keys = set()
    for n, idx in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if n >= 10**9: continue                                  # faceted meshes (GPolyMesh: clearance boxes, terrain TINs) are not solids of the element: no volume/area
        t = [tris[i] for i in idx]
        m = [meta[i] for i in idx] if meta and len(meta) == len(tris) else None
        if m and all(ev is not None or k == 'plane' for k, ev, _ in m):
            try: v, c, a, cc = refined_volume(t, m, levels=levels, centroid=True, fid=[fid[i] for i in idx] if fid is not None else None)
            except Exception: v, c, _, a = mesh_volume(t); cc = _mesh_centroid(t)
        else:
            v, c, _, a = mesh_volume(t); cc = _mesh_centroid(t)
        if not c:
            vk = {tuple(int(round(x / 5e-5)) for x in p) for tr in t for p in tr}
            Pn = np.array(t, float).reshape(-1, 3); sv = np.linalg.svd(Pn - Pn.mean(0), compute_uv=False)
            if sv[-1] < 1e-6 * max(sv[0], 1e-9): continue            # single planar face (layer interface / reference face): bounds no volume
            if closed_keys and vk <= closed_keys:                  # reference faces duplicating a closed body's faces (every corner already belongs to a closed node): drop
                continue
            t2, ncap, okh = heal_open(t)
            if okh and ncap:
                v2, c2, _, a2 = mesh_volume(t2)
                if c2: v, c, a = v2, True, a2
        else: closed_keys |= {tuple(int(round(x / 5e-5)) for x in p) for tr in t for p in tr}
        if not c and nearly_closed(t, 0.12, 40): c = True       # a handful of unmatched boundary edges (sampling mismatch on trimmed curved faces, terrain) does not change the volume
        if not c: closed_all = False
        vol += v; area += a; csum += v * np.asarray(cc)
    if centroid: return vol, closed_all, area, len(groups), (csum / vol if vol else np.zeros(3))
    return vol, closed_all, area, len(groups)


def _mesh_centroid(tris):
    """volume centroid of a (consistently oriented or not) closed triangle mesh: tetrahedra against the origin with the BFS-free abs trick are unreliable, so use signed volumes"""
    v = np.zeros(3); tot = 0.0
    for t in tris:
        a, b, c = [np.asarray(x, float) for x in t]; dv = float(np.dot(a, np.cross(b, c))) / 6.0; tot += dv; v += dv * (a + b + c) / 4
    return v / tot if tot else v
