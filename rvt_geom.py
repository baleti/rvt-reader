"""Geometry-derived values from decoded records (internal units: feet, radians)."""
import math

def _v(x): return [float(a) for a in x]

def is_line(o): return isinstance(o, dict) and 'm_dirVec' in o and 'm_endParams' in o and 'm_origin' in o
def is_arc(o): return isinstance(o, dict) and 'm_radius' in o and 'm_endParams' in o and 'm_center' in o

def curve_length(o):
    p = o['m_endParams']
    if is_line(o):
        d = _v(o['m_dirVec']); return abs(p[1] - p[0]) * math.sqrt(sum(a * a for a in d))
    if is_arc(o): return (abs(p[1] - p[0]) or 2 * math.pi) * float(o['m_radius'])      # endParams [0, 0] = full circle (Revit Length 2 pi r)
    return None

def find_curves(f, skip=('m_geomSteps', 'm_pGeomTable')):
    """curve objects (line/arc) reachable in a record's fields, document order, without the geometry-step bodies"""
    out = []
    def w(o):
        if isinstance(o, dict):
            if is_line(o) or is_arc(o): out.append(o); return
            for k, v in o.items():
                if k in skip: continue
                w(v)
        elif isinstance(o, list):
            for v in o: w(v)
    w(f); return out

def primary_curve(f):
    for k in ('m_pCurveDriver', 'm_pCurve', 'm_pCrv'):
        if k in f and f[k]:
            c = find_curves(f[k])
            if c: return c[0]
    c = find_curves(f); return c[0] if c else None

# ---- element-level derived Double parameters (feet / radians, Revit internal units) ----
import rvt_famparams as _F

def _g(f, *p):
    return _F.S_(f, *p)

def mep_curve(f, cls, lvl=None):
    """Derived parameters of a straight/arc pipe, duct, conduit, cable tray (RbsPipeCurve, RbsDuctCurve, RbsConduitCurve, CableTray)."""
    out = {}
    cu = primary_curve(f)
    if cu is None: return out
    L = curve_length(cu)
    if L is not None: out['Length'] = L
    s = f.get('m_dOffsetStart'); e = f.get('m_dOffsetEnd'); w = f.get('m_dWidthOrDiameter'); h = f.get('m_dHeight')
    dpm = f.get('m_pDesignPropManager') or {}
    dpm = dpm.get('obj', dpm) if isinstance(dpm, dict) else {}
    od = dpm.get('m_dOuterDiameter')
    if s is not None and e is not None:
        out['Start Middle Elevation'] = s; out['End Middle Elevation'] = e; out['Middle Elevation'] = (s + e) / 2 if s != e and False else s
        half = None
        if cls == 'RbsPipeCurve' or cls == 'RbsConduitCurve': half = (od if od else w) / 2 if (od or w) else None
        elif cls in ('RbsDuctCurve', 'CableTray'): half = h / 2 if h else None
        if half is not None:
            vert = is_line(cu) and abs(cu['m_dirVec'][2]) > 0.999999
            out['Top Elevation'] = max(s, e) + (0 if vert else half); out['Bottom Elevation'] = min(s, e) - (0 if vert else half)
        # end elevations (relative to the reference level, like m_dOffsetStart/End): 'Lower End' = the end with the lower centre line;
        # bottom/top = centre -/+ R k, invert/obvert with the inner radius, k = sqrt(1 - dz^2) (vertical extent of the cross-section of a sloped run)
        idm = dpm.get('m_dInnerDiameter')
        if is_line(cu):
            dv = cu['m_dirVec']; nn = math.sqrt(sum(a * a for a in dv)) or 1.0; k = math.sqrt(max(0.0, 1 - (dv[2] / nn) ** 2))
        else: k = 1.0
        if cls in ('RbsPipeCurve', 'RbsConduitCurve'): Ro = (od or w or 0) / 2; Ri = (idm or w or 0) / 2
        elif cls in ('RbsDuctCurve', 'CableTray'): Ro = Ri = ((h if h else w) or 0) / 2
        else: Ro = Ri = None
        if Ro is not None and (Ro or k < 1e-9):
            lo, hi = min(s, e), max(s, e)
            for nm, z in (('Lower End', lo), ('Upper End', hi)):
                out[nm + ' Centerline Elevation'] = z
                out[nm + ' Bottom Elevation'] = z - Ro * k; out[nm + ' Top Elevation'] = z + Ro * k
                if cls == 'RbsPipeCurve': out[nm + ' Invert Elevation'] = z - Ri * k; out[nm + ' Obvert Elevation'] = z + Ri * k
            out['_end_k'] = k; out['_end_R'] = Ro
        if is_line(cu) and L:
            hz = L * math.sqrt(max(0.0, 1 - cu['m_dirVec'][2] ** 2) / sum(a * a for a in cu['m_dirVec']))
            out['Slope'] = (e - s) / hz if hz > 1e-9 else 0.0
    if cls == 'RbsPipeCurve' and w is not None and L is not None: out['Area'] = math.pi * w * L
    if cls == 'RbsDuctCurve' and w is not None and h is not None and L is not None:
        out['Area'] = 2 * (w + h) * L if abs(w - h) > 0 or True else math.pi * w * L
    if cls in ('RbsDuctCurve', 'CableTray'):
        if w is not None: out['Width'] = w
        if h is not None: out['Height'] = h
    if cls in ('RbsPipeCurve',) and w is not None: out['Diameter'] = w
    if od is not None: out['Outside Diameter'] = od
    if dpm.get('m_dInnerDiameter') is not None: out['Inside Diameter'] = dpm['m_dInnerDiameter']
    return out

def fam_instance(f, lvl):
    out = {}
    z = _g(f, 'm_pInstanceInfo', 'm_Trf', 'm_or')
    lv = None
    for k in ('m_assocLevelId', 'm_idLevelStart', 'm_levelId', 'm_scheduleOnlyLevelId'):
        v = f.get(k)
        if v is not None and int(v) in lvl: lv = lvl[int(v)]; break
    if z is not None and lv is not None: out['Elevation from Level'] = z[2] - lv
    # vertical columns: m_refs = [base level + offset, top level + offset]; Revit's Length = top - base
    refs = f.get('m_refs')
    if isinstance(refs, list) and len(refs) == 2 and f.get('m_bVertical') == 1:
        r0, r1 = (_g(r, 'm_elemId') for r in refs); o0, o1 = (_g(r, 'm_offset') or 0.0 for r in refs)
        if r0 is not None and r1 is not None and int(r0) in lvl and int(r1) in lvl:
            out['Length'] = (lvl[int(r1)] + o1) - (lvl[int(r0)] + o0)
    # beams / braces / slanted columns: the member line (m_pCurveDriver.m_pCrv, a line) gives Length and the end elevations relative to the reference level
    cd = f.get('m_pCurveDriver'); cd = cd.get('obj') if isinstance(cd, dict) else None
    crv = ((cd or {}).get('m_pCrv') or {}); crv = crv.get('obj', crv) if isinstance(crv, dict) else None
    if crv and isinstance(crv.get('m_dirVec'), list) and isinstance(crv.get('m_origin'), list) and isinstance(crv.get('m_endParams'), list) and len(crv['m_endParams']) == 2 and isinstance(cd.get('m_refLevelElev'), float) and abs(cd['m_refLevelElev']) >= 1e20 and abs(crv['m_dirVec'][2]) < 1e-9:
        out['_refelev'] = crv['m_origin'][2]           # member without a reference level (Snowdon 2026 structure): Revit's Reference Level Elevation = the z of its horizontal member line (gt: 932 beams)
    if crv and isinstance(crv.get('m_dirVec'), list) and isinstance(crv.get('m_origin'), list) and isinstance(crv.get('m_endParams'), list) and len(crv['m_endParams']) == 2 and isinstance(cd.get('m_refLevelElev'), float) and abs(cd['m_refLevelElev']) < 1e20:
        o, d_, (t0, t1) = crv['m_origin'], crv['m_dirVec'], crv['m_endParams']
        out.setdefault('Length', t1 - t0)
        out['Start Level Offset'] = o[2] + d_[2] * t0 - cd['m_refLevelElev']; out['End Level Offset'] = o[2] + d_[2] * t1 - cd['m_refLevelElev']
        out['_refelev'] = cd['m_refLevelElev']
    return out
