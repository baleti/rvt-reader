import sys,glob,re,struct,os
sys.path.insert(0,'/home/user1/rvt-research')
os.environ['RVT_GEOM']='1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
from schema_view import tn
p=glob.glob(sys.argv[1])[0]; want=sys.argv[2]; nlog=int(sys.argv[3]) if len(sys.argv)>3 else 14
o,cls,ids=S.load(p); IDW=S.id_size(cls); IDF='<I' if IDW==4 else '<Q'
sch=D.Schema(cls); dec=D.Dec(sch,idsize=IDW,trace=True); et=I.element_tags(cls); by=sch.by
def fld(m):
    cn,fn=m.split('@@')[1].strip().split(' ')[0].split('.')[:2]
    for fl in cls[by[cn]]['fields']:
        if fl['name']==fn: return cn,fn,fl
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            eid=struct.unpack_from(IDF,chunk,i+4)[0]
            if eid not in ids: continue
            tag=struct.unpack_from('<H',chunk,i+12+IDW)[0]
            if tag not in et: continue
            dec.log=[]
            try: r,q=dec.record(chunk,i)
            except Exception: continue
            m=r.get('error') or ''
            if want in m:
                print('EXAMPLE',r['class'],eid,m[:260])
                cn,fn,fl=fld(m); print('FIELD',cn,fn,[hex(t) for t in fl['types']],fl.get('ns'),'ref',fl.get('ref'),tn(cls,fl))
                for d,n,a,b2,v in dec.log[-nlog:]: print(f'  {a:7}-{b2:7} {n:52} {v}')
                a=int(re.search(r' at (\d+):',m).group(1)); print('BYTES@fail-24..+72:',chunk[a-24:a+72].hex(' ')); raise SystemExit
