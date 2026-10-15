import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f); rec=doc.rec(eid); fl=rec['fields']; bb=fl['m_bBox']
geos,inst=EM._geos(fl); own=[];ownm=[];ownf=[];nface=0
for g in geos:
    t=M.element_faces_in_bbox(g,bb,eps=0.02); own+=t['tris']; ownm+=t['meta']; ownf+=[nface+x for x in t['fidx']]; nface+=t['faces']+1
tol=1e-6; key=lambda p:(round(p[0]/tol),round(p[1]/tol),round(p[2]/tol))
faces=collections.OrderedDict()
for t,m,fi in zip(own,ownm,ownf): faces.setdefault(fi,[]).append(t)
print('faces',len(faces))
cnt=collections.Counter()
fe={}
for fi,l in faces.items():
    area=sum(np.linalg.norm(np.cross(np.asarray(t[1])-np.asarray(t[0]),np.asarray(t[2])-np.asarray(t[0])))/2 for t in l)
    c=collections.Counter()
    for t in l:
        ks=[key(p) for p in t]
        for a,b in ((0,1),(1,2),(2,0)):
            if ks[a]!=ks[b]: c[frozenset((ks[a],ks[b]))]+=1
    fe[fi]={e for e,n in c.items() if n==1}
    pts=np.array([p for t in l for p in t]); print(fi,'area',round(area,3),'tris',len(l),'bnd edges',len(fe[fi]),'bbox',np.round(pts.min(0),2).tolist(),np.round(pts.max(0),2).tolist())
    for e in fe[fi]: cnt[e]+=1
print('edge usage',collections.Counter(cnt.values()))
