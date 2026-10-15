"""Compare element_mesh results with the Revit geometry oracle gt_geom/<file>.tsv (session 181): per element sum of solids (volume, area, centroid), element bbox (BB), classes from EL.
Usage: gt_geom_cmp.py corpus/2020/18_rst_basic_sample_project.rvt out.jsonl"""
import sys, os, json, collections
sys.path.insert(0, '/home/user1/rvt-research'); os.environ['RVT_GEOM'] = '1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f, out = sys.argv[1:3]; y = f.split('/')[-2]; b = os.path.basename(f)
tsv = '/home/user1/rvt-research/gt_geom/%s_%s.tsv' % (y, b)
if not os.path.exists(tsv): tsv = '/home/user1/rvt-research/gt_geom/%s.tsv' % os.path.splitext(b)[0]
finst = {}; chain = {}; lastd = {}; wsum = {}
cls = {}; sol = collections.defaultdict(lambda: [0.0, 0.0, np.zeros(3), 0]); bbox = {}
for ln in open(tsv, encoding='utf-8'):
    t = ln.rstrip('\n').split('\t')
    if t[0] == 'EL': cls[int(t[1])] = t[2]
    elif t[0] == 'FINST':
        kv = dict(x.split('=', 1) for x in t[2:] if '=' in x)
        try:
            tr = [np.array([float(x) for x in v.split(',')]) for v in kv['transform'].split(';')]
            finst[int(t[1])] = tr
        except Exception: pass
    elif t[0] == 'I':
        kv = dict(x.split('=', 1) for x in t[2:] if '=' in x)
        try:
            tr = [np.array([float(x) for x in v.split(',')]) for v in kv['transform'].split(';')]
            chain.setdefault(int(t[1]), {})[int(kv['depth'])] = tr; lastd[int(t[1])] = int(kv['depth'])
            for dd in [k for k in chain[int(t[1])] if k > int(kv['depth'])]: del chain[int(t[1])][dd]
        except Exception: pass
    elif t[0] == 'G':
        eid = int(t[1].split('.')[0]); kv = dict(x.split('=', 1) for x in t[2:] if '=' in x)
        if not kv.get('centroid'): continue
        v = float(kv['volume']); s = sol[eid]; s[0] += v; s[1] += float(kv['area']); c_ = np.array([float(x) for x in kv['centroid'].split(',')]); s[2] += v * c_; s[3] += 1
        ch = chain.get(eid)
        if ch:                                     # world centroid: compose the instance transforms from the deepest level up to the root
            p = c_
            gdepth = int(t[1].split('.')[1]) - 1 if t[1].count('.') >= 2 else 99        # G eid.N.M: N-1 = instance depth of this solid
            for dd in sorted([k for k in ch if k <= gdepth], reverse=True):
                o_, bx, by, bz = ch[dd]; p = o_ + p[0] * bx + p[1] * by + p[2] * bz
            wsum[eid] = wsum.get(eid, np.zeros(3)) + v * p
    elif t[0] == 'BB' and len(t) >= 4:
        bbox[int(t[1])] = (np.array([float(x) for x in t[2].split(',')]), np.array([float(x) for x in t[3].split(',')]))
doc = EM.Doc(f); rows = []
only = set(int(x) for x in os.environ['ONLY'].split(',')) if os.environ.get('ONLY') else None
for eid, (v, a, cs, n) in sol.items():
    if only and eid not in only: continue
    rc = (cs / v) if v else None
    row = {'eid': eid, 'cls': cls.get(eid, '?'), 'rvol': v, 'rarea': a, 'rcent': rc.tolist() if rc is not None else None, 'rcent_chain': ((wsum[eid] / v).tolist() if (eid in wsum and v) else None), 'rcent_world': ((finst[eid][0] + rc[0] * finst[eid][1] + rc[1] * finst[eid][2] + rc[2] * finst[eid][3]).tolist() if (rc is not None and eid in finst and len(finst[eid]) == 4) else None), 'rbb': [bbox[eid][0].tolist(), bbox[eid][1].tolist()] if eid in bbox else None}
    if eid not in doc.res: row['status'] = 'no_saved_graphics'; rows.append(row); continue
    m = EM.element_mesh(doc, eid, detail=3)
    if not m['tris']: row['status'] = 'empty_mesh'; rows.append(row); continue
    P = np.array([p for t in m['tris'] for p in t]); row['mbb'] = [P.min(0).tolist(), P.max(0).tolist()]
    if abs(v) < 1e-7 * max(1.0, abs(a)):                 # zero-volume 'solids' of the oracle (analytical surfaces, filled regions, mass level data): compare the sheet area
        seen_t = set(); ar = 0.0; cs_ = np.zeros(3)
        for tr in m['tris']:
            sg = tuple(sorted(tuple(np.round(np.asarray(p) * 1e4).astype(np.int64)) for p in tr))
            if sg in seen_t: continue
            seen_t.add(sg); p0, p1, p2 = [np.asarray(p, float) for p in tr]; a_ = np.linalg.norm(np.cross(p1 - p0, p2 - p0)) / 2; ar += a_; cs_ += a_ * (p0 + p1 + p2) / 3
        row['rarea'] = abs(a); row.update(status='mesh', source=m['source'], closed=True, mvol=0.0, marea=ar, mcent=(cs_ / ar).tolist() if ar else None, ntri=len(m['tris']), sheet=True)
        rows.append(row); continue
    if m.get('nid') and len(m['nid']) == len(m['tris']):
        vol, closed, area, nn, cen = M.volume_by_node(m['tris'], m.get('meta'), m['nid'], centroid=True, fid=m.get('fid'))
    else:
        vol, closed, _, area = M.mesh_volume(m['tris']); cen = None
    row.update(status='mesh', source=m['source'], closed=bool(closed), mvol=vol if closed else None, marea=area if closed else None, mcent=(np.asarray(cen).tolist() if (closed and cen is not None) else None), ntri=len(m['tris']))
    rows.append(row)
with open(out, 'w') as fh:
    for r in rows: fh.write(json.dumps(r) + '\n')
print(os.path.basename(f), len(rows), 'elements with solids in the oracle')
