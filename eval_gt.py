#!/usr/bin/env python3
"""Evaluate rvt_inventory against the Revit element dump (gt tsv: E/P rows from job3.cs).
usage: eval_gt.py FILE.rvt GT.tsv [--classes]"""
import sys, os, collections, math, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_inventory as I

def signed(v, w=4):
    if isinstance(v, int) and v >= 1 << (8 * w - 1): v -= 1 << (8 * w)
    return v

def params_of(rec, idw):
    out = {}
    for k in ('m_pParamValueSetDouble', 'm_pParamValueSetInt', 'm_pParamValueSetAString', 'm_pParamValueSetElementId'):
        slot = rec['fields'].get(k)
        if not isinstance(slot, dict): continue
        obj = slot.get('obj')
        if not isinstance(obj, dict): continue
        for it in obj.get('m_paramSet', []):
            if isinstance(it, dict) and 'm_paramId' in it:
                v = it['m_value']
                if isinstance(v, dict): v = v.get('m_id', v)
                out[signed(it['m_paramId'], idw)] = (k[len('m_pParamValueSet'):], v)
    return out

def load_gt(tsv):
    E = {}; P = collections.defaultdict(list)
    for ln in open(tsv, encoding='utf-8'):
        t = ln.rstrip('\n').split('\t')
        if t[0] == 'E': E[int(t[1])] = dict(cls=t[2], cat=t[3], name=t[4], tid=t[5], lvl=t[6], kind=t[7])
        elif t[0] == 'P' and len(t) >= 6: P[int(t[1])].append((int(t[2]), t[3], t[4], t[5]))
    return E, P

def same(storage, gt, mine):
    try:
        if storage == 'Double': return math.isclose(float(gt), float(mine), rel_tol=1e-6, abs_tol=1e-9)
        if storage == 'Integer': return int(gt) == int(mine)
        if storage == 'ElementId': return int(gt) == signed(int(mine) if not isinstance(mine, dict) else int(mine.get('m_id', -1)), 8)
        return str(gt) == str(mine)
    except Exception: return False

if __name__ == '__main__':
    rvt, tsv = sys.argv[1], sys.argv[2]
    E, P = load_gt(tsv)
    cls, ids, recs, st = I.inventory(rvt); import rvt_scan as S; idw = S.id_size(cls)
    last = {k: v[-1] for k, v in recs.items()}
    print('records complete:', sum(1 for r in last.values() if r.get('complete')), 'partial:', sum(1 for r in last.values() if not r.get('complete')))
    found = [i for i in E if i in last]
    print(f'GT elements {len(E)} (inst {sum(1 for e in E.values() if e["kind"]=="inst")}, type {sum(1 for e in E.values() if e["kind"]=="type")}); decoded {len(last)} ids; GT elements decoded {len(found)} ({100*len(found)//max(len(E),1)}%)')
    m = collections.defaultdict(collections.Counter)
    for i in found: m[E[i]['cls']][last[i]['class']] += 1
    tot = ok = missing = 0; per = collections.Counter(); perok = collections.Counter(); pm = collections.Counter()
    for i in found:
        mp = params_of(last[i], idw)
        for bip, nm, stg, val in P.get(i, []):
            if bip == -1 or val == '': continue
            tot += 1; per[stg] += 1
            if bip in mp:
                if same(stg, val, mp[bip][1]): ok += 1; perok[stg] += 1
                else: pm[(E[i]['cls'], bip, nm, stg)] += 1
            else: missing += 1
    print(f'builtin params with values (on decoded elements): {tot}; matched {ok}; absent in decode {missing}; present but different {tot-ok-missing}')
    print(' by storage:', {k: f'{perok[k]}/{per[k]}' for k in per})
    print(' API class -> internal class (top):')
    for c, cc in sorted(m.items(), key=lambda kv: -sum(kv[1].values()))[:25]: print('   ', c, dict(cc.most_common(3)))
    print(' top mismatches:', pm.most_common(8))
