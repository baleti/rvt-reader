import sys,collections; sys.path.insert(0,'/home/user1/rvt-research')
import rvt_elemmesh as EM, rvt_geomparams as GP, rvt_mesh as M, numpy as np
path=sys.argv[1]; doc=EM.Doc(path)
for eid in map(int,sys.argv[2:]):
    for d in (1,2,3):
        m=GP._mesh(doc,eid,d)
        if m is None: print(eid,d,None); continue
        vol,closed,area,_=M.volume_by_node(m['tris'],m.get('meta'),m['nid'],fid=m.get('fid'))
        per=collections.Counter(m['nid'])
        print(eid,'detail',d,'src',m.get('source'),'vol',round(vol,5),'closed',closed,'ntri',len(m['tris'])//1,'nodes',len(per))
        # per node volumes
        nodes=sorted(per)
        for n in nodes[:8]:
            idx=[i for i,x in enumerate(m['nid']) if x==n]
            mm={k:([v[i] for i in idx] if isinstance(v,list) and len(v)==len(m['nid']) else v) for k,v in m.items()}
            try: v2=M.volume_by_node(mm['tris'],mm.get('meta'),mm['nid'],fid=mm.get('fid'))[:2]
            except Exception as e: v2=repr(e)
            print('    node',n,per[n],v2)
