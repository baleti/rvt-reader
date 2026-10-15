#!/usr/bin/env python3
"""Extensible storage: find the schema table (vector<pair<GUID, ESSchema>>) in Global/Latest and decode it."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile, fmt_parser as fp
from rvtfmt import inflate_stream
import rvt_decode as D, rvt_scan as S
try: sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as _F
except Exception: _F = None
def decode_entry(dec, sch, d, p, pre, mid, post=0):
    """pair<GUID, ESSchema>; `pre` = leading pad bytes before the key GUID (2025+: 1), `mid` = pad bytes after m_documentation (2025+: 1)"""
    key = d[p + pre:p + pre + 16].hex(); q = p + pre + 16 + post; ci = sch.by['ESSchema']; out = {}; pend = []
    for f in sch.c[ci]['fields']:
        out[f['name']], q = dec.value(d, q, f, pend, ['es'])
        if f['name'] == 'm_documentation': q += mid
    return key, out, q

import re as _re
_NAME = _re.compile(r'^[A-Za-z0-9_\- ]{0,64}$')
def _good(key, sc):
    return key == sc['m_guid']['m_guid'] and (sc['m_schemaName'] != '' or len(sc['m_fields']) > 0) and bool(_NAME.match(sc['m_schemaName'])) and bool(_NAME.match(sc['m_vendorId'])) and all(_NAME.match(f['m_fieldName']) for f in sc['m_fields'])

def find_schemas(d, sch, W):
    if _F and _F.on(): return _F.find_schemas(d, sch, W)
    old = D.STRCAP; D.STRCAP = 100000
    try: return _find_schemas(d, sch, W)
    finally: D.STRCAP = old

def _find_schemas(d, sch, W):
    """{guid_hex: schema}. Pass 1: vector<pair<GUID,ESSchema>> with a leading count (<=2024 layout). Pass 2 (2025+): entries with a 1-byte lead and a 1-byte pad after m_documentation."""
    out = {}
    if 'ESSchema' not in sch.by: return out
    dec = D.Dec(sch, idsize=W); dec.STOP = ()
    n = len(d)
    import numpy as np, bisect
    a = np.frombuffer(d, dtype=np.uint8).astype(np.uint32); m = n - 8
    u32 = a[:m - 3] | (a[1:m - 2] << 8) | (a[2:m - 1] << 16) | (a[3:m] << 24)      # u32 at every offset p < len(u32)
    for pre, mid, post, counted in ((0, 0, 0, True), (0, 0, 4, True), (1, 4, 0, False), (1, 0, 4, False)):
        # numpy prefilter: only offsets whose count (if counted), name length and first name char look right are tried in Python
        L = len(u32); lim = L - 60 - (4 if counted else 0)
        if lim <= 0: continue
        idx = np.arange(lim)
        qq = idx + (4 if counted else 0) + pre + 16 + post
        ok = qq + 6 < L
        idx = idx[ok]; qq = qq[ok]
        ln = u32[qq]
        mask = ln <= 4000
        if counted:
            cnt = u32[idx]; mask &= (cnt >= 1) & (cnt <= 5000)
        p2 = np.minimum(qq + 4 + 2 * np.minimum(ln, 4000) + mid, L - 1); mask &= u32[p2] <= 500      # m_fields vector count follows the documentation string
        ch = np.where(ln > 0, a[np.minimum(qq + 4, n - 1)], 0x20)
        ch2 = np.where(ln > 0, a[np.minimum(qq + 5, n - 1)], 0)
        mask &= (ch >= 0x20) & (ch < 0x7f) & (ch2 == 0)
        cands = idx[mask].tolist(); ci = 0
        while ci < len(cands):
            p = cands[ci]; ci += 1
            q = p + 4 if counted else p
            if counted: cnt = struct.unpack_from('<I', d, p)[0]
            qq2 = q + pre + 16 + post
            if qq2 + 4 > n: break
            ln = struct.unpack_from('<I', d, qq2)[0]
            if not (0 <= ln <= 4000 and qq2 + 4 + 2 * ln <= n and all(d[qq2 + 4 + 2 * i + 1] == 0 and 0x20 <= d[qq2 + 4 + 2 * i] < 0x7f for i in range(min(ln, 3)))): continue
            try:
                pp = q; got = []
                for _ in range(cnt if counted else 100000):
                    try: key, sc, q2 = decode_entry(dec, sch, d, pp, pre, mid, post)
                    except Exception: break
                    if not _good(key, sc): break
                    got.append(sc); pp = q2
                if got:
                    for sc in got: out[sc['m_guid']['m_guid']] = sc
                    ci = bisect.bisect_left(cands, pp, ci)
                    continue
            except Exception: pass
    return out
def load(path):
    o = olefile.OleFileIO(path); cls, _ = fp.parse(inflate_stream(o.openstream('Formats/Latest').read())[1]); sch = D.Schema(cls); W = S.id_size(cls)
    pre, d, un = inflate_stream(o.openstream('Global/Latest').read())
    import hashlib, pickle
    cd = os.path.expanduser('~/.cache/rvt-schema'); fn = os.path.join(cd, 'es-' + hashlib.sha1(bytes(d)).hexdigest() + '.pkl')
    if not os.environ.get('RVT_NOCACHE'):
        try:
            with open(fn, 'rb') as fh: return pickle.load(fh), sch
        except Exception: pass
    r = find_schemas(d, sch, W)
    if os.environ.get('RVT_NOCACHE'): return r, sch
    try:
        os.makedirs(cd, exist_ok=True); tmp = fn + '.%d.tmp' % os.getpid()
        with open(tmp, 'wb') as fh: pickle.dump(r, fh, protocol=5)
        os.replace(tmp, fn)
    except Exception: pass
    return r, sch
if __name__ == '__main__':
    sc, sch = load(sys.argv[1])
    print(len(sc), 'schemas')
    for g, s in list(sc.items())[:int(sys.argv[2]) if len(sys.argv) > 2 else 8]:
        print(g, s['m_schemaName'], s['m_vendorId'], [(f['m_fieldName'], f['m_fieldTypeName'], f['m_containerType']) for f in s['m_fields']])
