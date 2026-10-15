import sys,os,struct,collections
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import numpy as np, olefile, rvt_scan as S, rvt_decode as D, rvt_inventory as I
from rvtfmt import inflate_stream
f=sys.argv[1]
o,cls,ids=S.load(f); W=S.id_size(cls); F='<I' if W==4 else '<Q'; sch=D.Schema(cls); dec=D.Dec(sch,idsize=W); et=I.element_tags(cls)
import rvt_es as ES
try: dec.es_schemas=ES.load(f)[0]
except Exception: dec.es_schemas={}
d=inflate_stream(o.openstream('Global/ContentDocuments').read())[1]
names={i+12:c['name'] for i,c in enumerate(cls)}
want={t for t in et if names[t] in ('ExtrusionElem','BlendElem','GenSweep','Sweep','RevolveElem','SweptBlendElem','FamilySymbol','CurveElem','Extrusion','VoidElem') or 'Extrusion' in names[t] or 'Sweep' in names[t] or 'Blend' in names[t] or 'Revol' in names[t]}
print('wanted tags',[names[t] for t in want])
found=collections.Counter(); ok=collections.Counter(); first={}
for a in (0,1):
    u=np.frombuffer(d,dtype='<u2',count=(len(d)-a)//2,offset=a)
    hit=np.nonzero(np.isin(u,list(want)))[0]
    for h in hit:
        tagpos=int(h)*2+a; i=tagpos-(12+W)
        if i<0: continue
        eid=struct.unpack_from(F,d,i+4)[0]
        found[names[int(u[h])]]+=1
        try: r,q=dec.record(d,i,False)
        except Exception: continue
        if r['fields'].get('m_id')==eid and r['complete']:
            ok[names[int(u[h])]]+=1; first.setdefault(names[int(u[h])],(i,eid,q-i))
print('tag hits',dict(found)); print('decoded ok',dict(ok)); print(first)
