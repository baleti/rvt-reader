"""Learn arithmetic expressions over a record's numeric leaves that reproduce Revit's computed Double parameters."""
import sys, os, math, itertools, collections, pickle, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('RVT_GEOM', '1')
import numpy as np
import rvt_geom as Gm

SKIP = {'m_geomSteps', 'm_pGeomTable', 'm_cellList', 'm_docAccess', 'm_pParamValueSetAString', 'm_pParamValueSetInt', 'm_pParamValueSetDouble', 'm_pParamValueSetElementId', 'm_pThumbnail', 'm_preview'}

def leaves(f, lvl_elev=None, maxn=80):
    out = {}
    def num(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    def w(o, p, d):
        if len(out) >= maxn or d > 7: return
        if isinstance(o, dict):
            for k, v in o.items():
                if k in SKIP or k in ('handle', 'ptr', 'ref'): continue
                if k == 'obj': w(v, p, d + 1)
                else: w(v, p + '.' + k if p else k, d + 1)
        elif isinstance(o, (list, tuple)):
            if 0 < len(o) <= 4 and all(num(a) for a in o):
                for i, a in enumerate(o): out[f'{p}[{i}]'] = float(a)
            elif len(o) <= 3:
                for i, a in enumerate(o): w(a, f'{p}[{i}]', d + 1)
        elif num(o): out[p] = float(o)
    w(f, '', 0)
    cu = Gm.primary_curve(f)
    if cu is not None:
        L = Gm.curve_length(cu)
        if L is not None: out['CL'] = L
        if Gm.is_line(cu):
            o = cu['m_origin']; dv = cu['m_dirVec']; t0, t1 = cu['m_endParams']
            out['Z0'] = o[2] + dv[2] * t0; out['Z1'] = o[2] + dv[2] * t1
            out['X0'] = o[0] + dv[0] * t0; out['Y0'] = o[1] + dv[1] * t0; out['X1'] = o[0] + dv[0] * t1; out['Y1'] = o[1] + dv[1] * t1
    if lvl_elev:
        for k in ('m_assocLevelId', 'm_idLevelStart', 'm_levelId', 'm_idLevel', 'm_baseLevelId', 'm_idBaseLevel'):
            v = f.get(k)
            if v is not None and int(v) in lvl_elev: out['LV'] = lvl_elev[int(v)]; break
    return out

CONST = {'1': 1.0, '2': 2.0, 'half': 0.5, 'pi': math.pi, 'pi/4': math.pi / 4, '12': 12.0}

def tstr(t):
    if isinstance(t, str): return t
    return '(%s %s %s)' % (tstr(t[1]), t[0], tstr(t[2]))

def teval(t, d):
    if isinstance(t, str):
        if t in CONST: return CONST[t]
        return d.get(t)
    a = teval(t[1], d); b = teval(t[2], d)
    if a is None or b is None: return None
    op = t[0]
    try:
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '*': return a * b
        if op == '/': return a / b
    except ZeroDivisionError: return None

def search(X, names, y, tol=1e-6, min_frac=0.9, max_cands=5):
    """X: [n, m] leaf matrix (nan = missing); y: [n] targets. Returns [(matches, tree, size)] best first (fewest nodes among ties)."""
    n, m = X.shape
    ok = ~np.isnan(y); n_ok = int(ok.sum())
    if n_ok == 0: return []
    X = X[ok]; y = y[ok]; tolv = tol * np.maximum(1.0, np.abs(y)); need = min_frac * n_ok
    keep = [j for j in range(m) if not np.isnan(X[:, j]).all()]
    nm1 = [names[j] for j in keep] + list(CONST); V1 = np.concatenate([X[:, keep].T, np.array([np.full(len(y), v) for v in CONST.values()])], axis=0)   # [k1, n]
    def sc(V):
        with np.errstate(all='ignore'): return np.sum(np.abs(V - y) <= tolv, axis=-1)
    best = []
    def offer(t, size, s):
        if s >= need: best.append((int(s), -size, t))
    s1 = sc(V1)
    for i in np.nonzero(s1 >= need)[0]: offer(nm1[i], 1, s1[i])
    k1 = len(nm1); ops = (('+', np.add), ('-', np.subtract), ('*', np.multiply), ('/', np.divide)); L2n = []; L2v = []
    with np.errstate(all='ignore'):
        for opn, f in ops:
            for i in range(k1):
                V = f(V1[i][None, :], V1)            # [k1, n]: leaf i (op) every leaf
                s = sc(V)
                for j in np.nonzero(s >= need)[0]: offer((opn, nm1[i], nm1[j]), 2, s[j])
                fin = np.isfinite(V).sum(axis=1) >= need
                for j in np.nonzero(fin)[0]:
                    if (opn in '+*' and j < i): continue
                    L2n.append((opn, nm1[i], nm1[j])); L2v.append(V[j])
        if best and max(b[0] for b in best) >= 0.99 * n_ok: return [(s, t, -sz) for s, sz, t in sorted(best, key=lambda z: (-z[0], -z[1]))[:max_cands]]
        T = np.array(L2v)    # [K, n]
        sc_n = []; sc_v = []
        for kn, kv in (('2', 2.0), ('pi', math.pi), ('half', 0.5), ('pi/4', math.pi / 4)):
            for i in range(len(nm1) - len(CONST)):
                sc_n.append(('*', kn, nm1[i])); sc_v.append(kv * V1[i])
        VL = np.concatenate([V1, np.array(sc_v)], axis=0) if sc_v else V1; nmL = nm1 + sc_n
        for opn, f in ops:
            for j in range(len(nmL)):
                a = VL[j][None, :]
                for flip in ((False, True) if opn in '-/' else (False,)):
                    V = f(a, T) if flip else f(T, a)
                    s = sc(V)
                    for q in np.nonzero(s >= need)[0]: offer((opn, nmL[j], L2n[q]) if flip else (opn, L2n[q], nmL[j]), 3, s[q])
    return [(s, t, -sz) for s, sz, t in sorted(best, key=lambda z: (-z[0], -z[1]))[:max_cands]]
