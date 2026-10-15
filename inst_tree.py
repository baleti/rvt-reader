import sys,os,pickle
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG, rvt_mesh as M
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec); fl=r['fields']
def ob(x): return x.get('obj',x) if isinstance(x,dict) else x
def geo_bbox(n):
    t=M.tessellate_geometry(n)
    if not t['tris']: return 'faces=%d tris=0 unsup=%s'%(len(n['m_pFaces']),sorted(set(t['unsupported'])))
    P=np.array([p for tr in t['tris'] for p in tr]); return 'faces=%d bbox %s .. %s unsup=%s'%(len(n['m_pFaces']),P.min(0).round(2),P.max(0).round(2),sorted(set(t['unsupported'])))
def walk(n,d,label):
    n=ob(n)
    if not isinstance(n,dict): return
    if 'm_pFaces' in n: print('  '*d+label,'GEOMETRY',geo_bbox(n)); return
    kids=n.get('m_subNodes') or []
    desc=[k for k in n if k in('m_instanceInfo','m_oEmbeddedSymbolGRep','m_elementId')]
    gi=ob(n.get('m_GInfo')) or {}
    print('  '*d+label,desc,'tag',gi.get('m_tag'))
    if 'm_instanceInfo' in n:
        ii=ob(n['m_instanceInfo']); t=ii.get('m_Trf'); print('  '*d+'   Trf origin',t['m_or'],'3x3',t['m_3x3'],'symbol',ii.get('m_symbolId'))
    if n.get('m_oEmbeddedSymbolGRep'): walk(n['m_oEmbeddedSymbolGRep'],d+1,'<embedded>')
    for j,k in enumerate(kids): walk(k,d+1,'[%d]'%j)
walk(fl,0,'root')
