import sys,collections,os
sys.path.insert(0,'.')
import rvt_inventory as I, rvt_uid, ifcguid, rvt_scan as S
f=sys.argv[1]; gt=sys.argv[2]
cls,ids,recs,st=I.inventory(f)
u=rvt_uid.unique_ids(f); own=S.owners(f); ifc={}; gcl={}
for ln in open(gt,encoding='utf-8'):
    q=ln.rstrip('\n').split('\t')
    if q[0]=='E': gcl[int(q[1])]=q[2]
    if q[0]=='P' and len(q)>5 and q[2]=='-1019000': ifc[int(q[1])]=q[5]
c=collections.Counter()
for k,v in ifc.items():
    o=own.get(k)
    if o is None: continue
    der=ifcguid.from_unique(u[k]) if k in u else None
    rc=recs[k][-1]['class'] if k in recs else None
    oc=recs[o][-1]['class'] if o in recs else None
    c[(gcl[k],rc,oc,'derived' if der==v else 'inherit' if ifc.get(o)==v else '?')]+=1
for kk,n in sorted(c.items(),key=lambda z:-z[1])[:16]: print(n,kk)
