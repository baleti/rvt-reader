import sys,os,pickle,itertools,math
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG, rvt_curves as C
f=sys.argv[1]; kind=sys.argv[2]; rank=int(sys.argv[3]) if len(sys.argv)>3 else 0
res=GG.cached_index(f); o,dec=GG.load_dec(f)
cand=sorted((r['size'],i) for i,r in res.items() if r['bodies'].get({'rev':'SurfRev','cone':'ConeSurf','hermite':'HermiteSurf','offset':'OffsetSurf'}[kind]))
print(len(cand),'records with',kind,cand[:3])
sz,i=cand[rank]; r=GG.get_record(f,res[i],o,dec)
geos=[]
def w(z):
    if isinstance(z,dict):
        if z.get('m_pFaces'): geos.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(r['fields'])
def ob(x): return x.get('obj',x) if isinstance(x,dict) else x
want={'rev':'m_pProfileCurve','cone':'m_halfAngle','hermite':'m_NodeArray','offset':'m_pBasisSurface'}[kind]
for g in geos:
    faces={fc['handle']:ob(fc) for fc in g['m_pFaces'] if isinstance(ob(fc),dict)}
    surf={h:ob(f_['m_pSurf']) for h,f_ in faces.items() if f_.get('m_pSurf')}
    target={h:s for h,s in surf.items() if want in s}
    pl={h:s for h,s in surf.items() if ('m_origin' in s and 'm_radius' not in s and 'm_xVec' in s and 'm_zVec' not in s) or ('m_radius' in s and 'm_zVec' in s)}
    if not target: continue
    print('record',i,'target faces',list(target),'plane faces',len(pl))
    s0=next(iter(target.values())); print({k:(str(v)[:100]) for k,v in s0.items() if k!='m_Envelope'})
    pts=[]
    for e in g['m_pEdges']:
        eo=ob(e)
        if not isinstance(eo,dict): continue
        fh=[(x.get('ref') if isinstance(x,dict) else None) for x in eo['m_pFace']]
        for si,h in enumerate(fh):
            if h in target and len(fh)>1 and fh[1-si] in pl:
                fl=eo['m_firstAndLastEdgePnts']
                for q in range(2):
                    uc=fl[q]['uv'][si]; up=fl[q]['uv'][1-si]; pp=pl[fh[1-si]]
                    if 'm_radius' in pp:
                        P=np.array(pp['m_center'])+pp['m_radius']*math.cos(up[0])*np.array(pp['m_xVec'])+pp['m_radius']*math.sin(up[0])*np.array(pp['m_yVec'])+up[1]*np.array(pp['m_zVec'])
                    else: P=np.array(pp['m_origin'])+up[0]*np.array(pp['m_xVec'])+up[1]*np.array(pp['m_yVec'])
                    pts.append((h,uc,P))
    print('edge samples',len(pts))
    if kind=='rev':
        for h,s in target.items():
            Cn=np.array(s['m_center']); X=np.array(s['m_xVec']); Y=np.array(s['m_yVec']); Z=np.array(s['m_zVec']); fn,t0,t1=C.curve_fn(s['m_pProfileCurve'])
            def variants():
                for order in ('uv','vu'):
                    for loc in ('global','local'):
                        for sign in (1,-1):
                            for tn in ('raw','norm'):
                                yield (order,loc,sign,tn)
            def ev(var,u,v):
                order,loc,sign,tn=var
                ang,pp=(u,v) if order=='uv' else (v,u)
                t=pp if tn=='raw' else t0+(t1-t0)*pp
                p=fn(t)
                if loc=='global': L=np.array([(p-Cn)@X,(p-Cn)@Y,(p-Cn)@Z])
                else: L=np.asarray(p)
                a=sign*ang; Xr=L[0]*math.cos(a)-L[1]*math.sin(a); Yr=L[0]*math.sin(a)+L[1]*math.cos(a)
                return Cn+Xr*X+Yr*Y+L[2]*Z
            best={}
            for hh,uc,P in pts:
                if hh!=h: continue
                for var in variants(): best.setdefault(var,[]).append(np.linalg.norm(ev(var,*uc)-P))
            for var,d in sorted(best.items(),key=lambda a:max(a[1]))[:4]: print(h,var,round(max(d),6),len(d))
    if kind=='cone':
        for h,s_ in target.items():
            Cn=np.array(s_['m_center']); X=np.array(s_['m_xVec']); Y=np.array(s_['m_yVec']); Z=np.array(s_['m_zVec']); al=float(s_['m_halfAngle'])
            forms={
             'r=v*tan,z=v':lambda u,v:(v*math.tan(al),v),'r=v*tan,z=-v':lambda u,v:(v*math.tan(al),-v),
             'slant r=v*sin,z=v*cos':lambda u,v:(v*math.sin(al),v*math.cos(al)),'slant r=v*cos,z=v*sin':lambda u,v:(v*math.cos(al),v*math.sin(al)),
             'r=v*sin,z=-v*cos':lambda u,v:(v*math.sin(al),-v*math.cos(al)),'r=v*cot,z=v':lambda u,v:(v/math.tan(al),v),
             'r=v,z=v*tan':lambda u,v:(v,v*math.tan(al)),'r=v,z=v/tan':lambda u,v:(v,v/math.tan(al)),'r=v,z=-v/tan':lambda u,v:(v,-v/math.tan(al)),'r=v,z=-v*tan':lambda u,v:(v,-v*math.tan(al))}
            best={}
            for hh,uc,P in pts:
                if hh!=h: continue
                for nm,fn in forms.items():
                    for uorder in ('uv','vu'):
                        u,v=(uc[0],uc[1]) if uorder=='uv' else (uc[1],uc[0])
                        r_,z_=fn(u,v); Q=Cn+r_*(math.cos(u)*X+math.sin(u)*Y)+z_*Z
                        best.setdefault((nm,uorder),[]).append(np.linalg.norm(Q-P))
            for var,d in sorted(best.items(),key=lambda a:max(a[1]))[:3]: print(h,var,round(max(d),6),len(d),'alpha',al)
    break
