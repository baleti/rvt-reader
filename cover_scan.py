import sys,os,struct
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_inventory as I
f,pn=sys.argv[1],sys.argv[2]; offs=[int(a) for a in sys.argv[3:]]
o,cls,ids=S.load(f); W=S.id_size(cls); F='<I' if W==4 else '<Q'; sch=D.Schema(cls); dec=D.Dec(sch,idsize=W); et=I.element_tags(cls)
import rvt_es as ES
try: dec.es_schemas=ES.load(f)[0]
except Exception: dec.es_schemas={}
ch=T.joined(o.openstream(pn).read()); idarr=np.array(sorted(ids),dtype=np.uint64)
cand=S.header_candidates(ch,idarr,W)
import bisect
cs=sorted(set(cand)); print("cands",len(cs),"buf",len(ch))
for off in offs:
    k=bisect.bisect_right(cs,off)-1
    print('nearest cands before',cs[max(0,k-4):k+1],'after',cs[k+1:k+3],'off',off)
    for i in cs[max(0,k-3):k+1]:
        for short in (False,True):
            try: r,q=dec.record(ch,i,short)
            except Exception: continue
            print(off,'cand',i,'short' if short else 'long',r['class'],r['id'],'range',i,q,'covers' if i<=off<q else 'no',r['complete'])
