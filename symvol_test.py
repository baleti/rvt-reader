import resource
def rss(t): print(t,resource.getrusage(resource.RUSAGE_SELF).ru_maxrss//1024,'MB',flush=True)
import sys,os,pickle,collections,math
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_mesh as M, rvt_brep as B, rvt_occ_brep as OB, rvt_xcache, eval_gt as G, rvt_famparams as F
f=sys.argv[1]; tsv=sys.argv[2]; res=pickle.load(open(sys.argv[3],'rb')); maxn=int(sys.argv[4]) if len(sys.argv)>4 else 300
import rvt_entities as E_
x=E_.extract(f,extra=('FamilyInstance',)); recs={}
for (e,c),r in x['recs'].items(): recs.setdefault(e,r)
rss('extracted')
E,P=G.load_gt(tsv)
o,dec=GG.load_dec(f); rss('dec loaded')
symvol={}
def sym_geo(sid):
    if sid in symvol: return symvol[sid]
    out=None
    if sid in res and res[sid]['bodies'].get('Face'):
        r=GG.get_record(f,res[sid],o,dec); geos=[]
        def w(z):
            if isinstance(z,dict):
                if 'm_pFaces' in z: geos.append(z)
                for b in z.values():
                    if b is not None: w(b)
            elif isinstance(z,list):
                for b in z: w(b)
        w(r['fields'])
        tr=[]; un=[]
        for g in geos:
            t=M.tessellate_geometry(g); tr+=t['tris']; un+=t['unsupported']
        out=(tr,un)
    symvol[sid]=out; rss('sym %d'%sid) if len(symvol)%20==0 else None; return out
stat=collections.Counter(); ex=[]
n=0
for eid,r in recs.items():
    if r['class']!='FamilyInstance': continue
    gtv=[float(v) for b,nm,stg,v in P.get(eid,[]) if nm=='Volume' and stg=='Double' and v!='']
    if not gtv or gtv[0]<=0: continue
    inf=F.S_(r['fields'],'m_pInstanceInfo'); sid=int(inf['m_symbolId']) if inf else None
    sg=sym_geo(eid)   # the element's OWN saved-graphics record (final evaluated solid)
    n+=1
    if n>maxn: break
    if not sg: stat['no brep for symbol']+=1; continue
    tr,un=sg
    if un: stat['unsupported:'+un[0]]+=1; continue
    vol,closed,nopen,area=M.mesh_volume(tr)
    if not closed: stat['open mesh']+=1; continue
    ratio=vol/gtv[0]
    k='exact(1e-4)' if abs(ratio-1)<1e-4 else ('approx(<=1%)' if abs(ratio-1)<=0.01 else ('approx(<=5%)' if abs(ratio-1)<=0.05 else 'off'))
    stat[k]+=1
    if k=='off' and len(ex)<8: ex.append((eid,sid,round(vol,4),gtv[0]))
print(dict(stat)); print(ex)
