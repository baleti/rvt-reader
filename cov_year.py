#!/usr/bin/env python3
"""Per-file coverage: of all element records found (header id in ElemTable, Element-derived class, m_id matches),
  complete = decoded with no error and geometry decoded; exact = decode end offset == next record header (when determinable).
usage: cov_year.py FILE  -> one JSON line"""
import sys, os, struct, json, collections, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['RVT_GEOM'] = '1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
p = sys.argv[1]; t0 = time.time()
o, cls, ids = S.load(p); W = S.id_size(cls); F = '<I' if W == 4 else '<Q'
import numpy as np
idarr = np.array(sorted(ids), dtype=np.uint32 if W == 4 else np.uint64)
sch = D.Schema(cls); dec = D.Dec(sch, idsize=W); et = I.element_tags(cls); EH = sch.by.get('ElementHeader', -999) + 12; hdrstat = {}
import rvt_es as ES
try: dec.es_schemas = ES.load(p)[0]
except Exception as _e: dec.es_schemas = {}
tot = comp = exact = partial = 0; idstat = {}; iderr = {}; idexact_fail = {}; err = collections.Counter(); byclass = collections.defaultdict(lambda: [0, 0])
seen = set()
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in [T.joined(o.openstream(pn).read())]:
        pos = []   # candidate header positions in this chunk
        for i in S.header_candidates(chunk, idarr, W):
            eid = struct.unpack_from(F, chunk, i + 4)[0]
            if struct.unpack_from('<H', chunk, i + 12 + W)[0] in et or struct.unpack_from('<H', chunk, i + 12 + W)[0] == EH: pos.append((i, eid, False))
            if i + 4 + W + 6 <= len(chunk) and (struct.unpack_from('<H', chunk, i + 8 + W)[0] in et or struct.unpack_from('<H', chunk, i + 8 + W)[0] == EH): pos.append((i, eid, True))
        
        for i, eid, shrt in pos:
            try: r, q = dec.record(chunk, i, shrt)
            except Exception: continue
            if r['class'] == 'ElementHeader':
                if r.get('complete') and not r.get('error'): hdrstat[eid] = 1
                continue
            if r['fields'].get('m_id') != eid: continue
            key = (eid, r['class'])
            tot += 1; ok = r.get('complete') and not r.get('error'); ex_here = False
            comp += bool(ok); byclass[r['class']][0] += 1; byclass[r['class']][1] += bool(ok)
            if not ok:
                m = r.get('error') or ''
                iderr[eid] = (r['class'], re.sub(r'\d+', 'N', m.split('@@')[-1].split(' at ')[0].strip()[:70] if '@@' in m else m[:50]) or '<geometry stop>')
                err[(r['class'], m.split('@@')[-1].split(' at ')[0].strip()[:60] if '@@' in m else m[:40])] += 1
            if q + 24 <= len(chunk):
                e2 = struct.unpack_from(F, chunk, q + 4)[0]
                if e2 == (1 << (8 * W)) - 1 or (e2 in ids and struct.unpack_from('<H', chunk, q + 12 + W)[0] in et) or (12 <= struct.unpack_from('<H', chunk, q + 12 + W)[0] < 12 + len(cls) and struct.unpack_from("<I", chunk, q)[0] < (1 << 24) and e2 < (1 << 40)): exact += 1; ex_here = True
            elif q == len(chunk): exact += 1; ex_here = True
            lv = 2 if (ok and ex_here) else (1 if ok else 0)
            idstat[eid] = max(idstat.get(eid, -1), lv)
n_ids = len(ids); el_exact = sum(1 for v in idstat.values() if v == 2); el_comp = sum(1 for v in idstat.values() if v >= 1)
if os.environ.get('COV_IDSTAT'):
    json.dump({'hdr': sorted(hdrstat), 'status': {str(k): v for k, v in idstat.items()}, 'err': {str(k): v for k, v in iderr.items() if idstat.get(k, 0) < 2}}, open(os.environ['COV_IDSTAT'], 'w'))
bad = collections.Counter(iderr[e] for e, v in idstat.items() if v < 2 and e in iderr)
noexact = sum(1 for v in idstat.values() if v == 1)
print(json.dumps({'unresolved': [(list(k), v) for k, v in bad.most_common(12)], 'ok_not_exact': noexact, 'file': os.path.basename(p), 'elements': n_ids, 'el_complete': el_comp, 'el_exact': el_exact, 'el_found': len(idstat), 'records': tot, 'complete': comp, 'exact_fit': exact, 'secs': round(time.time() - t0),
                  'worst_classes': sorted(((k, v[0], v[0] - v[1]) for k, v in byclass.items()), key=lambda x: -x[2])[:8], 'top_err': [(list(k), v) for k, v in err.most_common(6)]}))
