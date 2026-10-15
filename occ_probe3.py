import sys,os,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E
rvt,cl,eid=sys.argv[1],sys.argv[2],int(sys.argv[3])
x=E.extract(rvt,extra=(cl,),only_ids={eid})
r=list(x['recs'].values())[0]; f=r['fields']
def find(o,key,out):
    if isinstance(o,dict):
        if key in o and o[key] is not None: out.append(o)
        for v in o.values(): find(v,key,out)
    elif isinstance(o,list):
        for v in o: find(v,key,out)
g=f['m_geomSteps']
out=[]; find(g,'m_oOriginalFaceGeom',out)
G=out[0]['m_oOriginalFaceGeom']['obj']
print([k for k,v in G.items() if v is not None])
e=G['m_pEdges'][0]['obj']; print({k:(str(v)[:100]) for k,v in e.items() if v is not None})
fc=G['m_pFaces'][0]['obj']; print([k for k,v in fc.items() if v is not None])
print({k:str(v)[:200] for k,v in G.items() if k not in('m_pEdges','m_pFaces') and v is not None})
for k in ('m_pVertices','m_vertices','m_pCurves'):
    if G.get(k): print(k, str(G[k])[:400])
