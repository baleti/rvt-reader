#!/usr/bin/env python3
"""Learn which decoded internal field corresponds to which Revit API parameter, by value agreement over many elements.
usage: rvt_map.py OUT.json file1.rvt:gt1.tsv file2.rvt:gt2.tsv ..."""
import sys, os, math, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_cache, eval_gt as G, rvt_scan as S

def flat(v, prefix, out, depth=0):
    if depth > 4: return
    if isinstance(v, dict):
        if 'handle' in v and 'ptr' in v or set(v) == {'handle'}: return
        for k, x in v.items():
            if k.startswith('_'): continue
            flat(x, prefix + '.' + k if prefix else k, out, depth + 1)
    elif isinstance(v, list):
        if len(v) <= 4:
            for i, x in enumerate(v): flat(x, f'{prefix}[{i}]', out, depth + 1)
    elif isinstance(v, (int, float, str, bool)) and v is not None: out[prefix] = v

def eq(v, stg, gt, idw):
    try:
        if isinstance(v, str): return stg == 'String' and v == gt
        if isinstance(v, float):
            return stg == 'Double' and math.isclose(v, float(gt), rel_tol=1e-7, abs_tol=1e-9)
        if isinstance(v, bool): v = int(v)
        if stg in ('Integer',): return int(gt) == v
        if stg == 'ElementId': return int(gt) == G.signed(v, idw) or int(gt) == v
        if stg == 'Double': return float(gt) == float(v)
    except Exception: return False
    return False

def learn(pairs):
    agree = collections.defaultdict(lambda: [0, 0]); vals = collections.defaultdict(set); tot = collections.Counter(); apiclass = collections.defaultdict(collections.Counter)
    for rvt, tsv in pairs:
        d = rvt_cache.get(rvt); idw = 8 if any(c == 'Identifier' for c in d['cls_names']) and False else 4
        # id width from first record type
        import rvt_scan; 
        E, P = G.load_gt(tsv)
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            K = r['class']; apiclass[K][e['cls']] += 1; tot[K] += 1
            f = {}; flat(r['fields'], '', f)
            ps = [(bip, nm, stg, val) for bip, nm, stg, val in P.get(eid, []) if val != '']
            # pseudo params
            ps.append(('NAME', 'Name', 'String', e['name']))
            if e['lvl'] not in ('', '-1'): ps.append(('LEVELID', 'LevelId', 'ElementId', e['lvl']))
            if e['tid'] not in ('', '-1'): ps.append(('TYPEID', 'TypeId', 'ElementId', e['tid']))
            for path, v in f.items():
                for bip, nm, stg, val in ps:
                    key = (K, path, bip, nm, stg)
                    if eq(v, stg, val, idw): agree[key][0] += 1; vals[key].add(str(v)[:40])
            for bip, nm, stg, val in ps:
                for path in f: agree[(K, path, bip, nm, stg)][1] += 1
    # keep good pairs
    res = collections.defaultdict(dict)
    for (K, path, bip, nm, stg), (a, n) in agree.items():
        if a >= 5 and a / max(n, 1) >= 0.95 and len(vals[(K, path, bip, nm, stg)]) >= 2:
            cur = res[K].get(str(bip))
            cand = {'path': path, 'name': nm, 'storage': stg, 'agree': a, 'n': n, 'distinct': len(vals[(K, path, bip, nm, stg)])}
            if not cur or cand['agree'] > cur['agree']: res[K][str(bip)] = cand
    return res, {K: dict(c) for K, c in apiclass.items()}, dict(tot)

if __name__ == '__main__':
    out = sys.argv[1]; pairs = [a.split(':') for a in sys.argv[2:]]
    res, api, tot = learn(pairs)
    json.dump({'mapping': res, 'api_class': api, 'elements': tot}, open(out, 'w'), indent=1)
    print(len(res), 'internal classes with mappings;', sum(len(v) for v in res.values()), 'field->parameter links')
    for K in sorted(res, key=lambda k: -tot.get(k, 0))[:12]:
        print(K, tot[K], {v['name']: v['path'] for v in list(res[K].values())[:6]})
