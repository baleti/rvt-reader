import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); hh=int(sys.argv[3]); doc=EM.Doc(f); rec=doc.rec(eid)
geos,inst=EM._geos(rec['fields']); g=geos[0]
edges={e['handle']:M._ob(e) for e in g['m_pEdges'] if isinstance(e,dict) and isinstance(M._ob(e),dict)}
fc=[x for x in g['m_pFaces'] if x.get('handle')==hh][0]; fo=M._ob(fc); kind,ev=M.surface_eval(fo['m_pSurf']); print(kind,{k:v for k,v in M._ob(fo['m_pSurf']).items() if k!='m_Envelope'})
for eid_,e in edges.items():
    refs=[(r.get('ref') if isinstance(r,dict) else None) for r in (e.get('m_pFace') or [])]
    if hh in refs:
        side=refs.index(hh); fl=e['m_firstAndLastEdgePnts']
        print('edge',eid_,'faces',refs,'side',side,'a',M._ob(fl[0])['uv'][side],'b',M._ob(fl[1])['uv'][side],'interior',len(e.get('m_interiorEdgePnts') or []))
print('loops',M.face_loops_uv(hh,edges))
