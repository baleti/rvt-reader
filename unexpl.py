import sys, json, collections
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_map2 as M, rvt_cache, eval_gt as G
pairs = json.load(open('train_pairs.json')); te = [pairs[i] for i in (4, 6, 9)]
mapping = json.load(open('map2_train.json'))['mapping']
names = collections.Counter(); byst = collections.Counter(); ex = {}
for rvt, tsv in te:
    d = rvt_cache.get(rvt); E, P = G.load_gt(tsv); src = M.Src(d['last'], d.get('hdr'))
    for eid, e in E.items():
        r = d['last'].get(eid)
        if not r: continue
        mp = mapping.get(r['class'], {})
        for b, nm, stg, v in P.get(eid, []):
            if v == '' or b == -1: continue
            c = mp.get(str(b)); good = False
            if c:
                x = M.resolve(src, eid, c['via'], c['path'])
                good = x is not None and M.eqv(x, stg, v)
            if not good: names[(nm, stg)] += 1; ex.setdefault((nm, stg), (r['class'], eid, v))
tot = sum(names.values()); print('unexplained', tot)
for (nm, stg), n in names.most_common(30): print(f'{n:7d} {100*n/tot:5.1f}%  {nm} [{stg}]  e.g. {ex[(nm,stg)]}')
