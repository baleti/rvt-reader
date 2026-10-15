import sys,os,collections,json
sys.path.insert(0,'/home/user1/rvt-research'); os.environ['RVT_GEOM']='1'
import rvt_entities as E, rvt_famparams as F, eval_gt as G
rvt,tsv=sys.argv[1:3]
x=E.extract(rvt,want_all=True); Egt,P=G.load_gt(tsv)
byid={}
for (e,c),r in x['recs'].items(): byid.setdefault(e,r)
cand=[]
for (e,c),r in x['recs'].items():
    if c!='FamilyInstance': continue
    vol=[float(v) for b,nm,stg,v in P.get(e,[]) if nm=='Volume' and stg=='Double' and v!='']
    sid=F.S_(r['fields'],'m_pInstanceInfo','m_symbolId')
    s=byid.get(int(sid)) if sid is not None else None
    if vol and s: cand.append((s['bodies'].count('Face'),e,int(sid),vol[0]))
cand.sort(); print(cand[:8])
n,e,sid,vol=[c for c in cand if c[0]>=6][0]
s=byid[sid]; print('symbol',sid,'faces',n,'inst',e,'GT vol',vol)
def walk(o,p,d,seen):
    if d>6: return
    if isinstance(o,dict):
        for k,v in o.items():
            if v is None or k in('handle','ptr'): continue
            if isinstance(v,(dict,list)): print('  '*d+k+':'); walk(v,p+'.'+k,d+1,seen)
            else: print('  '*d+k+' = '+str(v)[:60])
    elif isinstance(o,list):
        if o and all(isinstance(a,(int,float)) for a in o): print('  '*d+str(o)[:100]); return
        for i,a in enumerate(o[:3]): print('  '*d+'[%d]'%i); walk(a,p,d+1,seen)
f=s['fields']
print([k for k in f.keys()][:60])
g=f.get('m_geomSteps'); 
walk(g,'g',0,set())
