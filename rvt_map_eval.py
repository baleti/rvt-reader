import sys, os, json, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_cache, rvt_map as M, eval_gt as G
def evaluate(mapping, pairs):
    ok = bad = 0; tot_params = 0; covered = 0; per = collections.Counter(); perbad = collections.Counter()
    for rvt, tsv in pairs:
        d = rvt_cache.get(rvt); E, P = G.load_gt(tsv)
        for eid, e in E.items():
            r = d['last'].get(eid)
            if not r: continue
            K = r['class']; mp = mapping.get(K, {})
            f = {}; M.flat(r['fields'], '', f)
            gt = {str(b): (stg, v) for b, nm, stg, v in P.get(eid, []) if v != ''}
            gt['NAME'] = ('String', e['name'])
            for bip, (stg, v) in gt.items():
                if bip != 'NAME': tot_params += 1
            for bip, c in mp.items():
                if bip in gt and c['path'] in f:
                    stg, v = gt[bip]
                    if M.eq(f[c['path']], stg, v, 4): ok += 1; per[K] += 1
                    else: bad += 1; perbad[(K, c['name'], c['path'])] += 1
    return ok, bad, tot_params, per, perbad
if __name__ == '__main__':
    mp = json.load(open(sys.argv[1]))['mapping']
    pairs = [a.split(':') for a in sys.argv[2:]]
    ok, bad, tot, per, perbad = evaluate(mp, pairs)
    print(f'held-out: predicted-and-correct {ok}, predicted-and-wrong {bad} (precision {100*ok/max(ok+bad,1):.1f}%), GT builtin params on found elements {tot}, explained {100*ok/max(tot,1):.1f}%')
    print('worst links:', perbad.most_common(8))
