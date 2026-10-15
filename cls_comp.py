import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_entities as E_
f=sys.argv[1]; want=sys.argv[2].split(','); res=GG.cached_index(f)
x=E_.extract(f,extra=tuple(want))
agg=collections.defaultdict(collections.Counter); n=collections.Counter()
for (eid,c),r in x['recs'].items():
    n[c]+=1
    if eid not in res: agg[c]['no saved graphics']+=1; continue
    b=res[eid]['bodies']
    for k in ('Geometry','Face','GPolyMesh','GInstance','GLine','GArc','GElement'):
        if b.get(k): agg[c][k]+=1
    agg[c]['size>200']+= res[eid]['size']>200
for c in want: print(c,n[c],dict(agg[c]))
