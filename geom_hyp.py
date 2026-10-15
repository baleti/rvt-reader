import sys,glob,struct,os,itertools
sys.path.insert(0,'/home/user1/rvt-research')
os.environ['RVT_GEOM']='1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
p=glob.glob(sys.argv[1])[0]; cname=sys.argv[2]
o,cls,ids=S.load(p); sch=D.Schema(cls); dec=D.Dec(sch,idsize=S.id_size(cls)); lt=sch.by[cname]+12; et=I.element_tags(cls)
gs=sch.by['DatumPlaneGeomStep']
samples=[]
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            eid=struct.unpack_from('<I',chunk,i+4)[0]
            if eid not in ids or struct.unpack_from('<H',chunk,i+16)[0]!=lt: continue
            os.environ['RVT_GEOM']=''; D.Dec.STOP=('GeomStepList','GeomTable')
            try:
                r,q=dec.record(chunk,i)
                if r['fields'].get('m_id')!=eid or r.get('error'): continue
                pend=[]; v,q2=dec.struct(chunk,q,sch.by['GeomStepList'],pend,['x'])
            except Exception: continue
            n=q2
            while n<len(chunk)-24:
                n+=1
                e2=struct.unpack_from('<I',chunk,n+4)[0]
                if e2 in ids and struct.unpack_from('<H',chunk,n+16)[0] in et: break
            samples.append((chunk,q2,n,v)); 
            if len(samples)>=6: break
        if len(samples)>=6: break
    if len(samples)>=6: break
print(len(samples),'samples; tails',[n-q for c,q,n,v in samples])
def attempt(chunk,q2,n,skip):
    d=D.Dec(sch,idsize=S.id_size(cls)); d.STOP=()
    try:
        pend=[]; v,p2=d.struct(chunk,q2+skip,gs,pend,['gs'])
        for slot,t in pend:
            r=d.body(chunk,p2,t,['gs*']); p2=r[1]
        return p2
    except Exception as e: return None
for skip in range(0,17,1):
    res=[attempt(c,q,n,skip) for c,q,n,v in samples]
    ok=sum(1 for r,(c,q,n,v) in zip(res,samples) if r==n)
    print('skip',skip,'exact matches',ok,'/',len(samples),[ (r-n) if r else None for r,(c,q,n,v) in zip(res,samples)])
