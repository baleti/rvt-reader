import sys,os,pickle
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG, rvt_mesh as M
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec); fl=r['fields']
print('bbox',fl['m_bBox'])
geos=[]; insts=[]
def w(z):
    if isinstance(z,dict):
        if 'm_pFaces' in z: geos.append(z)
        if 'm_instanceInfo' in z: insts.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(fl)
for g in geos:
    t=M.tessellate_geometry(g)
    if t['tris']:
        P=np.array([p for tr in t['tris'] for p in tr]); print('geom faces',t['faces'],'unsup',set(t['unsupported']),'bbox',P.min(0).round(3),P.max(0).round(3))
for z in insts:
    ii=z['m_instanceInfo']; ii=ii.get('obj',ii); print('instanceInfo',{k:str(v)[:150] for k,v in ii.items() if v is not None})
    em=z.get('m_oEmbeddedSymbolGRep'); print('embedded keys',list((em.get('obj',em) if isinstance(em,dict) else {}).keys())[:8] if em else None)
