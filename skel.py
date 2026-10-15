import sys,os,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E
rvt,cl,eid=sys.argv[1],sys.argv[2],int(sys.argv[3])
x=E.extract(rvt,extra=(cl,),only_ids={eid}); r=list(x['recs'].values())[0]
print(r['class'],len(r['bodies']),collections.Counter(r['bodies']).most_common(14))
paths=collections.Counter()
def w(o,p):
    if isinstance(o,dict):
        for k,v in o.items():
            if v is None or k in('handle','ptr','ref'): continue
            w(v,p+'.'+k if k!='obj' else p)
    elif isinstance(o,list):
        if o and not all(isinstance(a,(int,float)) for a in o):
            for a in o[:40]: w(a,p+'[]')
        else: paths[p+' =list'+str(len(o))]+=1
    else: paths[p]+=1
w(r['fields'],'')
for p,n in sorted(paths.items()):
    if any(s in p for s in sys.argv[4:]) or len(sys.argv)<5: print(n,p)
