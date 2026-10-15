import sys, os, struct, json, copy, itertools
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
class Eval:
    def __init__(self, targets):   # targets: [(path, [ids])]
        self.items = []
        for path, want in targets:
            o, cls, ids = S.load(path); W = S.id_size(cls); F = '<I' if W == 4 else '<Q'; sch = D.Schema(cls); et = I.element_tags(cls)
            for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
                for chunk in T.segments(o.openstream(pn).read()):
                    for i in range(0, len(chunk) - 24):
                        eid = struct.unpack_from(F, chunk, i + 4)[0]
                        if (want is None or eid in want) and eid in ids and struct.unpack_from('<H', chunk, i + 12 + W)[0] in et:
                            self.items.append((sch, W, F, ids, et, chunk, i, eid))
    def score(self, hints):
        comp = exact = 0
        for sch, W, F, ids, et, chunk, i, eid in self.items:
            d = D.Dec(sch, idsize=W); d.hints = hints
            try: r, q = d.record(chunk, i)
            except Exception: continue
            if r['fields'].get('m_id') != eid: continue
            if r.get('complete') and not r.get('error'):
                comp += 1
                if q + 24 <= len(chunk) and struct.unpack_from(F, chunk, q + 4)[0] in ids and struct.unpack_from('<H', chunk, q + 12 + W)[0] in et: exact += 1
                elif q == len(chunk): exact += 1
        return comp, exact
if __name__ == '__main__':
    ev = Eval([('exp_out/e1.rvt', {2471, 2472, 2473, 2474})])
    print(len(ev.items), 'items')
    base = D.load_hints()
    print('base', ev.score(base))
    cname = sys.argv[1]
    best = None
    for pre in range(0, 13):
        for order in ('base', 'derived'):
            h = copy.deepcopy(base); h[cname] = {'prefix': pre, 'order': order}
            sc = ev.score(h); print(cname, pre, order, sc, flush=True)
