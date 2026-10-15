import sys,time,os,subprocess,pickle
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'; os.environ['RVT_WORKERS']='1'
f=sys.argv[1]
if len(sys.argv)>2:
    import rvt_entities as E, rvt_decode as D
    t=time.time(); x=E.extract(f,want_all=True); dt=time.time()-t
    x.pop('sch',None); pickle.dump((dt,D._RC is not None,x),open(sys.argv[2],'wb')); print('dumped',dt,D._RC is not None); sys.exit()
env=dict(os.environ)
subprocess.run([sys.executable,__file__,f,'/tmp/ext_py.pkl'],env={**env,'RVT_NOFAST':'1'}); subprocess.run([sys.executable,__file__,f,'/tmp/ext_rs.pkl'],env=env)
ta,fa,a=pickle.load(open('/tmp/ext_py.pkl','rb')); tb,fb,b=pickle.load(open('/tmp/ext_rs.pkl','rb'))
def deep(x,y,path):
    if type(x)!=type(y): return '%s type %s vs %s %r %r'%(path,type(x).__name__,type(y).__name__,str(x)[:50],str(y)[:50])
    if isinstance(x,dict):
        if list(x)!=list(y): return '%s keys %s vs %s'%(path,list(x)[:6],list(y)[:6])
        for k in x:
            r=deep(x[k],y[k],path+'.'+str(k))
            if r: return r
        return None
    if isinstance(x,(list,tuple)):
        if len(x)!=len(y): return '%s len %d vs %d'%(path,len(x),len(y))
        for i,(p,q) in enumerate(zip(x,y)):
            r=deep(p,q,'%s[%d]'%(path,i))
            if r: return r
        return None
    if isinstance(x,float) and x!=x and y!=y: return None
    return None if x==y else '%s %r vs %r'%(path,x,y)
bad=0
for k in sorted(a['recs']):
    r=deep(a['recs'][k],b['recs'].get(k),'rec%s'%(k,))
    if r:
        bad+=1
        if bad<=5: print(r)
print('python',round(ta,1),fa,'rust',round(tb,1),fb,'differing records',bad,'of',len(a['recs']))
bad=0
for k in sorted(a['eh']):
    r=deep(a['eh'][k],b['eh'].get(k),'eh%s'%k)
    if r:
        bad+=1
        if bad<=3: print(r)
print('eh differing',bad,'of',len(a['eh']))
