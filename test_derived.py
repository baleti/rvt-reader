import sys,os,collections,math
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E, rvt_geom as Gm, eval_gt as G
rvt,tsv=sys.argv[1],sys.argv[2]
x=E.extract(rvt,want_all=True); Egt,P=G.load_gt(tsv)
lv={}
for (eid,c),r in x['recs'].items():
    if c=='Level':
        o=E.S_(r['fields'],'m_pSurface','m_origin')
        if o: lv[eid]=o[2]
res=collections.defaultdict(lambda:[0,0,0]); ex={}
for (eid,c),r in x['recs'].items():
    if c in ('RbsPipeCurve','RbsDuctCurve','RbsConduitCurve','CableTray'): d=Gm.mep_curve(r['fields'],c,lv)
    elif c=='FamilyInstance': d=Gm.fam_instance(r['fields'],lv)
    else: continue
    for b,nm,stg,v in P.get(eid,[]):
        if stg!='Double' or v=='' or nm not in d: continue
        k=res[(c,nm)]; k[0]+=1
        if abs(d[nm]-float(v))<=1e-6*max(1,abs(float(v))): k[1]+=1
        else: ex.setdefault((c,nm),(eid,d[nm],v))
    for b,nm,stg,v in P.get(eid,[]):
        if stg=='Double' and v!='' and c in ('RbsPipeCurve','RbsDuctCurve','RbsConduitCurve','CableTray','FamilyInstance'): res[(c,nm)][2]+=1
for (c,nm),(a,ok,t) in sorted(res.items()):
    if a: print(f'{c:16s} {nm:24s} derived {a:5d} correct {ok:5d} ({100*ok/a:5.1f}%) of {t:5d}',ex.get((c,nm),''))
