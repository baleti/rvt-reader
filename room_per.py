import sys,collections; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_elemmesh as EM, rvt_geomparams as GP, eval_gt as G
rvt,tsv=sys.argv[1:3]
E,P=G.load_gt(tsv); doc=EM.Doc(rvt); st=collections.Counter(); k=0
for eid,e in E.items():
    if e['cls'] not in('Room','Space') or eid not in doc.res: continue
    g={nm:float(v) for b,nm,s,v in P[eid] if nm in('Perimeter','Area') and v!=''}
    if 'Perimeter' not in g: continue
    r=GP.room_params(doc,eid)
    if 'Perimeter' not in r: st['none']+=1; continue
    q=r['Perimeter']/g['Perimeter'] if g['Perimeter'] else 0
    ok=abs(q-1)<1e-3
    st[(e['cls'],'ok' if ok else 'bad')]+=1
    if not ok and k<10: k+=1; print(eid,e['cls'],round(r['Perimeter'],3),round(g['Perimeter'],3),round(q,4),'area',round(r['Area'],2),g.get('Area'))
print(st)
