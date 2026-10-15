import sys,glob,struct,os
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
p=sys.argv[1]; target=int(sys.argv[2])
o,cls,ids=S.load(p); W=S.id_size(cls); F='<I' if W==4 else '<Q'
sch=D.Schema(cls); dec=D.Dec(sch,idsize=W,trace=True); et=I.element_tags(cls)
import rvt_es as ES
try: dec.es_schemas=ES.load(p)[0]
except Exception: dec.es_schemas={}
for pn in sorted(x for x in ['/'.join(e) for e in o.listdir(streams=True)] if x.startswith('Partitions/')):
    ch=T.joined(o.openstream(pn).read()); j=0; pat=struct.pack(F,target)
    j=ch.find(pat)
    while j>=0:
        i=j-4
        for short in (False,True):
            dec.log=[]
            try: r,q=dec.record(ch,i,short)
            except Exception as e: continue
            if r['id']==target:
                print(pn,i,short,r['class'],r['complete'],(r.get('error') or '')[:200],q-i)
                for d,n,a,b2,v in dec.log[-12:]: print(f'  {a:7}-{b2:7} {n:52} {str(v)[:60]}')
                if r.get('error'): 
                    import re; m=re.search(r' at (\d+)',r['error'])
                    if m: a=int(m.group(1)); print('BYTES',ch[a-40:a+80].hex(' '))
        j=ch.find(pat,j+1)
