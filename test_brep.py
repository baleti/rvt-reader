import sys,os,pickle,collections,math
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_brep as B
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
geos=[]
def w(x):
    if isinstance(x,dict):
        if 'm_pFaces' in x: geos.append(x)
        for b in x.values():
            if b is not None: w(b)
    elif isinstance(x,list):
        for b in x: w(b)
w(r['fields'])
for g in geos:
    fs=B.planar_faces(g)
    for fc in fs: print(fc['handle'],fc['surface_kind'],[len(l) for l in fc['loops']], [[round(c,3) for c in p] for p in fc['loops'][0][:4]] if fc['loops'] else None)
