#!/usr/bin/env python3
"""rvt2facts.py FILE [FILE ...]: one JSON object per line with the structured facts of a Revit file (.rvt .rfa .rte .rft), for the sqlite facts index (~/bin/index/cadfacts.py)
and for live queries. Lengths are converted from Revit's internal feet to mm, areas to m2, volumes to m3.
Record: {file, size, status, seconds, year, title, elems:[[eid,class,category,family,type,level,mark,name]], nums:[[eid,param,value,unit]], strs:[[eid,param,value]], levels, errors}
Only elements that belong to a Revit category are kept (no graphics styles, curves, fonts, ...), and only a whitelist of parameters (length-like numerics, identifying strings)."""
import sys, os, re, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.expanduser('~/src/rvt-core/python'))
import rvt_fast as F

HERE = os.path.dirname(os.path.abspath(__file__))
CATS = json.load(open(os.path.join(HERE, 'category_names.json')))
NOISE = {'GStyleElem', 'CurveElem', 'CategoryElem', 'FontElem', 'ParamBinding', 'SketchPlane', 'Hub', 'ReferencePoint', 'FamSymSurrogate', 'FamilySurrogate',
         'VarSketch', 'TextNoteAttributes', 'LinearDimString', 'Viewer', 'FamilyBase', 'MasterImportSymbol', 'ImportInstance', 'SlaveImportSymbol', 'LegendComponent',
         'SegmentCenterLine', 'PipeFittingCenterLine', 'DuctFittingCenterLine', 'CableTrayFittingCenterLine'}
LEN = re.compile(r'(width|height|length|thickness|depth|offset|elevation|diameter|radius|sill|head|distance|clearance|spacing|rise|run|extension|projection|span|gap|cover)', re.I)
AREA = re.compile(r'\barea\b', re.I); VOL = re.compile(r'\bvolume\b', re.I)
SKIPNUM = re.compile(r'(Middle|Lower End|Upper End|^Start |^End |Centerline|Fixed|Spring|Rotation|Translation|Coefficient|Thermal|Heat|Absorpt|Roughness|Lugs|Total|Demand|Connected|Angle)', re.I)
STRS = {'Mark', 'Type Mark', 'Comments', 'Type Comments', 'Description', 'Manufacturer', 'Model', 'Fire Rating', 'Assembly Code', 'Assembly Description', 'Keynote', 'URL',
        'OmniClass Number', 'OmniClass Title', 'Type Name', 'Family Name', 'View Name', 'Sheet Number|String', 'Sheet Name', 'Name', 'Number', 'Text', 'Cost'}
LVL = ('Level', 'Base Constraint', 'Base Level', 'Schedule Level', 'Reference Level')
M = 304.8
MEPCAT = re.compile(r'(Fittings|Accessories|Sprinklers|Pipes|Ducts|Conduits|Cable Tray|Flex)', re.I)
CORE = re.compile(r'^(Width|Height|Length|Diameter|Size|Thickness|Depth)$', re.I)

def facts(path):
    t0 = time.time(); st = os.stat(path)
    r = {'file': path, 'size': st.st_size, 'status': 'ok', 'errors': [], 'elems': [], 'nums': [], 'strs': [], 'levels': []}
    try:
        x, p = F.Model(path, progress=False).full()
    except Exception as e:
        r['status'] = 'error'; r['errors'].append(repr(e)[:300]); r['seconds'] = round(time.time() - t0, 2); return r
    def nm(i):
        v = p.get(i)
        if not v: return ''
        q = v['params']; return str(q.get('Name') or q.get('Type Name') or q.get('View Name') or '')
    for eid, v in p.items():
        c = v['class']
        if c in NOISE or c.startswith('Analytical'): continue
        q = v['params']; cid = q.get('Category|ElementId')
        cat = CATS.get(str(cid)) if isinstance(cid, int) else None
        if not cat and not c.startswith('DBView') and c not in ('Level', 'Grid', 'RoomElem', 'Family'): continue
        ty = q.get('Type')
        tq = p[ty]['params'] if isinstance(ty, int) and ty in p and ty != eid else q
        tname = str(tq.get('Type Name') or '')
        fam = str(tq.get('Family Name') or '')
        if not fam and ':' in tname: fam = tname.split(':')[0]
        if ':' in tname and fam and tname.startswith(fam + ':'): tname = tname[len(fam) + 1:]
        lv = ''
        for k in LVL:
            lid = q.get(k)
            if isinstance(lid, int) and lid > 0 and lid in p: lv = nm(lid); break
        name = str(q.get('Name') or q.get('View Name') or q.get('Type Name') or '')
        r['elems'].append([eid, c, cat or '', fam, tname, lv, str(q.get('Mark') or ''), name])
        for k, val in q.items():
            if '|' in k and k not in STRS: continue
            if isinstance(val, float):
                if SKIPNUM.search(k) or (cat and MEPCAT.search(cat) and not CORE.match(k)): continue
                if AREA.search(k): r['nums'].append([eid, k, round(val * 0.09290304, 4), 'm2'])
                elif VOL.search(k): r['nums'].append([eid, k, round(val * 0.028316846592, 5), 'm3'])
                elif LEN.search(k): r['nums'].append([eid, k, round(val * M, 2), 'mm'])
            elif k in STRS and isinstance(val, str) and val.strip(): r['strs'].append([eid, k, val[:300]])
        if c == 'Level':
            e = q.get('Elevation'); r['levels'].append([name, round(e * M, 1) if isinstance(e, float) else None])
    r['seconds'] = round(time.time() - t0, 2)
    return r

if __name__ == '__main__':
    for f in sys.argv[1:]:
        try: o = facts(f)
        except Exception as e: o = {'file': f, 'status': 'error', 'errors': [repr(e)[:300]]}
        sys.stdout.write(json.dumps(o, ensure_ascii=False) + '\n'); sys.stdout.flush()
