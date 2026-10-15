import sys,os
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import numpy as np, g103_get as GG
f=sys.argv[1]; res=GG.cached_index(f); o,dec=GG.load_dec(f)
cand=sorted((r['size'],i) for i,r in res.items() if r['bodies'].get('HermiteSurf'))
print(len(cand),cand[:3]); sz,i=cand[0]; r=GG.get_record(f,res[i],o,dec)
def ob(x): return x.get('obj',x) if isinstance(x,dict) else x
def walk(z):
    if isinstance(z,dict):
        if 'm_NodeArray' in z and 'm_uParams' in z:
            print('periodic',z.get('m_periodic'),'ok',z.get('m_constructedOK'),'u',z['m_uParams'],'v',z['m_vParams'],'nodes',len(z['m_NodeArray']))
            for n in z['m_NodeArray'][:4]: print('  node',{k:str(v)[:120] for k,v in ob(n).items()})
            print('envelope',z.get('m_Envelope')); return True
        for b in z.values():
            if b is not None and walk(b): return True
    elif isinstance(z,list):
        for b in z:
            if walk(b): return True
walk(r['fields'])
