import sys,os,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E, rvt_famparams as F, eval_gt as G
rvt,tsv=sys.argv[1],sys.argv[2]
x=E.extract(rvt,want_all=True); Egt,P=G.load_gt(tsv)
cap=F.captions(x['recs']); print('captions',len(cap))
byid={}
for (eid,c),r in x['recs'].items(): byid.setdefault(eid,r)
res=collections.defaultdict(lambda:[0,0,0]); ex={}
for (eid,c),r in x['recs'].items():
    if c!='FamilyInstance': continue
    f=r['fields']; sid=F.S_(f,'m_pInstanceInfo','m_symbolId')
    sym=byid.get(int(sid),{}).get('fields') if sid is not None else None
    nv=F.named_values(f,cap,sym)
    for b,nm,stg,v in P.get(eid,[]):
        if stg!='Double' or v=='': continue
        k=res[nm]; k[2]+=1
        if nm in nv and nv[nm][0] is not None:
            k[0]+=1
            if abs(float(nv[nm][0])-float(v))<=1e-6*max(1,abs(float(v))): k[1]+=1
            else: ex.setdefault(nm,(eid,nv[nm],v))
for nm,(a,ok,t) in sorted(res.items(),key=lambda z:-z[1][2])[:30]: print(f'{nm:28s} have {a:5d} match {ok:5d} of {t:5d}',ex.get(nm,''))
