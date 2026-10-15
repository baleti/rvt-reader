import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_, eval_gt as G
f,tsv,pk,maxn=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]); only=sys.argv[5].split(',') if len(sys.argv)>5 else None
doc=EM.Doc(f,pk); Egt,P=G.load_gt(tsv)
x=E_.extract(f,extra=tuple(only) if only else ('FamilyInstance',)); st=collections.defaultdict(collections.Counter); n=collections.Counter()
for (eid,c),r in x['recs'].items():
    if n[c]>=maxn: continue
    if eid not in doc.res: st[c]['no saved graphics']+=1; continue
    n[c]+=1
    m=EM.element_mesh(doc,eid); bb=m.get('bbox') or doc.res[eid].get('bbox')
    if not m['tris']: st[c]['empty mesh']+=1; continue
    Pp=np.array([p for t in m['tris'] for p in t]); lo,hi=Pp.min(0),Pp.max(0)
    if bb:
        l=np.maximum(lo,bb[0]); h=np.minimum(hi,bb[1]); inter=np.prod(np.clip(h-l,0,None)); iou=inter/(np.prod(hi-lo)+np.prod(np.array(bb[1])-np.array(bb[0]))-inter+1e-12)
    else: iou=None
    k='iou>=0.95' if iou is not None and iou>=0.95 else ('iou>=0.5' if iou is not None and iou>=0.5 else 'iou<0.5')
    st[c][k+'/'+m['source']]+=1
    vol,closed,_,_=M.mesh_volume(m['tris'])
    gtv=[float(v) for b,nm,stg,v in P.get(eid,[]) if nm=='Volume' and stg=='Double' and v!='']
    if closed and gtv and gtv[0]>0:
        rr=vol/gtv[0]; st[c]['volume exact(1e-4)' if abs(rr-1)<1e-4 else ('volume <=5%' if abs(rr-1)<=0.05 else 'volume off')]+=1
for c,cn in st.items(): print(c,dict(cn))
