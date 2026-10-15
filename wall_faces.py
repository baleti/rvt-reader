import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f); rec=doc.rec(eid); fl=rec['fields']; bb=fl['m_bBox']; print('bbox',np.round(bb,2).tolist())
geos,inst=EM._geos(fl); print('geometry nodes',[(len(g['m_pFaces']),len(g.get('m_pEdges') or [])) for g in geos],'instances',len(inst))
for gi,g in enumerate(geos):
    edges=M._edge_map(g)
    for fc in g['m_pFaces']:
        fo=M._ob(fc)
        if not isinstance(fo,dict): continue
        kind,ev=M.surface_eval(fo.get('m_pSurf')); loops=M.face_loops_uv(fc['handle'],edges)
        if ev is None or not loops: print(gi,fc['handle'],kind,'loops',len(loops)); continue
        P=np.array([ev(u,v) for u,v in max(loops,key=lambda l:abs(M._area2(l)))])
        a=abs(M._area2([tuple(p) for p in max(loops,key=lambda l:abs(M._area2(l)))]))
        inside=(P.min(0)>=np.array(bb[0])-0.02).all() and (P.max(0)<=np.array(bb[1])+0.02).all()
        print(gi,fc['handle'],kind,'loops',[len(l) for l in loops],'uvarea',round(a,3),'bbox',np.round(P.min(0),2).tolist(),np.round(P.max(0),2).tolist(),'INSIDE' if inside else '')
