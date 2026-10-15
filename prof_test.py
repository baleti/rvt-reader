import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_entities as E_, rvt_famparams as F
f=sys.argv[1]; doc=EM.Doc(f); x=E_.extract(f,extra=('FamilyInstance',)); n=0
for (eid,c),r in x['recs'].items():
    if eid not in doc.res or not doc.res[eid]['bodies'].get('Face'): continue
    m=EM.element_mesh(doc,eid)
    if not m['tris'] or len(m['tris'])>200: continue
    pr=EM.end_cap_profile(m['tris'])
    if not pr: continue
    cp=pr['caps'][0]
    if len(cp['loops'][0])>=8:
        print(eid,'tris',len(m['tris']),'cap area',round(cp['area'],4),'loops',[len(l) for l in cp['loops']],'outer pts',[[round(v,3) for v in p] for p in cp['loops'][0][:14]])
        n+=1
    if n>=3: break
