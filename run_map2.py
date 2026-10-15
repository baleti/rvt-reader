import sys, json
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_map2 as M
pairs = json.load(open('train_pairs.json'))
tr = [pairs[i] for i in (0, 1, 2, 3, 5, 7, 8)]; te = [pairs[i] for i in (4, 7 if False else 6, 9)]
res, api, tot = M.learn(tr)
json.dump({'mapping': res, 'api_class': api, 'elements': tot}, open('map2_train.json', 'w'))
print('learned', len(res), 'classes', sum(len(v) for v in res.values()), 'links', sum(1 for v in res.values() for c in v.values() if c['via']), 'via related')
ok, bad, total, ex, tt, wrong = M.evaluate(res, te)
print(f'held-out: correct {ok}, wrong {bad} (precision {100*ok/max(ok+bad,1):.1f}%), explained {100*ok/max(total,1):.1f}% of {total} non-shared params')
print({k: f'{ex[k]}/{tt[k]}' for k in tt}); print('worst', wrong.most_common(6))
