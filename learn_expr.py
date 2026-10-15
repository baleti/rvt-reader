import sys, os, pickle, json, collections
sys.path.insert(0, '/home/user1/rvt-research')
import numpy as np, rvt_expr as X
from multiprocessing import Pool
tr = [int(a) for a in sys.argv[1].split(',')]
rows = []
for i in tr: rows += pickle.load(open(f'exprdata2/{i}.pkl', 'rb'))
grp = collections.defaultdict(list)
for c, eid, lf, ps, cat in rows:
    for b, nm, stg, v in ps:
        try: grp[(c, cat, b, nm)].append((lf, float(v)))
        except ValueError: pass
def work(item):
    (c, cat, b, nm), items = item
    if len(items) < 8: return None
    import random
    full = items
    if len(items) > 200: items = random.Random(1).sample(items, 200)
    if len({round(v, 9) for _, v in full}) < 3: return None
    ys = np.array([v for _, v in items]); 
    cnt = collections.Counter(k for lf, _ in items for k in lf)
    names = [k for k, n in cnt.items() if n >= 0.5 * len(items)][:45]
    Xm = np.array([[lf.get(k, np.nan) for k in names] for lf, _ in items])
    r = X.search(Xm, names, ys)
    if not r: return ((c, cat, b, nm), len(items), None)
    s, t, sz = r[0]
    # verify on all rows
    ok = tot = 0
    for lf, v in full:
        x = X.teval(t, lf); tot += 1
        if x is not None and abs(x - v) <= 1e-6 * max(1, abs(v)): ok += 1
    return ((c, cat, b, nm), len(full), dict(matches=ok, tree=t, size=sz, rows=tot))
if __name__ == '__main__':
    items = sorted(grp.items(), key=lambda z: -len(z[1]))
    out = {}
    with Pool(int(os.environ.get('NP', 4))) as p:
        for res in p.imap_unordered(work, items, chunksize=1):
            if res is None: continue
            (c, cat, b, nm), n, r = res
            if r: out.setdefault(c, {}).setdefault(str(cat), {})[str(b)] = dict(name=nm, n=n, **r)
    json.dump(out, open(sys.argv[2], 'w'))
    print(sum(len(d) for v in out.values() for d in v.values()), 'rules over', len(out), 'classes;', len(items), 'groups')
