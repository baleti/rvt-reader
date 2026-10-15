import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_, eval_gt as G
f,tsv,cl=sys.argv[1:4]; doc=EM.Doc(f); Egt,P=G.load_gt(tsv); x=E_.extract(f,extra=(cl,)); n=0
for (eid,c),r in x['recs'].items():
    if eid not in doc.res: continue
    gt={nm:float(v) for b,nm,stg,v in P.get(eid,[]) if stg=='Double' and v!=''}
    m=EM.element_mesh(doc,eid)
    if not m['tris']: print(eid,'empty'); continue
    vol,closed,nopen,area=M.mesh_volume(m['tris'])
    print(eid,c,'src',m['source'],'tris',len(m['tris']),'closed',closed,'open',nopen,'vol',round(vol,3),'GT vol',gt.get('Volume'),'ratio',round(vol/gt['Volume'],4) if gt.get('Volume') else None,'area',round(area,2),'GT area',gt.get('Area'),m['flags'])
    n+=1
    if n>=8: break
