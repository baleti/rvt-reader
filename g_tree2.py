import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); i=int(sys.argv[3])
o,dec=GG.load_dec(f); r=GG.get_record(f,res[i],o,dec)
fl=r['fields']; print('id',i,{k:fl.get(k) for k in('m_gElemType','m_flags','m_bBox')})
def ob(x): return x.get('obj',x) if isinstance(x,dict) else x
def cond(c):
    c=ob(c); 
    if not isinstance(c,dict): return str(c)
    return '{'+','.join('%s=%s'%(k[2:],str(v)[:24]) for k,v in c.items() if v is not None)+'}'
def walk(n,d,label):
    n=ob(n)
    if not isinstance(n,dict): return
    kids=n.get('m_subNodes') or []
    conds=[cond(c) for c in (n.get('m_oConditions') or [])]
    keys=[k for k,v in n.items() if v is not None and k not in('m_GInfo','m_subNodes','m_oConditions','m_bIsNestedDetailFamily','handle','ptr')]
    extra=''
    if 'm_pFaces' in n: extra=' GEOMETRY faces=%d edges=%d'%(len(n['m_pFaces']),len(n.get('m_pEdges') or []))
    gi=n.get('m_GInfo') or {}
    print('  '*d+label,'keys',keys[:6],'conds',conds,'tag',gi.get('m_tag'),extra)
    for j,k in enumerate(kids): walk(k,d+1,'[%d]'%j)
walk(fl,0,'GElement')
