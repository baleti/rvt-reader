import sys,glob,os
sys.path.insert(0,'.')
import rvt_inventory as I, rvt_ifc, rvt_uid, ifcguid
f=sys.argv[1]; gt=sys.argv[2]
cls,ids,recs,st=I.inventory(f)
u=rvt_uid.unique_ids(f)
ifc={}
for ln in open(gt,encoding='utf-8'):
    q=ln.rstrip('\n').split('\t')
    if q[0]=='P' and len(q)>5 and q[2]=='-1019000': ifc[int(q[1])]=q[5]
n=0
for k,v in ifc.items():
    rl=recs.get(k,[])
    ss=[]
    for r in rl:
        s=[]; rvt_ifc._walk_strings(r['fields'],s); ss.append((r['where'][0][-3:],r['where'][2],s[-1] if s else None))
    d=ifcguid.from_unique(u[k]) if k in u else None
    st_=[x[2] for x in ss if x[2]]
    if st_ and st_[-1]!=v:
        print(k,'gt',v,'derived',d,'records',ss); n+=1
        if n>=6: break
