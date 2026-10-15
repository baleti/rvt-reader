import sys,os,collections,math
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E, rvt_geom as Gm, rvt_scan as S, rvt_solids as So, eval_gt as G
rvt,tsv=sys.argv[1:3]
x=E.extract(rvt,extra=('Floor','Ceiling','CurveElem')); Egt,P=G.load_gt(tsv); own=S.owners(rvt)
kids=collections.defaultdict(list)
for e,o in own.items():
    if o is not None: kids[o].append(e)
byid={}
for (e,c),r in x['recs'].items(): byid.setdefault(e,r)
def desc(e,d=0):
    for k in kids.get(e,[]):
        yield k
        if d<2: yield from desc(k,d+1)
res=collections.defaultdict(lambda:[0,0,0]); ex={}
for (eid,c),r in x['recs'].items():
    if c not in ('Floor','Ceiling'): continue
    cur=[]
    for k in desc(eid):
        rr=byid.get(k)
        if rr and rr['class']=='CurveElem':
            for cu in Gm.find_curves(rr['fields']): cur.append(cu)
    if not cur: continue
    loops=So.chain_loops(cur)
    gt={nm:float(v) for b,nm,stg,v in P.get(eid,[]) if stg=='Double' and v!=''}
    if not loops: res[(c,'no-loop')][0]+=1; continue
    # outer = loop with largest area
    faces=[]
    try:
        areas=[]
        for l in loops:
            f=So.planar_face([l]); areas.append((So.props_surface(f)[0],l))
        areas.sort(key=lambda a:-a[0]); outer=areas[0][1]; holes=[a[1] for a in areas[1:]]
        face=So.planar_face([outer]+holes)
        A=So.props_surface(face)[0]; per=So.perimeter([outer]+holes)
    except Exception as ex_:
        res[(c,'occ-error')][0]+=1; continue
    for nm,val in (('Area',A),('Perimeter',per)):
        if nm in gt:
            k=res[(c,nm)]; k[0]+=1; k[2]+=1
            if abs(val-gt[nm])<=1e-6*max(1,abs(gt[nm])): k[1]+=1
            else: ex.setdefault((c,nm),(eid,val,gt[nm]))
    if 'Area' in gt and 'Thickness' in gt and 'Volume' in gt:
        k=res[(c,'Volume=Area*GTThickness')]; k[0]+=1; k[2]+=1
        if abs(A*gt['Thickness']-gt['Volume'])<=1e-6*max(1,gt['Volume']): k[1]+=1
        else: ex.setdefault((c,'Volume'),(eid,A*gt['Thickness'],gt['Volume']))
for k,(a,ok,t) in sorted(res.items()): print(k,'tested',a,'match',ok,ex.get(k,''))
