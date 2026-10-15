#!/usr/bin/env python3
"""Learn parameter derivations: for each (internal class K, API parameter) find the source path - a field of the element itself, or of a related element
reached through up to 2 ElementId-valued fields - whose value equals Revit's value across >=95% of elements.
usage: rvt_map2.py OUT.json file1.rvt:gt1.tsv ..."""
import sys, os, math, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_cache, eval_gt as G, rvt_decode as D

def leaves(v, prefix, out, eids, depth=0):
    """collect scalar leaves into out{path: value}; ElementId-valued leaves also into eids{path: id}"""
    if depth > 5: return
    if isinstance(v, dict):
        if 'handle' in v and ('ptr' in v or 'es' in v) or set(v) <= {'handle', 'ref'}:
            sub = v.get('obj')
            if isinstance(sub, dict) and len(prefix) < 80: leaves(sub, prefix + '*', out, eids, depth + 1)
            return
        for k, x in v.items():
            if k.startswith('_'): continue
            leaves(x, prefix + '.' + k if prefix else k, out, eids, depth + 1)
    elif isinstance(v, list):
        if len(v) <= 6:
            for i, x in enumerate(v): leaves(x, f'{prefix}[{i}]', out, eids, depth + 1)
    elif isinstance(v, D.EID): eids[prefix] = int(v); out[prefix] = int(v)
    elif isinstance(v, (int, float, str)) and not isinstance(v, bool): out[prefix] = v
    elif isinstance(v, bool): out[prefix] = int(v)

def eqv(v, stg, gt):
    try:
        if isinstance(v, str): return stg == 'String' and v == gt
        if isinstance(v, float): return stg == 'Double' and math.isclose(v, float(gt), rel_tol=1e-7, abs_tol=1e-9)
        if stg == 'Integer': return int(gt) == int(v)
        if stg == 'ElementId':
            g = int(gt); iv = int(v)
            return g == iv or (iv >= 1 << 63 and g == iv - (1 << 64)) or (1 << 31 <= iv < 1 << 32 and g == iv - (1 << 32))
        if stg == 'Double': return float(gt) == float(v)
    except Exception: pass
    return False

class Src:
    """per-record flattened view with cached hops"""
    def __init__(s, last, hdr=None): s.last = last; s.cache = {}; s.hdr = hdr or {}
    def flat(s, rid):
        c = s.cache.get(rid)
        if c is None:
            r = s.last.get(rid)
            if r is None: c = ({}, {})
            else:
                out = {}; eids = {}; leaves(r['fields'], '', out, eids)
                h = s.hdr.get(rid)
                if h is not None: leaves(h['fields'], 'H', out, eids)
                c = (out, eids)
            s.cache[rid] = c
        return c
    def sources(s, rid, hops=2):
        """yield (via, path, value) for the element and related elements"""
        out, eids = s.flat(rid)
        for p, v in out.items(): yield ('', p, v)
        if hops >= 1:
            for p1, i1 in [(p, i) for p, i in eids.items() if '*' not in p and '[' not in p][:40]:
                if i1 in s.last and i1 != rid:
                    o1, e1 = s.flat(i1)
                    for p, v in o1.items(): yield (p1 + '>', p, v)
                    if hops >= 2:
                        for p2, i2 in [(p, i) for p, i in e1.items() if '*' not in p and '[' not in p][:12]:
                            if i2 in s.last and i2 not in (rid, i1):
                                o2, _ = s.flat(i2)
                                for p, v in o2.items(): yield (p1 + '>' + p2 + '>', p, v)

def learn(pairs, hops=2, min_support=6, min_rate=0.95):
    agree = collections.defaultdict(lambda: [0, 0]); vals = collections.defaultdict(set); tot = collections.Counter(); api = collections.defaultdict(collections.Counter)
    seen_keys = collections.defaultdict(set)
    for rvt, tsv in pairs:
        d = rvt_cache.get(rvt); E, P = G.load_gt(tsv); src = Src(d['last'], d.get('hdr'))
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            K = r['class']; api[K][e['cls']] += 1; tot[K] += 1
            ps = {str(b): (stg, v, nm) for b, nm, stg, v in P.get(eid, []) if v != '' and b != -1}
            ps['NAME'] = ('String', e['name'], 'Name')
            if e['lvl'] not in ('', '-1'): ps['LEVELID'] = ('ElementId', e['lvl'], 'LevelId')
            if e['tid'] not in ('', '-1'): ps['TYPEID'] = ('ElementId', e['tid'], 'TypeId')
            cat = e['cat'].split('|')[-1] if e['cat'] else ''
            if cat: ps['CATEGORYID'] = ('ElementId', cat, 'CategoryId')
            ssrc = list(src.sources(eid, hops))
            for via, path, v in ssrc:
                for bip, (stg, gv, nm) in ps.items():
                    key = (K, via, path, bip)
                    agree[key][1] += 1
                    if eqv(v, stg, gv): agree[key][0] += 1; vals[key].add(str(v)[:30])
    res = collections.defaultdict(dict)
    for (K, via, path, bip), (a, n) in agree.items():
        if a >= min_support and a / n >= min_rate and len(vals[(K, via, path, bip)]) >= 2:
            cur = res[K].get(bip)
            cand = {'via': via, 'path': path, 'agree': a, 'n': n, 'distinct': len(vals[(K, via, path, bip)])}
            if not cur or (cand['agree'], -len(via)) > (cur['agree'], -len(cur['via'])): res[K][bip] = cand
    return res, {k: dict(c) for k, c in api.items()}, dict(tot)

if __name__ == '__main__':
    out = sys.argv[1]; pairs = [a.split(':') for a in sys.argv[2:]]
    res, api, tot = learn(pairs)
    json.dump({'mapping': res, 'api_class': api, 'elements': tot}, open(out, 'w'), indent=0)
    print(len(res), 'classes;', sum(len(v) for v in res.values()), 'links;', sum(1 for v in res.values() for c in v.values() if c['via']), 'via related elements')

def resolve(src, rid, via, path):
    """value of `path` on the element reached from rid through `via` ('p1>p2>')"""
    cur = rid
    for hop in [h for h in via.split('>') if h]:
        _, eids = src.flat(cur); nxt = eids.get(hop)
        if nxt is None or nxt not in src.last: return None
        cur = nxt
    return src.flat(cur)[0].get(path)

def evaluate(mapping, pairs):
    ok = bad = tot = 0; wrong = collections.Counter(); expl_by_storage = collections.Counter(); tot_by_storage = collections.Counter()
    for rvt, tsv in pairs:
        d = rvt_cache.get(rvt); E, P = G.load_gt(tsv); src = Src(d['last'], d.get('hdr'))
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            mp = mapping.get(r['class'], {})
            ps = {str(b): (stg, v, nm) for b, nm, stg, v in P.get(eid, []) if v != '' and b != -1}
            for bip, (stg, gv, nm) in ps.items():
                tot += 1; tot_by_storage[stg] += 1
                c = mp.get(bip)
                if not c: continue
                v = resolve(src, eid, c['via'], c['path'])
                if v is None: continue
                if eqv(v, stg, gv): ok += 1; expl_by_storage[stg] += 1
                else: bad += 1; wrong[(r['class'], nm)] += 1
    return ok, bad, tot, expl_by_storage, tot_by_storage, wrong

SENT = {-1, 4294967295, 18446744073709551615}
def _valid(v, stg):
    if v is None: return False
    if stg == 'ElementId' and int(v) in SENT: return False
    return True

UNIV = False
def learn2(pairs, hops=2, min_support=6, max_sources=3):
    """ordered source lists: for each (class, parameter) pick sources greedily so that 'first valid source wins' reproduces Revit's value"""
    # pass 1: candidate keys
    agree = collections.defaultdict(lambda: [0, 0]); vals = collections.defaultdict(set); api = collections.defaultdict(collections.Counter); tot = collections.Counter(); gtvals = collections.defaultdict(set)
    data = []
    for rvt, tsv in pairs:
        d = rvt_cache.get(rvt); E, P = G.load_gt(tsv); src = Src(d['last'], d.get('hdr')); data.append((d, E, P, src))
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            K = '*' if UNIV else r['class']; api[K][e['cls']] += 1; tot[K] += 1
            ps = {str(b): (stg, v, nm) for b, nm, stg, v in P.get(eid, []) if v != '' and b != -1}
            cat = e['cat'].split('|')[-1] if e['cat'] else ''
            if cat: ps['CATEGORYID'] = ('ElementId', cat, 'CategoryId')
            for bip, (stg, gv, nm) in ps.items(): gtvals[(K, bip)].add(str(gv)[:30])
            for via, path, v in src.sources(eid, hops):
                for bip, (stg, gv, nm) in ps.items():
                    key = (K, via, path, bip); agree[key][1] += 1
                    if eqv(v, stg, gv): agree[key][0] += 1; vals[key].add(str(v)[:30])
    cand = collections.defaultdict(list)
    for key, (a, n) in agree.items():
        K, via, path, bip = key
        const_ok = len(gtvals[(K, bip)]) <= 3 and a >= 50 and a / n >= 0.9
        if a >= min_support and a / n >= 0.30 and (len(vals[key]) >= 2 or const_ok): cand[(K, bip)].append(key)
    # pass 2: per-element agreement sets for candidates only
    res = collections.defaultdict(dict)
    sets = collections.defaultdict(dict)       # key -> {(file_i, eid): (valid, agrees)}
    for fi, (d, E, P, src) in enumerate(data):
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            K = '*' if UNIV else r['class']
            ps = {str(b): (stg, v) for b, nm, stg, v in P.get(eid, []) if v != '' and b != -1}
            cat = e['cat'].split('|')[-1] if e['cat'] else ''
            if cat: ps['CATEGORYID'] = ('ElementId', cat)
            for bip, (stg, gv) in ps.items():
                for key in cand.get((K, bip), []):
                    v = resolve(src, eid, key[1], key[2])
                    sets[key][(fi, eid)] = (_valid(v, stg), v is not None and eqv(v, stg, gv))
    for (K, bip), keys in cand.items():
        remaining = None; chosen = []
        universe = set()
        for key in keys: universe |= set(sets[key])
        remaining = set(universe)
        for _ in range(max_sources):
            best = None
            for key in keys:
                if key in [c[0] for c in chosen]: continue
                s = sets[key]; good = sum(1 for e in remaining if e in s and s[e][1] and s[e][0]); bad = sum(1 for e in remaining if e in s and s[e][0] and not s[e][1])
                if good >= min_support and good / (good + bad) >= 0.9 and (best is None or good > best[1]): best = (key, good, bad)
            if not best: break
            chosen.append(best); remaining = {e for e in remaining if not (e in sets[best[0]] and sets[best[0]][e][0])}
        rules = [{'via': k[1], 'path': k[2], 'agree': g, 'bad': b} for k, g, b in chosen]
        # default: among training elements no chosen source covers, how often is the Revit value 'none' (-1)?
        left = [e for e in universe if not any(e in sets[k] and sets[k][e][0] for k, _, _ in chosen)]
        if left and gtvals.get((K, bip)) is not None:
            nn = 0; tt2 = 0
            for (fi, eid) in left:
                d, E, P, src = data[fi]
                for b2, nm2, stg2, gv2 in P.get(eid, []):
                    if str(b2) == bip and stg2 == 'ElementId': tt2 += 1; nn += int(gv2) == -1
            if tt2 >= 10 and nn / tt2 >= 0.95: rules.append({'default': -1, 'n': tt2, 'ok': nn})
        if rules: res[K][bip] = rules
    return res, {k: dict(c) for k, c in api.items()}, dict(tot)

def evaluate2(mapping, pairs):
    ok = bad = tot = 0; wrong = collections.Counter(); ex = collections.Counter(); tt = collections.Counter()
    for rvt, tsv in pairs:
        d = rvt_cache.get(rvt); E, P = G.load_gt(tsv); src = Src(d['last'], d.get('hdr'))
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            mp = mapping.get(r['class'], {})
            for b, nm, stg, gv in P.get(eid, []):
                if gv == '' or b == -1: continue
                tot += 1; tt[stg] += 1
                srcs = mp.get(str(b))
                if not srcs: continue
                v = None
                for c in srcs:
                    if 'default' in c: v = c['default']; break
                    x = resolve(src, eid, c['via'], c['path'])
                    if _valid(x, stg): v = x; break
                if v is None: continue
                if eqv(v, stg, gv): ok += 1; ex[stg] += 1
                else: bad += 1; wrong[(r['class'], nm)] += 1
    return ok, bad, tot, ex, tt, wrong
