import sys,os,pickle,itertools,math
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_brep as B
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
w(r['fields']); g=geos[0]
faces={fc['handle']:fc['obj'] for fc in g['m_pFaces'] if isinstance(fc.get('obj'),dict)}
surf={h:f['m_pSurf']['obj'] for h,f in faces.items()}
cyl={h:s for h,s in surf.items() if 'm_radius' in s}; pl={h:s for h,s in surf.items() if 'm_radius' not in s}
def p_plane(s,u,v): return B.uv3d((B._v(s['m_origin']),B._v(s['m_xVec']),B._v(s['m_yVec'])),u,v)
def add(a,b,k=1): return [a[j]+k*b[j] for j in range(3)]
def cyl_pt(s,u,v,form):
    c=B._v(s['m_center']); x=B._v(s['m_xVec']); y=B._v(s['m_yVec']); z=B._v(s['m_zVec']); R=s['m_radius']
    ax={'x':x,'y':y,'z':z}
    a,b,axis=form
    p=add(c,ax[a],R*math.cos(u)); p=add(p,ax[b],R*math.sin(u)); p=add(p,ax[axis],v); return p
best={}
for e in g['m_pEdges']:
    eo=e.get('obj'); 
    if not isinstance(eo,dict): continue
    fh=[x.get('ref') for x in eo['m_pFace']]
    if len(fh)<2: continue
    for si,(h) in enumerate(fh):
        if h in cyl:
            other=fh[1-si]
            if other in pl:
                fl=eo['m_firstAndLastEdgePnts']
                pts=[ (fl[0]['uv'], fl[1]['uv']) ]
                for q in range(2):
                    uc=fl[q]['uv'][si]; up=fl[q]['uv'][1-si]
                    P=p_plane(pl[other],up[0],up[1])
                    for form in itertools.product('xyz','xyz','xyz'):
                        if len(set(form))<3: continue
                        C=cyl_pt(cyl[h],uc[0],uc[1],form)
                        d=math.dist(P,C); best.setdefault(form,[]).append(d)
for form,d in sorted(best.items(),key=lambda a:max(a[1]))[:4]: print(form,round(max(d),6),len(d))
