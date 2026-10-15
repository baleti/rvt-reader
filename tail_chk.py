import sys,struct,os
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_scan as S, rvt_decode as D, rvt2text as T
p,pn,i=sys.argv[1],sys.argv[2],int(sys.argv[3])
o,cls,ids=S.load(p); W=S.id_size(cls); sch=D.Schema(cls); dec=D.Dec(sch,idsize=W)
import rvt_es as ES
dec.es_schemas=ES.load(p)[0]
ch=T.joined(o.openstream(pn).read()); r,q=dec.record(ch,i,False)
print(r['class'],q-i,r['bodies'][:12]); print('AFTER',ch[q:q+100].hex(' ')); print('PRE',ch[q-60:q].hex(' '))
import numpy as np
idarr=np.array(sorted(ids),dtype=np.uint64)
c=[x for x in S.header_candidates(ch[q:q+4000],idarr,W)]
print('next candidates (rel):',c[:5])
if c:
    k=c[0]; print('gap bytes',k, ch[q:q+k].hex(' '))
