import sys,os,json,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E, rvt_geom as Gm, eval_gt as G
rvt,tsv=sys.argv[1],sys.argv[2]
x=E.extract(rvt,want_all=True); Egt,P=G.load_gt(tsv)
res=collections.defaultdict(lambda:[0,0,0]); ex={}
for (eid,c),r in x['recs'].items():
    for b,nm,stg,v in P.get(eid,[]):
        if nm!='Length' or stg!='Double' or v=='': continue
        cu=Gm.primary_curve(r['fields'])
        res[c][2]+=1
        if cu is None: continue
        L=Gm.curve_length(cu)
        res[c][0]+=1
        if abs(L-float(v))<=1e-6*max(1,abs(float(v))): res[c][1]+=1
        else: ex.setdefault(c,(eid,L,v))
for c,(a,ok,t) in sorted(res.items(),key=lambda z:-z[1][2]): print(c,'curve',a,'match',ok,'of',t, ex.get(c,''))
