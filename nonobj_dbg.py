import sys,os,pickle,collections
sys.path.insert(0,"/home/user1/rvt-research"); os.environ['RVT_GEOM']='1'
import g103_get as GG
f=sys.argv[1]; res=pickle.load(open(sys.argv[2],'rb')); o,dec=GG.load_dec(f)
for i in [i for i,r in res.items() if r['bodies'].get('Face')][:200]:
    r=GG.get_record(f,res[i],o,dec); hm={}; non=[]
    st=[r['fields']]
    while st:
        z=st.pop()
        if isinstance(z,dict):
            if 'handle' in z and 'obj' in z and z['handle'] not in (None,0xffffffff): hm[z['handle']]=z['obj']
            if 'm_pFaces' in z:
                for fc in z['m_pFaces']:
                    if isinstance(fc,dict) and 'obj' not in fc: non.append(fc)
            for b in z.values():
                if b is not None: st.append(b)
        elif isinstance(z,list): st.extend(z)
    if non:
        print('record',i,'complete',r['complete'],'err',r['error'],'bodies Face',r['bodies'].count('Face'),'nonobj',len(non),non[:3],'defined handles with obj',len(hm))
        print('  hm contains nonobj handles?',[n['handle'] in hm for n in non[:5]])
        break
