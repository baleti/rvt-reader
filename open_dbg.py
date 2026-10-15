import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, rvt_entities as E_
f,pk=sys.argv[1],sys.argv[2]
doc=EM.Doc(f,pk); x=E_.extract(f,extra=('FamilyInstance',)); shown=0
for (eid,c),r in x['recs'].items():
    if eid not in doc.res or doc.res[eid]['size']>12000: continue
    m=EM.element_mesh(doc,eid)
    if not m['tris'] or m['source']!='own_geometry_in_bbox': continue
    vol,closed,nopen,area=M.mesh_volume(m['tris'])
    if closed: continue
    tris=m['tris']; tol=1e-6; key=lambda p:(round(p[0]/tol),round(p[1]/tol),round(p[2]/tol))
    em=collections.Counter()
    for t in tris:
        ks=[key(p) for p in t]
        for a,b in ((0,1),(1,2),(2,0)): em[frozenset((ks[a],ks[b]))]+=1
    opens=[tuple(e) for e,n in em.items() if n!=2 and len(e)==2]
    print('eid',eid,'tris',len(tris),'open edges',len(opens),'sample',[ [tuple(round(c*tol,3) for c in v) for v in e] for e in opens[:3]], 'flags',m['flags'])
    shown+=1
    if shown>=4: break
