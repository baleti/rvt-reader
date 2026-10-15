import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG
f=sys.argv[1]; res=GG.cached_index(f); o,dec=GG.load_dec(f)
cand=sorted((r['size'],i) for i,r in res.items() if r['bodies'].get('GPolyMesh'))
print(len(cand),cand[:4]); sz,i=cand[int(sys.argv[2]) if len(sys.argv)>2 else 0]; r=GG.get_record(f,res[i],o,dec)
print('bodies',{k:v for k,v in res[i]['bodies'].items()})
def sh(x,ind=0,k='',maxd=8):
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
        if x and all(isinstance(a,(int,float)) for a in x): print(pad+k+' [%d] '%len(x)+str(x[:12])[:130]); return
        print(pad+k+'[%d]'%len(x))
        for j,a in enumerate(x[:2]): sh(a,ind+1,'[%d]'%j,maxd)
    else: print(pad+k+' = '+str(x)[:70])
def find(z):
    if isinstance(z,dict):
        if 'm_pFacetedTopology' in z: return z
        for b in z.values():
            if b is not None:
                r_=find(b)
                if r_: return r_
    elif isinstance(z,list):
        for b in z:
            r_=find(b)
            if r_: return r_
pm=find(r['fields']); sh(pm,0,'GPolyMesh',9)
