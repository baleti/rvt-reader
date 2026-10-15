import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_scan as S
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); o,dec=GG.load_dec(f)
cls=S.load(f)[1]; names={i+12:c['name'] for i,c in enumerate(cls)}
cnt=collections.Counter(); hm_total=0
for i in [i for i,r in res.items() if r['bodies'].get('Face')][:200]:
    r=GG.get_record(f,res[i],o,dec); hm={}; refs=[]
    st=[r['fields']]
    while st:
        z=st.pop()
        if isinstance(z,dict):
            if 'handle' in z and 'obj' in z and z['handle'] not in (None,0xffffffff): hm[z['handle']]=z['obj']
            if 'ref' in z and len(z)==1: refs.append(z['ref'])
            if 'm_pFaces' in z:
                for fc in z['m_pFaces']:
                    ob=fc.get('obj') if isinstance(fc,dict) else None
                    if isinstance(ob,dict):
                        s=ob.get('m_pSurf')
                        if isinstance(s,dict) and 'obj' not in s: cnt[('surf-noobj',names.get(s.get('ptr')),'handle' if s.get('handle') not in (None,0xffffffff) else 'nohandle')]+=1
                    elif isinstance(fc,dict): cnt[('face-nonobj',tuple(fc.keys()))]+=1
            for b in z.values():
                if b is not None: st.append(b)
        elif isinstance(z,list): st.extend(z)
print(cnt.most_common(8))
