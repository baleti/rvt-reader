import sys,collections; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_params as RP, eval_gt as G
rvt,tsv=sys.argv[1:3]
p=RP.params(rvt,geom=True); E,P=G.load_gt(tsv)
c=collections.Counter(); ex={}
for eid,e in E.items():
    if e['cls']!='Panel': continue
    r=p.get(eid); has=bool(r and ('Volume' in r['params'] or 'Volume|Double' in r['params']))
    ft=[v for b,nm,stg,v in P.get(eid,[]) if nm=='Family and Type']
    gv=[v for b,nm,stg,v in P.get(eid,[]) if nm=='Volume']
    key=(e.get('type',''),has,r['class'] if r else None); c[key]+=1; ex.setdefault(key,(eid,gv,e))
for k,n in c.items(): print(n,k,ex[k])
