import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG, rvt_mesh as M
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); o,dec=GG.load_dec(f)
ids=[i for i,r in res.items() if r['bodies'].get('Face')][:int(sys.argv[3])]
kinds=collections.Counter(); ex={}
for i in ids:
    r=GG.get_record(f,res[i],o,dec); st=[r['fields']]
    while st:
        z=st.pop()
        if isinstance(z,dict):
            if 'm_pFaces' in z:
                for fc in z['m_pFaces']:
                    ob=fc.get('obj') if isinstance(fc,dict) else None
                    if not isinstance(ob,dict): kinds['face-ref/none']+=1; continue
                    s=ob.get('m_pSurf'); s=s.get('obj',s) if isinstance(s,dict) else s
                    k=tuple(sorted(a for a,b in (s or {}).items() if b is not None and a not in('m_Envelope',))) if isinstance(s,dict) else str(type(s))
                    kinds[k]+=1; ex.setdefault(k,(i,))
            for b in z.values():
                if b is not None: st.append(b)
        elif isinstance(z,list): st.extend(z)
for k,n in kinds.most_common(): print(n,k,ex.get(k))
