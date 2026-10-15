import sys,os,pickle,traceback
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_brep as B, rvt_occ_brep as OB
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
geos=[]
def w(z):
    if isinstance(z,dict):
        if 'm_pFaces' in z: geos.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(r['fields'])
faces=[fc['loops'] for g in geos for fc in B.planar_faces(g) if fc['plane'] and fc['loops']]
print(len(faces))
try: print(OB.solid_from_faces(faces))
except Exception: traceback.print_exc()
