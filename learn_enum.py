"""Bucket (a) learner: parameters whose Revit value is a FUNCTION of one stored scalar (an enum / kind / flag field of the element, or of an element
reached through 1 ElementId hop), e.g. system-type 'Family Name' by WallType kind, or a per-class constant.
For each (internal class K, parameter id) still missing from the current rules, every scalar source (via, path) builds a table source value -> Counter(Revit value);
a source is accepted when the table explains >= 97% of >= 12 training elements with <= 60 keys (keys seen only once are left out of the table and count as misses);
constants need >= 97% of >= 12.
usage: learn_enum.py OUT.json train|all [per_class [file-filter,...]]   (training pairs from split.json; xcache'd files)
Each file is counted in its own subprocess (learn_enum.py --one RVT TSV PER_CLASS OUT.pkl): peak memory = one file, the parent only holds the merged counts.
Output {K: {bip: {'via','path','table':{repr(src value): [storage, value]}, 'agree','n'} | {'const': [storage, value], 'agree','n'}}}"""
import sys, os, json, random, collections, gc, pickle, subprocess, tempfile
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'

def _key(v):
    if isinstance(v, bool) or isinstance(v, str): return repr(v)
    if isinstance(v, int): return repr(int(v))                        # EID (int subclass, Python decoder) and plain int (Rust path) give the same key
    if isinstance(v, float) and abs(v) < 1e6 and v == int(v): return repr(v)
    return None

def one_file(rvt, tsv, per_class):
    """counts of one training file: tot[(K,bip)], gtv[(K,bip)][(stg,v)], tab[(K,bip)][(via,path)][(key,stg,v)]"""
    import rvt_xcache, rvt_map2 as M, eval_gt as G, rvt_params as RP
    rnd = random.Random(11)
    tot = collections.Counter(); gtv = collections.defaultdict(collections.Counter)
    tab = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    x = rvt_xcache.get_x_ro(rvt); last = {}                          # read-only use: shares the records with rvt_params.params below
    for (eid, c), r in x['recs'].items(): last.setdefault(eid, r)
    src = M.Src(last, {e: {'fields': f} for e, f in x['eh'].items()})
    mine = RP.params(rvt, geom=False)
    E, P = G.load_gt(tsv)
    byc = collections.defaultdict(list)
    for eid in E:
        if eid in last: byc[last[eid]['class']].append(eid)
    for K, ids in byc.items():
        for eid in rnd.sample(ids, min(per_class, len(ids))):
            have = mine.get(eid, {}).get('params', {})
            todo = {}
            for b, nm, stg, v in P.get(eid, []):
                if v == '' or b == -1: continue
                x_ = have.get('%s|%s|%s' % (nm, stg, b), have.get(nm + '|' + stg, have.get(nm)))
                if x_ is not None and (M.eqv(x_, stg, v) or x_ == v): continue        # already reproduced
                todo[str(b)] = (stg, v)
            if not todo: continue
            srcs = [(via, p, _key(val)) for via, p, val in src.sources(eid, 1)]
            srcs = [s for s in srcs if s[2] is not None and '[' not in s[1][-4:]]
            for bip, (stg, v) in todo.items():
                tot[(K, bip)] += 1; gtv[(K, bip)][(stg, v)] += 1
                t = tab[(K, bip)]
                for via, p, k in srcs: t[(via, p)][(k, stg, v)] += 1
        for kb in [kb for kb in tab if kb[0] == K]:                            # in-file bound: a source with > 60 distinct keys can never be accepted
            t = tab[kb]
            for sk in list(t):
                if len({k for (k, _, _) in t[sk]}) > 60: del t[sk]
    return dict(tot), {k: dict(v) for k, v in gtv.items()}, {k: {s: dict(c) for s, c in t.items()} for k, t in tab.items()}

def main():
    out, which = sys.argv[1], sys.argv[2]; per_class = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    split = json.load(open('/home/user1/rvt-research/split.json')); pairs = split['train'] if which == 'train' else split['train'] + split['test']
    if len(sys.argv) > 4: pairs = [p for p in pairs if any(k in p[0] for k in sys.argv[4].split(','))]
    tab = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))     # (K,bip) -> (via,path) -> Counter((key, stg, gt))
    tot = collections.Counter(); gtv = collections.defaultdict(collections.Counter); pruned = set()
    def _prune(kb):
        # once >= 12 samples exist, a source can only survive if it is present and functional on most of them (lenient 0.85: final test is 0.97);
        # the (K,bip) is then frozen to its surviving sources (sources first seen later cannot reach 97% coverage anyway)
        n = tot[kb]; t = tab[kb]
        for sk in list(t):
            if len({k for (k, _, _) in t[sk]}) > 60: del t[sk]
        if n < 12: return
        for sk in list(t):
            cnt = t[sk]
            if sum(cnt.values()) < n * 0.85: del t[sk]; continue
            per = collections.defaultdict(collections.Counter)
            for (k, stg, v), c in cnt.items(): per[k][(stg, v)] += c
            if sum(c.most_common(1)[0][1] for c in per.values()) < n * 0.85: del t[sk]
        pruned.add(kb)
    tmpd = tempfile.mkdtemp(prefix='learn_enum_')
    for i, (rvt, tsv) in enumerate(pairs):
        if not os.path.exists(rvt): continue
        pk = os.path.join(tmpd, '%d.pkl' % i)
        rc = subprocess.call([sys.executable, os.path.abspath(__file__), '--one', rvt, tsv, str(per_class), pk])
        if rc != 0 or not os.path.exists(pk): print(os.path.basename(rvt), 'FAILED rc', rc, flush=True); continue
        ft, fg, fb = pickle.load(open(pk, 'rb')); os.remove(pk)
        for kb, n in ft.items(): tot[kb] += n
        for kb, c in fg.items(): gtv[kb].update(c)
        for kb, srcs in fb.items():
            t = tab[kb]
            for sk, c in srcs.items():
                if kb in pruned and sk not in t: continue
                t[sk].update(c)
        for kb in fb: _prune(kb)
        del ft, fg, fb; gc.collect()
        print(os.path.basename(rvt), 'classes', len({k for k, _ in tot}), 'entries', sum(len(c) for t in tab.values() for c in t.values()), 'rss_mb', int(open('/proc/self/statm').read().split()[1]) * 4096 >> 20, flush=True)
    os.rmdir(tmpd)
    res = collections.defaultdict(dict)
    for (K, bip), n in tot.items():
        if n < 12: continue
        (cst, cn), = gtv[(K, bip)].most_common(1)
        best = None
        if cn / n >= 0.97: best = (cn, {'const': list(cst), 'agree': cn, 'n': n})
        for (via, p), cnt in tab[(K, bip)].items():
            if sum(cnt.values()) < n * 0.97: continue                     # source present on (almost) every element
            per = collections.defaultdict(collections.Counter)
            for (k, stg, v), c in cnt.items(): per[k][(stg, v)] += c
            per = {k: c for k, c in per.items() if sum(c.values()) >= 2}  # keys seen once: no evidence, left out (their elements count as misses)
            if len(per) > 60 or len(per) < 2: continue
            agree = sum(c.most_common(1)[0][1] for c in per.values())
            if agree / n < 0.97: continue
            if best is None or agree > best[0] or (agree == best[0] and 'const' not in best[1] and len(per) < len(best[1]['table'])):
                if best is not None and 'const' in best[1] and agree <= best[0]: continue
                tb = {k: list(c.most_common(1)[0][0]) for k, c in per.items()}
                rule = {'via': via, 'path': p, 'table': tb, 'agree': agree, 'n': n}
                stgs = {sv[0] for sv in tb.values()}
                if len(stgs) == 1 and all(sv[1] == k.strip("'") for k, sv in tb.items()): rule['identity'] = stgs.pop()     # value = the source itself (ids): generalises beyond the training keys
                best = (agree, rule)
        if best: res[K][bip] = best[1]
    json.dump(res, open(out, 'w'))
    print('rules', sum(len(v) for v in res.values()), 'over', len(res), 'classes')

if __name__ == '__main__':
    if sys.argv[1] == '--one':
        r = one_file(sys.argv[2], sys.argv[3], int(sys.argv[4]))
        pickle.dump(r, open(sys.argv[5] + '.tmp', 'wb'), protocol=5); os.replace(sys.argv[5] + '.tmp', sys.argv[5])
    else: main()
