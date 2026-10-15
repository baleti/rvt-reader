"""Validate rvt_materials.py against the Revit oracle gt_mat/*.tsv (MAT / APP / APROP / FMAT / LAYER rows).  usage: gtg_mat.py corpus-file [more files]"""
import sys, os, re, collections
sys.path.insert(0, '/home/user1/rvt-research')
import rvt_materials as RM, rvt_elemmesh as E
def kv(t): return dict(x.split('=', 1) for x in t if '=' in x)
tot = collections.Counter(); bad = collections.defaultdict(list)
for f in sys.argv[1:]:
    y = f.split('/')[-2]; b = os.path.basename(f); tsv = '/home/user1/rvt-research/gt_mat/%s_%s.tsv' % (y, b)
    mt = RM.material_table(f); app = RM.appearance_table(f); doc = None
    aprop = collections.defaultdict(dict); appn = {}
    for l in open(tsv, encoding='utf-8'):
        t = l.rstrip('\n').split('\t')
        if t[0] == 'APROP' and len(t) >= 5: aprop[int(t[1])][t[2]] = (t[3], t[4])
        elif t[0] == 'APP': appn[int(t[1])] = kv(t[2:])
    for l in open(tsv, encoding='utf-8'):
        t = l.rstrip('\n').split('\t')
        if t[0] == 'MAT':
            mid = int(t[1]); d = kv(t[2:]); m = mt.get(mid); tot['MAT'] += 1
            if m is None: bad['MAT missing'].append(mid); continue
            ok = {}
            ok['name'] = m['name'] == d['name']; ok['class'] = (m['class'] or '') == d['class']; ok['category'] = (m['category'] or '') == d['category']
            ok['color'] = m['color'] == [int(x) for x in d['color'].split(',')]
            ok['transparency'] = abs(round((m['transparency'] or 0) * 100) - int(d['transparency'])) <= 1
            ok['shininess'] = m['shininess'] == int(d['shininess']); ok['smoothness'] = round((m['smoothness'] or 0) * 100) == int(d['smoothness'])
            ok['appearance_id'] = (m['appearance_asset_id'] or -1) == int(d['appearanceAssetId'])
            for pn, key in (('cutPattern', 'cut_pattern'), ('surfPattern', 'surface_pattern')):
                pid, r_, g_, b_ = [int(x) for x in d[pn].split(',')]
                ok[pn] = (m[key]['id'] or -1) == pid
            for k, v in ok.items():
                tot['MAT.' + k] += 1; tot['MAT.' + k + '.ok'] += v
                if not v: bad['MAT.' + k].append(mid)
        elif t[0] == 'APP':
            aid = int(t[1]); a = app.get(aid); tot['APP'] += 1
            if a is None: bad['APP missing'].append(aid); continue
            d = kv(t[2:]); sch = d.get('schema', '').split('/')[0]
            tot['APP.schema'] += 1; tot['APP.schema.ok'] += (a['schema'] == sch or a['properties'].get('BaseSchema') == sch)
            for pn, (ty, val) in aprop[aid].items():
                if pn in ('thumbnail', 'category', 'keyword', 'ExchangeGUID') or '.connected' in pn: continue
                tot['APROP'] += 1
                if '::' in pn:                                   # property of a connected (texture) asset: parent::child
                    par, ch = pn.split('::', 1); raw = a['raw'].get(par); got = None
                    if isinstance(raw, dict):
                        for c in raw.get('connected', []):
                            if ch in c['props']: got = c['props'][ch]; break
                        if got is None and ch == 'BaseSchema': got = next((c['schema'] for c in raw.get('connected', [])), None)
                else: got = a['properties'].get(pn)
                if isinstance(got, dict): got = got.get('value')
                if ty == 'Integer' and got is not None and int(got) >= 2**31: got = int(got) - 2**32
                try:
                    if ty.startswith('Double') or ty in ('Float',):
                        want = [float(x) for x in val.split(',')]; g = got if isinstance(got, list) else [got]
                        okp = g is not None and len(g) >= len(want) and all(abs(float(a_) - w) <= 1e-4 * max(1, abs(w)) for a_, w in zip(g, want))
                    elif ty == 'Boolean': okp = bool(int(got)) == (val == 'True') if got is not None else False
                    elif ty == 'Integer': okp = int(got) == int(val)
                    else:
                        gs = '' if got is None else str(got).replace('\\', '/'); vs = val.replace('\\', '/')
                        try: okp = abs(float(gs) - float(vs)) < 1e-6
                        except Exception: okp = gs == vs
                except Exception: okp = False
                tot['APROP.ok'] += okp
                if not okp: bad['APROP ' + pn].append((aid, str(got)[:30], val[:30]))
        elif t[0] == 'LAYER':
            tot['LAYER'] += 1
    print(b, 'done')
for k in sorted(tot):
    if not k.endswith('.ok'): print('%-22s %6d  ok %6d  %5.1f%%' % (k, tot[k], tot.get(k + '.ok', tot[k]) if k != 'MAT' and k != 'APP' else tot[k], 100.0 * tot.get(k + '.ok', tot[k]) / max(tot[k], 1)))
for k, v in sorted(bad.items(), key=lambda a: -len(a[1]))[:12]: print('MISMATCH', k, len(v), v[:3])
