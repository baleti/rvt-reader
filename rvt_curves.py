"""Evaluators for decoded Revit GCurve nodes (line, arc, ellipse, Hermite spline, NURBS, helix, offset curve). Units feet."""
import math
import numpy as np

def _ob(x): return x.get('obj', x) if isinstance(x, dict) else x
def _v(x): return np.array([float(a) for a in x], dtype=float)

def kind(c):
    c = _ob(c)
    if not isinstance(c, dict): return None
    if 'm_NodeArray' in c: return 'hermite'
    if 'm_Knots' in c: return 'nurbs'
    if 'm_pitchOver2PI' in c: return 'helix'
    if 'm_oBaseCurve' in c: return 'offset'
    if 'm_xLen' in c: return 'ellipse'
    if 'm_radius' in c and 'm_center' in c: return 'arc'
    if 'm_dirVec' in c: return 'line'
    return None

def _hermite(c):
    nodes = [_ob(n) for n in (c.get('m_NodeArray') or []) if isinstance(_ob(n), dict)]
    T = np.array([float(n['m_iParametr']) for n in nodes]); P = np.array([_v(n['m_iPoint']) for n in nodes]); M = np.array([_v(n['m_iTangent']) for n in nodes])
    def f(t):
        i = int(np.clip(np.searchsorted(T, t, side='right') - 1, 0, len(T) - 2)); h = T[i + 1] - T[i]; s = (t - T[i]) / h
        h00 = 2 * s**3 - 3 * s**2 + 1; h10 = s**3 - 2 * s**2 + s; h01 = -2 * s**3 + 3 * s**2; h11 = s**3 - s**2
        return h00 * P[i] + h10 * h * M[i] + h01 * P[i + 1] + h11 * h * M[i + 1]
    return f, float(T[0]), float(T[-1])

def _nurbs(c):
    deg = int(c['m_Degree']); K = np.array([float(k) for k in c['m_Knots']])
    cp = []
    for p in c['m_ctrlPoints']:
        p = _ob(p)
        if isinstance(p, dict):
            xyz = None
            for k in ('m_xyz', 'm_pnt', 'm_point', 'm_pt'):
                if k in p: xyz = _v(p[k]); break
            w = float(p.get('m_weight', p.get('m_w', 1.0)))
            if xyz is None:
                vals = [v for v in p.values() if isinstance(v, list) and len(v) == 3]
                xyz = _v(vals[0]) if vals else np.zeros(3)
            cp.append((xyz, w))
        else: cp.append((_v(p), 1.0))
    X = np.array([a for a, _ in cp]); W = np.array([w for _, w in cp])
    def basis(i, k, t):
        if k == 0: return 1.0 if (K[i] <= t < K[i + 1]) or (t == K[-1] and K[i] < K[i + 1] == K[-1]) else 0.0
        a = 0.0; b = 0.0
        if K[i + k] > K[i]: a = (t - K[i]) / (K[i + k] - K[i]) * basis(i, k - 1, t)
        if K[i + k + 1] > K[i + 1]: b = (K[i + k + 1] - t) / (K[i + k + 1] - K[i + 1]) * basis(i + 1, k - 1, t)
        return a + b
    def f(t):
        N = np.array([basis(i, deg, t) for i in range(len(X))]) * W
        s = N.sum()
        return (N[:, None] * X).sum(0) / s if s else X[0]
    return f, float(K[deg]), float(K[len(X)])

def curve_fn(c):
    """-> (f(t) -> xyz ndarray, t0, t1) or None"""
    c = _ob(c); k = kind(c)
    if k is None: return None
    t0, t1 = [float(a) for a in c.get('m_endParams', (0.0, 1.0))]
    if k == 'line':
        o = _v(c['m_origin']); d = _v(c['m_dirVec']); return (lambda t: o + t * d), t0, t1
    if k == 'arc':
        ce = _v(c['m_center']); x = _v(c['m_xVec']); y = _v(c['m_yVec']); r = float(c['m_radius'])
        return (lambda t: ce + r * math.cos(t) * x + r * math.sin(t) * y), t0, t1
    if k == 'ellipse':
        ce = _v(c['m_center']); x = _v(c['m_xVec']); y = _v(c['m_yVec']); a = float(c['m_xLen']); b = float(c['m_yLen'])
        return (lambda t: ce + a * math.cos(t) * x + b * math.sin(t) * y), t0, t1
    if k == 'hermite':
        f, a, b = _hermite(c); return f, (t0 if 'm_endParams' in c else a), (t1 if 'm_endParams' in c else b)
    if k == 'nurbs':
        f, a, b = _nurbs(c); return f, (t0 if 'm_endParams' in c else a), (t1 if 'm_endParams' in c else b)
    if k == 'helix':
        bp = _v(_ob(c['m_basePnt'])) if not isinstance(c['m_basePnt'], list) else _v(c['m_basePnt'])
        def vec(n): v = c[n]; v = _ob(v); return _v(v) if isinstance(v, list) else _v(list(v.values())[0])
        x = vec('m_xVec'); y = vec('m_yVec'); z = vec('m_zVec'); r = float(c['m_radius']); p = float(c['m_pitchOver2PI'])
        return (lambda t: bp + r * math.cos(t) * x + r * math.sin(t) * y + p * t * z), t0, t1
    if k == 'offset':
        base = curve_fn(c['m_oBaseCurve']); ref = _v(c['m_referenceVector']) if isinstance(c.get('m_referenceVector'), list) else None; d = float(c['m_signedOffsetDistance'])
        if base is None or ref is None: return None
        f0, a, b = base
        def f(t, h=1e-5):
            tan = f0(t + h) - f0(t - h); n = np.cross(tan, ref); n = n / (np.linalg.norm(n) or 1.0); return f0(t) + d * n
        return f, a, b
    return None

def sample(c, n=24):
    fn = curve_fn(c)
    if fn is None: return None
    f, a, b = fn
    return [f(a + (b - a) * i / n) for i in range(n + 1)]
