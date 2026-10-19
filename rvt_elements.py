#!/usr/bin/env python3
"""Anchored element extraction from decoded Partitions/NN data (schema-guided).
Currently: sheets (DBViewDrafting: DBView.m_viewName ... DBViewDrafting.m_sheetNumber..m_issueDate)."""
import re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile
from rvtfmt import strip_pages, GZ
import zlib

def load_partitions(path):
    """Return {partition_name: decoded_bytes} for all Partitions/* streams."""
    o = olefile.OleFileIO(path); out = {}
    for e in o.listdir(streams=True):
        if e[0] != 'Partitions': continue
        data = strip_pages(o.openstream('/'.join(e)).read()); buf = bytearray(); pos = 0
        while True:
            i = data.find(GZ, pos)
            if i < 0: break
            d = zlib.decompressobj(-15)
            try: buf += d.decompress(data[i+10:])
            except zlib.error: pos = i + 4; continue
            pos = len(data) - len(d.unused_data)
        out['/'.join(e)] = bytes(buf)
    return out

def read_str(b, p, maxlen=300):
    """u32 nchars + UTF-16LE (printable). returns (text, next_pos) or None"""
    if p + 4 > len(b): return None
    L = struct.unpack_from('<I', b, p)[0]
    if L > maxlen or p + 4 + 2 * L > len(b): return None
    raw = b[p+4:p+4+2*L]
    try: t = raw.decode('utf-16le')
    except UnicodeDecodeError: return None
    if any((not c.isprintable() and c not in '\t\n\r') or c in '\ufffd\uffff\ufffe' for c in t): return None
    return t, p + 4 + 2 * L

def chain(b, p, n):
    out = []
    for _ in range(n):
        r = read_str(b, p)
        if r is None: return None
        out.append(r[0]); p = r[1]
    return out, p

DESIGNER = struct.pack('<I', 8) + 'Designer'.encode('utf-16le')

def _chains(b):
    """All 7-string DBViewDrafting chains found in one partition: (offset_of_sheetNumber, [7 strings])"""
    out = []
    for m in re.finditer(re.escape(DESIGNER), b):
        a = m.start()
        for q in range(a - 240, a - 3):
            r = chain(b, q, 4)
            if r and r[1] == a:
                tail = chain(b, a, 3)
                if tail: out.append((q, r[0] + tail[0]))
                break
    return out

DATE = re.compile(r'^\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}$')

def _chains_dated(b):
    """Second anchor for sheets whose designer/approver were filled in (no 'Designer' default): sheetNumber, a
    date-like m_date, four short strings, and a date-like or empty m_issueDate."""
    out = []
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){5,10}', b):
        a = m.start()
        if a < 4 or struct.unpack_from('<I', b, a - 4)[0] != (m.end() - a) // 2: continue
        if not DATE.match(b[a:m.end()].decode('utf-16le')): continue
        for q in range(max(0, a - 4 - 2 * 16 - 4), a - 4):      # sheetNumber string ending right at the date's length prefix
            r = read_str(b, q, 20)
            if r and r[0].strip() and r[1] == a - 4:
                tail = chain(b, a - 4, 6)
                if tail and all(len(x) <= 30 and x.isprintable() for x in tail[0]) and (tail[0][5] == '' or DATE.match(tail[0][5])):
                    out.append((q, [r[0]] + tail[0]))
                break
    return out

def _strings_before(b, q, span=700):
    """printable non-empty strings ending before q: list of (gap_to_q, text)"""
    rows = []
    for st in range(max(0, q - span), q - 3):
        r = read_str(b, st, 120)
        if r and r[0].strip() and r[1] <= q and len(r[0]) >= 1: rows.append((q - r[1], r[0]))
    return rows

def expected_gap(classes, idsize):
    """Estimate bytes between the end of DBView.m_viewName and DBViewDrafting.m_sheetNumber from the schema
    (null pointer = 6 bytes, empty vector/string = 4, ElementId = idsize). Approximate: used only as a prior."""
    by = {c['name']: c for c in classes}
    if 'DBViewDrafting' not in by: return None
    c = by['DBViewDrafting']; ch = [c]
    while c['parent_tag']: c = classes[c['parent_tag'] - 12]; ch.append(c)
    seq = [f for c in reversed(ch) for f in c['fields']]
    names = [f['name'] for f in seq]
    if 'm_viewName' not in names or 'm_sheetNumber' not in names: return None
    tot = 0
    for f in seq[names.index('m_viewName') + 1:names.index('m_sheetNumber')]:
        t = f['type']; tn = classes[f['ref_tag'] - 12]['name'] if f['ref_tag'] and f['ref_tag'] - 12 < len(classes) else ''
        if t == 'bool': tot += 1
        elif t == 'u16': tot += 2
        elif t in ('u32', 'f32'): tot += 4
        elif t in ('f64', 'u64'): tot += 8
        elif t == 'guid': tot += 16
        elif t.startswith('f64['): tot += 8 * int(t[4:-1])
        elif t == 'string' or ('<' in t and t.startswith('ref')): tot += 4
        elif t.startswith('ref*'): tot += 6
        elif t == 'ref' and tn == 'ElementId': tot += idsize
    return tot

def find_sheets(parts, prior=None):
    """parts: {name: bytes}. Returns list of dicts. The byte gap between m_viewName and m_sheetNumber is constant within
    a file, so learn it as the most common gap among candidate strings, then read every sheet's name at that gap."""
    import collections
    hits = []   # (partition, q, seven_strings, candidates)
    for pn, b in parts.items():
        for q, seven in _chains(b):
            if not seven[0].strip(): continue          # drafting views have an empty sheet number
            hits.append((pn, q, seven, _strings_before(b, q)))
    hist = collections.Counter()
    for _, _, _, cand in hits:
        for g, t in set(cand):
            if 120 <= g <= 400: hist[g] += 1
    gap = None
    if hist:
        g, n = hist.most_common(1)[0]
        if n >= 3 or prior is None: gap = g
        else:
            near = [g2 for g2 in hist if abs(g2 - prior) <= 80]
            gap = min(near, key=lambda g2: abs(g2 - prior)) if near else g
    res = []
    for pn, q, seven, cand in hits:
        name = next((t for g, t in cand if g == gap), '') if gap else ''
        res.append({'partition': pn, 'offset': q, 'sheet_number': seven[0], 'sheet_name': name, 'date': seven[1], 'drawn_by': seven[2],
                    'checked_by': seven[3], 'designed_by': seven[4], 'approved_by': seven[5], 'issue_date': seven[6], 'name_gap': gap})
    # de-duplicate (same sheet appears in several partitions/history copies)
    seen = set(); uniq = []
    for r in res:
        k = (r['sheet_number'], r['sheet_name'])
        if k not in seen: seen.add(k); uniq.append(r)
    return uniq

if __name__ == '__main__':
    import export_schemas as ES
    o = olefile.OleFileIO(sys.argv[1]); info = ES.build_info(o)
    js, _ = ES.export(sys.argv[1], os.environ.get('TMPDIR', '/tmp'))
    idsize = 8 if int(info['format'] or info['revit'] or 0) >= 2024 else 4
    prior = expected_gap(js['classes'], idsize)
    parts = load_partitions(sys.argv[1])
    print(f"# revit={info['revit']} idsize={idsize} prior_gap={prior}")
    for r in find_sheets(parts, prior): print(f"{r['sheet_number']:>8} | {r['sheet_name']:<40} | drawn={r['drawn_by']} issue={r['issue_date']} (gap {r['name_gap']})")
