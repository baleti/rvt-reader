import sys,os,struct,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_scan as S, rvt_decode as D, rvt2text as T, rvt_xcache
f=sys.argv[1]; klass=sys.argv[2]; nmax=int(sys.argv[3])
o,cls,ids=S.load(f); W=S.id_size(cls); F='<I' if W==4 else '<Q'; sch=D.Schema(cls); dec=D.Dec(sch,idsize=W)
import rvt_es as ES
try: dec.es_schemas=ES.load(f)[0]
except Exception: dec.es_schemas={}
x=rvt_xcache.get_x(f)
sample=[e for (e,c) in x['recs'] if c==klass][:nmax]
names={i+12:c['name'] for i,c in enumerate(cls)}
tally=collections.Counter(); sizes=collections.defaultdict(list)
for pn in sorted(n for n in ['/'.join(e) for e in o.listdir(streams=True)] if n.startswith('Partitions/')):
    ch=T.joined(o.openstream(pn).read())
    idarr=np.array(sorted(sample),dtype=np.uint64 if W==8 else np.uint32)
    for i in S.header_candidates(ch,idarr,W):
        eid=struct.unpack_from(F,ch,i+4)[0]
        for short in (False,True):
            tag=struct.unpack_from('<H',ch,i+12+W-(4 if short else 0))[0]
            if tag not in names: continue
            try: r,q=dec.record(ch,i,short)
            except Exception: continue
            if r['id']!=eid: continue
            tally[(names[tag],short)]+=1; sizes[(names[tag],short)].append(q-i)
for k,n in tally.most_common(): print(k,n,'avg size',sum(sizes[k])//len(sizes[k]),'max',max(sizes[k]))
