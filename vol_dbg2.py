import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f); m=EM.element_mesh(doc,eid)
tris=m['tris']; meta=m['meta']; print('tris',len(tris),collections.Counter(k for k,_,_ in meta))
for lv in (0,1,3,5):
    v,c,a=M.refined_volume(tris,meta,levels=lv); print('levels',lv,'vol',round(v,4),'closed',c,'area',round(a,4))
# per kind areas
by=collections.defaultdict(float)
for t,(k,_,_) in zip(tris,meta): by[k]+=np.linalg.norm(np.cross(np.asarray(t[1])-np.asarray(t[0]),np.asarray(t[2])-np.asarray(t[0])))/2
print({k:round(v,4) for k,v in by.items()})
R=0.4921; h=19.692; print('expected lateral',2*np.pi*R*h,'caps',2*np.pi*R**2,'vol',np.pi*R*R*h)
