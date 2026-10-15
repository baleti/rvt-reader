import sys, json, collections, math
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_cache, eval_gt as G, rvt_map2 as M
pairs = json.load(open('train_pairs.json'))
tot = collections.Counter(); bad = collections.Counter(); ex = {}
for rvt, tsv in pairs:
    d = rvt_cache.get(rvt); E, P = G.load_gt(tsv); W = 8 if 'Identifier' in d['cls_names'] and int(rvt.split('/')[1]) >= 2024 else 4
    for eid, e in E.items():
        r = d['last'].get(eid)
        if not r: continue
        ps = G.params_of(r, W)          # {bip: (kind, value)}
        gt = {b: (stg, v) for b, nm, stg, v in P.get(eid, []) if b != -1}
        for bip, (kind, val) in ps.items():
            if bip not in gt: tot['stored_not_in_revit'] += 1; continue
            stg, gv = gt[bip]; tot[stg] += 1
            if not M.eqv(val if not isinstance(val, dict) else val.get('m_id', -1), stg, gv):
                bad[stg] += 1; ex.setdefault((stg, r['class'], bip), (eid, val, gv))
print('stored parameter values compared:', {k: v for k, v in tot.items()}); print('mismatches:', dict(bad))
for k, v in list(ex.items())[:12]: print(k, v)
