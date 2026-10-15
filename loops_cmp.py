import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); doc=EM.Doc(f); rec=doc.rec(eid); geos,inst=EM._geos(rec['fields']); g=geos[0]
em=M._edge_map(g)
for fc in g['m_pFaces']:
    h=fc.get('handle'); fo=M._ob(fc)
    if not isinstance(fo,dict): continue
    os.environ['RVT_LOOPS']='ptr'; a=M.face_loops_uv(h,em); del os.environ['RVT_LOOPS']; b=M.face_loops_uv(h,em)
    ar=lambda L:[round(abs(M._area2(l)),3) for l in L]
    flag='' if sorted(ar(a))==sorted(ar(b)) else '  <<<<'
    print(h,'ptr',ar(a),'cyc',ar(b),flag)
