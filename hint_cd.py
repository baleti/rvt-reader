import sys, os, copy, json, itertools, random
sys.path.insert(0, '/home/user1/rvt-research')
import hint_search2 as H, rvt_decode as D
items = H.build('exp_out/e1.rvt', [(2471, 2472), (2472, 2473), (2473, 2474)])
classes = sys.argv[1].split(','); rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cur = D.load_hints(); best = H.dist(items, cur); print('start', best)
for rd in range(rounds):
    for cname in classes:
        cand = [dict()]
        for pre in range(0, 9):
            for order in ('base', 'derived'):
                for suf in (0, 1, 2, 3, 4):
                    cand.append({'prefix': pre, 'order': order, 'suffix': suf})
        for c in cand:
            h = copy.deepcopy(cur)
            if c: h[cname] = {**h.get(cname, {}), **c}
            else: h.pop(cname, None)
            sc = H.dist(items, h)
            if sc[0] < best[0]: best = sc; cur = h; print('round', rd, cname, c, '->', best, flush=True)
json.dump(cur, open('/home/user1/rvt-research/rvt_hints_candidate.json', 'w'), indent=1); print(json.dumps(cur)); print(best)
