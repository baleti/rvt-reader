import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f)
def ob(x): return x.get('obj',x) if isinstance(x,dict) else x
def cond(c):
    c=ob(c)
    return '{'+','.join('%s=%s'%(k[2:],str(v)[:20]) for k,v in c.items() if v is not None)+'}' if isinstance(c,dict) else str(c)
def walk(n,d,label,rec_id):
    n=ob(n)
    if not isinstance(n,dict): return
    conds=[cond(c) for c in (n.get('m_oConditions') or [])]
    if n.get('m_pFaces'):
        t=M.tessellate_geometry(n); v,c,_,a=M.mesh_volume(t['tris']) if t['tris'] else (0,False,0,0)
        print('  '*d+label,'GEOMETRY faces',len(n['m_pFaces']),'vol(coarse)',round(v,4),'closed',c); return
    gi=ob(n.get('m_GInfo')) or {}
    print('  '*d+label,'conds',conds,'tag',gi.get('m_tag'),'inst' if 'm_instanceInfo' in n else '')
    for j,k in enumerate(n.get('m_subNodes') or []): walk(k,d+1,'[%d]'%j,rec_id)
    if 'm_instanceInfo' in n:
        sid=int(ob(n['m_instanceInfo'])['m_symbolId']); print('  '*d+'  -> symbol',sid)
        sr=doc.rec(sid)
        if sr and sid!=rec_id: walk(sr['fields'],d+2,'SYM%d'%sid,sid)
rec=doc.rec(eid); print('GT-less structure of',eid); walk(rec['fields'],0,'root',eid)
