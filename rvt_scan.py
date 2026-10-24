#!/usr/bin/env python3
"""Element inventory: find element record headers [u32 A][u32 id][u64 stamp][u16 class tag] in decoded partitions.
An id must exist in Global/ElemTable and the tag must be a class of the file's schema. 4-byte-id era only (Revit <= 2023) for now."""
import sys, os, struct, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile, fmt_parser as fp
from rvtfmt import inflate_stream
import rvt2text as T

def id_size(cls):
    for c in cls:
        if c['name'] == 'Identifier':
            return 8 if any((f['T'] & 0xff) == 0x0b for f in c['fields']) else 4
    return 4

def load(path):
    o = olefile.OleFileIO(path)
    cls, _ = fp.parse(inflate_stream(o.openstream('Formats/Latest').read())[1])
    et = inflate_stream(o.openstream('Global/ElemTable').read())[1]
    idsize = id_size(cls)
    nh = struct.unpack_from('<I', et, 2)[0]                                   # header row count: a second table follows the element rows in real office files (corpus 2026-10-23)
    if idsize == 4: ids = {struct.unpack_from('<I', et, 6 + 28 * k)[0] for k in range(min(nh, (len(et) - 6) // 28) if nh else (len(et) - 6) // 28)}
    else:
        n = (len(et) - 6) // 40
        if 0 < nh <= n: n = nh
        ids = {struct.unpack_from('<Q', et, 6 + 40 * k)[0] for k in range(n)}
        # elements without their own ElemTable row (sketch lines, floors/sketches inside parents) are referenced at row offset +20
        top = max(ids) + 16
        ids |= {v for v in (struct.unpack_from('<Q', et, 6 + 40 * k + 20)[0] for k in range(n)) if 0 < v < top}
    return o, cls, ids

def scan(path):
    o, cls, ids = load(path); n = len(cls)
    found = {}      # id -> (partition, offset, tag) first occurrence; also all occurrences
    allocc = collections.defaultdict(list)
    for pn in [x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')]:
        for si, chunk in enumerate(T.segments(o.openstream(pn).read())):
            for i in range(0, len(chunk) - 18):
                idv = struct.unpack_from('<I', chunk, i + 4)[0]
                if idv in ids:
                    tag = struct.unpack_from('<H', chunk, i + 16)[0]
                    if 12 <= tag < 12 + n and struct.unpack_from('<I', chunk, i + 12)[0] == tag - 0 + 0 * 1 or False: pass
                    if 12 <= tag < 12 + n and chunk[i + 18:i + 20] in (b'\x00\x00', b'\xff\xff') or (12 <= tag < 12 + n):
                        allocc[idv].append((pn, si, i, tag))
    return cls, ids, allocc

if __name__ == '__main__':
    p = glob.glob(sys.argv[1])[0]
    cls, ids, occ = scan(p)
    print(len(ids), 'ids in ElemTable;', len(occ), 'ids with a header-like match')
    tagc = collections.Counter()
    for idv, lst in occ.items():
        for t in {x[3] for x in lst}: tagc[cls[t - 12]['name']] += 1
    print(tagc.most_common(25))


def header_candidates(chunk, idarr, W):
    """Positions i where chunk[i+4 : i+4+W] (little endian) is an ElemTable id. idarr: numpy array of ids (uint32 or uint64)."""
    import numpy as np
    n = len(chunk)
    if n < 32: return []
    out = []
    if W == 4:
        for a in range(4):
            m = (n - a) // 4
            if m <= 0: continue
            arr = np.frombuffer(chunk, dtype='<u4', count=m, offset=a)
            hit = np.nonzero(np.isin(arr, idarr))[0]
            out.extend(int(h) * 4 + a - 4 for h in hit)
    else:
        for a in range(8):
            m = (n - a) // 8
            if m <= 0: continue
            arr = np.frombuffer(chunk, dtype='<u8', count=m, offset=a)
            hit = np.nonzero(np.isin(arr, idarr))[0]
            out.extend(int(h) * 8 + a - 4 for h in hit)
    return sorted(i for i in out if 0 <= i <= n - 24)


def header_candidates_tagged(chunk, idarr, W, tags):
    """Like header_candidates, but keeps only positions whose class tag (u16 at i+12+W for long headers, i+8+W for short ones) is in `tags`: exact for the extractor
    (every other candidate is skipped by it) and ~100x fewer positions, without a 20M-element Python list.  Returns a sorted numpy int64 array."""
    import numpy as np
    n = len(chunk)
    if n < 32: return np.zeros(0, dtype=np.int64)
    buf = np.frombuffer(chunk, dtype=np.uint8)
    tagmask = np.zeros(65536, dtype=bool); tagmask[np.array(sorted(tags), dtype=np.int64)] = True
    parts = []
    dt = '<u4' if W == 4 else '<u8'
    for a in range(W):
        m = (n - a) // W
        if m <= 0: continue
        arr = np.frombuffer(chunk, dtype=dt, count=m, offset=a)
        pos = np.nonzero(np.isin(arr, idarr))[0].astype(np.int64) * W + a - 4
        pos = pos[(pos >= 0) & (pos <= n - 24)]
        if not len(pos): continue
        ok = np.zeros(len(pos), dtype=bool)
        for off in (12 + W, 8 + W):
            q = pos + off; v = q + 1 < n
            t = np.zeros(len(pos), dtype=np.int64); t[v] = buf[q[v]].astype(np.int64) | (buf[q[v] + 1].astype(np.int64) << 8)
            ok |= v & tagmask[t]
        parts.append(pos[ok])
    return np.sort(np.concatenate(parts)) if parts else np.zeros(0, dtype=np.int64)


def owners(path):
    """{element id: owner id or None} from Global/ElemTable"""
    import olefile
    from rvtfmt import inflate_stream
    o = olefile.OleFileIO(path); cls, _ = fp.parse(inflate_stream(o.openstream('Formats/Latest').read())[1]); W = id_size(cls)
    et = inflate_stream(o.openstream('Global/ElemTable').read())[1]; out = {}; nh = struct.unpack_from('<I', et, 2)[0]
    if W == 4:
        for k in range(min(nh, (len(et) - 6) // 28) if nh else (len(et) - 6) // 28):
            r = struct.unpack_from('<7I', et, 6 + 28 * k); out[r[0]] = None if r[6] == 0xffffffff else r[6]
    else:
        for k in range(min(nh, (len(et) - 6) // 40) if nh else (len(et) - 6) // 40):
            i = struct.unpack_from('<Q', et, 6 + 40 * k)[0]; ow = struct.unpack_from('<Q', et, 6 + 40 * k + 28)[0]; out[i] = None if ow == 0xffffffffffffffff else ow
    return out
