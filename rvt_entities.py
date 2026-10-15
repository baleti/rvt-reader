#!/usr/bin/env python3
"""Fast entity extraction from a Revit file (2011-2026): decodes only the record classes that carry user-facing content.
extract(path) -> dict with: counts (internal class -> n), levels, grids, rooms, views, sheets, phases, families, types, materials, textnotes, params"""
import sys, os, re, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('RVT_GEOM', '1')
import numpy as np
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
try: sys.path.append(os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as _F
except Exception: _F = None

M2FT = 0.3048
def rtf_text(b):
    t = b.decode('cp1252', 'ignore') if isinstance(b, (bytes, bytearray)) else str(b)
    t = re.sub(r'\{\\\*[^{}]*\}', '', t); t = re.sub(r'\{\\fonttbl.*?\}\}', '', t, flags=re.S); t = re.sub(r'\{\\colortbl[^}]*\}', '', t)
    t = re.sub(r"\\'([0-9a-f]{2})", lambda m: bytes.fromhex(m.group(1)).decode('cp1252', 'ignore'), t)
    t = re.sub(r'\\par\b', '\n', t); t = re.sub(r'\\[a-zA-Z]+-?\d* ?', '', t); t = re.sub(r'[{}]', '', t)
    return '\n'.join(l.strip() for l in t.replace('\x00', '').splitlines() if l.strip())

WANT_PREFIX = ('DBView', 'Viewport')
WANT = {'Level', 'Grid', 'RoomElem', 'ProjectPhase', 'Family', 'FamSymSurrogate', 'FamilySurrogate', 'MaterialElem', 'TextNote', 'ProjectInfo', 'RefPlane', 'AreaSchemeElem', 'Viewport',
        'ParamElemProject', 'ParamElemExternal', 'ParamElemFamily', 'SunAndShadowSettings', 'HVACLoadSpaceTypeElem',
        'RbsPipeCurve', 'RbsDuctCurve', 'RbsConduitCurve', 'CableTray', 'SWall'}

def _run_work(rng): return _WORK(*rng)

def extract(path, extra=(), only_ids=None, want_all=False, slim=None):
    """slim: optional predicate class_name -> bool; records of classes for which it is False are kept as {'id','class','fields':{}} (class census only; large files then stay within ~1 GB)"""
    if _F and _F.on(): return _F.extract(path, extra=extra, only_ids=only_ids, want_all=want_all, slim=slim)
    o, cls, ids = S.load(path); W = S.id_size(cls); F = '<I' if W == 4 else '<Q'; sch = D.Schema(cls); dec = D.make_dec(sch, idsize=W); idarr = np.array(sorted(ids), dtype=np.uint32 if W == 4 else np.uint64)
    EH = sch.by.get('ElementHeader', -999) + 12; names = {i + 12: c['name'] for i, c in enumerate(cls)}; et = I.element_tags(cls)
    wanted = {t for t, n in names.items() if t in et and (n in WANT or n.startswith(WANT_PREFIX)) and n != 'DBView'}
    if extra or want_all: wanted = {t for t, n in names.items() if t in et and (want_all or n in extra)}
    import rvt_es as ES
    try: dec.es_schemas = ES.load(path)[0]
    except Exception: dec.es_schemas = {}
    counts = collections.Counter(); recs = {}; eh = {}
    import multiprocessing as mp
    def _auto_workers():
        # forked workers each dirty ~1 GB of the master's heap (refcount writes): size the pool from the cgroup memory limit when there is one
        n = min(6, os.cpu_count() or 1)
        try:
            cg = open('/proc/self/cgroup').read().strip().split('::')[-1]
            lim = open('/sys/fs/cgroup%s/memory.max' % cg).read().strip()
            if lim != 'max': n = max(1, min(n, int((int(lim) / 2**30 - 2.5) / 1.5)))
        except Exception: pass
        return n
    NW = int(os.environ.get('RVT_WORKERS', _auto_workers()))
    def work(lo, hi):
        """decode candidates cand[lo:hi] of the current chunk (inherited through fork); returns ([( (eid,cls), rec )], [(eid, fields)])"""
        lrecs = {}; leh = {}
        for i in (CAND[lo:hi].tolist() if hasattr(CAND, 'tolist') else CAND[lo:hi]):
            eid = struct.unpack_from(F, CHUNK, i + 4)[0]
            if only_ids is not None and eid not in only_ids: continue
            for short in (False, True):
                tag = struct.unpack_from('<H', CHUNK, i + 12 + W - (4 if short else 0))[0]
                if tag in wanted:
                    if (eid, names[tag]) in lrecs: continue
                    try: r, q = dec.record(CHUNK, i, short)
                    except Exception: continue
                    if r['fields'].get('m_id') == eid and r['id'] == eid:
                        if slim is not None and not slim(r['class']): r = {'id': r['id'], 'class': r['class'], 'fields': {}, 'complete': r.get('complete')}
                        lrecs.setdefault((eid, r['class']), r); break
                elif tag == EH:
                    if eid in leh: break
                    try: r, q = dec.record(CHUNK, i, short)
                    except Exception: continue
                    if r.get('complete') and not r.get('error') and r['id'] == eid: leh[eid] = r['fields']; break
        return list(lrecs.items()), list(leh.items())
    global CHUNK, CAND, _WORK
    _WORK = work
    for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
        CHUNK = T.joined(o.openstream(pn).read()); CAND = S.header_candidates(CHUNK, idarr, W) if os.environ.get('RVT_OLDCAND') else S.header_candidates_tagged(CHUNK, idarr, W, wanted | {EH})
        if NW > 1 and len(CAND) > 4000:
            step = max(2000, (len(CAND) + NW * 64 - 1) // (NW * 64)); rngs = [(k, min(k + step, len(CAND))) for k in range(0, len(CAND), step)]
            with mp.get_context('fork').Pool(NW, maxtasksperchild=64) as pool:
                for lr, le in pool.imap(_run_work, rngs):      # ordered, merged as they arrive: first record wins, as in the sequential loop; no list of all results held at once
                    for k, r in lr: recs.setdefault(k, r)
                    for k, v in le: eh.setdefault(k, v)
        else:
            for lr, le in [work(0, len(CAND))]:
                for k, r in lr: recs.setdefault(k, r)
                for k, v in le: eh.setdefault(k, v)
    return dict(eh=eh, recs=recs, W=W, sch=sch)

def S_(r, *path, default=None):
    v = r
    for p in path:
        if isinstance(v, dict) and p in v: v = v[p]
        elif isinstance(v, dict) and 'obj' in v and isinstance(v['obj'], dict) and p in v['obj']: v = v['obj'][p]
        else: return default
    if isinstance(v, dict) and 'obj' in v: v = v['obj']
    return v

def parse(path):
    x = extract(path); W = x['W']; by = collections.defaultdict(list); recs = {}; own = S.owners(path)
    for (eid, c), r in x['recs'].items():
        if own.get(eid) is not None and c in ('Level', 'Grid', 'RoomElem', 'DBViewDrafting'): continue     # copies owned by groups / assemblies, not project-level elements
        by[c].append(r); recs.setdefault(eid, r)
    nm = lambda i: (recs[i]['fields'].get('m_text') or recs[i]['fields'].get('m_viewName') or recs[i]['fields'].get('m_name') or '') if i in recs else ''
    import json as _j
    cat = _j.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'category_names.json')))
    def sc(v): v = int(v); return v - (1 << (8 * W)) if v >= 1 << (8 * W - 1) else v
    ccount = collections.Counter(cat.get(str(sc(h['m_categroryId'])), 'cat %d' % sc(h['m_categroryId'])) for h in x['eh'].values())
    out = {'counts': dict(ccount.most_common())}
    cat_of = lambda i: sc(x['eh'][i]['m_categroryId']) if i in x['eh'] else None
    out['levels'] = sorted([{'id': r['id'], 'name': r['fields'].get('m_text', ''), 'elevation_ft': (S_(r['fields'], 'm_pSurface', 'm_origin') or [None] * 3)[2]} for r in by['Level']], key=lambda l: (l['elevation_ft'] is None, l['elevation_ft']))
    import rvt_geom as Gm
    q = {}
    for c, label in (('SWall', 'Walls'), ('RbsDuctCurve', 'Ducts'), ('RbsPipeCurve', 'Pipes'), ('RbsConduitCurve', 'Conduits'), ('CableTray', 'Cable trays')):
        tot = n = 0.0
        for r in by.get(c, []):
            cu = Gm.primary_curve(r['fields']); L = Gm.curve_length(cu) if cu is not None else None
            if L is not None: tot += L; n += 1
        if n: q[label] = {'count': int(n), 'length_m': tot * 0.3048}
    out['quantities'] = q
    out['grids'] = sorted(r['fields'].get('m_text', '') for r in by['Grid'])
    rooms = []
    for r in by['RoomElem']:
        f = r['fields']; ps = (S_(f, 'm_pParamValueSetAString', 'm_paramSet') or [])
        vals = [p['m_value'] for p in ps if isinstance(p, dict)]
        kind = {-2000160: 'Room', -2003600: 'Space', -2003200: 'Area'}.get(cat_of(r['id']), 'Room')
        rooms.append({'kind': kind, 'id': r['id'], 'number': vals[0] if vals else '', 'name': vals[1] if len(vals) > 1 else '', 'level': nm(int(f.get('m_levelId', -1))) or nm(int(f.get('m_assocLevelId', -1))), 'point': f.get('m_point')})
    out['rooms'] = rooms
    views = []; sheets = []
    for c, lst in by.items():
        if not c.startswith('DBView'): continue
        for r in lst:
            f = r['fields']; n = f.get('m_viewName')
            if n is None: continue
            if c == 'DBViewDrafting' and f.get('m_sheetNumber'):
                sheets.append({'id': r['id'], 'number': f.get('m_sheetNumber'), 'name': n, 'issue_date': f.get('m_issueDate'), 'drawn_by': f.get('m_drawnBy'), 'viewports': [int(v) for v in (f.get('m_sheetViewportElemIds') or [])]})
            else: views.append({'id': r['id'], 'name': n, 'class': c, 'template': bool(f.get('m_isTemplate')), 'scale': f.get('m_scale')})
    vp = {r['id']: int(r['fields'].get('m_dbViewId', -1)) for r in by['Viewport']}
    for s in sheets: s['views'] = [nm(vp[v]) for v in s.pop('viewports') if v in vp and vp[v] in recs]
    out['views'] = sorted(views, key=lambda v: (v['class'], v['name'])); out['sheets'] = sorted(sheets, key=lambda s: str(s['number']))
    out['phases'] = [r['fields'].get('m_name') for r in by['ProjectPhase']]
    out['families'] = sorted({r['fields'].get('m_name') for r in by['Family'] if r['fields'].get('m_name')})
    out['types'] = sorted({r['fields'].get('m_name') for c in ('FamSymSurrogate', 'FamilySurrogate') for r in by[c] if r['fields'].get('m_name')})
    out['materials'] = sorted({S_(r['fields'], 'm_pMaterial', 'm_name') for r in by['MaterialElem'] if S_(r['fields'], 'm_pMaterial', 'm_name')})
    out['textnotes'] = [t for t in (rtf_text(S_(r['fields'], 'm_oSavedRtfData', 'm_arrRtfStream') or b'') for r in by['TextNote']) if t]
    out['params'] = sorted({S_(r['fields'], 'm_pParamDef', 'm_caption') for c in ('ParamElemProject', 'ParamElemExternal', 'ParamElemFamily') for r in by[c] if S_(r['fields'], 'm_pParamDef', 'm_caption')})
    return out

if __name__ == '__main__':
    import json, time
    t = time.time(); r = parse(sys.argv[1]); print(json.dumps({k: (v if k in ('counts',) else (v[:6] if isinstance(v, list) else v)) for k, v in r.items()}, default=str)[:3000]); print('secs', round(time.time() - t, 1))
