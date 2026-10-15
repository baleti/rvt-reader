import sys,os,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E
rvt=sys.argv[1]; sid=int(sys.argv[2])
x=E.extract(rvt,extra=('FamilySymbol',),only_ids={sid})
r=[v for (e,c),v in x['recs'].items()][0]
f=r['fields']
paths=collections.Counter()
def walk(o,p):
    if isinstance(o,dict):
        ks=set(o)
        if 'm_xVec' in ks or 'm_loops' in ks or 'm_edges' in ks or 'm_pSurface' in ks: paths[(p,tuple(sorted(k for k in ks if o[k] is not None))[:14])]+=1
        for k,v in o.items():
            if v is not None: walk(v,p+'.'+k)
    elif isinstance(o,list):
        for i,v in enumerate(o[:50]): walk(v,p+'[]')
walk(f,'')
for (p,k),n in paths.most_common(12): print(n,p,k)
