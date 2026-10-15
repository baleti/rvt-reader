"""Family parameters stored per instance (m_pInstParams) / per symbol (m_pParams), named via ParamElem* m_pParamDef.m_caption."""
import os
def S_(o, *p):
    for k in p:
        if isinstance(o, dict):
            if k in o: o = o[k]
            elif 'obj' in o and isinstance(o['obj'], dict) and k in o['obj']: o = o['obj'][k]
            else: return None
        else: return None
    if isinstance(o, dict) and 'obj' in o: o = o['obj']
    return o

def captions(recs):
    """{param element id: caption}"""
    out = {}
    for (eid, c), r in recs.items():
        if c.startswith('ParamElem'):
            cap = S_(r['fields'], 'm_pParamDef', 'm_caption')
            if cap: out[eid] = cap
    return out

def entries(f, key):
    ps = S_(f, key, 'm_params')
    return ps if isinstance(ps, list) else []

def named_values(f, cap, symbol_fields=None):
    """{caption: (m_value, m_int, m_str, m_elemId)} for the instance, with the type's values underneath"""
    out = {}
    for src, key in ((symbol_fields, 'm_pParams'), (f, 'm_pInstParams')):
        if src is None: continue
        for e in entries(src, key):
            if not isinstance(e, dict): continue
            pid = e.get('m_paramId'); nm = cap.get(int(pid)) if pid is not None else None
            if nm: out[nm] = (e.get('m_value'), e.get('m_int'), e.get('m_str'), e.get('m_elemId'))
    return out
