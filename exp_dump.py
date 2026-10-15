#!/usr/bin/env python3
"""exp_dump.py FILE.rvt ID [ID...]  -> for each element id: header + raw bytes of its record region (to next header), with doubles highlighted."""
import sys, os, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
def records(path, want=None):
    o, cls, ids = S.load(path); W = S.id_size(cls); F = '<I' if W == 4 else '<Q'; sch = D.Schema(cls); et = I.element_tags(cls); out = {}
    for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
        for chunk in T.segments(o.openstream(pn).read()):
            for i in range(0, len(chunk) - 24):
                eid = struct.unpack_from(F, chunk, i + 4)[0]
                if (want and eid not in want) or eid not in ids: continue
                tag = struct.unpack_from('<H', chunk, i + 12 + W)[0]
                if tag not in et: continue
                # end = next header
                n = i + 18
                while n < len(chunk) - 24:
                    n += 1
                    e2 = struct.unpack_from(F, chunk, n + 4)[0]
                    if e2 in ids and struct.unpack_from('<H', chunk, n + 12 + W)[0] in et: break
                else: n = len(chunk)
                out.setdefault(eid, []).append((sch.name(tag), chunk[i:n], pn))
    return out, sch, W
if __name__ == '__main__':
    recs, sch, W = records(sys.argv[1], {int(x) for x in sys.argv[2:]})
    for eid, lst in recs.items():
        for cn, b, pn in lst:
            print(f'== id {eid} class {cn} len {len(b)} in {pn}')
            for off in range(0, len(b), 16):
                row = b[off:off + 16]; print(f'{off:5d}', row.hex(' '))
