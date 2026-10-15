import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, rvt_elemmesh as EM, rvt_mesh as M, eval_gt as G
f,tsv=sys.argv[1:3]; eids=[int(x) for x in sys.argv[3].split(',')]; doc=EM.Doc(f); E,P=G.load_gt(tsv)
for e in eids:
    gt=[float(v) for b,nm,stg,v in P[e] if nm=='Volume' and stg=='Double' and v!=''][0]
    m=EM.element_mesh(doc,e,detail=2); v,c,a,n=M.volume_by_node(m['tris'],m['meta'],m['nid'])
    print(e,m['source'],'nodes',n,'closed',c,'vol',round(v,4),'gt',round(gt,4),'ratio',round(v/gt,4))
