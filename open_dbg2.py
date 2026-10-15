import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f); m=EM.element_mesh(doc,eid)
print('source',m['source'],'tris',len(m['tris']),'flags',m['flags'])
tris=m['tris']; tol=5e-5; key=lambda p:(round(p[0]/tol),round(p[1]/tol),round(p[2]/tol))
em=collections.defaultdict(list)
for ti,t in enumerate(tris):
    ks=[key(p) for p in t]
    for a,b in ((0,1),(1,2),(2,0)):
        if ks[a]!=ks[b]: em[frozenset((ks[a],ks[b]))].append(ti)
op=[(e,v) for e,v in em.items() if len(v)==1]; mul=[(e,v) for e,v in em.items() if len(v)>2]
print('edges',len(em),'open',len(op),'nonmanifold(>2)',len(mul))
for e,v in op[:6]:
    pts=[np.array(k)*tol for k in e]; print('  open edge',np.round(pts[0],3).tolist(),np.round(pts[1],3).tolist(),'len',round(float(np.linalg.norm(pts[0]-pts[1])),4),'tri',v)
# which kinds of surface
print('kinds',collections.Counter(k for k,_,_ in m['meta']))
