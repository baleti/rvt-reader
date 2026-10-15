import sys, os, collections, json
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_params as RP, rvt_map2 as M, eval_gt as G
rvt, tsv = sys.argv[1:3]
p = RP.params(rvt); E, P = G.load_gt(tsv)
tot = ok = bad = 0; by = collections.Counter(); byok = collections.Counter(); wrong = collections.Counter()
for eid, e in E.items():
    r = p.get(eid)
    for b, nm, stg, v in P.get(eid, []):
        if v == '' or b == -1: continue
        tot += 1; by[stg] += 1
        if not r or nm not in r['params']: continue
        x = r['params'][nm]
        if M.eqv(x, stg, v) or (isinstance(x, str) and x == v): ok += 1; byok[stg] += 1
        else: bad += 1; wrong[(r['class'], nm)] += 1
print(os.path.basename(rvt), f'GT params {tot}: correct {ok} ({100*ok/tot:.1f}%), wrong {bad}, precision {100*ok/max(ok+bad,1):.1f}%', {k: f'{byok[k]}/{by[k]}' for k in by}, wrong.most_common(4))
