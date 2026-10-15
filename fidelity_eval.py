import sys,os,json,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_, eval_gt as G
f,tsv,out=sys.argv[1:4]; cap=int(sys.argv[4]) if len(sys.argv)>4 else 300
doc=EM.Doc(f); Egt,P=G.load_gt(tsv)
x=E_.extract(f,want_all=True); st=collections.defaultdict(collections.Counter); n=collections.Counter()
for (eid,c),r in x['recs'].items():
    if eid not in doc.res: st[c]['no_saved_graphics']+=1; continue
    if n[c]>=cap: continue
    n[c]+=1
    try: m=EM.element_mesh(doc,eid)
    except Exception as e: st[c]['error']+=1; continue
    bb=doc.res[eid].get('bbox')
    if not m['tris']: st[c]['box_only(empty mesh)']+=1; continue
    Pp=np.array([p for t in m['tris'] for p in t]); lo,hi=Pp.min(0),Pp.max(0)
    iou=None
    if bb:
        l=np.maximum(lo,bb[0]); h=np.minimum(hi,bb[1]); inter=np.prod(np.clip(h-l,0,None)); iou=inter/(np.prod(hi-lo)+np.prod(np.array(bb[1])-np.array(bb[0]))-inter+1e-12)
    vol,closed,_,_=M.mesh_volume(m['tris'])
    if m.get('meta') and len(m['meta'])==len(m['tris']) and any(k!='plane' for k,_,_ in m['meta']):
        try:
            v3,c3,_=M.refined_volume(m['tris'],m['meta'],levels=3)
            if c3: vol,closed=v3,True
        except Exception: pass
    healed=False
    if not closed:
        t2,ncap,okh=M.heal_open(m['tris'])
        if okh and ncap:
            v2,c2,_,_=M.mesh_volume(t2)
            if c2: vol,closed,healed=v2,True,True
    gtv=[float(v) for b,nm,stg,v in P.get(eid,[]) if nm=='Volume' and stg=='Double' and v!='']
    if closed and gtv and gtv[0]>0 and abs(vol/gtv[0]-1)<1e-4: k='exact(volume,healed)' if healed else 'exact(volume)'
    elif iou is not None and iou>=0.95: k='approx(bbox iou>=.95)'
    elif iou is not None and iou>=0.5: k='partial(bbox iou .5-.95)'
    else: k='box_only(iou<.5)'
    st[c][k]+=1
json.dump({c:dict(v) for c,v in st.items()},open(out,'w'))
print(os.path.basename(f),{c:dict(v) for c,v in sorted(st.items(),key=lambda a:-sum(a[1].values()))[:6]})
