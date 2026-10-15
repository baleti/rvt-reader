import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
geos=[]
def w(o,path):
    if isinstance(o,dict):
        if 'm_pFaces' in o: geos.append(o)
        for a,b in o.items():
            if b is not None: w(b,path+'/'+a)
    elif isinstance(o,list):
        for j,b in enumerate(o): w(b,path+'[%d]'%j)
w(r['fields'],'')
g=geos[0]
print('faces handles',[ (fc.get('handle'),fc.get('ptr')) for fc in g['m_pFaces']])
print('edges handles',[ (e.get('handle'),e.get('ptr')) for e in g['m_pEdges']])
for e in g['m_pEdges'][:3]:
    ob=e['obj']; print('edge face refs',[x.get('ref') if x else None for x in ob['m_pFace']],'next',[x.get('ref') if x else None for x in ob['m_next']],'prev',[x.get('ref') if x else None for x in ob['m_prev']])
    print('  firstlast',ob['m_firstAndLastEdgePnts'],'interior',ob['m_interiorEdgePnts'][:2] if ob['m_interiorEdgePnts'] else ob['m_interiorEdgePnts'], 'flags',ob['m_flags'])
fl=g['m_pFaces'][0]['obj']['m_pFirstLoop']; print('loop handle',fl.get('handle'),'ref next',fl['obj']['m_next'],'prev',fl['obj']['m_prev'])
