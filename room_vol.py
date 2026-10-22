import sys,collections; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_elemmesh as EM, rvt_mesh as M, eval_gt as G, rvt_xcache
rvt,tsv=sys.argv[1:3]
E,P=G.load_gt(tsv); doc=EM.Doc(rvt); st=collections.Counter(); k=0
for eid,e in E.items():
    if e['cls'] not in('Room','Space') or eid not in doc.res: continue
    g=[float(v) for b,nm,s,v in P[eid] if nm=='Volume']
    if not g: continue
    m=EM.element_mesh(doc,eid,detail=3)
    if not m['tris']: st['nomesh']+=1; continue
    vol,closed,area,_=M.volume_by_node(m['tris'],m.get('meta'),m['nid'],fid=m.get('fid'))
    r=vol/g[0] if g[0] else 0
    st['ok' if abs(r-1)<0.02 else 'bad']+=1
    if k<8 and abs(r-1)>=0.02: k+=1; print(eid,e['cls'],round(vol,2),round(g[0],2),closed)
print(st)
