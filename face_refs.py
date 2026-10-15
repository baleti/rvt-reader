import sys,os,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import rvt_elemmesh as EM, rvt_mesh as M
f=sys.argv[1]; eid=int(sys.argv[2]); hh=[int(x) for x in sys.argv[3].split(',')]; doc=EM.Doc(f); rec=doc.rec(eid); geos,inst=EM._geos(rec['fields']); g=geos[0]
em=M._edge_map(g); print('edges defined',len(em),'min/max handle',min(em),max(em))
faces=[M._ob(fc) for fc in g['m_pFaces']]
for h in hh:
    fc=[x for x in g['m_pFaces'] if x.get('handle')==h][0]; fo=M._ob(fc)
    print('face',h,'keys',[k for k,v in fo.items() if v is not None],'loop',M._ob(fo['m_pFirstLoop']).get('m_next') if fo.get('m_pFirstLoop') else None)
    refs=[eh for eh,e in em.items() if any(isinstance(r,dict) and r.get('ref')==h for r in (e.get('m_pFace') or []))]
    print('   edges referencing it',refs[:10])
# all refs to handle across record
cnt=collections.Counter(); st=[rec['fields']]
while st:
    z=st.pop()
    if isinstance(z,dict):
        if 'ref' in z and len(z)==1 and z['ref'] in hh: cnt[z['ref']]+=1
        for b in z.values():
            if b is not None: st.append(b)
    elif isinstance(z,list): st.extend(z)
print('refs found anywhere',dict(cnt))
