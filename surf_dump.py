import sys,os,pickle
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); want=sys.argv[3]; rank=int(sys.argv[4]) if len(sys.argv)>4 else 0
o,dec=GG.load_dec(f)
cand=sorted((r['size'],i) for i,r in res.items() if r['bodies'].get(want))
sz,i=cand[rank]; r=GG.get_record(f,res[i],o,dec); print('id',i,sz,r['bodies'] if len(r['bodies'])<40 else len(r['bodies']))
def sh(x,ind=0,k='',maxd=9):
    pad='  '*ind
    if ind>maxd: return
    if isinstance(x,dict):
        keys=[a for a,b in x.items() if b is not None and a not in('handle','ptr')]
        print(pad+k+': {'+','.join(keys)+'}')
        for a in keys:
            b=x[a]
            if isinstance(b,(dict,list)): sh(b,ind+1,a,maxd)
            else: print(pad+'  '+a+' = '+str(b)[:70])
    elif isinstance(x,list):
        if x and all(isinstance(a,(int,float)) for a in x): print(pad+k+' '+str(x)[:110]); return
        print(pad+k+'[%d]'%len(x))
        for j,a in enumerate(x[:3]): sh(a,ind+1,'[%d]'%j,maxd)
    else: print(pad+k+' = '+str(x)[:70])
geos=[]
def w(z):
    if isinstance(z,dict):
        if z.get('m_pFaces'): geos.append(z)
        for b in z.values():
            if b is not None: w(b)
    elif isinstance(z,list):
        for b in z: w(b)
w(r['fields'])
done=False
for g in geos:
    for fc in g['m_pFaces']:
        fo=fc.get('obj')
        if isinstance(fo,dict):
            s=fo.get('m_pSurf'); s=s.get('obj') if s else None
            if isinstance(s,dict) and ('m_pProfileCurve1' in s or 'm_pProfileCurve' in s or 'm_halfAngle' in s):
                print('--- face',fc['handle']); sh(s,0,'Surface',9); 
                print('loop envelope',fo['m_pFirstLoop']['obj']['m_Envelope'])
                done=True; break
    if done: break
