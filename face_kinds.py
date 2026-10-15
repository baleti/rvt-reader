import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f); rec=doc.rec(eid); fl=rec['fields']; bb=fl['m_bBox']; print('bbox',np.round(bb,3).tolist())
geos,inst=EM._geos(fl)
for gi,g in enumerate(geos):
    em=M._edge_map(g); print('geo',gi,'faces',len(g['m_pFaces']),'edges',len(em))
    for fc in g['m_pFaces']:
        fo=M._ob(fc)
        if not isinstance(fo,dict): print('  nonobj'); continue
        kind,ev=M.surface_eval(fo.get('m_pSurf')); loops=M.face_loops_uv(fc['handle'],em)
        s=M._ob(fo.get('m_pSurf')); extra=''
        if kind in('cylinder',): extra='R=%.4f'%s['m_radius']
        if kind=='cone': extra='alpha=%.4f'%s['m_halfAngle']
        env=s.get('m_Envelope') if isinstance(s,dict) else None
        print('  ',fc['handle'],kind,extra,'loops',[len(l) for l in loops],'uvarea',[round(abs(M._area2(l)),4) for l in loops][:3],'env',np.round(env['m_corners'],3).tolist() if env else None,'orient',s.get('m_orientFlag') if isinstance(s,dict) else None)
