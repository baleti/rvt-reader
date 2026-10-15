import sys, os, json, collections
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_params as RP, rvt_map2 as M, eval_gt as G
rvt, tsv = sys.argv[1:3]
if os.environ.get('SKIP_EXISTING') and os.path.exists(os.environ.get('POUT_DIR', 'pout') + '/%s.json' % os.path.basename(rvt)): sys.exit(0)
p = RP.params(rvt); E, P = G.load_gt(tsv)
cnt = collections.Counter(); ex = {}
for eid, e in E.items():
    r = p.get(eid)
    for b, nm, stg, v in P.get(eid, []):
        if v == '' or b == -1: continue
        cls = r['class'] if r else '<none:%s>' % e['cls']
        st = 'norec'
        if r:
            key = '%s|%s|%s' % (nm, stg, b) if ('%s|%s|%s' % (nm, stg, b)) in r['params'] else (nm + '|' + stg if (nm + '|' + stg) in r['params'] else nm)      # parameter-id key first: Revit has distinct parameters with the same name and storage (view Family -1012109 / -1139999)
            if key in r['params']:
                x = r['params'][key]
                st = 'ok' if (M.eqv(x, stg, v) or (isinstance(x, str) and x == v)) else 'wrong'
                if st == 'wrong' and stg == 'Double' and isinstance(x, (int, float)):
                    try:
                        g = float(v)
                        if abs(x - g) <= 1e-4 * max(abs(g), 1e-6): st = 'approx'          # geometry-derived value within 0.01% (curved bodies): reported separately, never as exact
                    except ValueError: pass
            else: st = 'missing'
        cnt[(cls, e['cls'], b, nm, stg, st)] += 1
        if st != 'ok': ex.setdefault((cls, b, nm, stg, st), (eid, v[:60], str(r['params'].get(nm))[:60] if r else None))
POUT = os.environ.get('POUT_DIR', 'pout'); os.makedirs(POUT, exist_ok=True)
out = [[list(k), n] for k, n in cnt.items()]
json.dump({'file': os.path.basename(rvt), 'rows': out, 'ex': [[list(k), v] for k, v in ex.items()]}, open(POUT + '/%s.json' % os.path.basename(rvt), 'w'))
print(os.path.basename(rvt), sum(n for k, n in cnt.items() if k[5] == 'ok'), sum(cnt.values()))
