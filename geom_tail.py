import sys,glob,struct,os
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
p=glob.glob(sys.argv[1])[0]; cname=sys.argv[2]; N=int(sys.argv[3]) if len(sys.argv)>3 else 4
o,cls,ids=S.load(p); sch=D.Schema(cls); dec=D.Dec(sch,idsize=S.id_size(cls)); lt=sch.by[cname]+12; et=I.element_tags(cls)
res=[]
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            eid=struct.unpack_from('<I',chunk,i+4)[0]
            if eid not in ids or struct.unpack_from('<H',chunk,i+16)[0]!=lt: continue
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
            res.append((eid,q2,n,chunk[q2:n],[(s['ptr'],sch.name(s['ptr'])) for s in v['m_nonBRepGList']]))
            if len(res)>=N: break
        if len(res)>=N: break
    if len(res)>=N: break
for eid,a,b,d,pt in res:
    print(eid,'GeomStepList ends at',a,'next header at',b,'tail',len(d),'bytes; nonBRep ptrs',pt)
    print(' '.join(d[k:k+4].hex() for k in range(0,min(len(d),320),4)))
