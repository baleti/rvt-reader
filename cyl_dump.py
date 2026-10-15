import sys,os,pickle
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); want=sys.argv[3]
o,dec=GG.load_dec(f)
# first record whose bodies include want, smallest size
cand=sorted((r['size'],i) for i,r in res.items() if r['bodies'].get(want))
print(cand[:5]); sz,i=cand[0]
r=GG.get_record(f,res[i],o,dec); print('id',i,r['class'],sz,r['bodies'])
geos=[]
def w(z):
    if isinstance(z,dict):
        if 'm_pFaces' in z: geos.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(r['fields'])
def sh(x,ind=0,k='',maxd=7):
    pad='  '*ind
    if ind>maxd: return
    if isinstance(x,dict):
        keys=[a for a,b in x.items() if b is not None and a not in('handle','ptr')]
        print(pad+k+': {'+','.join(keys)+'}')
        for a in keys:
            b=x[a]
            if isinstance(b,(dict,list)): sh(b,ind+1,a,maxd)
            else: print(pad+'  '+a+' = '+str(b)[:60])
    elif isinstance(x,list):
        if x and all(isinstance(a,(int,float)) for a in x): print(pad+k+' '+str(x)[:100]); return
        print(pad+k+'[%d]'%len(x))
        for j,a in enumerate(x[:3]): sh(a,ind+1,'[%d]'%j,maxd)
    else: print(pad+k+' = '+str(x)[:60])
for g in geos:
    for fc in g['m_pFaces']:
        f_=fc.get('obj') 
        if isinstance(f_,dict):
            sf=f_.get('m_pSurf'); s=sf.get('obj') if sf else None
            if isinstance(s,dict) and 'm_radius' in s or (isinstance(s,dict) and set(s)-{'m_Envelope','m_orientFlag','m_origin','m_xVec','m_yVec'}):
                print('--- face',fc.get('handle')); sh(f_,0,'Face',5); break
    else: continue
    # print edges with interior pts
    for e in g['m_pEdges'][:40]:
        eo=e.get('obj')
        if isinstance(eo,dict) and eo.get('m_interiorEdgePnts'):
            print('--- edge',e.get('handle')); sh(eo,0,'Edge',5); break
    break
