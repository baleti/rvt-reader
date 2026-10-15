#!/usr/bin/env python3
"""Inventory of all decodable element records in a Revit file (4-byte ElementId era for now).
A record is accepted when: header id is in Global/ElemTable, class derives from Element, decode succeeds and Element.m_id == header id."""
import sys, os, struct, json, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_scan as S, rvt_decode as D, rvt2text as T

def element_tags(cls):
    n = len(cls); ok = set()
    for t in range(12, 12 + n):
        i = t - 12
        while True:
            if cls[i]['name'] == 'Element': ok.add(t); break
            pt = cls[i]['parent'] & 0x7fff
            if not pt: break
            i = pt - 12
    return ok

def inventory(path, only_tags=None, progress=False):
    """returns cls, ids, recs{id:[records of Element-derived classes]}, stats; ElementHeader records are returned in stats['_hdr'] as {id: record}"""
    import numpy as np
    o, cls, ids = S.load(path); IDW = S.id_size(cls); IDF = '<I' if IDW == 4 else '<Q'; sch = D.Schema(cls); dec = D.Dec(sch, idsize=IDW); etags = element_tags(cls)
    EH = sch.by.get('ElementHeader', -999) + 12; idarr = np.array(sorted(ids), dtype=np.uint32 if IDW == 4 else np.uint64)
    import rvt_es as ES
    try: dec.es_schemas = ES.load(path)[0]
    except Exception: dec.es_schemas = {}
    recs = {}; hdr = {}; stats = collections.Counter()
    for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
        chunk = T.joined(o.openstream(pn).read())
        for i in S.header_candidates(chunk, idarr, IDW):
            eid = struct.unpack_from(IDF, chunk, i + 4)[0]
            for short in (False, True):
                tag = struct.unpack_from('<H', chunk, i + 12 + IDW - (4 if short else 0))[0]
                if tag != EH and (tag not in etags or (only_tags and tag not in only_tags)): continue
                stats['cand'] += 1
                try: r, q = dec.record(chunk, i, short)
                except (D.Desync, struct.error, IndexError, UnicodeDecodeError, RecursionError, KeyError, TypeError): stats['desync'] += 1; continue
                if tag == EH:
                    if r.get('complete') and not r.get('error'): hdr[eid] = r; stats['hdr'] += 1
                    continue
                if r['fields'].get('m_id') != eid: stats['idmismatch'] += 1; continue
                stats['ok'] += 1; r['where'] = (pn, 0, i); r['len'] = q - i
                recs.setdefault(eid, []).append(r)
    stats['_hdr'] = hdr
    return cls, ids, recs, stats

if __name__ == '__main__':
    p = glob.glob(sys.argv[1])[0]
    cls, ids, recs, st = inventory(p)
    print(dict(st), len(recs), 'distinct ids decoded of', len(ids))
    cc = collections.Counter(r[-1]['class'] for r in recs.values())
    print(cc.most_common(30))
