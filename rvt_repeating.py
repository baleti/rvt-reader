"""Repeating detail components (Revit 'Repeating Detail'): a CurveElem (the path) whose m_data.m_oUserData.m_symbolId is a RepeatingDetailAttributes record
(type 'Brick': spacing, layout, rotation, inside, m_detail = the detail component FamilySymbol) and whose m_number is the repeat count.
repeating_details(file) -> [{'eid','owner_view','type_id','type_name','detail_symbol','spacing','layout','rotation','inside','number','mirrored',
 'path': {'type':'line','p0','p1','dir','length'}, 'boundary': [{'p0','p1'}...] (the repeat envelope: width side, ends), 'placements': [{'origin','xvec','yvec'}...]}]
Each placement is the detail symbol's local frame (symbol x -> xvec = the boundary width direction, symbol y -> yvec = the path direction); symbol curves come from
rvt_elemmesh.element_curves(doc, detail_symbol) (local coordinates). Validated on 2020 Commercial (Typ. Parapet brick, 25 repeats: floor(path length / spacing) = number,
envelope height = (number-1)*spacing + symbol height 0.2223 ft, envelope width = symbol width 0.3021 ft). Only straight paths are placed; other paths get no placements."""
import numpy as np, rvt_materials as RM

def _ob(o): return o.get('obj', o) if isinstance(o, dict) else o
def _line(c):
    c = _ob(c); o = np.array([float(v) for v in c['m_origin']]); d = np.array([float(v) for v in c['m_dirVec']]); t0, t1 = [float(v) for v in c['m_endParams']]
    return o + d * t0, o + d * t1, d

def repeating_details(file):
    ctx = RM._ctx(file); recs = ctx.recs; out = []
    types = {e: r for e, r in recs.items() if r['class'] == 'RepeatingDetailAttributes'}
    if not types: return out
    for e, r in recs.items():
        if r['class'] != 'CurveElem': continue
        f = r['fields']; ud = _ob(((f.get('m_data') or {}).get('m_oUserData')))
        if not isinstance(ud, dict) or 'm_symbolId' not in ud: continue
        tid = RM._eid(ud['m_symbolId'])
        if tid not in types: continue
        tf = types[tid]['fields']; nm = _ob(tf.get('m_symbolInfo') or {}).get('m_name') if isinstance(tf.get('m_symbolInfo'), dict) else None
        spacing = float(tf['m_spacing']); number = int(ud.get('m_number') or 0)
        d = {'eid': e, 'owner_view': RM._eid(f.get('m_ownerDBViewId')), 'type_id': tid, 'type_name': nm, 'detail_symbol': RM._eid(tf['m_detail']), 'spacing': spacing, 'layout': int(tf['m_layout']),
             'rotation': int(tf['m_rotation']), 'inside': bool(tf['m_bInside']), 'number': number, 'mirrored': bool(ud.get('m_bMirrored')), 'path': None, 'boundary': [], 'placements': []}
        try:
            crv = _ob(_ob(f['m_pCurveDriver'])['m_pCrv'])
            if 'm_origin' in crv and 'm_dirVec' in crv and 'm_endParams' in crv and 'm_radius' not in crv:
                p0, p1, dv = _line(crv); d['path'] = {'type': 'line', 'p0': p0.tolist(), 'p1': p1.tolist(), 'dir': dv.tolist(), 'length': float(np.linalg.norm(p1 - p0))}
        except Exception: pass
        for b in (ud.get('m_oBoundary') or []):
            try: p0, p1, dv = _line(b); d['boundary'].append({'p0': p0.tolist(), 'p1': p1.tolist(), 'dir': dv.tolist()})
            except Exception: pass
        if d['path'] and d['boundary']:
            p0 = np.array(d['path']['p0']); yv = np.array(d['path']['dir']); xv = np.array(d['boundary'][0]['dir'])
            d['placements'] = [{'origin': (p0 + yv * spacing * i).tolist(), 'xvec': xv.tolist(), 'yvec': yv.tolist()} for i in range(number)]
        out.append(d)
    return out
