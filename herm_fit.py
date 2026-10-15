import sys,os,itertools,math
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG
f=sys.argv[1]; rank=int(sys.argv[2]) if len(sys.argv)>2 else 0
res=GG.cached_index(f); o,dec=GG.load_dec(f)
cand=sorted((r['size'],i) for i,r in res.items() if r['bodies'].get('HermiteSurf'))
def ob(x): return x.get('obj',x) if isinstance(x,dict) else x
def pt_plane(pp,up): return np.array(pp['m_origin'])+up[0]*np.array(pp['m_xVec'])+up[1]*np.array(pp['m_yVec'])
def pt_cyl(pp,up): return np.array(pp['m_center'])+pp['m_radius']*(math.cos(up[0])*np.array(pp['m_xVec'])+math.sin(up[0])*np.array(pp['m_yVec']))+up[1]*np.array(pp['m_zVec'])
def basis(s):
    return (2*s**3-3*s**2+1, s**3-2*s**2+s, -2*s**3+3*s**2, s**3-s**2)
def mk(s,order,tmap,twist_sign):
    U=np.array(s['m_uParams']); V=np.array(s['m_vParams']); nu,nv=len(U),len(V)
    nodes=[ob(n) for n in s['m_NodeArray']]
    P=np.zeros((nu,nv,3)); Tu=np.zeros((nu,nv,3)); Tv=np.zeros((nu,nv,3)); W=np.zeros((nu,nv,3))
    for k,n in enumerate(nodes):
        i,j=(k%nu,k//nu) if order=='ufast' else (k//nv,k%nv)
        P[i,j]=n['m_iPoint']; t=n['m_iTangent']; a,b=(np.array(t[0]),np.array(t[1])) if tmap=='01' else (np.array(t[1]),np.array(t[0]))
        Tu[i,j]=a; Tv[i,j]=b; W[i,j]=np.array(n['m_iMixedDer'])*twist_sign
    def ev(u,v):
        i=int(np.clip(np.searchsorted(U,u,side='right')-1,0,nu-2)); j=int(np.clip(np.searchsorted(V,v,side='right')-1,0,nv-2))
        hu=U[i+1]-U[i]; hv=V[j+1]-V[j]; su=(u-U[i])/hu; sv=(v-V[j])/hv; bu=basis(su); bv=basis(sv); out=np.zeros(3)
        # bicubic Hermite: sum over corners
        for (a,ia) in ((0,i),(1,i+1)):
            for (b,jb) in ((0,j),(1,j+1)):
                fu=(bu[0] if a==0 else bu[2], bu[1] if a==0 else bu[3]); fv=(bv[0] if b==0 else bv[2], bv[1] if b==0 else bv[3])
                out+=fu[0]*fv[0]*P[ia,jb]+fu[1]*hu*fv[0]*Tu[ia,jb]+fu[0]*fv[1]*hv*Tv[ia,jb]+fu[1]*hu*fv[1]*hv*W[ia,jb]
        return out
    return ev
for sz,i in cand[:12]:
    r=GG.get_record(f,res[i],o,dec); geos=[]
    def w(z):
        if isinstance(z,dict):
            if z.get('m_pFaces'): geos.append(z)
            for b in z.values():
                if b is not None: w(b)
        elif isinstance(z,list):
            for b in z: w(b)
    w(r['fields'])
    for g in geos:
        faces={fc['handle']:ob(fc) for fc in g['m_pFaces'] if isinstance(ob(fc),dict)}
        surf={h:ob(f_['m_pSurf']) for h,f_ in faces.items() if f_.get('m_pSurf')}
        herm={h:s for h,s in surf.items() if 'm_NodeArray' in s}
        known={h:s for h,s in surf.items() if 'm_NodeArray' not in s and ('m_origin' in s or 'm_radius' in s) and ('m_pProfileCurve1' not in s)}
        if not herm: continue
        pts=[]
        for e in g['m_pEdges']:
            eo=ob(e)
            if not isinstance(eo,dict): continue
            fh=[(x.get('ref') if isinstance(x,dict) else None) for x in eo['m_pFace']]
            for si,h in enumerate(fh):
                if h in herm and len(fh)>1 and fh[1-si] in known:
                    fl=list(eo['m_firstAndLastEdgePnts'])+[ob(p) for p in (eo.get('m_interiorEdgePnts') or [])]
                    for q in range(len(fl)):
                        uc=fl[q]['uv'][si]; up=fl[q]['uv'][1-si]; pp=known[fh[1-si]]
                        P=pt_cyl(pp,up) if 'm_radius' in pp else pt_plane(pp,up); pts.append((h,uc,P))
        if not pts: continue
        print('record',i,'herm faces',list(herm),'samples',len(pts))
        h0=pts[0][0]; s=herm[h0]; best={}
        for order,tmap,ts in itertools.product(('ufast','vfast'),('01','10'),(1,-1)):
            try: ev=mk(s,order,tmap,ts)
            except Exception as e: continue
            d=[np.linalg.norm(ev(*uc)-P) for h,uc,P in pts if h==h0]
            best[(order,tmap,ts)]=max(d)
        for k,v in sorted(best.items(),key=lambda a:a[1])[:4]: print(k,round(v,6))
        sys.exit()
