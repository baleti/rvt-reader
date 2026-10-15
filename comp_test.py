import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG, rvt_mesh as M, rvt_entities as E_, eval_gt as G, rvt_famparams as F
f=sys.argv[1]; tsv=sys.argv[2]; res=pickle.load(open(sys.argv[3],'rb')); maxn=int(sys.argv[4])
x=E_.extract(f,extra=('FamilyInstance',)); Egt,P=G.load_gt(tsv); o,dec=GG.load_dec(f)
stat=collections.Counter(); ex=[]; n=0; dbg=[]
for (eid,c),r in x['recs'].items():
    if c!='FamilyInstance' or eid not in res or not res[eid]['bodies'].get('Face'): continue
    gtv=[float(v) for b,nm,stg,v in P.get(eid,[]) if nm=='Volume' and stg=='Double' and v!='']
    if not gtv or gtv[0]<=0: continue
    n+=1
    if n>maxn: break
    rec=GG.get_record(f,res[eid],o,dec); bb=rec['fields'].get('m_bBox')
    geos=[]
    def w(z):
        if isinstance(z,dict):
            if 'm_pFaces' in z and z['m_pFaces']: geos.append(z)
            for b in z.values():
                if b is not None: w(b)
        elif isinstance(z,list):
            for b in z: w(b)
    w(rec['fields'])
    tr=[]; un=[]
    for g in geos:
        t=M.element_faces_in_bbox(g,bb); tr+=t['tris']; un+=t['unsupported']
    if not tr: stat['no faces inside bbox']+=1; continue
    vol,closed,nopen,area=M.mesh_volume(tr)
    if not closed: stat['open (%s)'%('unsup' if un else 'cut/dup')]+=1; continue
    ratio=vol/gtv[0]
    k='exact(1e-4)' if abs(ratio-1)<1e-4 else ('approx(<=1%)' if abs(ratio-1)<=0.01 else ('approx(<=5%)' if abs(ratio-1)<=0.05 else 'off'))
    stat[k]+=1
    if k=='off' and len(ex)<6: ex.append((eid,round(vol,3),gtv[0]))
print(dict(stat)); print(ex); print(dbg)
