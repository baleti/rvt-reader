#!/usr/bin/env python3
"""Export the parsed Formats/Latest class schema of each .rvt as JSON + a cross-version summary."""
import sys, os, re, json, glob, olefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rvtfmt import inflate_stream
import fmt_parser as fp
PRIM = {0x01:'bool',0x02:'u16',0x04:'u32',0x05:'u32',0x06:'f32',0x07:'f64',0x08:'string',0x09:'guid',0x0b:'u64',0x0d:'array',0x0e:'ref'}
def tname(types, f):
    k = types[0] & 0xff; fl = (types[0] >> 8) & 0xff
    base = PRIM.get(k, f'0x{k:02x}')
    if k == 0x0d: base = 'array<' + PRIM.get(types[-1] & 0xff, '?') + '>'
    mod = {0x00:'',0x10:f"[{f.get('n','?')}]",0x50:'<vector>',0x51:'<set>',0x60:'',0x01:'*',0x02:'**',0x03:'***'}.get(fl, f'/{fl:02x}')
    return base + mod
def build_info(o):
    b = o.openstream('BasicFileInfo').read()
    i = b.find('Worksharing'.encode('utf-16le'))
    t = b[i:].decode('utf-16le', 'ignore') if i >= 0 else b.decode('utf-16le', 'ignore')
    g = lambda k: (re.search(k + r':\s*([^\r\n]*)', t) or [None, None])[1]
    build = g('Build'); rb = g('Revit Build')
    fmt = g('Format'); rev = None
    if rb:
        m = re.search(r'Autodesk Revit[^(]*?(\d{4})\s*\(Build:\s*([^)]*\)?)', rb); 
        if m: rev, build = m.group(1), (m.group(2) if m.group(2).endswith(')') else m.group(2) + ')')
    if not rev: rev = fmt
    return {'format': fmt, 'build': build, 'revit': rev}
def export(path, outdir):
    o = olefile.OleFileIO(path); info = build_info(o)
    pre, out, un = inflate_stream(o.openstream('Formats/Latest').read())
    classes, variant = fp.parse(out)
    js = {'file': os.path.basename(path), **info, 'layout': variant, 'classes': []}
    for i, c in enumerate(classes):
        js['classes'].append({'index': i, 'name': c['name'], 'parent_tag': c['parent'] & 0x7fff, 'parent_inline': bool(c['parent'] & 0x8000),
                              'parent_name': c.get('parent_def'), 'version_word': c['X'], 'guid_count': len(c.get('guids', [])),
                              'fields': [{'name': f['name'], 'type': tname(f['types'], f), 'ref_tag': f.get('ref', 0) & 0x7fff if 'ref' in f else None, 'inline_class': f.get('def')} for f in c['fields']]})
    tag = os.path.basename(path).split('.')[0][:30]
    p = os.path.join(outdir, f'formats-{tag}.json'); json.dump(js, open(p, 'w'), indent=1); return js, p
if __name__ == '__main__':
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True); rows = []
    for f in sys.argv[2:]:
        try:
            js, p = export(f, outdir); names = {c['name'] for c in js['classes']}
            rows.append((js['revit'], js['file'], js['build'], len(js['classes']), sum(len(c['fields']) for c in js['classes']), names))
            print(f"{js['revit']} {js['file'][:34]:34} build={js['build']} classes={len(js['classes'])} fields={rows[-1][4]}")
        except Exception as e: print('FAIL', f, e)
    base = {r[0]: r[5] for r in rows}
    ys = sorted(base)
    print('\nclass names added/removed between consecutive Revit versions in the sample set:')
    for a, b in zip(ys, ys[1:]): print(f'  {a} -> {b}: +{len(base[b]-base[a])} -{len(base[a]-base[b])}  (common {len(base[a]&base[b])})')
