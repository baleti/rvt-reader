import sys,os,pickle,itertools,math
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG, rvt_brep as B, rvt_mesh as M
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
geos=[]
def w(z):
    if isinstance(z,dict):
        if z.get('m_pFaces'): geos.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(r['fields']); g=geos[0]
faces={fc['handle']:fc['obj'] for fc in g['m_pFaces'] if isinstance(fc.get('obj'),dict)}
surf={h:f['m_pSurf']['obj'] for h,f in faces.items()}
ruled={h:s for h,s in surf.items() if 'm_pProfileCurve1' in s}; pl={h:s for h,s in surf.items() if 'm_origin' in s and 'm_radius' not in s}
def ell(c,t):
    c=c['obj']; return np.array(c['m_center'])+c['m_xLen']*math.cos(t)*np.array(c['m_xVec'])+c['m_yLen']*math.sin(t)*np.array(c['m_yVec'])
def plane(s,u,v): return np.array(s['m_origin'])+u*np.array(s['m_xVec'])+v*np.array(s['m_yVec'])
def forms(s):
    c1=s['m_pProfileCurve1']; c2=s['m_pProfileCurve2']; t0,t1=c1['obj']['m_endParams']; 
    def mk(var):
        def f(u,v):
            # variants: which of (u,v) selects curve param vs blend
            a,b=(u,v) if var[0]=='uv' else (v,u)
            tp = t0+(t1-t0)*(a if var[1]=='fwd' else 1-a) if var[2]=='norm' else t0+a*(t1-t0)
            bl = (-b if var[3]=='neg' else b)
            bl = bl if var[4]=='b1' else 1-bl
            return (1-bl)*ell(c1,tp)+bl*ell(c2,tp)
        return f
    return {var:mk(var) for var in itertools.product(('uv','vu'),('fwd','rev'),('norm',),('neg','pos'),('b1','b0'))}
best={}
for e in g['m_pEdges']:
    eo=e.get('obj')
    if not isinstance(eo,dict): continue
    fh=[x.get('ref') for x in eo['m_pFace']]
    if len(fh)<2: continue
    for si,h in enumerate(fh):
        if h in ruled and fh[1-si] in pl:
            fl=eo['m_firstAndLastEdgePnts']
            for q in range(2):
                uc=fl[q]['uv'][si]; up=fl[q]['uv'][1-si]; P=plane(pl[fh[1-si]],*up)
                for var,fn in forms(ruled[h]).items():
                    d=np.linalg.norm(fn(*uc)-P); best.setdefault(var,[]).append(d)
for var,d in sorted(best.items(),key=lambda a:max(a[1]))[:5]: print(var,round(max(d),6),len(d))
