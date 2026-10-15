"""IfcGUID per element from the file alone: stored string param (-1019000) if present, else owner-chain root's, else derived from UniqueId."""
import os, sys, struct
os.environ.setdefault('RVT_GEOM', '1')
import rvt_inventory as I, rvt_scan as S, rvt_uid, ifcguid

IFC_PID = (-1019000) & 0xffffffffffffffff

def _walk_strings(x, out):
    if isinstance(x, dict):
        if 'm_paramSet' in x:
            for e in x['m_paramSet']:
                if not isinstance(e, dict): continue
                pid = e.get('m_paramId'); v = e.get('m_value')
                if pid is not None and (int(pid) & 0xffffffffffffffff) in (IFC_PID, (-1019000) & 0xffffffff) and isinstance(v, str) and v: out.append(v)
        for b in x.values(): _walk_strings(b, out)
    elif isinstance(x, (list, tuple)):
        for b in x: _walk_strings(b, out)

def stored(recs):
    """{eid: last stored IfcGUID string among all records}"""
    out = {}
    for eid, rl in recs.items():
        for r in rl:
            s = []; _walk_strings(r['fields'], s)
            if s: out[eid] = s[-1]
    return out

def ifc_guids(path, recs=None):
    if recs is None: recs = I.inventory(path)[2]
    st = stored(recs); klass = {e: rl[-1]['class'] for e, rl in recs.items()}; uid = rvt_uid.unique_ids(path); own = S.owners(path); out = {}
    def get(e, n=0):
        if e in out: return out[e]
        v = st.get(e)
        if v is None:
            o = own.get(e)
            if o is not None and n < 12 and klass.get(e, '').endswith('CenterLine') and (o in uid or o in st): v = get(o, n + 1)
            if v is None and e in uid: v = ifcguid.from_unique(uid[e])
        if v is not None: out[e] = v
        return v
    for e in set(uid) | set(st): get(e)
    return out
