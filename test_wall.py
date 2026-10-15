import sys,os,collections,math
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E, rvt_geom as Gm, eval_gt as G
rvt,tsv=sys.argv[1:3]
x=E.extract(rvt,extra=('SWall','FamilyInstance'))
Egt,P=G.load_gt(tsv)
hosts=collections.Counter()
for (e,c),r in x['recs'].items():
    if c=='FamilyInstance':
        h=r['fields'].get('m_hostId')
        if h is not None: hosts[int(h)]+=1
res=collections.defaultdict(lambda:[0,0]); ex={}
def gtp(e): return {nm:float(v) for b,nm,stg,v in P.get(e,[]) if stg=='Double' and v!=''}
for (eid,c),r in x['recs'].items():
    if c!='SWall': continue
    gt=gtp(eid); cu=Gm.primary_curve(r['fields'])
    if cu is None or 'Unconnected Height' not in gt: continue
    L=Gm.curve_length(cu); H=gt['Unconnected Height']
    tid=int(Egt.get(eid,{}).get('tid') or -1); tw=gtp(tid).get('Width')
    inserts=hosts.get(eid,0)
    key=('hosted' if inserts else 'plain')
    if 'Area' in gt:
        k=res[(key,'Area=L*H')]; k[0]+=1
        if abs(L*H-gt['Area'])<=1e-6*gt['Area']: k[1]+=1
        else: ex.setdefault((key,'Area=L*H'),(eid,L*H,gt['Area']))
    if 'Volume' in gt and tw:
        k=res[(key,'Volume=L*H*W')]; k[0]+=1
        if abs(L*H*tw-gt['Volume'])<=1e-6*gt['Volume']: k[1]+=1
        else: ex.setdefault((key,'Volume=L*H*W'),(eid,L*H*tw,gt['Volume']))
for k,(a,ok) in sorted(res.items()): print(k,a,ok,ex.get(k,''))
