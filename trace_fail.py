import sys,glob,struct,collections
sys.path.insert(0,'/home/user1/rvt-research')
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
from schema_view import tn
p=glob.glob(sys.argv[1])[0]; cname=sys.argv[2]; fld=sys.argv[3]; nlog=int(sys.argv[4]) if len(sys.argv)>4 else 25
o,cls,ids=S.load(p); IDW=S.id_size(cls); IDF='<I' if IDW==4 else '<Q'
sch=D.Schema(cls); dec=D.Dec(sch,idsize=IDW,trace=True); et=I.element_tags(cls); tag=sch.by[cname]+12
done=0
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            eid=struct.unpack_from(IDF,chunk,i+4)[0]
            if eid not in ids or struct.unpack_from('<H',chunk,i+12+IDW)[0]!=tag: continue
            dec.log=[]
            try: dec.record(chunk,i)
            except Exception as e:
                m=str(e)
                if fld in m:
                    print('FAIL',m[:300]); 
                    for d,n,a,b,v in dec.log[-nlog:]: print(f'{a:7}-{b:7} {n:55} {v}')
                    st=int(m.split(' at ')[-2].split(':')[0].split()[-1]) if False else None
                    done+=1
                    if done>=1: raise SystemExit
