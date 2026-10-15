import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_cache, rvt_map as M, eval_gt as G
mp = json.load(open(sys.argv[1]))['mapping']; pairs = [a.split(':') for a in sys.argv[2:]]
tot = collections.Counter(); expl = collections.Counter(); names = collections.Counter(); bycls = collections.Counter()
for rvt, tsv in pairs:
    d = rvt_cache.get(rvt); E, P = G.load_gt(tsv)
    for eid, e in E.items():
        r = d['last'].get(eid)
        if not r: continue
        K = r['class']; f = {}; M.flat(r['fields'], '', f); ps = G.params_of(r, 4); m = mp.get(K, {})
        for bip, nm, stg, v in P.get(eid, []):
            if v == '': continue
            kind = 'builtin' if bip != -1 else 'nonbuiltin'
            tot[kind] += 1
            how = None
            if bip in ps and M.eq(ps[bip][1], stg, v, 4): how = 'paramset'
            elif str(bip) in m and m[str(bip)]['path'] in f and M.eq(f[m[str(bip)]['path']], stg, v, 4): how = 'field-map'
            if how: expl[(kind, how)] += 1
            else: names[(kind, nm)] += 1; bycls[(kind, e['cls'])] += 1
print('totals', dict(tot)); print('explained', dict(expl))
print('top unexplained builtin names:', [(n, c) for (k, n), c in names.most_common(40) if k == 'builtin'][:25])
print('top unexplained non-builtin names:', [(n, c) for (k, n), c in names.most_common(60) if k == 'nonbuiltin'][:12])
