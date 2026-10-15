import sys,json,os
sys.path.insert(0,'/home/user1/rvt-research')
os.environ['RVT_GEOM']='1'
import rvt_entities as E
def show(x,ind=0,maxd=99):
    pad=' '*ind
    if isinstance(x,dict):
        for a,b in x.items():
            if b is None: continue
            if isinstance(b,(dict,list)) and ind<maxd: print(pad+str(a)+':'); show(b,ind+2,maxd)
            else: print(pad+str(a)+' = '+str(b)[:70])
    elif isinstance(x,list):
        if x and all(isinstance(b,(int,float)) for b in x): print(pad+str(x)[:200])
        else:
            for i,b in enumerate(x[:5]): print(pad+'[%d]'%i); show(b,ind+2,maxd)
    else: print(pad+str(x)[:70])
if __name__=='__main__':
    rvt=sys.argv[1]; cl=sys.argv[2]; ids={int(a) for a in sys.argv[3].split(',')}; keys=sys.argv[4].split(',') if len(sys.argv)>4 else None
    x=E.extract(rvt,extra=(cl,),only_ids=ids)
    for (e,c),r in x['recs'].items():
        print('==',e,c,r['complete'],r['error'])
        show({k:v for k,v in r['fields'].items() if not keys or k in keys})
