import sys,os,pickle
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG, rvt_mesh as M
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
geos=[]
def w(z):
    if isinstance(z,dict):
        if 'm_pFaces' in z and z['m_pFaces']: geos.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(r['fields']); g=geos[0]
edges={e['handle']:M._ob(e) for e in g['m_pEdges'] if isinstance(e,dict) and isinstance(M._ob(e),dict)}
for fc in g['m_pFaces']:
    fo=M._ob(fc)
    if not isinstance(fo,dict): print('face nonobj',fc); continue
    kind,ev=M.surface_eval(fo.get('m_pSurf'))
    loops=M.face_loops_uv(fc['handle'],edges)
    s=M._ob(fo.get('m_pSurf')); 
    bb=''
    if ev and loops:
        P=np.array([ev(u,v) for u,v in loops[0]]); bb=str(P.min(0).round(2))+str(P.max(0).round(2))
    print(fc['handle'],kind,'loops',[len(l) for l in loops],bb)
