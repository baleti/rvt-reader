import sys,os,struct,re
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_scan as S, rvt_decode as D, rvt2text as T
p=sys.argv[1]; want=int(sys.argv[2]); nlog=int(sys.argv[3]) if len(sys.argv)>3 else 40; skipid=sys.argv[4] if len(sys.argv)>4 else ''
o,cls,ids=S.load(p); W=S.id_size(cls); F='<I' if W==4 else '<Q'; sch=D.Schema(cls); dec=D.Dec(sch,idsize=W,trace=True)
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    for chunk in T.segments(o.openstream(pn).read()):
        for i in range(0,len(chunk)-24):
            if struct.unpack_from(F,chunk,i+4)[0]!=want: continue
            tag=struct.unpack_from('<H',chunk,i+12+W)[0]
            if not 12<=tag<12+len(cls): continue
            dec.log=[]
            try: r,q=dec.record(chunk,i)
            except Exception as e: continue
            if r['fields'].get('m_id')!=want: continue
            print('class',r['class'],'complete',r['complete'],'err',r.get('error'),'start',i,'end',q,'len',len(chunk))
            rows=[x for x in dec.log if not re.search(r'Identifier\.|ElementId\.',x[1])]
            for d,n,a,b2,v in rows[-nlog:]: print(f'  {a:6}-{b2:6} {n:50} {v[:70]}')
            raise SystemExit
