import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_, eval_gt as G
f,tsv=sys.argv[1:3]; doc=EM.Doc(f); Egt,P=G.load_gt(tsv); x=E_.extract(f,extra=('FamilyInstance',)); n=0
st=collections.Counter()
for (eid,c),r in x['recs'].items():
    if eid not in doc.res or not doc.res[eid]['bodies'].get('CylSurf'): continue
    gtv=[float(v) for b,nm,stg,v in P.get(eid,[]) if nm=='Volume' and stg=='Double' and v!='']
    if not gtv or gtv[0]<=0: continue
    m=EM.element_mesh(doc,eid)
    if not m['tris'] or not m.get('meta'): continue
    v0,c0,_,_=M.mesh_volume(m['tris'])
    if len(m['meta'])!=len(m['tris']): st['meta mismatch']+=1; continue
    out=[]
    for lv in (0,2,4):
        v,c,_=M.refined_volume(m['tris'],m['meta'],levels=lv); out.append((lv,round(v/gtv[0],5)))
    st['closed coarse' if c0 else 'open']+=1
    n+=1
    if n<=12: print(eid,m['source'],'coarse',round(v0/gtv[0],5),'closed',c0,out)
print(dict(st))
