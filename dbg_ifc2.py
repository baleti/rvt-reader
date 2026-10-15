import sys,collections,os
sys.path.insert(0,'.')
import rvt_uid, ifcguid, rvt_scan as S
f=sys.argv[1]; gt=sys.argv[2]
u=rvt_uid.unique_ids(f); own=S.owners(f); ifc={}; cl={}
for ln in open(gt,encoding='utf-8'):
    q=ln.rstrip('\n').split('\t')
    if q[0]=='E': cl[int(q[1])]=q[2]
    if q[0]=='P' and len(q)>5 and q[2]=='-1019000': ifc[int(q[1])]=q[5]
c=collections.Counter()
for k,v in ifc.items():
    o=own.get(k)
    der=ifcguid.from_unique(u[k]) if k in u else None
    c[(cl[k], o is not None, 'derived' if der==v else '', 'owner' if o is not None and ifc.get(o)==v else '')]+=1
for kk,n in sorted(c.items(),key=lambda z:-z[1])[:14]: print(n,kk)
