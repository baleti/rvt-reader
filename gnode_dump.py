import sys,os
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E
rvt,cl,eid=sys.argv[1],sys.argv[2],int(sys.argv[3]); key=sys.argv[4] if len(sys.argv)>4 else 'm_pretaggingGNodes'; maxd=int(sys.argv[5]) if len(sys.argv)>5 else 9
x=E.extract(rvt,extra=(cl,),only_ids={eid}); r=list(x['recs'].values())[0]; f=r['fields']
def show(o,ind,k=''):
    pad='  '*ind
    if ind>maxd: print(pad+k+': ...'); return
    if isinstance(o,dict):
        keys=[a for a,b in o.items() if b is not None and a not in('handle','ptr')]
        print(pad+k+': {'+','.join(keys[:12])+('...' if len(keys)>12 else '')+'}')
        for a in keys:
            b=o[a]
            if isinstance(b,(dict,list)): show(b,ind+1,a)
            else: print(pad+'  '+a+' = '+str(b)[:70])
    elif isinstance(o,list):
        if o and all(isinstance(a,(int,float)) for a in o): print(pad+k+' '+str(o)[:110]); return
        print(pad+k+'[%d]'%len(o))
        for i,a in enumerate(o[:4]): show(a,ind+1,'[%d]'%i)
    else: print(pad+k+' = '+str(o)[:70])
show(f[key],0,key)
