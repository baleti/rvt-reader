#!/usr/bin/env python3
"""rvt2text - plain-text extraction from Revit files (.rvt .rfa .rte .rft) with no Autodesk code.

  header + project metadata, editors, external references, sheets (number / name / dates), and the distinct
  human-readable strings found in the model data (family, type, material, level, room, text-note names, ...).

Bounded memory: partitions are decoded one gzip segment at a time. Every stage is wrapped so one failing stage never
loses the others; the exit status is 0 whenever any text was produced.

Usage:  rvt2text.py FILE [--max-strings N] [--json]
"""
import sys, os, re, io, zlib, struct, zipfile, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile
from rvtfmt import strip_pages, inflate_stream, GZ
import fmt_parser as fp
import export_schemas as ES
import rvt_elements as RE

NOISE = re.compile(r'^(autodesk\.|revit\.local|SecretInternal|common_|unifiedbitmap|urn:|[0-9a-f]{8}-[0-9a-f]{4}-|.*_colorspace$|.*\.fbx$)', re.I)
SKIP_EXACT = {'Arial', 'Type', 'Name', 'Generic', '<None>', 'auto', 'all', 'Solid', 'Hidden'}
PR = re.compile(rb'(?:[\x20-\x7e]\x00){3,}')

def segments(stored):
    """Yield decoded chunks of one (possibly multi-member) paged stream, one gzip member at a time."""
    data = strip_pages(stored); pos = 0
    while True:
        i = data.find(GZ, pos)
        if i < 0: return
        d = zlib.decompressobj(-15)
        try: out = d.decompress(data[i + 10:])
        except zlib.error: pos = i + 4; continue
        yield out
        pos = len(data) - len(d.unused_data)

def joined(stored):
    """all decoded gzip members of one partition as ONE buffer (records can straddle member boundaries)"""
    return b''.join(segments(stored))

def clean_strings(buf, base_off=0):
    """Length-prefixed UTF-16 strings (u32 nchars + chars): exact boundaries, no fragments."""
    for m in PR.finditer(buf):
        s = m.start()
        if s < 4: continue
        L = struct.unpack_from('<I', buf, s - 4)[0]; run = (m.end() - s) // 2
        if 3 <= L <= run and L <= 200:
            yield buf[s:s + 2 * L].decode('utf-16le')

def clean(l):
    return ''.join(c for c in l if c.isprintable()).strip()

def basic_info(o):
    b = o.openstream('BasicFileInfo').read(); i = b.find('Worksharing'.encode('utf-16le'))
    if i < 0:   # old layout: text starts after a few header bytes
        t = b.decode('utf-16le', 'ignore')
        return [clean(l) for l in re.split(r'[\r\n]+', t) if re.search(r'(Build|Format|Worksharing|Path|Username|Locale)', l)]
    return [clean(l) for l in b[i:].decode('utf-16le', 'ignore').splitlines() if l.strip()]

def run(path, max_strings=30000):
    out = []; add = out.append; res = {}
    o = olefile.OleFileIO(path)
    names = ['/'.join(e) for e in o.listdir(streams=True)]
    add(f'# Revit file: {os.path.basename(path)}')
    try:
        info = ES.build_info(o); res['info'] = info
        add(f"Revit version: {info.get('revit')}  format: {info.get('format')}  build: {info.get('build')}")
        for l in basic_info(o):
            if not re.search(r'(GUID|Identity|Author:|ClientAppName|IsSingleUser)', l): add(l)
    except Exception as e: add(f'[basic info failed: {e}]')
    try:
        if 'ProjectInformation' in names:
            z = zipfile.ZipFile(io.BytesIO(o.openstream('ProjectInformation').read()))
            x = z.read(z.namelist()[0]).decode('utf-8', 'replace')
            t = re.search(r'<title>([^<]+)', x)
            if t: add('Project title: ' + t.group(1))
    except Exception as e: add(f'[project information failed: {e}]')
    try:
        if 'TransmissionData' in names:
            t = o.openstream('TransmissionData').read().decode('utf-16le', 'ignore')
            for p in sorted(set(re.findall(r'<LastSavedAbsolutePath>([^<]+)', t))): add('External reference: ' + p)
    except Exception: pass
    try:
        pre, dit, _ = inflate_stream(o.openstream('Global/DocumentIncrementTable').read())
        eds = collections.Counter(m.group().decode('utf-16le') for m in PR.finditer(dit))
        users = [u for u, n in eds.most_common() if re.search(r'[A-Za-z]{3}', u)]
        if users: add('Editors: ' + ', '.join(users[:30]))
    except Exception: pass

    # schema prior for sheet-name offset
    prior = None; idsize = 4
    try:
        pre, fm, _ = inflate_stream(o.openstream('Formats/Latest').read())
        cls, variant = fp.parse(fm)
        classes = [{'name': c['name'], 'parent_tag': c['parent'] & 0x7fff,
                    'fields': [{'name': f['name'], 'type': ES.tname(f['types'], f), 'ref_tag': (f['ref'] & 0x7fff) if 'ref' in f else None} for f in c['fields']]}
                   for c in cls]
        idsize = 8 if int(res['info'].get('format') or res['info'].get('revit') or 0) >= 2024 else 4
        prior = RE.expected_gap(classes, idsize)
        add(f'Schema: {len(cls)} classes')
    except Exception as e: add(f'[schema failed: {e}]')

    strings = collections.Counter(); hits = []
    try:
        tail = b''
        for pn in [n for n in names if n.startswith('Partitions/')]:
            tail = b''
            for chunk in segments(o.openstream(pn).read()):
                buf = tail + chunk
                for q, seven in RE._chains(buf) + [c for c in RE._chains_dated(buf) if c[0] not in {x[0] for x in RE._chains(buf)}]:
                    if seven[0].strip(): hits.append((pn, q, seven, RE._strings_before(buf, q)))
                if len(strings) < max_strings * 3:
                    for s in clean_strings(buf): strings[s] += 1
                tail = chunk[-2048:]
    except Exception as e: add(f'[partitions failed: {e}]')

    # sheets
    try:
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
        seen = set(); sheets = []
        for pn, q, seven, cand in hits:
            name = next((t for g, t in cand if g == gap), '') if gap else ''
            k = (seven[0], name)
            if k in seen: continue
            if not name and not seven[2].strip() and not seven[6].strip(): continue   # placeholder, not a real sheet
            seen.add(k); sheets.append({'number': seven[0], 'name': name, 'date': seven[1], 'drawn_by': seven[2], 'issue_date': seven[6]})
        res['sheets'] = sheets
        if sheets:
            add(f'Sheets ({len(sheets)}):')
            for s in sorted(sheets, key=lambda s: s['number']): add(f"  Sheet {s['number']} - {s['name']}" + (f"  (issued {s['issue_date']})" if s['issue_date'] else ''))
    except Exception as e: add(f'[sheets failed: {e}]')

    # names / text
    try:
        keep = []
        for s, n in strings.most_common():
            s2 = s.strip()
            if len(s2) < 3 or s2 in SKIP_EXACT or NOISE.match(s2): continue
            if not re.search(r'[A-Za-z]{2}', s2): continue
            keep.append(s2)
            if len(keep) >= max_strings: break
        res['strings'] = len(keep)
        add(f'Names and text ({len(keep)}):')
        out.extend(keep)
    except Exception as e: add(f'[strings failed: {e}]')
    return out, res

if __name__ == '__main__':
    ap = sys.argv[1:]
    if not ap: print(__doc__); sys.exit(2)
    ms = int(ap[ap.index('--max-strings') + 1]) if '--max-strings' in ap else 30000
    try:
        lines, res = run(ap[0], ms)
    except Exception as e:
        print(f'rvt2text: cannot read {ap[0]}: {e}', file=sys.stderr); sys.exit(1)
    sys.stdout.write('\n'.join(lines) + '\n')
