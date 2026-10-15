import sys,glob,struct,os,collections
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
p=glob.glob(sys.argv[1])[0]
o,cls,ids=S.load(p); W=S.id_size(cls); sch=D.Schema(cls); dec=D.Dec(sch,idsize=W); et=I.element_tags(cls); F='<I' if W==4 else '<Q'
gsl=sch.by['GeomStepList']
pat=collections.defaultdict(collections.Counter); n=0
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            eid=struct.unpack_from(F,chunk,i+4)[0]
            if eid not in ids or struct.unpack_from('<H',chunk,i+12+W)[0] not in et: continue
            try:
                r,q=dec.record(chunk,i)
                if r['fields'].get('m_id')!=eid or r.get('error'): continue
                f=r['fields'].get('m_geomSteps')
                if not f or f.get('obj')!='<geometry not decoded>': continue
                pend=[]; v,q2=dec.struct(chunk,q,gsl,pend,['x'])
            except Exception: continue
            for sl in v['m_nonBRepGList']+v['m_bRepFormGList']+v['m_bRepAdjustGList']:
                if not isinstance(sl,dict): continue
                t=sl['ptr']; 
                pat[sch.name(t)][chunk[q2:q2+9].hex()[:18]]+=1
                break
            n+=1
            if n>4000: break
print(n)
for k,c in sorted(pat.items(),key=lambda kv:-sum(kv[1].values()))[:12]:
    print(k,sum(c.values()),c.most_common(6))
