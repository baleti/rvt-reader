import sys, os, pickle
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_entities as E, rvt_expr as X, eval_gt as G, rvt_famparams as F
rvt, tsv, out = sys.argv[1:4]
x = E.extract(rvt, want_all=True); Egt, P = G.load_gt(tsv)
lv = {}
for (eid, c), r in x['recs'].items():
    if c == 'Level':
        o = E.S_(r['fields'], 'm_pSurface', 'm_origin')
        if o: lv[eid] = o[2]
cap = F.captions(x['recs']); byid = {}
for (eid, c), r in x['recs'].items(): byid.setdefault(eid, r)
rows = []
for (eid, c), r in x['recs'].items():
    ps = [(b, nm, stg, v) for b, nm, stg, v in P.get(eid, []) if stg == 'Double' and v != '']
    if not ps: continue
    lf = X.leaves(r['fields'], lv)
    sid = F.S_(r['fields'], 'm_pInstanceInfo', 'm_symbolId')
    sym = byid.get(int(sid), {}).get('fields') if sid is not None else None
    for k, (v0, vi, vs, ve) in F.named_values(r['fields'], cap, sym).items():
        if isinstance(v0, (int, float)): lf['P:' + k] = float(v0)
    h = x['eh'].get(eid) or {}
    cid = h.get('m_categroryId'); cid = None if cid is None else int(cid)
    if cid is not None and cid >= 1 << (8 * x['W'] - 1): cid -= 1 << (8 * x['W'])
    rows.append((c, eid, lf, ps, cid))
pickle.dump(rows, open(out, 'wb'))
print(rvt, len(rows))
