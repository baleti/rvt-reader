import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_, eval_gt as G
f,tsv=sys.argv[1:3]
doc=EM.Doc(f); Egt,P=G.load_gt(tsv); x=E_.extract(f,extra=('FamilyInstance',)); st=collections.Counter(); ex=[]
for (eid,c),r in x['recs'].items():
    if eid not in doc.res: continue
    gt={nm:float(v) for b,nm,stg,v in P.get(eid,[]) if stg=='Double' and v!=''}
    if 'Volume' not in gt or gt['Volume']<=0: continue
    m=EM.element_mesh(doc,eid)
    if not m['tris']: continue
    vol,closed,_,area=M.mesh_volume(m['tris'])
    if not closed: st['not closed']+=1; continue
    rr=vol/gt['Volume']; st['closed: vol exact' if abs(rr-1)<1e-4 else ('closed: vol <=1%' if abs(rr-1)<=0.01 else ('closed: vol <=5%' if abs(rr-1)<=0.05 else 'closed: vol off'))]+=1
    if abs(rr-1)>1e-4: continue
    st['exact-volume instances']+=1
    if 'Area' in gt:
        r_=area/gt['Area']; st['area exact(1e-4)' if abs(r_-1)<1e-4 else ('area <=2%' if abs(r_-1)<=0.02 else 'area off')]+=1
        if abs(r_-1)>0.02 and len(ex)<5: ex.append((eid,round(area,3),gt['Area']))
print(dict(st),ex)
