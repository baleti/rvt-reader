import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_xcache
f=sys.argv[1]; pk=sys.argv[2]; res=pickle.load(open(pk,'rb')); x=rvt_xcache.get_x(f); cl={}
for (e,c) in x['recs']: cl.setdefault(e,c)
want=sys.argv[3]
cand=sorted((r['bodies'].get('Face',0),i) for i,r in res.items() if cl.get(i)==want and 5<=r['bodies'].get('Face',0)<=14)
print(cand[:10])
fc,i=cand[len(cand)//2] if len(sys.argv)<5 else cand[int(sys.argv[4])]
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
print('id',i,want,'faces',fc,'bodies',collections.Counter(r['bodies']).most_common(12),'size',res[i]['size'])
def show(o,ind,k='',maxd=30):
    pad='  '*ind
    if ind>maxd: return
    if isinstance(o,dict):
        keys=[a for a,b in o.items() if b is not None and a not in('handle','ptr')]
        print(pad+k+': {'+','.join(keys[:10])+('...' if len(keys)>10 else '')+'}')
        for a in keys:
            b=o[a]
            if isinstance(b,(dict,list)): show(b,ind+1,a)
            else: print(pad+'  '+a+' = '+str(b)[:50])
    elif isinstance(o,list):
        if o and all(isinstance(a,(int,float)) for a in o): print(pad+k+' '+str(o)[:90]); return
        print(pad+k+'[%d]'%len(o))
        for j,a in enumerate(o[:2]): show(a,ind+1,'[%d]'%j)
    else: print(pad+k+' = '+str(o)[:50])
# find the Geometry nodes
geos=[]
def w(o,path):
    if isinstance(o,dict):
        if 'm_pFaces' in o: geos.append((path,o))
        for a,b in o.items():
            if b is not None: w(b,path+'/'+a)
    elif isinstance(o,list):
        for j,b in enumerate(o): w(b,path+'[%d]'%j)
w(r['fields'],'')
print('Geometry nodes',len(geos))
show(geos[0][1],0,'Geometry')
