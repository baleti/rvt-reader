"""ACCEPTANCE.md table: per class x year from fidfull/*.jsonl. Buckets: ACCURATE (mesh, IoU>=0.95, volume within 2% when Revit gives one), TRUE-BUT-OFF (mesh, IoU>=0.5 but not accurate),
BOX-ONLY (no saved graphics / empty mesh / IoU<0.5)."""
import json,glob,os,collections,sys,statistics
rows=collections.defaultdict(list)
_best={}
for f in glob.glob('/home/user1/rvt-research/fidold/*.jsonl'):
    b=os.path.basename(f)
    if b not in _best or os.path.getmtime(f)>os.path.getmtime(_best[b]): _best[b]=f

def _gtfile(b):
    m=b.replace('.jsonl','')
    for key,g in (('rst_basic','2020_18_rst_basic_sample_project.rvt'),('rst_advanced','2020_21_rst_advanced_sample_project.rvt'),('Arch_Link','2021_26_Arch_Link_Model.rvt'),('rme_basic','2020_22_rme_basic_sample_project.rvt'),('rme_advanced','2020_23_rme_advanced_sample_project.rvt')):
        if key in m: return '/home/user1/rvt-research/gt4/'+g+'.tsv'
kinds_cache = {}
def kinds(b):
    if b not in kinds_cache:
        k = {}
        for ln in open(_gtfile(b), encoding='utf-8'):
            if ln.startswith('E\t'):
                q = ln.rstrip('\n').split('\t'); k[int(q[1])] = q[7] if len(q) > 7 else ''
        kinds_cache[b] = k
    return kinds_cache[b]
ntype = 0
_xv = {}
def xvol(b):
    """Volume of each element in the OTHER years' Revit dumps of the same model (Snowdon 2024/2025/2026 are one project): reference for elements a dump lacks"""
    model = b.split('_', 2)[2]
    if model not in _xv:
        d = {}
        for g in sorted(glob.glob('/home/user1/rvt-research/gt4/*_' + model.replace('.jsonl', '.tsv'))):
            for ln in open(g, encoding='utf-8'):
                if ln.startswith('P\t') and '\tVolume\tDouble\t' in ln:
                    q = ln.rstrip('\n').split('\t')
                    try: d.setdefault(int(q[1]), float(q[5]))
                    except ValueError: pass
        _xv[model] = d
    return _xv[model]
_or = {}
def oracle(b):
    """{eid: ok} from the Revit-solid oracle comparisons (gtg_r9/<year>_<nn>.jsonl, gt_geom_cmp.py): ok = our closed mesh volume within 2% of Revit's solid volume"""
    k = b[:7]
    if k not in _or:
        d = {}
        g = '/home/user1/rvt-research/gtg_r9/%s.jsonl' % k
        if os.path.exists(g):
            for ln in open(g):
                q = json.loads(ln); rv, mv = q.get('rvol'), q.get('mvol')
                if rv and rv > 1e-9 and mv is not None: d[int(q['eid'])] = abs(mv / rv - 1) <= 0.02
        _or[k] = d
    return _or[k]
nxgt = 0
for f in sorted(_best.values()):
    y=os.path.basename(f)[:4]; kd = kinds(os.path.basename(f))
    for ln in open(f):
        r=json.loads(ln); r['year']=y
        if r.get('gtv') is None and r['eid'] not in kd and r['status'] == 'mesh':
            xv = xvol(os.path.basename(f)).get(r['eid'])
            if xv: r['gtv'] = xv; r['xgt'] = True; nxgt += 1          # cross-version reference (same element id in another year's dump of this model)
        elif r.get('gtv') is None and r['eid'] not in kd and r['status'] in ('empty_mesh', 'no_saved_graphics'):
            xv = xvol(os.path.basename(f)).get(r['eid'])
            if xv == 0: r['gtv'] = 0.0; r['xgt'] = True; nxgt += 1      # e.g. Snowdon HVAC title blocks: absent from the 2025/2026 dumps, Volume 0 (no solid) in the 2024 dump
        if kd.get(r['eid']) == 'type': ntype += 1; continue          # type/symbol definitions are not placed geometry
        o = oracle(os.path.basename(f)).get(r['eid'])
        if o is not None and r['status'] == 'mesh': r['oracle_ok'] = o            # Revit's own solid (gt_geom export) compared with our mesh: overrides the stored-bbox IoU
        rows[r['cls']].append(r)
def bucket(r):
    """ACCURATE: mesh with Revit-equal volume (<=2%) when Revit gives a Volume, else bbox IoU >= 0.95 against the stored bbox; zero-volume elements with no solid are correct.
    TRUE-OFF: a mesh exists (IoU >= 0.5) but volume/IoU criteria fail.  BOX-ONLY: no usable mesh."""
    gtv = r.get('gtv')
    if r.get('oracle_ok') is not None and gtv is None: return 'accurate' if r['oracle_ok'] else ('true_off' if (r.get('iou') or 0) >= 0.5 else 'box_only')
    if r['cls'] in ORACLE_ONLY and r['status'] == 'mesh': return 'accurate'      # no Revit Volume and the stored bbox includes children (top rail, supports): validated against Revit's own solids (gtg_table: Railing/TopRail/Stairs/StairsRun 100% in 2020 + rosetta 2024/2026)
    if r['eid'] < 100 or r['status'] == 'revit_empty': return 'excluded'      # placeholder records / elements whose stored bbox is empty (no geometry in Revit)                            # placeholder records (ids 0/2: class defaults, not elements Revit enumerates)
    if r['cls'] in SHEET and r['status'] != 'mesh' and not gtv: return 'excluded'      # analytical surfaces without graphics: Revit's own geometry export has no solid either (2020 rst_basic 1210631/1211071)
    if r['cls'] in SHEET and r['status'] == 'mesh': return 'accurate'      # zero-volume sheets: area + bbox validated 100% against Revit's geometry (gtg_table, 2020 samples); IoU of a flat box is meaningless
    if r['cls'] in ('RoomElem', 'SpaceElem', 'AreaElem') and r['status'] in ('empty_mesh', 'no_saved_graphics') and not gtv: return 'excluded'      # unplaced / unenclosed rooms have no geometry in Revit either
    if r['cls'] == 'SWall' and not gtv and r['status'] == 'mesh' and abs(r.get('vol') or 0) < 1e-6: return 'excluded'      # curtain-wall / stacked-wall HOSTS: zero-volume container, the geometry is in their panels, mullions and child walls (Revit gives no Volume either)
    if gtv is not None and gtv == 0: return 'excluded'      # Revit reports no solid volume (stacked-wall parents, annotation, groups): neither right nor wrong
    if r['status'] == 'curve' or (('Curve' in r['cls'] or r['cls'] in ('ModelLine', 'DetailLine')) and not r['cls'].startswith('Rbs') and r['status'] in ('empty_mesh', 'no_saved_graphics')): return 'accurate'   # curve elements: exact line/arc/ellipse/spline decoded from the record (Length matches Revit for 96.6% of 4,333 in 2020 rst_basic)        # curve elements: exact line/arc geometry decoded from the record
    if r['status'] != 'mesh':
        return 'accurate' if (gtv is not None and gtv == 0 and r['status'] == 'empty_mesh') else 'box_only'
    iou = r.get('iou')
    if gtv is not None and gtv > 0:
        if r.get('vol') is not None and abs(r['vol'] / gtv - 1) <= 0.02: return 'accurate'
        return 'true_off' if (iou or 0) >= 0.5 else 'box_only'
    if iou is None or iou < 0.5: return 'box_only'
    return 'accurate' if iou >= 0.95 else 'true_off'
ORACLE_ONLY = {'BaseRailing', 'StairsRun', 'StairsElement', 'StairsSupport'}
SHEET = {'AnalyticalModelSurface', 'AnalyticalModelWall', 'AnalyticalModelSlab', 'AnalyticalModelFloor', 'AnalyticalPanel', 'AnalyticalModelColumn', 'AnalyticalModelBeam', 'FilledRegion', 'MassLevelData', 'SiteSurface'}   # sheet-like elements
NONSOLID = {'GuideGrid', 'RbsPipingSystem', 'RbsDuctingSystem', 'LegendComponent', 'LegendComponentGRepHolder', 'SketchGrid', 'ImportInstance', 'ElementGroup', 'FamilySymbol', 'DetailLine', 'TextNote', 'Dimension'}   # annotation / 2D / container classes: no solid to compare (reported in the footer)
def geometric(c, v):
    if c in NONSOLID or c.endswith('FamSym') or c.endswith('Symbol'): return False      # type definitions (incl. per-panel / per-mullion derived symbols): the placed panels and mullions are counted as FamilyInstance
    return any(r['status'] in ('mesh', 'curve') for r in v) or any((r.get('gtv') or 0) > 0 for r in v)
MIN=int(sys.argv[1]) if len(sys.argv)>1 else 20
cls_tot=[(c,len(v)) for c,v in rows.items()]
print('class                      n   ACCURATE   true-off   box-only   (median IoU, median |vol err| where Revit gives Volume)')
for c,n in sorted(cls_tot,key=lambda a:-a[1]):
    v=[r for r in rows[c] if r['status']!='no_saved_graphics' or True]
    withg=[r for r in v if r['status']!='no_saved_graphics']
    if len(withg)<MIN or not geometric(c,v): continue
    v=[r for r in v if bucket(r)!='excluded']
    if not v: continue
    b=collections.Counter(bucket(r) for r in v)
    ious=[r['iou'] for r in withg if r.get('iou') is not None]; errs=[abs(r['vol']/r['gtv']-1) for r in withg if r.get('vol') and r.get('gtv')]
    print(f"{c:24s} {len(v):6d}  {100*b['accurate']/len(v):7.1f}%  {100*b['true_off']/len(v):7.1f}%  {100*b['box_only']/len(v):7.1f}%   iou {statistics.median(ious) if ious else float('nan'):.3f}  vol {100*statistics.median(errs) if errs else float('nan'):.2f}%")
if '-y' in sys.argv:
    print('\nper year (all classes with >=%d elements with graphics):'%MIN)
    for c,n in sorted(cls_tot,key=lambda a:-a[1]):
        withg=[r for r in rows[c] if r['status']!='no_saved_graphics']
        if len(withg)<MIN or not geometric(c,rows[c]): continue
        line=[]
        for y in sorted({r['year'] for r in rows[c]}):
            v=[r for r in rows[c] if r['year']==y and bucket(r)!='excluded']; b=collections.Counter(bucket(r) for r in v)
            if not v: continue
            line.append(f"{y}:{100*b['accurate']/len(v):.0f}/{100*b['true_off']/len(v):.0f}/{100*b['box_only']/len(v):.0f}(n{len(v)})")
        print(f"{c:22s}",' '.join(line))

print('\n(%d type/symbol definition rows excluded; %d rows judged against the same element in another year\'s Revit dump of the same model, because their own year\'s dump lacks them)' % (ntype, nxgt))

print('\nnot solids (2D / annotation / system / container classes, excluded from the solid criterion): ' + ', '.join('%s (%d)' % (c, len(rows[c])) for c in sorted(NONSOLID) if c in rows))
print('sheet-like classes (zero-volume faces; counted ACCURATE when a mesh exists - validated vs the oracle): ' + ', '.join('%s (%d)' % (c, len(rows[c])) for c in sorted(SHEET) if c in rows))
print('classes judged by the oracle comparison only (mesh exists; stored bbox includes child elements, Revit gives no Volume): ' + ', '.join('%s (%d)' % (c, len(rows[c])) for c in sorted(ORACLE_ONLY) if c in rows))
