import sys, os, struct, json, copy, itertools
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
# items: (file, id, next_id)
def build(file, pairs):
    o, cls, ids = S.load(file); W = S.id_size(cls); F = '<I' if W == 4 else '<Q'; sch = D.Schema(cls); et = I.element_tags(cls); items = []
    for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
        for chunk in T.segments(o.openstream(pn).read()):
            pos = {}
            for i in range(0, len(chunk) - 24):
                eid = struct.unpack_from(F, chunk, i + 4)[0]
                if eid in dict(pairs) or eid in dict(pairs).values():
                    if struct.unpack_from('<H', chunk, i + 12 + W)[0] in et: pos.setdefault(eid, i)
            for a, b in pairs:
                if a in pos and b in pos and pos[b] > pos[a]: items.append((sch, W, chunk, pos[a], pos[b], a))
    return items
def dist(items, hints):
    tot = 0; ok = 0
    for sch, W, chunk, i, end, eid in items:
        d = D.Dec(sch, idsize=W); d.hints = hints
        try: r, q = d.record(chunk, i)
        except Exception: tot += 5000; continue
        dd = abs(q - end) if (r.get('complete') or True) else 5000
        if not r.get('complete') and q < end: dd += 100
        tot += dd; ok += (q == end and r.get('complete') and not r.get('error'))
    return tot, ok
if __name__ == '__main__':
    items = build('exp_out/e1.rvt', [(2471, 2472), (2472, 2473), (2473, 2474)])
    print(len(items), 'items'); base = D.load_hints(); print('base', dist(items, base))
    for cname in sys.argv[1:]:
        res = []
        for pre in range(0, 13):
            for order in ('base', 'derived'):
                h = copy.deepcopy(base); h[cname] = {'prefix': pre, 'order': order}
                res.append((dist(items, h), pre, order))
        res.sort(); print(cname, res[:5])
