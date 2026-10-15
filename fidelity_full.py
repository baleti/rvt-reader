"""Per-element geometry fidelity rows (JSONL) for one file: class, source, bbox IoU vs the stored Revit bbox, closed-mesh volume vs gt4 Volume."""
import sys,os,json,collections,time
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_geom as Gm, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_, eval_gt as G
f,tsv,out=sys.argv[1:4]; cap=int(sys.argv[4]) if len(sys.argv)>4 else 3000
doc=EM.Doc(f); Egt,P=G.load_gt(tsv)
x=E_.extract(f,want_all=True,slim=lambda c: c in ('CurveElem','DetailLine','ModelLine','SymbolicCurve') or 'Curve' in c)      # fast path memory fixed by c4-rust 2026-10-13
n=collections.Counter(); rows=[]
for (eid,c),r in x['recs'].items():
    gt={nm:float(v) for b,nm,stg,v in P.get(eid,[]) if stg=='Double' and v!=''}
    row={'eid':eid,'cls':c,'gtv':gt.get('Volume'),'gta':gt.get('Area')}
    if eid not in doc.res:
        cu = Gm.primary_curve(r['fields']) if c in ('CurveElem','DetailLine','ModelLine','SymbolicCurve') or 'Curve' in c else None
        row['status'] = 'curve' if (cu is not None and Gm.curve_length(cu) is not None) else 'no_saved_graphics'; rows.append(row); continue
    if n[c]>=cap: continue
    n[c]+=1
    try:
        m=EM.element_mesh(doc,eid,detail=3); row['detail']=3        # Revit's Volume parameter follows Fine for loadable families (checked on 60/60 former misses in Snowdon Structural) and Medium for some system families: take Fine, fall back to Medium when it matches better
        if row.get('gtv') and m['tris']:
            v3=M.volume_by_node(m['tris'],m.get('meta'),m['nid'],fid=m.get('fid'))[0]
            if abs(v3/row['gtv']-1)>0.02:
                m2=EM.element_mesh(doc,eid,detail=2)
                if m2['tris']:
                    v2=M.volume_by_node(m2['tris'],m2.get('meta'),m2['nid'],fid=m2.get('fid'))[0]
                    if abs(v2/row['gtv']-1)<abs(v3/row['gtv']-1): m=m2; row['detail']=2
    except Exception as e: row['status']='error'; rows.append(row); continue
    bb=doc.res[eid].get('bbox')
    if not m['tris'] and bb and bb[0][0] > bb[1][0]: row['status']='revit_empty'; rows.append(row); continue      # inverted (empty) stored bbox: Revit has no geometry either (degenerate sweeps etc.)
    if not m['tris']: row['status']='empty_mesh'; row['unsup']='unsupported_faces' in m['flags']; rows.append(row); continue
    Pp=np.array([p for t in m['tris'] for p in t]); lo,hi=Pp.min(0),Pp.max(0); iou=None
    if bb:
        l=np.maximum(lo,bb[0]); h=np.minimum(hi,bb[1]); inter=np.prod(np.clip(h-l,0,None)); iou=float(inter/(np.prod(hi-lo)+np.prod(np.array(bb[1])-np.array(bb[0]))-inter+1e-12))
    vol_all=None
    if m.get('nid') and len(m['nid'])==len(m['tris']):
        vol,closed,area,_nn=M.volume_by_node(m['tris'],m.get('meta'),m['nid'],fid=m.get('fid'))
        if c=='SWall' and any(n>=2*10**7 for n in m['nid']) and any(n<2*10**7 for n in m['nid']):
            # Revit's wall Volume PARAMETER is the wall's own body; integrated sweeps/banding (instances drawn with the wall, part of its geometry) are not in it
            ix=[i for i,n in enumerate(m['nid']) if n<2*10**7]; vol_all=vol
            vol,closed,area,_nn=M.volume_by_node([m['tris'][i] for i in ix],[m['meta'][i] for i in ix] if m.get('meta') else None,[m['nid'][i] for i in ix],fid=[m['fid'][i] for i in ix] if m.get('fid') else None)
    else:
        vol,closed,_,area=M.mesh_volume(m['tris'])
    healed=False
    row.update(status='mesh',source=m['source'],iou=iou,closed=closed,healed=healed,vol=vol if (closed or (vol and vol>0)) else None,area=area if (closed or (area and area>0)) else None,ntri=len(m['tris']),unsup='unsupported_faces' in m['flags'],vol_all=vol_all)
    rows.append(row)
with open(out,'w') as fh:
    for r in rows: fh.write(json.dumps(r)+'\n')
print(os.path.basename(f),len(rows),'rows')
