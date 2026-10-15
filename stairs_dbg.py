import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_entities as E_
f=sys.argv[1]; doc=EM.Doc(f); x=E_.extract(f,extra=('StairsElement','StairsRun','StairsSupport','StairsTriserSymbol','StairsSym'))
def ob(z): return z.get('obj',z) if isinstance(z,dict) else z
for (eid,c),r in x['recs'].items():
    if eid not in doc.res: print(c,eid,'no saved'); continue
    rec=doc.rec(eid); geos,inst=EM._geos(rec['fields']); m=EM.element_mesh(doc,eid)
    print(c,eid,'geos',[ (len(g['m_pFaces']),len(g.get('m_pEdges') or [])) for g in geos],'inst',[(ob(z['m_instanceInfo']).get('m_symbolId'), z['m_instanceInfo'] and 1) for z in inst],'mesh tris',len(m['tris']),m['source'],'bbox',rec['fields'].get('m_bBox'))
    for z in inst:
        sid=int(ob(z['m_instanceInfo'])['m_symbolId']); print('    symbol',sid,'in index',sid in doc.res, doc.res.get(sid,{}).get('bodies'))
