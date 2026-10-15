import sys, pickle, json, collections, math
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_expr as X
rules = json.load(open(sys.argv[1])); import rvt_expr as _X
def _leaves(t): return [t] if isinstance(t, str) and t not in _X.CONST else ([] if isinstance(t, str) else [l for a in t[1:] for l in _leaves(a)])
MINF = float(sys.argv[3]) if len(sys.argv) > 3 else 0.97
rules = {c: {k: {b: r for b, r in d.items() if _leaves(r['tree']) and r['matches'] >= MINF * r['rows']} for k, d in dd.items()} for c, dd in rules.items()}
te = [int(a) for a in sys.argv[2].split(',')]
def tup(t): return tuple(tup(a) for a in t) if isinstance(t, list) else t
ok = bad = nocov = tot = 0; byn = collections.Counter(); wrong = collections.Counter(); cov = collections.Counter()
for i in te:
    for c, eid, lf, ps, cat in pickle.load(open(f'exprdata2/{i}.pkl', 'rb')):
        for b, nm, stg, v in ps:
            try: y = float(v)
            except ValueError: continue
            tot += 1
            r = rules.get(c, {}).get(str(cat), {}).get(str(b))
            if not r: nocov += 1; byn[(c, nm)] += 1; continue
            x = X.teval(tup(r['tree']), lf)
            if x is None or not math.isfinite(x): nocov += 1; byn[(c, nm)] += 1; continue
            if abs(x - y) <= 1e-6 * max(1, abs(y)): ok += 1
            else: bad += 1; wrong[(c, nm, X.tstr(tup(r['tree'])))] += 1
print(f'doubles {tot}: correct {ok} ({100*ok/tot:.1f}%), wrong {bad}, no rule/leaf {nocov}; precision {100*ok/max(ok+bad,1):.1f}%')
print('worst wrong', wrong.most_common(8)); print('top uncovered', byn.most_common(12))
